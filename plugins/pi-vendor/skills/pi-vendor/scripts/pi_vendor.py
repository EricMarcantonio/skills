#!/usr/bin/env python3
"""pi-vendor: report drift, snapshot the pi packages, into pi-vendor-archive."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys

ARCHIVE_REPO = "EricMarcantonio/pi-vendor-archive"


def config_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("PI_CODING_AGENT_DIR", pathlib.Path.home() / "pi-config")).resolve()


def archive_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("PI_VENDOR_ARCHIVE", pathlib.Path.home() / "pi-vendor-archive")).resolve()


def load_archive_lib(archive: pathlib.Path):
    """The archive owns its manifest format; import its library."""
    lib_path = archive / "lib"
    if not (lib_path / "archive_lib.py").is_file():
        raise SystemExit(f"FAIL {lib_path}/archive_lib.py missing; is {archive} the archive clone?")
    sys.path.insert(0, str(lib_path))
    import archive_lib

    return archive_lib


def read_settings(cfg: pathlib.Path) -> tuple:
    settings = json.loads((cfg / "settings.json").read_text())
    packages = list(settings.get("packages", []))
    npm = [p.split(":", 1)[1] for p in packages if p.startswith("npm:")]
    git = [p.split(":", 1)[1] for p in packages if p.startswith("git:")]
    return packages, npm, git


def read_lockfile(cfg: pathlib.Path) -> dict:
    return json.loads((cfg / "npm" / "package-lock.json").read_text())["packages"]


def package_name(lock_path: str) -> str:
    """Lockfile keys carry no name; the last node_modules/ segment is the name."""
    return lock_path.split("node_modules/")[-1]


def git_dir(cfg: pathlib.Path, spec: str) -> pathlib.Path:
    return cfg / "git" / spec


def repo_slug(spec: str) -> str:
    return "/".join(spec.split("/")[-2:])


def git_head(directory: pathlib.Path) -> str:
    return subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def drift(cfg: pathlib.Path, archive: pathlib.Path) -> list:
    """Compare the live install against the manifest.

    Returns (kind, flavour, identifier, detail) with kind in
    missing / extra / changed. An uninitialised archive reports everything as
    missing rather than crashing, so it can bootstrap itself.
    """
    lib = load_archive_lib(archive)
    manifest_path = archive / "MANIFEST.json"
    if manifest_path.is_file():
        manifest = lib.load_manifest(manifest_path)
    else:
        manifest = {"version": lib.MANIFEST_VERSION, "items": []}
    archived_npm = {i["path"]: i for i in manifest["items"] if i["kind"] == "npm"}
    archived_git = {i["repo"]: i for i in manifest["items"] if i["kind"] == "git"}

    current_npm = {p: m for p, m in read_lockfile(cfg).items() if m.get("integrity")}
    findings = []
    for path in sorted(set(current_npm) - set(archived_npm)):
        findings.append(("missing", "npm", path, current_npm[path].get("version", "?")))
    for path in sorted(set(archived_npm) - set(current_npm)):
        findings.append(("extra", "npm", path, archived_npm[path].get("version", "?")))
    for path in sorted(set(current_npm) & set(archived_npm)):
        if current_npm[path].get("integrity") != archived_npm[path]["integrity"]:
            findings.append(
                ("changed", "npm", path, f"{archived_npm[path]['version']} -> {current_npm[path].get('version', '?')}")
            )

    # settings.json can declare an npm package that was never installed, so it never
    # reaches the lockfile; compare the declared names against the manifest's direct
    # items so a declared-but-unarchived package is reported instead of passing.
    direct_archived = {
        i.get("name") for i in manifest["items"] if i["kind"] == "npm" and i.get("direct")
    }
    for name in sorted(set(read_settings(cfg)[1]) - direct_archived):
        findings.append(("missing", "npm-settings", name, "declared in settings.json, not archived"))

    _, _, git_specs = read_settings(cfg)
    for spec in git_specs:
        directory = git_dir(cfg, spec)
        if not directory.is_dir():
            findings.append(("missing", "git", repo_slug(spec), "not installed"))
            continue
        head = git_head(directory)
        item = archived_git.get(repo_slug(spec))
        if item is None:
            findings.append(("missing", "git", repo_slug(spec), head[:7]))
        elif item["commit"] != head:
            findings.append(("changed", "git", repo_slug(spec), f"{item['commit'][:7]} -> {head[:7]}"))
    for slug in sorted(set(archived_git) - {repo_slug(s) for s in git_specs}):
        findings.append(("extra", "git", slug, archived_git[slug]["commit"][:7]))
    return findings


def cmd_status(args) -> int:
    cfg, archive = config_dir(), archive_dir()
    initialized = (archive / "MANIFEST.json").is_file()
    findings = drift(cfg, archive)
    if not findings:
        print(f"pi-vendor: archive is current for {cfg}")
        return 0
    if not initialized:
        print(f"pi-vendor: {archive} is not initialised yet")
    for kind, flavour, identifier, detail in findings:
        print(f"{kind:8} {flavour:4} {identifier} ({detail})")
    print(f"pi-vendor: {len(findings)} drift finding(s); run snapshot to refresh")
    return 3 if args.fail_on_drift else 0


def npm_cache_dir() -> pathlib.Path:
    return pathlib.Path.home() / ".npm" / "_cacache"


def ensure_archive_ready(archive: pathlib.Path) -> None:
    """Refuse to snapshot onto a dirty or behind clone."""
    if not (archive / ".git").exists():
        raise SystemExit(f"FAIL {archive} is not a git clone")
    status = subprocess.run(
        ["git", "-C", str(archive), "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if status:
        raise SystemExit(f"FAIL {archive} has uncommitted changes; commit or stash them first")
    subprocess.run(["git", "-C", str(archive), "fetch", "--quiet", "origin"], check=True)
    behind = subprocess.run(
        ["git", "-C", str(archive), "rev-list", "--count", "HEAD..@{upstream}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if behind != "0":
        raise SystemExit(f"FAIL {archive} is {behind} commit(s) behind origin; pull first")


def build_npm_items(cfg: pathlib.Path, archive: pathlib.Path, lib) -> list:
    """Copy each lockfile entry's exact published tarball out of the npm cache."""
    cache = npm_cache_dir()
    items = []
    for lock_path, meta in sorted(read_lockfile(cfg).items()):
        integrity = meta.get("integrity")
        if not integrity:
            continue
        blob = lib.cacache_path(cache, integrity)
        name = package_name(lock_path)
        version = meta.get("version", "0.0.0")
        if not blob.is_file():
            raise SystemExit(
                f"FAIL {name}@{version} is missing from the npm cache ({blob}); "
                f"run `npm cache add {name}@{version}` or "
                f"`npm pack {name}@{version} --pack-destination <archive>/vendor/npm`"
            )
        relative = pathlib.Path("vendor") / "npm" / lib.tarball_filename(name, version)
        destination = archive / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blob, destination)
        items.append(
            {
                "kind": "npm",
                "name": name,
                "version": version,
                "path": lock_path,
                "resolved": meta.get("resolved", ""),
                "integrity": integrity,
                "sha256": lib.sha256_file(destination),
                "bytes": destination.stat().st_size,
                "file": relative.as_posix(),
                "direct": name in direct_npm_names(cfg),
            }
        )
    return items


def direct_npm_names(cfg: pathlib.Path) -> set:
    _, npm, _ = read_settings(cfg)
    return {name for name in npm}


def build_git_items(cfg: pathlib.Path, archive: pathlib.Path, lib, specs: list) -> list:
    items = []
    for spec in specs:
        slug = repo_slug(spec)
        directory = git_dir(cfg, spec)
        if not directory.is_dir():
            raise SystemExit(f"FAIL {directory} is not installed; cannot bundle {slug}")
        relative = pathlib.Path("vendor") / "git" / lib.bundle_filename(slug)
        destination = archive / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "-C", str(directory), "bundle", "create", str(destination), "--all"],
            check=True,
            capture_output=True,
            text=True,
        )
        upstream = subprocess.run(
            ["git", "-C", str(directory), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        items.append(
            {
                "kind": "git",
                "repo": slug,
                "upstreamUrl": upstream,
                "commit": git_head(directory),
                "branch": subprocess.run(
                    ["git", "-C", str(directory), "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip(),
                "headSubject": subprocess.run(
                    ["git", "-C", str(directory), "log", "-1", "--format=%s"],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip(),
                "sha256": lib.sha256_file(destination),
                "bytes": destination.stat().st_size,
                "file": relative.as_posix(),
            }
        )
    return items


def write_manifest(cfg: pathlib.Path, archive: pathlib.Path, lib, items: list) -> dict:
    """Copy the lockfile pair, refuse on secrets, and write MANIFEST.json."""
    packages, _, git_specs = read_settings(cfg)
    vendor_npm = archive / "vendor" / "npm"
    vendor_npm.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copy2(cfg / "npm" / name, vendor_npm / name)
    secrets = lib.scan_for_secrets((vendor_npm / "package-lock.json").read_text())
    if secrets:
        raise SystemExit(f"FAIL copied package-lock.json looks like it carries a credential: {secrets}")
    # The lockfile pair is the only record of the resolved dependency graph, because
    # pi-config's npm/ is gitignored. Record it as manifest items so verify.sh's
    # existing generic file/size/sha256 check covers it without any change to
    # verify.py: check_item only special-cases kind == "npm", and restore's item
    # filters are kind-based too.
    lockfile_items = []
    for name in ("package.json", "package-lock.json"):
        path = vendor_npm / name
        lockfile_items.append(
            {
                "kind": "lockfile",
                "name": name,
                "file": path.relative_to(archive).as_posix(),
                "sha256": lib.sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "version": lib.MANIFEST_VERSION,
        "updatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "settingsPackages": packages,
            "lockfile": "vendor/npm/package-lock.json",
            "gitDirs": [str(git_dir(cfg, spec)) for spec in git_specs],
            "piConfigCommit": subprocess.run(
                ["git", "-C", str(cfg), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
            ).stdout.strip(),
        },
        "items": items + lockfile_items,
    }
    lib.save_manifest(archive / "MANIFEST.json", manifest)
    return manifest


def cmd_snapshot(args) -> int:
    cfg, archive = config_dir(), archive_dir()
    ensure_archive_ready(archive)
    lib = load_archive_lib(archive)

    findings = drift(cfg, archive)
    if findings and not args.allow_drift:
        for kind, flavour, identifier, detail in findings:
            print(f"{kind:8} {flavour:4} {identifier} ({detail})")
        print("pi-vendor: drift detected; re-run with --allow-drift once the above is expected")
        return 3

    _, _, git_specs = read_settings(cfg)
    items = build_npm_items(cfg, archive, lib)
    items += build_git_items(cfg, archive, lib, git_specs)
    write_manifest(cfg, archive, lib, items)

    verify = subprocess.run([str(archive / "verify.sh")], cwd=str(archive), capture_output=True, text=True)
    if verify.returncode != 0:
        raise SystemExit(f"FAIL archive verify failed:\n{verify.stdout}{verify.stderr}")

    subprocess.run(["git", "-C", str(archive), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(archive), "commit", "-q", "-m", f"chore: snapshot {len(items)} packages"],
        check=True,
    )
    subprocess.run(["git", "-C", str(archive), "push", "origin", "HEAD"], check=True)
    print(f"pi-vendor: archived {len(items)} items from {cfg}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pi-vendor archive helper")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="report drift against the archive")
    status.add_argument("--fail-on-drift", action="store_true", help="exit 3 when drift is found")
    status.set_defaults(func=cmd_status)
    snapshot = sub.add_parser("snapshot", help="refresh the archive from the live install")
    snapshot.add_argument("--allow-drift", action="store_true", help="snapshot despite reported drift")
    snapshot.set_defaults(func=cmd_snapshot)
    return parser


def main(argv: list = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

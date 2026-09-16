#!/usr/bin/env python3
"""pi-vendor: report drift, snapshot the pi packages, into pi-vendor-archive."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pi-vendor archive helper")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="report drift against the archive")
    status.add_argument("--fail-on-drift", action="store_true", help="exit 3 when drift is found")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

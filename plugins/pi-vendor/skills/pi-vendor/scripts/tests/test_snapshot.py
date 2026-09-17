from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import pi_vendor


def build_fixture(tmp: pathlib.Path) -> tuple:
    """pi-config-shaped dir with a real npm cache blob and a real git repo."""
    cfg = tmp / "pi-config"
    (cfg / "npm").mkdir(parents=True)
    (cfg / "settings.json").write_text(json.dumps({"packages": ["npm:@demo/pkg", "git:github.com/owner/repo"]}))

    blob = b"pretend published tarball"
    hexd = hashlib.sha512(blob).hexdigest()
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(blob).digest()).decode()
    cache = tmp / "npm-cache"
    blob_path = cache / "content-v2" / "sha512" / hexd[:2] / hexd[2:4] / hexd[4:]
    blob_path.parent.mkdir(parents=True)
    blob_path.write_bytes(blob)

    (cfg / "npm" / "package.json").write_text(json.dumps({"name": "pi-extensions", "private": True}))
    (cfg / "npm" / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "pi-extensions", "version": "1.0.0"},
                    "node_modules/@demo/pkg": {
                        "version": "2.5.0",
                        "resolved": "https://registry.npmjs.org/@demo/pkg/-/pkg-2.5.0.tgz",
                        "integrity": integrity,
                    },
                },
            }
        )
    )

    repo = cfg / "git" / "github.com" / "owner" / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "T"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/owner/repo"], check=True
    )
    (repo / "f.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)

    archive = tmp / "archive"
    (archive / "lib").mkdir(parents=True)
    source_lib = (
        pathlib.Path.home() / "pi-vendor-archive" / "lib" / "archive_lib.py"
    )
    assert source_lib.is_file(), "run Task 1 first: ~/pi-vendor-archive/lib/archive_lib.py must exist"
    (archive / "lib" / "archive_lib.py").write_text(source_lib.read_text())
    subprocess.run(["git", "init", "-q", str(archive)], check=True)
    subprocess.run(["git", "-C", str(archive), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(archive), "config", "user.name", "T"], check=True)
    (archive / ".keep").write_text("")
    subprocess.run(["git", "-C", str(archive), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(archive), "commit", "-q", "-m", "init"], check=True)
    return cfg, archive, cache


class SnapshotTest(unittest.TestCase):
    def test_builds_npm_items_from_cache_blob(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive, cache = build_fixture(pathlib.Path(tmp))
            lib = pi_vendor.load_archive_lib(archive)
            pi_vendor.npm_cache_dir = lambda: cache
            items = pi_vendor.build_npm_items(cfg, archive, lib)
            self.assertEqual(len(items), 1)
            item = items[0]
            self.assertEqual(item["name"], "@demo/pkg")
            self.assertEqual(item["version"], "2.5.0")
            self.assertEqual(item["file"], "vendor/npm/@demo+pkg-2.5.0.tgz")
            self.assertTrue((archive / item["file"]).is_file())
            self.assertEqual((archive / item["file"]).read_bytes(), b"pretend published tarball")

    def test_missing_cache_blob_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive, cache = build_fixture(pathlib.Path(tmp))
            lib = pi_vendor.load_archive_lib(archive)
            pi_vendor.npm_cache_dir = lambda: pathlib.Path(tmp) / "empty-cache"
            with self.assertRaises(SystemExit) as ctx:
                pi_vendor.build_npm_items(cfg, archive, lib)
            self.assertIn("@demo/pkg", str(ctx.exception))

    def test_bundles_git_repo_and_records_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive, _ = build_fixture(pathlib.Path(tmp))
            lib = pi_vendor.load_archive_lib(archive)
            items = pi_vendor.build_git_items(cfg, archive, lib, ["github.com/owner/repo"])
            self.assertEqual(len(items), 1)
            item = items[0]
            self.assertEqual(item["repo"], "owner/repo")
            self.assertEqual(item["upstreamUrl"], "https://github.com/owner/repo")
            self.assertEqual(item["file"], "vendor/git/owner+repo.bundle")
            self.assertTrue((archive / item["file"]).is_file())

    def test_write_manifest_is_loadable_and_copies_lockfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive, cache = build_fixture(pathlib.Path(tmp))
            lib = pi_vendor.load_archive_lib(archive)
            pi_vendor.npm_cache_dir = lambda: cache
            items = pi_vendor.build_npm_items(cfg, archive, lib)
            items += pi_vendor.build_git_items(cfg, archive, lib, ["github.com/owner/repo"])
            manifest = pi_vendor.write_manifest(cfg, archive, lib, items)
            self.assertEqual(manifest["version"], 1)
            self.assertEqual(
                sorted(i["kind"] for i in manifest["items"]),
                ["git", "lockfile", "lockfile", "npm"],
            )
            self.assertEqual(
                sorted(i["name"] for i in manifest["items"] if i["kind"] == "lockfile"),
                ["package-lock.json", "package.json"],
            )
            for item in manifest["items"]:
                self.assertGreater(item["bytes"], 0)
                self.assertEqual(len(item["sha256"]), 64)
            self.assertTrue((archive / "vendor" / "npm" / "package-lock.json").is_file())
            self.assertEqual(lib.load_manifest(archive / "MANIFEST.json")["items"], manifest["items"])

    def test_snapshot_refuses_dirty_archive_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive, cache = build_fixture(pathlib.Path(tmp))
            (archive / "dirty.txt").write_text("x")
            with self.assertRaises(SystemExit) as ctx:
                pi_vendor.ensure_archive_ready(archive)
            self.assertIn("uncommitted", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

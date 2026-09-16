from __future__ import annotations

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
    """A pi-config-shaped dir plus an archive clone with a two-item manifest."""
    cfg = tmp / "pi-config"
    (cfg / "npm").mkdir(parents=True)
    (cfg / "settings.json").write_text(
        json.dumps({"packages": ["npm:demo", "git:github.com/owner/repo"]})
    )
    (cfg / "npm" / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "pi-extensions", "version": "1.0.0"},
                    "node_modules/demo": {
                        "version": "1.0.0",
                        "resolved": "https://registry.npmjs.org/demo/-/demo-1.0.0.tgz",
                        "integrity": "sha512-AAAA",
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
    (repo / "f.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()

    archive = tmp / "archive"
    (archive / "lib").mkdir(parents=True)
    source_lib = pathlib.Path.home() / "pi-vendor-archive" / "lib" / "archive_lib.py"
    assert source_lib.is_file(), "run Task 1 first: ~/pi-vendor-archive/lib/archive_lib.py must exist"
    (archive / "lib" / "archive_lib.py").write_text(source_lib.read_text())
    manifest = {
        "version": 1,
        "updatedAt": "2026-09-16T00:00:00Z",
        "source": {"settingsPackages": ["npm:demo", "git:github.com/owner/repo"]},
        "items": [
            {
                "kind": "npm",
                "name": "demo",
                "version": "1.0.0",
                "path": "node_modules/demo",
                "integrity": "sha512-AAAA",
                "direct": True,
            },
            {
                "kind": "git",
                "repo": "owner/repo",
                "upstreamUrl": "https://github.com/owner/repo",
                "commit": head,
                "branch": "master",
                "headSubject": "init",
            },
        ],
    }
    (archive / "MANIFEST.json").write_text(json.dumps(manifest))
    return cfg, archive


class HelperTest(unittest.TestCase):
    def test_package_name_handles_scope_and_nesting(self):
        self.assertEqual(pi_vendor.package_name("node_modules/@scope/pkg"), "@scope/pkg")
        self.assertEqual(pi_vendor.package_name("node_modules/a/node_modules/b"), "b")

    def test_repo_slug_takes_last_two_segments(self):
        self.assertEqual(pi_vendor.repo_slug("github.com/obra/superpowers"), "obra/superpowers")

    def test_read_settings_splits_npm_and_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, _ = build_fixture(pathlib.Path(tmp))
            packages, npm, git = pi_vendor.read_settings(cfg)
            self.assertEqual(len(packages), 2)
            self.assertEqual(npm, ["demo"])
            self.assertEqual(git, ["github.com/owner/repo"])


class DriftTest(unittest.TestCase):
    def test_no_drift_on_fresh_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive = build_fixture(pathlib.Path(tmp))
            self.assertEqual(pi_vendor.drift(cfg, archive), [])

    def test_uninitialised_archive_reports_everything_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive = build_fixture(pathlib.Path(tmp))
            (archive / "MANIFEST.json").unlink()
            drift = pi_vendor.drift(cfg, archive)
            self.assertEqual(sorted(d[2] for d in drift), ["demo", "node_modules/demo", "owner/repo"])
            self.assertTrue(all(d[0] == "missing" for d in drift))

    def test_detects_new_package_in_lockfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive = build_fixture(pathlib.Path(tmp))
            lock_path = cfg / "npm" / "package-lock.json"
            lock = json.loads(lock_path.read_text())
            lock["packages"]["node_modules/extra"] = {
                "version": "9.9.9",
                "integrity": "sha512-BBBB",
            }
            lock_path.write_text(json.dumps(lock))
            drift = pi_vendor.drift(cfg, archive)
            self.assertEqual([(d[0], d[2]) for d in drift], [("missing", "node_modules/extra")])

    def test_detects_changed_npm_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive = build_fixture(pathlib.Path(tmp))
            lock_path = cfg / "npm" / "package-lock.json"
            lock = json.loads(lock_path.read_text())
            lock["packages"]["node_modules/demo"]["integrity"] = "sha512-CCCC"
            lock["packages"]["node_modules/demo"]["version"] = "1.0.1"
            lock_path.write_text(json.dumps(lock))
            drift = pi_vendor.drift(cfg, archive)
            self.assertEqual([(d[0], d[2]) for d in drift], [("changed", "node_modules/demo")])
            self.assertIn("1.0.0 -> 1.0.1", drift[0][3])

    def test_detects_advanced_git_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive = build_fixture(pathlib.Path(tmp))
            repo = cfg / "git" / "github.com" / "owner" / "repo"
            (repo / "f.txt").write_text("y\n")
            subprocess.run(["git", "-C", str(repo), "commit", "-qam", "second"], check=True)
            drift = pi_vendor.drift(cfg, archive)
            self.assertEqual([(d[0], d[2]) for d in drift], [("changed", "owner/repo")])

    def test_detects_settings_package_missing_from_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive = build_fixture(pathlib.Path(tmp))
            manifest_path = archive / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["items"] = [i for i in manifest["items"] if i["kind"] != "npm"]
            manifest_path.write_text(json.dumps(manifest))
            drift = pi_vendor.drift(cfg, archive)
            findings = [(d[0], d[2]) for d in drift if d[1] == "npm-settings"]
            self.assertEqual(findings, [("missing", "demo")])

    def test_cli_reports_drift_and_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, archive = build_fixture(pathlib.Path(tmp))
            (cfg / "npm" / "package-lock.json").write_text(
                json.dumps({"lockfileVersion": 3, "packages": {}})
            )
            env = {
                "PI_CODING_AGENT_DIR": str(cfg),
                "PI_VENDOR_ARCHIVE": str(archive),
                "PATH": "/usr/bin:/bin",
            }
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "pi_vendor.py"), "status", "--fail-on-drift"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 3)
            # An empty lockfile means the archive holds items this install no longer
            # has, so the drift vocabulary is `extra`; `missing` is covered by
            # test_detects_new_package_in_lockfile.
            self.assertIn("extra", result.stdout)
            self.assertIn("node_modules/demo", result.stdout)


if __name__ == "__main__":
    unittest.main()

---
name: pi-vendor
description: Use when the user wants to snapshot, verify, or restore the offline archive of pi packages installed by pi-config, or before/after changing pi-config's settings.json, models.json, mcp.json, extensions, agents, or prompts. Triggers on "snapshot pi packages", "archive pi", "vendor pi", "rebuild pi from scratch", "is the pi archive current".
---

# pi-vendor

Keeps `EricMarcantonio/pi-vendor-archive` (private) in sync with the packages
`pi-config` installs, so a vanished upstream package cannot make the pi setup
unrebuildable. The archive is a **separate repository with independent history** —
never merge it into `pi-config`, and never add it as a submodule or subtree.

## Locations

- config dir: `$PI_CODING_AGENT_DIR`, else `~/pi-config`
- archive clone: `$PI_VENDOR_ARCHIVE`, else `~/pi-vendor-archive`
- if the clone is missing: `gh repo clone EricMarcantonio/pi-vendor-archive ~/pi-vendor-archive`

## When to use

Before any change to `pi-config`'s `settings.json`, `models.json`, `mcp.json`,
`extensions/`, `agents/`, or `prompts/`, run `status` first and tell the user if the
archive is behind. After changing which packages are installed, run `snapshot`.

## Commands

```bash
cd <skill>/scripts

# What has drifted since the last snapshot? Exit 3 with --fail-on-drift.
python3 pi_vendor.py status [--fail-on-drift]

# Refresh the archive: copy tarballs, bundle git repos, write the manifest, verify,
# commit and push. Refuses when the clone is dirty or behind.
python3 pi_vendor.py snapshot [--allow-drift]

# Archive-side checks (no skill needed):
~/pi-vendor-archive/verify.sh [--deep]
~/pi-vendor-archive/restore.sh --into /tmp/scratch
```

`verify` and `restore` are archive-side commands, not subcommands of this skill: the skill
exposes only `status` and `snapshot`, and calls the archive's own `verify.sh` / `restore.sh`
for everything else. Recovery must not depend on this skill being installed — that is why the
archive carries those scripts itself.

## Rules

- `snapshot` copies the exact published tarballs out of npm's content-addressed
  cache, located by the lockfile's `integrity`. A tarball that is missing from the
  cache is a hard failure: report the package name, then either
  `npm cache add <name>@<version>` or `npm pack <name>@<version> --pack-destination`
  into the archive and retry. Never skip an item silently.
- `snapshot` refuses to run with a dirty archive clone, or when the clone is behind
  `origin`. Pull first; never force-push.
- `restore.sh` defaults to a throwaway `/tmp` directory. Restoring over a live config
  directory requires `--in-place` and is disaster recovery only.
- The archive must never lose `vendor/npm/package.json` and
  `vendor/npm/package-lock.json`: `npm/` is gitignored in `pi-config`, so they are the
  only record of the dependency graph.
- Scope is the 6 `settings.json` `packages` and their npm closure. The pi CLI,
  `~/blender_mcp`, `mcp_homedepot`, and `uvx freecad-mcp` are deliberately not
  archived; say so if the user asks about them.

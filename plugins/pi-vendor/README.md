# pi-vendor

Keeps `EricMarcantonio/pi-vendor-archive` (private) in sync with the packages
`pi-config` installs, so a package vanishing upstream cannot make the pi setup
unrebuildable.

## Why

`pi-config` is a thin layer over software that lives elsewhere: four npm packages and two
git repos, plus their transitive npm dependencies. `npm/` and `git/` are gitignored there,
so the config repo's history contains none of that code — not even the resolved
`package-lock.json`. Losing an upstream artifact means the setup cannot be rebuilt.

## What it does

- `status` reports drift between the live install and the archive: packages added,
  removed, version-changed, a git package that advanced to a new commit, or a package
  declared in `settings.json` but never archived.
- `snapshot` copies the exact published tarballs out of npm's content-addressed cache
  (located by the lockfile's `integrity`, so the bytes are verifiable), re-bundles the git
  packages with `git bundle --all`, rewrites `MANIFEST.json`, runs the archive's own
  `verify.sh`, and commits and pushes.
- `verify` and `restore` live in the archive repo and work without this plugin, so
  recovery never depends on the skill being installed.

## Installation

```bash
/plugin install EricMarcantonio/skills/plugins/pi-vendor
```

## The archive repo is never merged

`pi-vendor-archive` is an independent repository: no subtree, no submodule, no shared
commits. It is not a branch of `pi-config` and is never merged into it.

## Scope

Covers the six `settings.json` `packages` and their npm closure. Not covered: the pi CLI
itself, `~/blender_mcp`, `mcp_homedepot`, and `uvx freecad-mcp`.

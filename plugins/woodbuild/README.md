# woodbuild

Turns a reference structure — a product page, a photo, a drawing or a FreeCAD model —
into a buildable wood version with a cutlist, an optimised buy plan and a priced
deviations table.

## Overview

Seven steps, each owned by one skill: intake and invariants, reference-to-wood
translation, the build spec, framing derivation, sheet and board nesting, the bill of
materials, and product matching and pricing. The engine (`woodbuild-engine`) is
stdlib-only Python and ships inside this plugin; a test enforces that the skills stay
single-purpose and that no store name escapes the store plugin.

## Skills

| Skill | Job |
|-------|-----|
| `building-from-reference` | Orchestration: intake, invariants, translation, spec, verification |
| `wood-framing` | Studs, plates, corners, headers, rafters, blocking, panelisation |
| `sheet-and-board-nesting` | Kerf, offcuts, grain locking, sheet and board choice |
| `build-pricing` | The store-agnostic pricing method: judge, verify, provenance, honest `unpriced` |
| `freecad-model-to-spec` | Generic FreeCAD ingestion: envelope, openings, drift checks |
| `woodbuild-engine` | The engine itself (hidden from the model prompt) |

## Installation

```
/plugin install EricMarcantonio/skills/plugins/woodbuild
```

For pi, install the whole repo as a package (it declares `pi.skills` in `package.json`):

```
pi install git:github.com/EricMarcantonio/skills
```

Paths in the skills use `<skills-repo>` for that clone:
`<agentDir>/git/github.com/EricMarcantonio/skills/`, i.e.
`~/pi-config/git/github.com/EricMarcantonio/skills/` for a config directory at
`~/pi-config`.

## Running the engine's tests

From the repository root:

```
python3 -m unittest discover \
  -s plugins/woodbuild/skills/woodbuild-engine/scripts/tests \
  -t plugins/woodbuild/skills/woodbuild-engine/scripts
```

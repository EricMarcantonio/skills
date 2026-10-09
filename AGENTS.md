# Claude Code Skills Repo

This repository contains Claude Code plugins by Eric Marcantonio, published via the marketplace at `.claude-plugin/marketplace.json`.

## Repository Structure

```
.claude-plugin/
  marketplace.json          # Marketplace index listing all plugins
plugins/
  <plugin-name>/
    .claude-plugin/
      plugin.json           # Plugin metadata (name, version, description, tags, author)
    skills/
      <skill-name>/
        SKILL.md            # Skill definition (frontmatter + instructions)
    README.md               # Plugin documentation
package.json                # pi package manifest; declares "pi": {"skills": ["plugins/*/skills"]}
README.md                   # Repo overview and install instructions
CLAUDE.md                   # This file
```

## Adding a New Plugin

1. Create `plugins/<plugin-name>/` following the structure above
2. Write the `SKILL.md` with YAML frontmatter (`name`, `description`) and skill instructions
3. Write `plugin.json` with name, version, description, tags, and author
4. Write a `README.md` for the plugin
5. Confirm the root `package.json` still declares the pi skills glob (`"pi": {"skills": ["plugins/*/skills"]}`) so pi discovers the new plugin
6. Add an entry to `.claude-plugin/marketplace.json` under `"plugins"`
7. Add a row to the table in the root `README.md`

## Plugin Metadata (`plugin.json`)

Required fields: `name`, `version`, `description`, `tags` (array), `author` (`name` + `url`).

## Skill Frontmatter (`SKILL.md`)

Required fields:
- `name` — skill identifier
- `description` — trigger description used by Claude to decide when to invoke the skill; be specific and include example phrases

## Available Plugins

| Plugin | Purpose |
|--------|---------|
| `clean-code` | Enforces Clean Code principles when writing or reviewing code |
| `marketplace-listing` | Creates optimized Marketplace/Kijiji/Craigslist listings with researched pricing |
| `woodbuild` | Turns a reference structure into a buildable wood version: spec, framing, cutlist, nesting, BOM, priced workbook |
| `freecad` | FreeCAD authoring hygiene and reliable view capture |
| `homedepot` | Home Depot Canada sourcing and pricing for the woodbuild engine |
| `car-manual-specs` | Extracts maintenance and torque specs from car service manual PDFs |
| `create-presentation` | Builds animated, narrated video presentations with Remotion and Kokoro TTS |

<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
<!-- graft:end -->

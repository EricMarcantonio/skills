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
README.md                   # Repo overview and install instructions
CLAUDE.md                   # This file
```

## Adding a New Plugin

1. Create `plugins/<plugin-name>/` following the structure above
2. Write the `SKILL.md` with YAML frontmatter (`name`, `description`) and skill instructions
3. Write `plugin.json` with name, version, description, tags, and author
4. Write a `README.md` for the plugin
5. Add an entry to `.claude-plugin/marketplace.json` under `"plugins"`
6. Add a row to the table in the root `README.md`

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

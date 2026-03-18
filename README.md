# skills

Claude Code plugins by [Eric Marcantonio](https://github.com/EricMarcantonio).

## Installation

Install an individual plugin:

```
/plugin install EricMarcantonio/skills/plugins/<plugin-name>
```

## Available Plugins

| Plugin | Description | Install |
|--------|-------------|---------|
| [clean-code](plugins/clean-code/) | Applies Clean Code and The Art of Clean Code principles when writing, reviewing, or refactoring | `/plugin install EricMarcantonio/skills/plugins/clean-code` |

## Contributing

Contributions welcome. Each plugin lives in `plugins/<name>/` and requires:

- `.claude-plugin/plugin.json` — plugin metadata
- `README.md` — documentation
- `skills/<name>/SKILL.md` — skill definition

Add your plugin to `.claude-plugin/marketplace.json` and open a PR.

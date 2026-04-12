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
| [create-presentation](plugins/create-presentation/) | Build animated, narrated video presentations using Remotion + Kokoro TTS — no external services, outputs MP4 | `/plugin install EricMarcantonio/skills/plugins/create-presentation` |
| [marketplace-listing](plugins/marketplace-listing/) | Creates optimized Facebook Marketplace, Kijiji, and Craigslist listings with researched retail pricing and specs | `/plugin install EricMarcantonio/skills/plugins/marketplace-listing` |

## Contributing

Contributions welcome. Each plugin lives in `plugins/<name>/` and requires:

- `.claude-plugin/plugin.json` — plugin metadata
- `README.md` — documentation
- `skills/<name>/SKILL.md` — skill definition

Add your plugin to `.claude-plugin/marketplace.json` and open a PR.

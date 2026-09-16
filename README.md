# skills

Claude Code plugins by [Eric Marcantonio](https://github.com/EricMarcantonio).

## Installation

Install an individual plugin:

```
/plugin install EricMarcantonio/skills/plugins/<plugin-name>
```

For pi, install the whole repository as a package — it declares its skills in
`package.json`:

```
pi install git:github.com/EricMarcantonio/skills
```

## Available Plugins

| Plugin | Description | Install |
|--------|-------------|---------|
| [clean-code](plugins/clean-code/) | Applies Clean Code and The Art of Clean Code principles when writing, reviewing, or refactoring | `/plugin install EricMarcantonio/skills/plugins/clean-code` |
| [create-presentation](plugins/create-presentation/) | Build animated, narrated video presentations using Remotion + Kokoro TTS — no external services, outputs MP4 | `/plugin install EricMarcantonio/skills/plugins/create-presentation` |
| [marketplace-listing](plugins/marketplace-listing/) | Creates optimized Facebook Marketplace, Kijiji, and Craigslist listings with researched retail pricing and specs | `/plugin install EricMarcantonio/skills/plugins/marketplace-listing` |
| [woodbuild](plugins/woodbuild/) | Turns a reference structure into a buildable wood version: spec, framing, cutlist, nesting, BOM and a priced workbook | `/plugin install EricMarcantonio/skills/plugins/woodbuild` |
| [freecad](plugins/freecad/) | FreeCAD authoring hygiene and reliable view capture | `/plugin install EricMarcantonio/skills/plugins/freecad` |
| [homedepot](plugins/homedepot/) | Home Depot Canada sourcing and pricing for the woodbuild engine | `/plugin install EricMarcantonio/skills/plugins/homedepot` |
| [car-manual-specs](plugins/car-manual-specs/) | Extracts maintenance and torque specs from car service manual PDFs | `/plugin install EricMarcantonio/skills/plugins/car-manual-specs` |
| [pi-vendor](plugins/pi-vendor/) | Keeps a private offline archive of the packages `pi-config` installs, so a vanished upstream package cannot make the setup unrebuildable | `/plugin install EricMarcantonio/skills/plugins/pi-vendor` |

## Contributing

Contributions welcome. Each plugin lives in `plugins/<name>/` and requires:

- `.claude-plugin/plugin.json` — plugin metadata
- `README.md` — documentation
- `skills/<name>/SKILL.md` — skill definition

Add your plugin to `.claude-plugin/marketplace.json` and open a PR.

# skills

Claude Code plugins and pi skills by [Eric Marcantonio](https://github.com/EricMarcantonio).

Most of these are specific to my own projects (wood framing, FreeCAD, Home Depot pricing). If you
are a developer looking for something general-purpose, start with **clean-code**. You don't need to
install the whole repo; every method below lets you pick single plugins or skills.

## Plugins

| Plugin | Skills | What it's for | Who it's for |
|---|---|---|---|
| [clean-code](plugins/clean-code/) | `clean-code` | Clean Code and The Art of Clean Code rules for writing, reviewing and refactoring code | **Any developer** |
| [create-presentation](plugins/create-presentation/) | `create-presentation` | Animated, narrated MP4 presentations with Remotion and Kokoro TTS | Anyone presenting a project |
| [marketplace-listing](plugins/marketplace-listing/) | `marketplace-listing` | Facebook Marketplace, Kijiji and Craigslist listings with researched prices | Anyone selling things |
| [car-manual-specs](plugins/car-manual-specs/) | `car-manual-specs` | Pulls maintenance and torque specs out of a service manual PDF | Car owners |
| [woodbuild](plugins/woodbuild/) | `building-from-reference`, `wood-framing`, `sheet-and-board-nesting`, `build-pricing`, `freecad-model-to-spec`, `woodbuild-engine` | Turns a reference structure into a buildable wood version: spec, framing, cutlist, nesting and priced BOM | Wood builds |
| [freecad](plugins/freecad/) | `freecad-model-hygiene`, `freecad-render-views` | FreeCAD modelling hygiene and reliable view capture | FreeCAD users |
| [homedepot](plugins/homedepot/) | `homedepot-catalogue` | Home Depot Canada sourcing and pricing for woodbuild | woodbuild users in Canada |

## Install in Claude Code

Add the marketplace once, then install only the plugins you want:

```
/plugin marketplace add EricMarcantonio/skills
/plugin install clean-code@ericmarcantonio
```

Replace `clean-code` with any plugin name from the table. `/plugin` with no arguments opens a browser
where you can see and toggle everything in the marketplace.

## Install in pi

`pi install git:github.com/EricMarcantonio/skills` loads **every** skill in the repo. To load only
some of them, add the package to `~/.pi/agent/settings.json` in object form with a `skills` filter:

```json
{
  "packages": [
    {
      "source": "git:github.com/EricMarcantonio/skills",
      "skills": ["plugins/clean-code/skills/clean-code"]
    }
  ]
}
```

Add more paths to the list for more skills; each one is `plugins/<plugin>/skills/<skill>`. Then run
`pi update` to fetch the package.

If you already installed the whole repo, run `pi config` to switch off the skills you don't want.

## Copy a single skill by hand

Each skill is a self-contained folder with a `SKILL.md`. Copying the folder works with any agent
that reads skill folders:

```bash
git clone --depth 1 https://github.com/EricMarcantonio/skills /tmp/eric-skills
cp -r /tmp/eric-skills/plugins/clean-code/skills/clean-code ~/.claude/skills/   # Claude Code
cp -r /tmp/eric-skills/plugins/clean-code/skills/clean-code ~/.pi/agent/skills/ # pi
```

Hand-copied skills don't update themselves; repeat the copy to pick up changes.

## Contributing

Each plugin lives in `plugins/<name>/` and needs:

- `.claude-plugin/plugin.json`: plugin metadata
- `README.md`: documentation
- `skills/<name>/SKILL.md`: the skill itself

Add the plugin to `.claude-plugin/marketplace.json` and open a PR. pi picks up new skills
automatically through the `plugins/*/skills` glob in `package.json`.

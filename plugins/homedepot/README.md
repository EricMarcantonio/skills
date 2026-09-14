# homedepot

Home Depot Canada sourcing and pricing for the woodbuild engine.

## Skills

| Skill | Job |
|-------|-----|
| `homedepot-catalogue` | The store adapter the engine takes via `--adapter`, the store id and provincial tax table, availability traps, and the search terms that actually work |

## Installation

```
/plugin install EricMarcantonio/skills/plugins/homedepot
```

Use it with the `woodbuild` plugin. Without this plugin the engine still runs: prices
come from the cache only and tax reports as 0.0.

`<skills-repo>` is the root of this repository — for a pi install,
`<agentDir>/git/github.com/EricMarcantonio/skills/`.

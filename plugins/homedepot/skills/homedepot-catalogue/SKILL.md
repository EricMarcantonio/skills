---
name: homedepot-catalogue
description: Use when sourcing or pricing a build from Home Depot Canada — finding the right SKU for a stock class, resolving a per-store price, or deciding what to buy when the store does not carry the ideal material.
---

# Home Depot catalogue

The store-specific half of pricing. `build-pricing` holds the method; this skill
holds everything that names a shop.

## Adapter

`<repo>/skills/homedepot-catalogue/scripts/homedepot_adapter.py` is the only file
in the repository that names a store. It supplies the MCP tool names, the store id,
the provincial tax table and the availability labels to the engine, which knows
none of them:

```bash
E=<repo>/skills/woodbuild-engine/scripts
python3 $E/woodbuild.py \
  --spec <workspace>/spec.json --prices <workspace>/prices.json \
  --out <workspace>/out \
  --adapter <repo>/skills/homedepot-catalogue/scripts/homedepot_adapter.py
```

Without `--adapter` the engine prices from the cache only and reports tax as zero.

## MCP server

`server_path` defaults to `~/.pi/agent/mcp-servers/mcp_homedepot/dist/index.js`
(override with `HD_SERVER_PATH`). The clone is machine-local and gitignored; to
restore it:

```bash
git clone https://github.com/sstepanovvl/mcp_homedepot.git \
  ~/.pi/agent/mcp-servers/mcp_homedepot
cd ~/.pi/agent/mcp-servers/mcp_homedepot && npm install && npm run build
```

`HD_DEFAULT_STORE` is set from the spec's `pricing.store` (default 7011) by the
adapter's `env()`. The spec's store wins over the cache's.

## Tax

`TAX_RATES` covers the provinces in the adapter file. A province that is not
listed returns **0.0** — a guessed tax is worse than no tax — and the CLI prints a
note when it reports zero. Put the spec's `pricing.province` in and check the
workbook subtitle.

## What the store actually carries

See `stock-availability.md` for the availability traps and
`substitutions-hd.md` for the material lessons this store forced. The
headlines: no ground-contact 2x4 exists; bulk packs pay off only at the right
size; price availability is per SKU; and search terms decide everything
(`2x4x8 SPF stud` returns anchor bolts).

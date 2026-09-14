---
name: woodbuild-engine
description: The stdlib-only woodbuild engine — build spec to cutlist, nesting plan, bill of materials and priced workbook. Use when reading, running or extending the engine, or when another skill points here for its API.
disable-model-invocation: true
---

# woodbuild engine

The shared library behind `building-from-reference`, `wood-framing`,
`sheet-and-board-nesting`, `build-pricing` and `freecad-model-to-spec`. This is a
library that happens to ship as a skill: it is hidden from the model prompt and is
read when another skill points at it, or explicitly with
`/skill:woodbuild-engine`.

**Path coupling:** the other skills reach it as `../woodbuild-engine/scripts/...`.
That holds only while the whole `skills/` tree travels together — same repo, same
package. Do not split the tree across packages.

## Modules

| module | responsibility |
|---|---|
| `stock.py` | stock geometry: sheet sizes, board sections, sale lengths, kerf. No availability |
| `spec.py` | the spec dataclass, derived dimensions, `validate()` |
| `frame.py` | framing derivation (the rules are in `wood-framing`) |
| `optimise.py` | sheet nesting and board cutting-stock |
| `bom.py` | bill of materials and consumable amounts from geometry |
| `pricing.py` | the price cache and the candidate/verify/resolve policy |
| `adapters.py` | `StoreAdapter`, `NullAdapter`, `load_adapter` — the store seam |
| `from_model.py` | FreeCAD document → envelope and openings; the only FreeCAD importer |
| `report.py` | `budget.html`, `cutlist.csv`, `cart.csv`, `sku-qty.txt` |
| `cli.py` | the command line and the pipeline order |

The engine names **no** store, tool, store id or tax rate. Those arrive as a
`StoreAdapter`; with none, prices come from the cache only and tax is 0.0.

## Stock geometry

Moved here from the old `stock-catalogue.md` as that file is deleted: this is the
engine's own vocabulary, not a store's availability (that is
`homedepot-catalogue/stock-availability.md`). Sizes are millimetres; the names are
imperial because that is what a builder asks for at the saw.

| class | size | thick | grain | category |
|---|---|---|---|---|
| `osb_7_16` | 1219 × 2438 | 11 | – | sheets |
| `plywood_tg_18` | 1219 × 2438 | 18 | deck | sheets |
| `plywood_ext_18` | 1219 × 2438 | 18 | face | sheets |
| `smartside_grooved` | 1219 × 2438 | 11 | groove | sheets |
| `polycarbonate_6` | 610 × 1220 | 6 | – | glazing |

| class | section | sale lengths | category |
|---|---|---|---|
| `2x4` | 38 × 89 | 8 / 10 / 12 / 16 ft | lumber |
| `2x6` | 38 × 140 | 8 / 10 / 12 / 16 ft | lumber |
| `2x8` | 38 × 184 | 8 / 10 / 12 / 16 ft | lumber |
| `pt_2x4` | 38 × 89 | 8 / 10 / 12 / 16 ft | lumber |
| `pt_4x4` | 89 × 89 | 8 / 10 / 12 ft | base |

Optimiser constants: **kerf 3.0 mm** between adjacent parts and at board cut ends;
**offcuts ≥ 300 mm** reported as reusable. The rules that use them are in
`sheet-and-board-nesting`.

## Running

```bash
python3 scripts/woodbuild.py --spec <workspace>/spec.json \
  --prices <workspace>/prices.json --out <workspace>/out \
  [--adapter <repo>/skills/homedepot-catalogue/scripts/homedepot_adapter.py] \
  [--candidates | --set-price CLASS SKU --why TEXT | --fetch] \
  [--compare old-prices.json] [--server PATH] [--today YYYY-MM-DD]
```

Pipeline order matters: `frame.derive` → partition sheet/board → `optimise` →
`bom.build_bom` → `report`. Prices are resolved **before** BOM and nesting, because
board choice is cost-aware.

## Tests

```bash
cd <repo>
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests \
  -t skills/woodbuild-engine/scripts
```

`-t` is required: the tests and the package are siblings under `scripts/`, and
without the top-level dir the `woodbuild` import fails.

## Extending

- New stock class: geometry in `stock.py` **and** a category, then a test
  (`test_every_class_has_a_category` catches a miss). Missing geometry or category
  fails at import, not at build time.
- New store: a new adapter file, not an engine change.
- New project: a new spec and workspace, not an engine change.

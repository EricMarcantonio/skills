---
name: building-from-reference
description: Use when asked to rebuild an existing structure or product in wood — a shed, bench, cabinet or fence from a photo, drawing, product page or CAD model — producing a build spec, a cutlist, an optimised buy plan and a priced deviations table.
---

# Building from a reference

A reference is not a build. A moulded panel shed, a photo of a bench, or a drawing
of a cabinet contains no studs, plates, headers or fasteners — those must be
derived. Never translate a reference's parts straight into wood, and never price
anything from memory.

This skill orchestrates. Framing rules live in `wood-framing`, nesting in
`sheet-and-board-nesting`, the pricing method in `build-pricing`, the store in
`homedepot-catalogue`, and model ingestion in `freecad-model-to-spec`. The engine
they all use is `woodbuild-engine`.

## Workspace

Ask for a project slug — never guess one — and create:

```
~/Documents/woodbuild/<slug>/
├── spec.json        envelope (the fixed thing), wall/roof/floor build-ups,
│                    openings, substitutions, pricing.store/province/search, options
├── prices.json      the price cache
├── decisions.md     prose: why these invariants are what they are
└── out/             budget.html, cutlist.csv, cart.csv, sku-qty.txt,
                     candidates.json (written by the candidate pass, read by you),
                     price-deltas.txt (only with --compare)
```

The CLI writes everything it produces under `--out`; that is why `candidates.json`
lives there and not beside `spec.json`.

## Workflow

1. **Intake** — get numbers, not impressions: envelope, opening sizes and positions,
   roof pitch, and what each part is made of. A data sheet or an existing CAD model
   beats a photo; if the only source is an image, write down which dimensions you are
   guessing. For a CAD model, hand off to `freecad-model-to-spec`.
2. **Name the invariants** — which dimensions are fixed (usually the exterior
   envelope and the clear door opening) and which give (wall build-up, floor
   structure, roof build-up). State it out loud in `decisions.md`; every later
   conflict resolves against it.
3. **Translate** — for every reference material write the wood equivalent and its
   dimensional consequence, as a row in `spec.json`'s `substitutions`. Anything the
   store does not stock becomes a substitution row. Changing the diagram is expected;
   hiding it is not.
   The general rules are in `reference/substitutions.md`.
4. **Write the spec** — one `spec.json`. With a CAD model, `from_model` derives the
   envelope and the door and band openings; everything else is locked decisions you
   write down.
5. **Derive and nest** — `wood-framing` and `sheet-and-board-nesting` own those rules.
   Run the engine (below) and read the cutlist.
6. **Verify** — every part placed, no sheet overfilled, sheet count plausible, and
   the door opening still the reference's size. `spec.validate()` refuses a spec whose
   band no longer fits under the roof build-up or whose openings no longer close;
   treat a refusal as the design conflict it is.
7. **Match products, then price** — `build-pricing` for the method,
   `homedepot-catalogue` for the store. Read the deviations table *before* the
   totals, and report anything unpriced with its reason.

## Running the engine

```bash
cd ~/Documents/woodbuild/<slug>
E=<repo>/skills/woodbuild-engine/scripts
python3 $E/woodbuild.py --spec spec.json --prices prices.json --out out
python3 $E/woodbuild.py --spec spec.json --prices prices.json --out out --candidates \
  --adapter <repo>/skills/homedepot-catalogue/scripts/homedepot_adapter.py
```

The engine is stdlib-only; there is nothing to install.

## Hard rules

- **No invented prices, and no auto-accepted ones.** Unmatched stays `unpriced`.
- **No invented quantities.** Quantities come from nesting and cutting-stock.
- **Framing is derived, never copied** — see `wood-framing`.
- **Fixed dimensions stay fixed** unless the person you are building for agrees;
  thicker walls mean a smaller interior, and that must be stated in m²/m³.
- **Consumables come from connections and joints**, not from material length, and
  their coverage assumptions belong in the workbook.

# What the store actually carries

Learned the hard way, one unpriced or wrong line at a time. Prices and stock are
per SKU and per store, never per product line.

## Consumables

Screws, nails, adhesive, sealant, hinges, hasp, louvre, steel roofing and pad
material are not stock classes: `bom.consumables()` invents their keys and emits
**physical amounts** (pieces, ml). Their prices are keyed the same way in the spec's
`pricing.search` map.

## What the store does not have

- **No ground-contact rated 2x4 pressure-treated lumber.** The ground-contact range
  is 4x4 / 4x6 / 5x5 / 6x6 posts only; every 2x4 PT board is "Above Ground Use
  Only". Design so that only skids need ground contact — joists on skids and a sole
  plate on a deck are above grade, which makes above-ground PT correct there. See
  `substitutions-hd.md`.
- **Bulk packs only pay off at the right size.** Structural screws exist as 50-count
  (~$0.48/pc), 850-count (~$0.13/pc) and 2000-count; the per-piece price varies ~4x
  for the same screw.
- **Price availability is per SKU, not per product line.** Sibling roof panels from
  the same manufacturer can differ: one has a store price, another returns `null`.
  An unpriced line is the honest outcome.
- **Search terms decide everything.** `2x4x8 SPF stud` returns Power-Stud *anchor
  bolts*; `corrugated steel roof panel` returns ceiling tiles. Lead with the
  material and the dimension, drop adjectives ("corrugated", "heavy duty"), and try
  a trade name — the Canadian pressure-treated brand is **MicroPro Sienna**.

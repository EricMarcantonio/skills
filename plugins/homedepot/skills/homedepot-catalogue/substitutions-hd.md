# Store substitutions

The store-level counterpart to `building-from-reference/reference/substitutions.md`.
That file holds the general translation rules; this one holds only the material
lessons this store forces that are not already covered by `stock-availability.md`.
Add a lesson when a build teaches a general one, but never write a build's SKU,
product name or dimensions into it — a build's own substitutions are rows in its
`spec.json`, re-derivable from that build and nothing else.

## Where stock forces a redesign

- **Prefer a redesign over a silent substitution.** When the ideal material is
  unavailable, change the detail so it is not needed rather than buying the nearest
  product and assuming it will do. The store's ground-contact gap (see
  `stock-availability.md`) is the model: moving the floor detail removed the need
  for the unavailable board.

## Dimensional consequences of buying stock

- **Grooved-siding groove pitch is the supplier's, not the reference's.** A
  reference that promises a plank pitch cannot be matched exactly with a stock
  panel; the pitch becomes cosmetic. It does not move the drawing, and neither does
  a change in wall thickness — the exterior envelope is held, so a build-up change
  shows up as interior clear dimensions. What does move it is the band narrowing,
  an opening changing shape, the floor moving below the datum, or a different roof
  section.
- **A moulded reference part has no stock thickness.** A formed panel or post
  carries a wall thickness the lumber yard does not sell; the stock build-up that
  replaces it is thicker or thinner, and the difference flows into the interior
  clear dimensions. Carry that consequence into the build's substitution row
  instead of recording the reference dimension as met.

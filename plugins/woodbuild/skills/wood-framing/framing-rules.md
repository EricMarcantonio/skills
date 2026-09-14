# Framing rules

The values `woodbuild/frame.py` implements. Change the code and this file together.

## Walls

- **Studs 2x4 @ 406.4 mm o.c.**, laid out evenly: `stud_positions(length, spacing)`
  returns **n + 1** positions at pitch `span / n`, so the last stud lands exactly on
  the end. The pitch is `span / n`, *not* the nominal spacing — a part sized from
  nominal spacing will be 8 mm too long on a 2.79 m wall and 43 mm on a 2.18 m one.
- **Sole plate** PT (ground contact if it touches soil), **one top plate plus one
  bearing plate** under the rafters (2 plates total).
- **Corners are 3-stud assemblies**, 89 × 140 mm, replacing a moulded post. They
  occupy 89 mm along each wall, which is why a clerestory band narrows: 2788.92 mm
  between 45 mm posts becomes **2610.92 mm between 89 mm corners**.
- **Blocking at the roof bearing line**, one run per wall, `qty = bays`,
  `width = span / bays − 38` (the *actual* bay pitch minus a stud). Blocking is not
  optional garnish: the brief that specified it and the code that emitted nothing
  were both wrong until a review caught the gap.

## Openings

- **King studs both sides** (full height), **jack/trim studs** under the header.
- **Doubled header**, depth ≥ span ÷ 20 rounded **up** to the next stock depth
  (1.39 m door → 2x6 is enough; 3 m → 2x8). Say so if a span needs a beam.
- **Cripples** above the head down from the top plate.
- **No sill plate across a door** — a door needs a clear threshold, not a trip hazard.
- **Every opening id carries its wall** (`king_left_transom`): part ids are cutlist
  keys, and a left and right transom are different parts.

## Datums (the two rules that keep a build legal)

1. **Floor structure sits *below* the envelope datum.** 89 skid + 89 joist + 18 deck
   = 196 mm, all under the zero plane, so a reference's clear door height survives.
   The base becomes an excavation or a levelled pad, and that is a deviation.
2. **The clerestory band lives between the door head and the roof build-up.**
   Band top = wall top = `height_tall − roof_build_up`; band sill must stay ≥ the
   door head. A 2x6 rafter + deck + steel build-up (171 mm) will not fit the band;
   2x4 rafters @ 304.8 mm o.c. with a **mid-span purlin** (120 mm) will, leaving
   27 mm of strip above the doors. `spec.py` fails the run if this stops being true.

## Roof, floor, surfaces

- **Rafters 2x4 @ 304.8 mm o.c.** with a mid purlin when the build-up is capped;
  follow the fall (pent roofs fall front → back when the tall side is the door side).
- **Floor**: PT skids, PT joists @ 406.4 mm o.c., 18 mm T&G deck.
- **Panelise everything.** No part may exceed a sheet of its own stock class:
  a 2788.92 mm wall face comes off 1219 mm sheets as 3 panels, and glazing panes go
  through the same splitter. `_split_surface()` raises rather than emit something
  unplaceable.
- **Glazing** is the band height minus two rails (300 − 80 = **220 mm**), not the
  full band.

## Fasteners (connections, not length)

- Framing screws = `SCREWS_PER_BOARD_END (3) × 2 ends × number of board parts`,
  then a `CONSUMABLE_OVERBUY` factor (1.10). Deriving from total board length
  over-counts roughly 2× (it produces a screw every 100 mm of every board).
- Sheathing nails use the perimeter/field model (edge 150 mm, field 300 mm).
- Adhesive ≈ 7 m of bead per 295 ml cartridge; sealant ≈ 10 m per 300 ml. State the
  coverage assumptions in the workbook so a reader can disagree with them.
- Buy consumables in the **best value pack** (price per piece). A 50-count box of
  structural screws at $23.98 is $0.48/screw; an 850-count box at $113 is
  $0.13/screw for the same job.

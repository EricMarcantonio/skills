---
name: freecad-model-to-spec
description: Use when turning a FreeCAD model into a build spec for a wood rebuild — bounding the envelope from the model's own geometry, reading door and band cutters, re-placing an opening for a different build-up, or failing loudly when a model no longer matches its spec.
---

# FreeCAD model to build spec

Ingestion only: a model in, an envelope and openings out. No stores, no prices, no
framing policy. If the model is being *built or repaired* rather than read, that is
`freecad-model-hygiene`; if it needs screenshots, `freecad-render-views`.

`woodbuild-engine`'s `woodbuild/from_model.py` is the engine half. It names no
project: object names,
the model's own roof thickness, the roof fall and the corner width are arguments.

## Workflow

1. **Bound the envelope.** `wall_bounds(doc, wall_object="WallsOpen")` when the model
   has a wall solid, otherwise let the panel and post naming convention supply it:
   `wall_bounds(doc, panel_suffixes=("Cut",), post_prefixes=("Post",))`. An empty
   bound is a spec error, never an empty envelope.
2. **Derive the envelope.** `envelope_from_bounds(bounds, model_roof_t=80.0,
   roof_fall=200.0, tall_side="front")`. The model's wall top *is* its roof
   underside, so the product's overall height is that z plus the **model's own** roof
   thickness. The wood roof build-up is a spec decision and must not enter here —
   mixing the two is how an envelope silently grows.
3. **Read the openings.** `openings_from_cutters(doc, envelope, door_name="fw_door",
   band_name="fw_band", corner_width=..., roof_build_up=...)` reads only what a
   cutter can tell you: the door's clear size and head, and the band's size and sill.
   Transoms, louvres, headers and sills are intent, so they arrive as spec data.
4. **Re-place the band, do not clamp it.** A thicker roof build-up drops the band and
   narrower corners narrow it. If the new sill lands below the door head,
   `band_opening` raises — that is a design conflict for
   `building-from-reference` to resolve, not something to fudge.
5. **Check before trusting.** `check_envelope(spec, doc)` re-bounds the model and
   refuses a mismatch beyond 1 mm, so a moved part cannot quietly invalidate a spec.
6. **Write the spec's openings, not its decisions.** Locked decisions — wall layers,
   roof and floor build-up, store, substitutions — belong to the spec's author.

## Testing without FreeCAD

`bounds_from_shapes`, `envelope_from_bounds` and `band_opening` are pure: they take
numbers and lists, so they are testable with FreeCAD absent. Keep new logic on that
side of the line, and keep the `import FreeCAD` inside the functions that need it.

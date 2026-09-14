---
name: freecad-model-hygiene
description: Use when building parametric FreeCAD models, boolean cuts, or anything with multiple touching parts - especially when faces look doubled, joins are unreadable, or a cut silently removes nothing.
---

# FreeCAD model hygiene

Overlapping solids are why you cannot see where one part ends: two interpenetrating
parts leave doubled edges on the shared face. Worse, a cutter that only *touches* a
surface removes nothing, and FreeCAD reports success either way.

## Audit the right objects

The disjoint rule applies to **final parts only**. Tools overlap their base by
construction, so auditing every object with a shape gives guaranteed false
positives (every `Base` against its `Cut` result).

**A part is a DAG root: an object no other object references through `Base`,
`Tool` or `Shapes`.** That rule also tracks replacements automatically — when a
`Cut` is superseded, the old base stops being a root and the new result starts
being one, which a name-prefix or visibility filter silently misses.

```python
import sys; sys.path.insert(0, "/Users/eric/.pi/agent/skills/freecad-model-hygiene/scripts")
from audit import dag_roots, check_disjoint, pairwise_overlap, cut_removed_material
parts = dag_roots(doc)
print(check_disjoint(parts))        # (sum, union, overlap) - see the tolerance below
print(pairwise_overlap(parts))      # names every offending pair, worst first
```

`Base`/`Tool` are single links, not lists. **Tolerance:** exact zero is not
achievable — a correctly disjoint model reports 3e-6 to 7e-6 mm³ from OCCT
`multiFuse` round-off, so `check_disjoint` returns the overlap and you compare it
against `TOLERANCE_MM3 = 1e-3`. `pairwise_overlap`'s threshold (default 1 mm³)
hides smaller interpenetrations: lower it deliberately, and know that an empty
result means "none above the threshold", not "none".

## Prove a cut bit before building it

`cutter.Shape.common(part.Shape).Volume` tells you what a boolean will remove —
check it *before* creating the `Part::Cut`. It is also the only way to catch a
cutter that sits in **air**, which happens whenever the intended location is
already an opening (the tangent trap's quieter twin).

| Symptom | Cause | Fix |
|---|---|---|
| Cut removes nothing; volume and face count unchanged | cutter exactly **tangent** to the surface | extend the cutter 1 mm past the face (`y = -1.0`, length `depth + 1.0`) |
| Cut removes nothing, same again | cutter is entirely inside a **pre-existing opening** | check `common().Volume` first; relocate to remaining material |
| Roof cuts into a rail or post top | sloped underside against a horizontal top | size the part from the roof underside at its **far** edge, or cut a wedge |
| Louvre slats poke through the wall or roof | slats sized from the opening's nominal size, not the geometry actually cut | compute each slat's length from the cut shape at its own height |
| A part's dimension is right but it does not fit | sized from nominal spacing while the layout is even (`span / n`) | derive from the actual step; note `stud_positions` returns **n+1** positions |
| A part vanishes from the result tree | raw panel hidden, boolean result hidden too | drive visibility from a `parts` dict, never from name prefixes |

## Verification loop

1. Build the booleans.
2. `check_disjoint(dag_roots(doc))` → overlap below `TOLERANCE_MM3`.
3. `pairwise_overlap(...)` → fix each named pair, re-run until empty.
4. Only then render, export, or quote a cutlist.

## Headless vs GUI

- `freecadcmd` has **no view state at all**: every `ViewObject` is `None`, so
  visibility cannot be set or read, and a headless save keeps geometry but no
  appearance. Use headless for booleans, audits and exports; build in the GUI only
  when the file's appearance is the deliverable.
- A helper script named after a stdlib module (`inspect.py`, `json.py`) shadows it
  inside `freecadcmd` and the process then exits 0 with **no output at all**. Name
  helpers distinctively.
- `freecadcmd` runs a script with `__name__` set to the module name, not
  `"__main__"`, so a trailing `if __name__ == "__main__":` never fires — call your
  entry point explicitly.

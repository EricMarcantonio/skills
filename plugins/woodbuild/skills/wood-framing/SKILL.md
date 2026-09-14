---
name: wood-framing
description: Use when deriving wall, roof or floor framing for a stick-built structure — studs, plates, corners, headers, rafters, blocking, panelisation or datums — or when a framing count, header depth or part length needs to be justified.
---

# Wood framing

The rules `woodbuild/frame.py` implements, in `framing-rules.md`. **Change the code
and that file together** — a rule that lives only in prose does not get built.

Read it for: stud layout as `span / n` (not the nominal spacing), three-stud
corners, doubled headers sized at span ÷ 20 rounded up to the next stock depth,
cripples over a head, no sill across a door, blocking at the roof bearing line,
and part ids that carry their wall.

## Running the derivation

```bash
cd <workspace>
E=<repo>/skills/woodbuild-engine/scripts
python3 $E/woodbuild.py --spec spec.json --prices prices.json \
  --out out            # --adapter ... for live prices; not needed to see framing
```

`frame.derive(spec)` is the entry point the CLI calls. It reads the spec and
nothing else; it never touches prices or nesting.

## What this skill does not decide

- Stock sizes and kerf — the engine's geometry catalogue.
- Whether the parts fit on the sheets and boards — `sheet-and-board-nesting`.
- What the material costs — `build-pricing`.
- The envelope and openings — `building-from-reference`.

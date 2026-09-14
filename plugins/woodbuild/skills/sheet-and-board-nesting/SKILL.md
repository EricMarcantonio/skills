---
name: sheet-and-board-nesting
description: Use when laying out sheet goods or dimensional lumber for a cutlist — shelf packing, grain locking, kerf, offcut retention, board choice or yield — or when a nesting result, sheet count or board count looks wrong.
---

# Sheet and board nesting

Turning parts into sheets and boards. The rules the optimiser implements, and what
a sane result looks like.

## Constants and policy

- **Kerf 3.0 mm** between adjacent parts and at board cut ends.
- **Offcuts ≥ 300 mm** are reported as reusable; smaller remainders are waste.
- **Grain-locked parts are never rotated.** They are reported unplaced instead, so
  a face-grained panel can never come out cross-grained.
- Sheet nesting is shelf packing, decreasing height.
- Board choice minimises cost, then waste, then the number of boards, then stock
  length. Waste counts kerfs **actually cut** (`parts − boards`, not `boards − 1`).

## Calling it

```python
from woodbuild import optimise, stock
sheet_parts = [p for p in parts if stock.is_sheet(p.stock)]
board_parts = [p for p in parts if not stock.is_sheet(p.stock)]
sheet_plans, unplaced_sheets = optimise.pack_sheets(sheet_parts)
board_plans, unplaced_boards = optimise.cut_boards(board_parts, prices=prices)
```

Each optimiser rejects a foreign stock class, so **partition first**. `NestError`
means a part cannot be placed at all; unplaced parts are a build failure, not a
warning — report them and stop.

## Hard rule

**No invented quantities.** Sheet counts and board counts come from nesting and
cutting-stock. Area ÷ sheet size is not a quantity.

## What this skill does not decide

- Which stock classes exist and how thick they are — `woodbuild-engine`'s
  `woodbuild/stock.py`.
- Why a part is that size — `wood-framing` and the build's spec.
- What a board costs — `build-pricing`.

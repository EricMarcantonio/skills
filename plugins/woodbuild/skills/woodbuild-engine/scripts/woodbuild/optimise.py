# woodbuild/optimise.py
"""Kerf-aware nesting: 2D shelf packing for sheet goods, 1D cutting-stock for boards."""

import math
from dataclasses import dataclass, field

from . import stock


class NestError(Exception):
    """Raised when a part cannot be placed on any available sheet."""


@dataclass
class Part:
    id: str
    w: float
    h: float
    qty: int = 1
    stock: str = ""
    grain_locked: bool = False
    assembly: str = ""
    note: str = ""

    def area(self):
        return self.w * self.h * self.qty

    def expanded(self):
        """One Part per physical copy, ids suffixed #n when qty > 1."""
        if self.qty == 1:
            return [self]
        out = []
        for n in range(1, self.qty + 1):
            out.append(Part(id="%s#%d" % (self.id, n), w=self.w, h=self.h, qty=1,
                            stock=self.stock, grain_locked=self.grain_locked,
                            assembly=self.assembly, note=self.note))
        return out


@dataclass
class Placement:
    part_id: str
    x: float
    y: float
    w: float
    h: float
    rotated: bool = False


@dataclass
class SheetPlan:
    stock: str
    sheets: list = field(default_factory=list)   # list[list[Placement]]

    @property
    def count(self):
        return len(self.sheets)

    @property
    def sheet_area(self):
        w, h = stock.sheet_size(self.stock)
        return w * h * self.count

    @property
    def used_area(self):
        return sum(p.w * p.h for s in self.sheets for p in s)

    def yield_pct(self):
        return 100.0 * self.used_area / self.sheet_area if self.sheet_area else 0.0

    def offcuts(self):
        """Remaining rectangles >= RETAIN_OFFCUT_MIN, one per shelf remainder."""
        out = []
        w_sheet, h_sheet = stock.sheet_size(self.stock)
        for sheet in self.sheets:
            shelf_y = 0.0
            for p in sorted(sheet, key=lambda q: q.y):
                if p.y > shelf_y:
                    h = p.y - shelf_y
                    if h >= stock.RETAIN_OFFCUT_MIN:
                        out.append((w_sheet, h))
                shelf_y = max(shelf_y, p.y + p.h)
            if h_sheet - shelf_y >= stock.RETAIN_OFFCUT_MIN:
                out.append((w_sheet, h_sheet - shelf_y))
        return out


def parts_area(parts):
    return sum(p.area() for p in parts)


def _fits(part, sheet_w, sheet_h, kerf, rotated):
    w, h = (part.h, part.w) if rotated else (part.w, part.h)
    if w > sheet_w + 1e-9 or h > sheet_h + 1e-9:
        return None
    return w, h


def _orientations(part, sheet_w, sheet_h):
    opts = []
    straight = _fits(part, sheet_w, sheet_h, stock.KERF, False)
    if straight:
        opts.append((False, straight))
    if not part.grain_locked:
        rot = _fits(part, sheet_w, sheet_h, stock.KERF, True)
        if rot and (abs(rot[0] - part.w) > 1e-9):
            opts.append((True, rot))
    # prefer the orientation that leaves the shelf shorter, i.e. wide-and-short
    opts.sort(key=lambda o: (o[1][1], -o[1][0]))
    return opts


def pack_sheets(parts, kerf=stock.KERF):
    """Shelf packing, decreasing height. Returns (plans, unplaced_parts)."""
    todo = []
    for p in parts:
        if not p.qty:
            continue
        if not stock.is_sheet(p.stock):
            raise NestError("not a sheet stock class: %s (%s)" % (p.stock, p.id))
        todo.extend(p.expanded())

    by_class = {}
    for p in todo:
        by_class.setdefault(p.stock, []).append(p)

    plans, unplaced = [], []
    for cls in sorted(by_class):
        sheet_w, sheet_h = stock.sheet_size(cls)
        queue = sorted(by_class[cls], key=lambda p: (-max(p.w, p.h), p.id))
        plan = SheetPlan(stock=cls)
        sheet, shelf_y = [], 0.0
        shelf_h, cursor_x = 0.0, 0.0

        def new_sheet():
            nonlocal sheet, shelf_y, shelf_h, cursor_x
            if sheet:
                plan.sheets.append(sheet)
            sheet, shelf_y, shelf_h, cursor_x = [], 0.0, 0.0, 0.0

        for part in queue:
            opts = _orientations(part, sheet_w, sheet_h)
            if not opts:
                unplaced.append(part)
                continue
            placed = False
            while not placed:
                for rotated, (w, h) in opts:
                    if cursor_x + w <= sheet_w + 1e-9 and shelf_y + h <= sheet_h + 1e-9:
                        sheet.append(Placement(part.id, cursor_x, shelf_y, w, h, rotated))
                        cursor_x += w + kerf
                        shelf_h = max(shelf_h, h)
                        placed = True
                        break
                if placed:
                    break
                if shelf_y + shelf_h + kerf + min(o[1][1] for o in opts) <= sheet_h + 1e-9:
                    shelf_y += shelf_h + kerf      # open a new shelf on the same sheet
                    shelf_h, cursor_x = 0.0, 0.0
                else:
                    if not sheet:                  # nothing on this sheet: cannot fit at all
                        unplaced.append(part)
                        placed = True
                        break
                    new_sheet()
        if sheet:
            plan.sheets.append(sheet)
        if plan.sheets:
            plans.append(plan)
    return plans, unplaced


@dataclass
class BoardPlan:
    stock: str
    length_mm: float
    count: int
    cuts: list = field(default_factory=list)   # list[list[(part_id, used_mm)]]

    @property
    def purchased_mm(self):
        return self.length_mm * self.count

    @property
    def used_mm(self):
        return sum(u for c in self.cuts for _, u in c)

    def yield_pct(self):
        return 100.0 * self.used_mm / self.purchased_mm if self.purchased_mm else 0.0

    def offcuts(self):
        """Remainders >= RETAIN_OFFCUT_MIN, board by board.

        A board holding k parts is cut k-1 times, so the kerf is accounted per
        board rather than pooled across the plan.
        """
        out = []
        for row in self.cuts:
            used = sum(x for _, x in row)
            rem = self.length_mm - used - stock.KERF * max(0, len(row) - 1)
            if rem >= stock.RETAIN_OFFCUT_MIN:
                out.append(round(rem, 1))
        return out


def _ffd(lengths, stock_len, kerf):
    """First-fit-decreasing into boards of stock_len. Returns list of boards."""
    boards = []
    for ln in sorted(lengths, reverse=True):
        for board in boards:
            used = sum(x for _, x in board) + kerf * len(board)
            if used + ln <= stock_len + 1e-9:
                board.append((None, ln))
                break
        else:
            if ln > stock_len + 1e-9:
                return None
            boards.append([(None, ln)])
    return boards


def _price_for_length(prices, cls, length_mm):
    """(price, is_length_table) for one sale length.

    `prices[cls]` is either a flat per-board price entry (`{"price": 4.25, ...}`,
    which is what the real price cache holds) or a length -> price table (tests).
    A length table that omits a length means that length is not priced: the
    caller skips the candidate rather than ranking millimetres against dollars.
    """
    entry = (prices or {}).get(cls)
    if isinstance(entry, dict):
        if length_mm in entry:
            return float(entry[length_mm]), True
        if "price" in entry:
            value = entry["price"]
            return (float(value) if value is not None else None), False
        numeric = [v for k, v in entry.items() if isinstance(k, (int, float))]
        return None, bool(numeric)
    if isinstance(entry, (int, float)):
        return float(entry), False
    return None, False


def cut_boards(parts, prices=None, kerf=stock.KERF):
    """Cheapest mix of sale lengths. `prices` maps stock class -> {length_mm: price}."""
    todo, unplaced = [], []
    for p in parts:
        if not p.qty:
            continue
        if p.stock not in stock.BOARDS:
            # boards are the only 1D stock; sheets are handled by pack_sheets
            raise NestError("not a board stock class: %s (%s)" % (p.stock, p.id))
        for _ in range(p.qty):
            todo.append(p)

    by_class = {}
    for p in todo:
        by_class.setdefault(p.stock, []).append(p)

    plans = []
    for cls in sorted(by_class):
        group = by_class[cls]
        lengths = [p.w for p in group]
        candidates = []
        for stock_len in stock.board_lengths_mm(cls):
            boards = _ffd(lengths, stock_len, kerf)
            if boards is None:
                continue
            price, length_table = _price_for_length(prices, cls, stock_len)
            if length_table and price is None:
                continue                                  # unpriced length in a partial table
            if price is not None:
                cost = len(boards) * price
            else:
                cost = len(boards) * stock_len            # no prices: rank by purchased length
            # kerfs actually cut: a board holding k parts is cut k-1 times
            waste = (len(boards) * stock_len - sum(lengths)
                     - kerf * (len(lengths) - len(boards)))
            candidates.append((cost, waste, stock_len, boards))
        if not candidates:
            unplaced.extend(group)
            continue
        # cheapest total, then least waste, then fewest boards, then shortest stock
        candidates.sort(key=lambda c: (c[0], c[1], len(c[3]), c[2]))
        cost, waste, stock_len, boards = candidates[0]

        # assign real part ids to the cuts, longest first within each board
        pool = sorted(group, key=lambda p: -p.w)
        cuts = []
        for board in boards:
            row = []
            for _, used in board:
                part = pool.pop(0)
                row.append((part.id, used))
            cuts.append(row)
        plans.append(BoardPlan(stock=cls, length_mm=stock_len, count=len(boards), cuts=cuts))
    return plans, unplaced

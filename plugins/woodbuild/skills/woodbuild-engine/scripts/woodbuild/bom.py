# woodbuild/bom.py
"""Buy plan -> SKU lines, plus consumables derived from the part list."""

import math
import re
from dataclasses import dataclass

from . import stock

# ---------------------------------------------------------------------------
# Consumable coverage assumptions. Each is overridable through the spec's
# options map (same name, lower case); the values here are the defaults. They
# are printed in the workbook methodology so a reader can audit the arithmetic.
# ---------------------------------------------------------------------------
SCREWS_PER_BOARD_END = 3              # each board end lands on 2-3 screws
SHEATHING_FASTENER_EDGE_MM = 150.0    # sheathing nails on panel edges
SHEATHING_FASTENER_FIELD_MM = 300.0   # sheathing nails in the panel field
ADHESIVE_ML_PER_M_JOINT = 295.0 / 7.0  # a 295 ml cartridge lays ~7 m of bead
SEALANT_ML_PER_M_JOINT = 300.0 / 10.0  # a 300 ml cartridge lays ~10 m of bead
CONSUMABLE_OVERBUY = 1.10             # explicit waste / breakage factor

# Classes sold only in packs, so a per-pack price must never price loose pieces.
PACK_PRICED = ("screws_3in", "nails_8d", "adhesive", "sealant")

_PACK_NUMBER = re.compile(r"(\d+(?:\.\d+)?)")


@dataclass
class BomLine:
    category: str
    stock: str
    description: str
    qty: float
    uom: str
    unit_price: float = None
    sku: str = None
    source: str = None
    note: str = ""

    def line_total(self):
        if self.unit_price is None:
            return None
        return round(self.unit_price * self.qty, 2)


def _option(spec, key, default):
    """A coverage assumption from spec.options, else the module default."""
    opts = (spec or {}).get("options", {}) or {}
    try:
        return float(opts[key])
    except (KeyError, TypeError, ValueError):
        return float(default)


def _price_for(prices, cls):
    if not prices:
        return None
    entry = prices.get(cls)
    if not entry or entry.get("price") is None:
        return None
    return entry


def _pack_size(pack):
    """Parse a matched pack label into (amount, unit) or None.

    Accepts the labels the matching pass records: "50 count", "432 pcs",
    "295 ml", "300 ml". An unparseable or absent label means unknown, and an
    unknown pack is never guessed.
    """
    if not pack:
        return None
    m = _PACK_NUMBER.search(str(pack))
    if not m:
        return None
    n = float(m.group(1))
    if n <= 0:
        return None
    low = str(pack).lower()
    if "ml" in low:
        return (n, "ml")
    if any(w in low for w in ("count", "pcs", "pc", "piece", "each", "qty", "pack")):
        return (n, "count")
    return None


def _apply_pack(line, prices):
    """Convert a physical consumable line to packs using the matched pack size.

    A cache price is a price per pack, so it may only ever price a pack. With a
    known pack, pieces/ml become packs. Without one the line stays in its
    physical unit and unpriced: never guess a pack, never price pieces as packs.
    """
    if line.stock not in PACK_PRICED:
        return line
    entry = (prices or {}).get(line.stock) or {}
    pack = _pack_size(entry.get("pack"))
    if pack is None:
        line.unit_price = None
        line.note = _join(line.note, "pack size unknown - not priced "
                          "(a per-pack price cannot price loose pieces)")
        return line
    n, unit = pack
    want = "ml" if line.uom == "ml" else "count" if line.uom == "each" else line.uom
    if unit != want:
        line.unit_price = None
        line.note = _join(line.note, "pack unit %r does not match line unit %r - not "
                          "priced" % (unit, line.uom))
        return line
    packs = int(math.ceil(line.qty / n))
    line.note = _join(line.note, "%d pack(s) of %g %s = %g, %g needed"
                      % (packs, n, unit, packs * n, line.qty))
    line.qty = packs
    line.uom = "pack"
    return line


def _join(note, extra):
    return "%s; %s" % (note, extra) if note else extra


def build_bom(parts, sheet_plans, board_plans, prices=None, spec=None):
    lines = []
    for plan in sheet_plans:
        entry = _price_for(prices, plan.stock)
        lines.append(BomLine(
            category=stock.category(plan.stock), stock=plan.stock,
            description=stock.label(plan.stock), qty=plan.count,
            uom=stock.unit_label(plan.stock),
            unit_price=(entry or {}).get("price"), sku=(entry or {}).get("sku"),
            source=(entry or {}).get("source"),
            note="yield %.1f%%" % plan.yield_pct()))
    for plan in board_plans:
        ft = plan.length_mm / stock.FT
        entry = _price_for(prices, plan.stock)
        lines.append(BomLine(
            category=stock.category(plan.stock), stock=plan.stock,
            description="%s - %g ft" % (stock.label(plan.stock), round(ft)),
            qty=plan.count, uom=stock.unit_label(plan.stock),
            unit_price=(entry or {}).get("price"), sku=(entry or {}).get("sku"),
            source=(entry or {}).get("source"),
            note="yield %.1f%%" % plan.yield_pct()))
    if spec is not None:                     # a parts-only BOM omits the consumables
        lines.extend(consumables(spec, parts, prices=prices))
    lines = [_apply_pack(l, prices) for l in lines]
    lines.sort(key=lambda l: (l.category, l.stock, l.description))
    return lines


def consumables(spec, parts, prices=None):
    """Fasteners, adhesive and sealant derived from geometry, never guessed.

    Quantities are physical: pieces for screws and nails, millilitres for
    adhesive and sealant. `build_bom` is what enforces the pack policy: it
    converts these to packs using a matched pack size, and leaves them unpriced
    when the pack size is unknown. A raw cache price is attached here only so
    callers that ask for it can see the matched price; it is not a usable line
    total until `build_bom` has made the units agree.
    """
    board_parts = 0.0
    panel_perimeter_mm = 0.0
    for p in parts:
        if p.stock in stock.BOARDS:
            board_parts += p.qty
        if p.id.startswith(("sheathing_", "deck", "roof_deck")):
            panel_perimeter_mm += 2 * (p.w + p.h) * p.qty
    # A butt seam between two panels appears in both panels' perimeters, so the
    # unique linear joint length is about half the summed perimeter.
    joint_mm = panel_perimeter_mm / 2.0

    per_end = _option(spec, "screws_per_board_end", SCREWS_PER_BOARD_END)
    edge = _option(spec, "sheathing_fastener_edge_mm", SHEATHING_FASTENER_EDGE_MM)
    field = _option(spec, "sheathing_fastener_field_mm", SHEATHING_FASTENER_FIELD_MM)
    adh = _option(spec, "adhesive_ml_per_m_joint", ADHESIVE_ML_PER_M_JOINT)
    seal = _option(spec, "sealant_ml_per_m_joint", SEALANT_ML_PER_M_JOINT)
    overbuy = _option(spec, "consumable_overbuy", CONSUMABLE_OVERBUY)

    screws = int(math.ceil(per_end * 2 * board_parts * overbuy))
    nails = int(math.ceil((panel_perimeter_mm / edge + panel_perimeter_mm / field)
                          * overbuy))
    adhesive_ml = int(math.ceil(joint_mm / 1000.0 * adh * overbuy))
    sealant_ml = int(math.ceil(joint_mm / 1000.0 * seal * overbuy))
    waste = round((overbuy - 1.0) * 100)

    out = [
        BomLine("fasteners", "screws_3in", '3" exterior structural screws',
                screws, "each", None, None, None,
                "%d screws: %g per board end x 2 ends x %g board parts, "
                "+%d%% overbuy" % (screws, per_end, board_parts, waste)),
        BomLine("fasteners", "nails_8d", "8d galvanised sheathing nails",
                nails, "each", None, None, None,
                "%d nails from %.1f m of panel perimeter at %g/%g mm o.c. "
                "(incl. %d%% waste)"
                % (nails, panel_perimeter_mm / 1000.0, edge, field, waste)),
        BomLine("fasteners", "adhesive", "construction adhesive",
                adhesive_ml, "ml", None, None, None,
                "%d ml from %.1f m of panel joint at %.1f m per 295 ml cartridge "
                "(incl. %d%% waste)" % (adhesive_ml, joint_mm / 1000.0, 7.0, waste)),
        BomLine("finish", "sealant", "exterior sealant / caulk",
                sealant_ml, "ml", None, None, None,
                "%d ml from %.1f m of panel joint at %.1f m per 300 ml cartridge "
                "(incl. %d%% waste)" % (sealant_ml, joint_mm / 1000.0, 10.0, waste)),
        BomLine("hardware", "hinges", "shed door hinges (pair per leaf)",
                4, "each", None, None, None, "3 per leaf, 2 leaves"),
        BomLine("hardware", "hasp", "hasp and staple + cylinder lock", 1, "set"),
        BomLine("vents", "louvre_12x18", '12 x 18 in aluminium louvre',
                2, "each", None, None, None,
                "replaces the moulded triangular vent (deviation)"),
        BomLine("roof", "steel_roof", "corrugated steel roofing panel",
                1, "each", None, None, None, "cut to the pent roof span"),
        BomLine("base", "gravel", "compacted gravel / pavers for the pad",
                1, "load", None, None, None, "the reference needs level ground only"),
    ]
    for line in out:            # a consumable may have a cache entry by its class
        entry = _price_for(prices, line.stock)
        if entry:
            line.unit_price = entry.get("price")
            line.sku = entry.get("sku")
            line.source = entry.get("source")
    return out


def unpriced(lines):
    return [l for l in lines if l.unit_price is None]


def subtotal(lines):
    return round(sum(l.line_total() for l in lines if l.line_total() is not None), 2)


def totals(lines, tax_rate):
    sub = subtotal(lines)
    tax = round(sub * tax_rate, 2)
    return {"subtotal": sub, "tax": tax, "total": round(sub + tax, 2),
            "unpriced": len(unpriced(lines)),
            "lines": len(lines)}

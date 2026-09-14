# woodbuild/frame.py
"""Derive a stick-framed build from the envelope.

The reference structure supplies the surfaces and the critical dimensions; the
framing schedule is derived here, because a reference model of a moulded panel
shed contains no studs, plates, headers or rafters.
"""

import math

from . import stock
from .optimise import Part

STUD_SPACING_DEFAULT = 406.4
WALL_NAMES = ("front", "back", "left", "right")


def stud_positions(length, spacing):
    """Stud centre lines from 0 to length, closing the run with an end stud."""
    if length <= 0:
        return []
    n = max(1, int(math.ceil(length / spacing)))
    step = length / n
    return [round(i * step, 2) for i in range(n + 1)]


def header_depth_for_span(span):
    """Conventional span rule: header depth >= span/20, rounded up to stock depth."""
    need = span / 20.0
    depths = sorted({stock.board_dims(cls)[1] for cls in stock.BOARDS if cls != "pt_4x4"})
    for d in depths:
        if d >= need:
            return d
    return depths[-1]


def header_class_for_span(span):
    depth = header_depth_for_span(span)
    for cls in ("2x4", "2x6", "2x8"):
        if stock.board_dims(cls)[1] >= depth:
            return cls
    return "2x8"


def _wall_span(spec, wall):
    env = spec.envelope
    return env["width"] if wall in ("front", "back") else env["depth"]


def _split_surface(pid, w, h, cls, assembly, note, grain_locked=True):
    """Tile a surface into sheet-sized panels.

    A 2788.92 mm wall face cannot come off a 1219 mm sheet, so every surface is
    panelised before it reaches the optimiser. One Part per distinct tile size
    (qty = tile count) keeps the cutlist readable.
    """
    sw, sh = stock.sheet_size(cls)
    gap = stock.KERF
    nx = max(1, int(math.ceil(w / (sw - gap))))
    ny = max(1, int(math.ceil(h / (sh - gap))))
    tw = (w - gap * (nx - 1)) / nx
    th = (h - gap * (ny - 1)) / ny
    if tw > sw - gap or th > sh - gap:
        raise ValueError("panel %s still exceeds a %s sheet: %.1f x %.1f"
                         % (pid, cls, tw, th))
    return Part(id=pid, w=round(tw, 2), h=round(th, 2), qty=nx * ny, stock=cls,
                assembly=assembly, grain_locked=grain_locked,
                note="%s (%d x %d panels)" % (note, nx, ny))


def _wall_plates(spec, wall, parts):
    env = spec.envelope
    span = _wall_span(spec, wall)
    sole = Part(id="sole_plate_%s" % wall, w=span, h=stock.board_dims("pt_2x4")[1],
                qty=1, stock="pt_2x4", assembly="wall_%s" % wall,
                note="PT sole plate, ground contact")
    top = Part(id="top_plate_%s" % wall, w=span, h=stock.board_dims("2x4")[1],
               qty=2, stock="2x4", assembly="wall_%s" % wall,
               note="single top plate + bearing plate (sloped bearing cut on site)")
    parts.extend([sole, top])


def _wall_studs(spec, wall, parts):
    span = _wall_span(spec, wall)
    spacing = float(spec.data["wall"].get("spacing", STUD_SPACING_DEFAULT))
    studs = stud_positions(span, spacing)
    # studs stop at the roof underside, not the roof top: the 120 mm build-up is
    # rafters, deck and steel, none of which a stud spans
    parts.append(Part(id="stud_%s" % wall, w=round(spec.wall_top_front(), 2),
                      h=stock.board_dims("2x4")[1], qty=len(studs), stock="2x4",
                      assembly="wall_%s" % wall,
                      note="studs @ %.1f mm o.c." % spacing))


def _corners(spec, parts):
    for tag in ("FL", "FR", "BL", "BR"):
        parts.append(Part(id="corner_stud_" + tag, w=round(spec.wall_top_front(), 2),
                          h=stock.board_dims("2x4")[1], qty=3, stock="2x4",
                          assembly="corner_%s" % tag,
                          note="3-stud corner replacing the moulded 45x45 post"))


def _blocking(spec, wall, parts):
    """Solid blocking between studs at the roof bearing line."""
    span = _wall_span(spec, wall)
    spacing = float(spec.data["wall"].get("spacing", STUD_SPACING_DEFAULT))
    bays = max(0, len(stud_positions(span, spacing)) - 1)
    if bays:
        # studs are laid out evenly, so the bay pitch is span / bays (equivalently
        # span / n, NOT span / len(positions): stud_positions returns n + 1
        # positions). The clear bay is that pitch minus one stud's thickness; using
        # the nominal spacing instead over-lengths blocking by 8 mm on the long
        # walls and 43 mm on the side walls.
        step = span / bays
        parts.append(Part(id="blocking_%s" % wall,
                          w=round(step - stock.board_dims("2x4")[0], 2),
                          h=stock.board_dims("2x4")[1], qty=bays, stock="2x4",
                          assembly="wall_%s" % wall,
                          note="blocking at the roof bearing line"))


def _opening_frame(spec, opening, parts):
    wall = opening["wall"]
    kind = opening["kind"]
    width = float(opening["width"])
    height = float(opening["height"])
    head = float(opening["sill"]) + height
    assembly = "%s_%s" % (wall, kind)
    tall = round(spec.wall_top_front(), 2)

    header_cls = opening.get("header") or header_class_for_span(width)
    parts.append(Part(id="king_%s_%s" % (wall, kind), w=tall, h=stock.board_dims("2x4")[1],
                      qty=2, stock="2x4", assembly=assembly,
                      note="king studs both sides of the opening"))
    parts.append(Part(id="jack_%s_%s" % (wall, kind), w=height, h=stock.board_dims("2x4")[1],
                      qty=2, stock="2x4", assembly=assembly, note="jack/trim studs"))
    parts.append(Part(id="header_%s_%s" % (wall, kind), w=width,
                      h=stock.board_dims(header_cls)[1], qty=2, stock=header_cls,
                      assembly=assembly, note="doubled header, %s" % header_cls))
    cripple_len = tall - head
    if cripple_len > 50.0:
        n = max(1, int(math.ceil(width / 406.4)) - 1)
        parts.append(Part(id="cripple_%s_%s" % (wall, kind), w=round(cripple_len, 2),
                          h=stock.board_dims("2x4")[1], qty=n, stock="2x4",
                          assembly=assembly, note="cripples above the head"))
    if kind != "door":                      # a door has no sill plate to trip over
        parts.append(Part(id="sill_%s_%s" % (wall, kind), w=width, h=stock.board_dims("2x4")[1],
                          qty=1, stock="2x4", assembly=assembly, note="sill plate"))


def _glazing(spec, parts):
    band = [o for o in spec.openings("front") if o["kind"] == "band"]
    if band:
        b = band[0]
        panes = b.get("panes", [1])
        mullions = int(b.get("mullions", len(panes) - 1))
        usable = float(b["width"])
        total = float(sum(panes))
        glass_h = float(b["height"]) - 2.0 * float(spec.data.get("band_rail", 40.0))
        for i, frac in enumerate(panes, start=1):
            # panes are panelised too: a legal single-pane band is 2610.92 mm wide
            # and a polycarbonate sheet is 610 x 1220
            parts.append(_split_surface("band_pane_%d" % i,
                                        round(usable * frac / total, 2),
                                        round(glass_h, 2), "polycarbonate_6",
                                        "glazing_front",
                                        "clerestory pane %d of %d" % (i, len(panes)),
                                        grain_locked=False))
        parts.append(Part(id="band_mullion", w=round(float(b["height"]), 2),
                          h=stock.board_dims("2x4")[1], qty=mullions, stock="2x4",
                          assembly="glazing_front", note="mullions between panes"))
    for wall in ("left", "right"):
        for o in spec.openings(wall):
            if o["kind"] == "transom":
                parts.append(_split_surface("transom_pane_%s" % wall,
                                            float(o["width"]), float(o["height"]),
                                            "polycarbonate_6", "glazing_%s" % wall,
                                            "side transom glazing",
                                            grain_locked=False))


def _floor(spec, parts):
    env = spec.envelope
    f = spec.data["floor"]
    build_up = float(f["build_up"])
    clear_w = env["width"] - 2 * spec.wall_build_up()
    clear_d = env["depth"] - 2 * spec.wall_build_up()
    parts.append(Part(id="skid", w=env["depth"], h=stock.board_dims(f["skids"])[1],
                      qty=3, stock=f["skids"], assembly="floor",
                      note="PT skids below the datum (%.1f mm total build-up)" % build_up))
    spacing = float(f.get("spacing", 406.4))
    n_joists = len(stud_positions(clear_d, spacing))
    parts.append(Part(id="joist", w=clear_w, h=stock.board_dims(f["joist"])[1],
                      qty=n_joists, stock=f["joist"], assembly="floor",
                      note="PT joists @ %.1f mm o.c." % spacing))
    w, h = stock.sheet_size(f["deck"])
    parts.append(_split_surface("deck", clear_w, clear_d, f["deck"], "floor",
                                "T&G deck, %dx%d mm sheets" % (w, h)))


def _roof(spec, parts):
    env = spec.envelope
    r = spec.data["roof"]
    spacing = float(r.get("spacing", 304.8))
    n_rafters = len(stud_positions(env["depth"], spacing))
    parts.append(Part(id="rafter", w=env["depth"], h=stock.board_dims(r["rafter"])[1],
                      qty=n_rafters, stock=r["rafter"], assembly="roof",
                      note="rafters @ %.1f mm o.c., mid-span purlin" % spacing))
    parts.append(Part(id="purlin", w=env["width"], h=stock.board_dims("2x4")[1],
                      qty=1, stock="2x4", assembly="roof", note="mid-span purlin"))
    ov = r.get("overhang", {})
    w = env["width"] + 2 * float(ov.get("side", 0.0))
    d = env["depth"] + float(ov.get("front", 0.0)) + float(ov.get("back", 0.0))
    parts.append(_split_surface("roof_deck", w, d, r["deck"], "roof",
                                "OSB deck + steel covering"))


def _walls(spec, parts):
    env = spec.envelope
    for wall in WALL_NAMES:
        span = _wall_span(spec, wall)
        h = round(spec.wall_top_front(), 2)
        parts.append(_split_surface("sheathing_%s" % wall, span, h, "osb_7_16",
                                    "wall_%s" % wall, "OSB sheathing"))
        parts.append(_split_surface("siding_%s" % wall, span, h, "smartside_grooved",
                                    "wall_%s" % wall,
                                    "grooved siding laid horizontally"))
        _wall_plates(spec, wall, parts)
        _wall_studs(spec, wall, parts)
        _blocking(spec, wall, parts)


def _doors(spec, parts):
    doors = [o for o in spec.openings() if o["kind"] == "door"]
    for o in doors:
        leaf_w = float(o["width"]) / 2.0
        leaf_h = float(o["height"]) - 4.0
        parts.append(Part(id="leaf_skin", w=leaf_w, h=leaf_h, qty=2,
                          stock="plywood_ext_18", assembly="doors", grain_locked=True,
                          note="exterior plywood skin per leaf"))
        parts.append(Part(id="leaf_frame_rail", w=leaf_w, h=stock.board_dims("2x4")[1],
                          qty=4, stock="2x4", assembly="doors"))
        parts.append(Part(id="leaf_frame_stile", w=leaf_h, h=stock.board_dims("2x4")[1],
                          qty=4, stock="2x4", assembly="doors"))


def derive(spec):
    spec.validate()
    parts = []
    _walls(spec, parts)
    _corners(spec, parts)
    for o in spec.openings():
        _opening_frame(spec, o, parts)
    _glazing(spec, parts)
    _floor(spec, parts)
    _roof(spec, parts)
    _doors(spec, parts)
    return parts


def summary(parts):
    out = {}
    for p in parts:
        out[p.assembly] = out.get(p.assembly, 0) + p.qty
    return out

# woodbuild/frame.py
"""Derive a stick-framed build from the envelope.

The reference structure supplies the surfaces and the critical dimensions; the
framing schedule is derived here, because a reference model of a moulded panel
shed contains no studs, plates, headers or rafters.
"""

import math

from . import stock
from .optimise import Part
from .spec import SpecError

STUD_SPACING_DEFAULT = 406.4
WALL_NAMES = ("front", "back", "left", "right")

KIND_BY_PREFIX = (
    ("sole_plate", "sole_plate"), ("top_plate", "top_plate"), ("stud", "stud"),
    ("king", "king"), ("jack", "jack"), ("cripple", "cripple"),
    ("header", "header"), ("blocking", "blocking"), ("sill", "sill"),
    ("corner_stud", "corner"),
)


def kind_of(part_id):
    """The member class a part id belongs to: what the elevation labels it as."""
    for prefix, kind in KIND_BY_PREFIX:
        if part_id.startswith(prefix):
            return kind
    return ""


def _stud_half():
    return stock.board_dims("2x4")[0] / 2.0     # 19.0 mm


def thickness_of(cls):
    """The member's across-the-wall thickness: its drawn width when it stands up."""
    return stock.board_dims(cls)[0]


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
    sole_cls, top_cls = "pt_2x4", "2x4"
    top = spec.wall_top_front()
    parts.append(Part(id="sole_plate_%s" % wall, w=span, h=stock.board_dims(sole_cls)[1],
                      qty=1, stock=sole_cls, assembly="wall_%s" % wall,
                      note="PT sole plate, ground contact",
                      wall=wall, x=0.0, y=0.0,
                      run=round(span, 2), rise=thickness_of(sole_cls), kind="sole_plate"))
    parts.append(Part(id="top_plate_%s" % wall, w=span, h=stock.board_dims(top_cls)[1],
                      qty=2, stock=top_cls, assembly="wall_%s" % wall,
                      note="single top plate + bearing plate (sloped bearing cut on site)",
                      wall=wall, x=0.0, y=round(top - 2 * thickness_of(top_cls), 2),
                      run=round(span, 2), rise=thickness_of(top_cls), kind="top_plate"))
    PLACEMENTS["top_plate_%s" % wall] = [0.0, round(top - thickness_of(top_cls), 2)]


def placed_centres(spec, wall):
    """Centre lines of the studs actually placed on a wall.

    A stud is removed only where an opening reaches the floor (a door, sill <= 0): there
    is no stud to stand on and the opening's king and jack studs replace it. An opening
    that starts above the floor — a window, a transom, the clerestory band — keeps its
    studs, because the sill, header and cripples attach to them and the engine models no
    cripples below a sill. Removing them would leave a hole nothing fills.
    """
    span = _wall_span(spec, wall)
    spacing = float(spec.data["wall"].get("spacing", STUD_SPACING_DEFAULT))
    clear = [(spec.opening_x(o), spec.opening_x(o) + float(o["width"]))
             for o in spec.openings(wall) if float(o["sill"]) <= 0.0]
    out = [c for c in stud_positions(span, spacing)
           if not any(a <= c <= b for a, b in clear)]
    if not out:
        raise SpecError("wall %s has no studs left after its openings" % wall)
    return out


def _wall_studs(spec, wall, parts):
    centres = placed_centres(spec, wall)
    half = _stud_half()
    spacing = float(spec.data["wall"].get("spacing", STUD_SPACING_DEFAULT))
    # studs stop at the roof underside, not the roof top: the 120 mm build-up is
    # rafters, deck and steel, none of which a stud spans
    parts.append(Part(id="stud_%s" % wall, w=round(spec.wall_top_front(), 2),
                      h=stock.board_dims("2x4")[1], qty=len(centres), stock="2x4",
                      assembly="wall_%s" % wall,
                      note="studs @ %.1f mm o.c." % spacing,
                      wall=wall, x=round(centres[0] - half, 2), y=0.0,
                      run=thickness_of("2x4"), rise=round(spec.wall_top_front(), 2),
                      kind="stud"))
    PLACEMENTS["stud_%s" % wall] = [round(c - half, 2) for c in centres]


def _corners(spec, parts):
    """Corner assemblies, drawn on the wall whose run they terminate.

    A corner belongs to two walls; the wall it ends is where it has to appear, so FR/BR
    sit at the end of the front/back run and FL/BL at its start. The assembly row is
    still emitted once, so the schedule counts three studs per corner, not six.
    """
    span = spec.envelope["width"]
    for tag, wall, x in (("FL", "front", 0.0), ("BL", "back", 0.0),
                         ("FR", "front", span - 89.0), ("BR", "back", span - 89.0)):
        parts.append(Part(id="corner_stud_" + tag, w=round(spec.wall_top_front(), 2),
                          h=stock.board_dims("2x4")[1], qty=3, stock="2x4",
                          assembly="corner_%s" % tag,
                          note="3-stud corner replacing the moulded 45x45 post",
                          wall=wall, x=x, y=0.0,
                          run=89.0, rise=round(spec.wall_top_front(), 2), kind="corner"))


def _blocking(spec, wall, parts):
    centres = placed_centres(spec, wall)
    if len(centres) < 2:
        return
    half = _stud_half()
    thick = stock.board_dims("2x4")[0]
    parts.append(Part(id="blocking_%s" % wall,
                      w=round(centres[1] - centres[0] - thick, 2),
                      h=stock.board_dims("2x4")[1], qty=len(centres) - 1, stock="2x4",
                      assembly="wall_%s" % wall,
                      note="blocking at the roof bearing line",
                      wall=wall, x=round(centres[0] + half, 2),
                      y=round(spec.wall_top_front() - thickness_of("2x4"), 2),
                      run=round(centres[1] - centres[0] - thick, 2),
                      rise=thickness_of("2x4"), kind="blocking"))
    PLACEMENTS["blocking_%s" % wall] = [c + half for c in centres[:-1]]


def _opening_frame(spec, opening, parts):
    wall = opening["wall"]
    kind = opening["kind"]
    x = spec.opening_x(opening)
    width = float(opening["width"])
    height = float(opening["height"])
    sill = float(opening["sill"])
    head = sill + height
    assembly = "%s_%s" % (wall, kind)
    tall = round(spec.wall_top_front(), 2)
    thick = stock.board_dims("2x4")[0]
    header_cls = opening.get("header") or header_class_for_span(width)

    parts.append(Part(id="king_%s_%s" % (wall, kind), w=tall, h=thick, qty=2, stock="2x4",
                      assembly=assembly, note="king studs both sides of the opening",
                      wall=wall, x=round(x - thick, 2), y=0.0,
                      run=thick, rise=tall, kind="king"))
    PLACEMENTS["king_%s_%s" % (wall, kind)] = [round(x - thick, 2), round(x + width, 2)]
    parts.append(Part(id="jack_%s_%s" % (wall, kind), w=height, h=thick, qty=2, stock="2x4",
                      assembly=assembly, note="jack/trim studs",
                      wall=wall, x=x, y=sill, run=thick, rise=height, kind="jack"))
    PLACEMENTS["jack_%s_%s" % (wall, kind)] = [x, round(x + width - thick, 2)]
    parts.append(Part(id="header_%s_%s" % (wall, kind), w=width,
                      h=stock.board_dims(header_cls)[1], qty=2, stock=header_cls,
                      assembly=assembly, note="doubled header, %s" % header_cls,
                      wall=wall, x=x, y=round(head, 2),
                      run=width, rise=stock.board_dims(header_cls)[1], kind="header"))
    cripple_len = tall - head
    if cripple_len > 50.0:
        n = max(1, int(math.ceil(width / 406.4)) - 1)
        pitch = width / (n + 1.0)                    # evenly pitched across the opening
        centres = [round(x + pitch * i, 2) for i in range(1, n + 1)]
        parts.append(Part(id="cripple_%s_%s" % (wall, kind), w=round(cripple_len, 2),
                          h=thick, qty=n, stock="2x4", assembly=assembly,
                          note="cripples above the head",
                          wall=wall, x=round(centres[0] - thick / 2.0, 2),
                          y=round(head + stock.board_dims(header_cls)[1], 2),
                          run=thick, rise=round(cripple_len, 2), kind="cripple"))
        PLACEMENTS["cripple_%s_%s" % (wall, kind)] = [round(c - thick / 2.0, 2)
                                                      for c in centres]
    if kind != "door":                      # a door has no sill plate to trip over
        parts.append(Part(id="sill_%s_%s" % (wall, kind), w=width, h=thick, qty=1,
                          stock="2x4", assembly=assembly, note="sill plate",
                          wall=wall, x=x, y=sill, run=width, rise=thick, kind="sill"))


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


PLACEMENTS = {}      # part id -> [x, ...] for members that repeat along a wall


def derive(spec):
    spec.validate()
    PLACEMENTS.clear()          # cleared FIRST: the member groups below fill it
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

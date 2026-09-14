"""Stock geometry catalogue: sheet goods, dimensional lumber, kerf.

All sizes in mm. Imperial names are kept because that is what a builder asks for
at the saw. This module knows geometry, not availability: whether a store carries
a class is the store adapter's business.
"""

KERF = 3.0
FT = 304.8
RETAIN_OFFCUT_MIN = 300.0

# stock class -> geometry. "grain" marks parts that may not be rotated when nested.
SHEETS = {
    "osb_7_16":         dict(size=(1219.0, 2438.0), thick=11.0, grain=None,
                             label='7/16" OSB sheathing', unit="sheet"),
    "plywood_tg_18":    dict(size=(1219.0, 2438.0), thick=18.0, grain="deck",
                             label='3/4" T&G plywood subfloor', unit="sheet"),
    "plywood_ext_18":   dict(size=(1219.0, 2438.0), thick=18.0, grain="face",
                             label='3/4" exterior plywood', unit="sheet"),
    "smartside_grooved": dict(size=(1219.0, 2438.0), thick=11.0, grain="groove",
                             label="LP SmartSide grooved panel siding", unit="sheet"),
    "polycarbonate_6":  dict(size=(610.0, 1220.0), thick=6.0, grain=None,
                             label="6 mm polycarbonate sheet", unit="sheet"),
}

# stock class -> (thickness, width) of the board's cross-section, plus sale lengths
BOARDS = {
    "pt_2x4": dict(dims=(38.0, 89.0), lengths_ft=(8, 10, 12, 16),
                   label='2x4x8-16 PT ground contact', unit="each"),
    "2x4":    dict(dims=(38.0, 89.0), lengths_ft=(8, 10, 12, 16), label="2x4 SPF", unit="each"),
    "2x6":    dict(dims=(38.0, 140.0), lengths_ft=(8, 10, 12, 16), label="2x6 SPF", unit="each"),
    "2x8":    dict(dims=(38.0, 184.0), lengths_ft=(8, 10, 12, 16), label="2x8 SPF", unit="each"),
    "pt_4x4": dict(dims=(89.0, 89.0), lengths_ft=(8, 10, 12), label="4x4 PT skid", unit="each"),
}

CATEGORIES = {
    "osb_7_16": "sheets", "plywood_tg_18": "sheets", "plywood_ext_18": "sheets",
    "smartside_grooved": "sheets", "polycarbonate_6": "glazing",
    "pt_2x4": "lumber", "2x4": "lumber", "2x6": "lumber", "2x8": "lumber",
    "pt_4x4": "base",
}


def _rec(cls):
    if cls in SHEETS:
        return SHEETS[cls]
    if cls in BOARDS:
        return BOARDS[cls]
    raise KeyError("unknown stock class: %s" % cls)


def is_sheet(cls):
    return cls in SHEETS


def sheet_size(cls):
    return tuple(_rec(cls)["size"])


def thickness(cls):
    return float(_rec(cls)["thick"] if cls in SHEETS else _rec(cls)["dims"][0])


def board_dims(cls):
    """(thickness, width) of a board's cross-section."""
    if cls not in BOARDS:
        raise KeyError("not a board stock class: %s" % cls)
    return BOARDS[cls]["dims"]


def board_lengths_mm(cls):
    return [round(ft * FT, 1) for ft in BOARDS[cls]["lengths_ft"]]


def grain(cls):
    return _rec(cls).get("grain")


def category(cls):
    return CATEGORIES[cls]


def unit_label(cls):
    return _rec(cls)["unit"]


def label(cls):
    return _rec(cls)["label"]

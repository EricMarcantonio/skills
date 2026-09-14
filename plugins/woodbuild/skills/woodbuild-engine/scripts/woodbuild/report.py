# woodbuild/report.py
"""Workbook + CSV exports. Deviations are printed before any money."""

import csv
import html as html_mod
import os

from . import bom, stock
from .bom import totals, unpriced

CSS = """
body{background:#15161a;color:#e8e6e3;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:24px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:26px 0 8px;color:#c8b48a}
.sub{color:#8d9096;margin:0 0 18px}
table{border-collapse:collapse;width:100%;margin:6px 0 18px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid #2c2f38;vertical-align:top}
th{color:#8d9096;font-weight:500}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 6px}
.card{background:#20222a;border:1px solid #2c2f38;border-radius:10px;padding:10px 14px;min-width:150px}
.card b{display:block;font-size:19px}.card span{color:#8d9096;font-size:12px}
.bar{background:#2c2f38;border-radius:4px;height:8px;width:120px;display:inline-block}
.bar i{display:block;height:8px;border-radius:4px;background:#7f9f6a}
.warn{color:#e0b060}tr.unpriced td{color:#e0b060}
"""


def cutlist_rows(parts, sheet_plans, board_plans):
    """One row per part with its finished size and where it comes off."""
    source = {}
    for plan in sheet_plans:
        for i, sheet in enumerate(plan.sheets, start=1):
            for pl in sheet:
                base = pl.part_id.split("#")[0]
                source[base] = "%s sheet %d" % (plan.stock, i)
    for plan in board_plans:
        for i, board in enumerate(plan.cuts, start=1):
            for pid, _ in board:
                base = pid.split("#")[0]
                source[base] = "%s @ %g ft" % (plan.stock, round(plan.length_mm / stock.FT))
    rows = []
    for p in sorted(parts, key=lambda p: (p.assembly, p.id)):
        rows.append({
            "assembly": p.assembly,
            "part": p.id,
            "qty": p.qty,
            "size": "%.1f x %.1f x %.1f mm" % (p.w, p.h, stock.thickness(p.stock)),
            "stock": p.stock,
            "grain": "locked" if p.grain_locked else "free",
            "source": source.get(p.id, "consumable / uncut"),
            "note": p.note,
        })
    return rows


def _num(v, dash="unpriced"):
    return dash if v is None else "%.2f" % v


def _provenance(line, cache, adapter=None):
    """What backs a line's price: an agent match, a raw candidate, or nothing.

    Returns (label, warn). The cache entry is authoritative: a line built from
    an agent-matched class is labelled 'agent' even if the line carries a search
    source, and a search entry with no matched_by is a candidate that still
    needs verifying. Which labels mean 'candidate' is the adapter's business.
    """
    entry = cache.get(line.stock) if cache is not None else None
    if entry and entry.get("matched_by") == "agent":
        return "agent", False
    if adapter is not None and adapter.is_candidate(line.source):
        return "candidate - verify", True
    if line.unit_price is None:
        return "unpriced", True
    return (line.source or "-"), False


def render_html(spec, parts, sheet_plans, board_plans, lines, cache, adapter=None,
                tax_rate=0.0, today=None):
    t = totals(lines, tax_rate)
    rows = cutlist_rows(parts, sheet_plans, board_plans)
    e = html_mod.escape

    out = ["<!doctype html><meta charset=utf-8>",
           "<title>Wood build budget - %s</title>" % e(spec.data.get("build", "")),
           "<style>%s</style>" % CSS,
           "<h1>%s</h1>" % e(spec.data.get("build", "build")),
           "<p class=sub>store %s &middot; %s &middot; price cache %s &middot; "
           "tax %.1f%% &middot; generated %s</p>"
           % (e(str(cache.store)), e(str(cache.data.get("storeName") or "")),
              e(str(cache.fetched)), tax_rate * 100, e(today or ""))]

    out.append("<div class=cards>")
    for label, value in (("subtotal", "$%.2f" % t["subtotal"]),
                         ("tax", "$%.2f" % t["tax"]),
                         ("total", "$%.2f" % t["total"]),
                         ("lines", str(t["lines"])),
                         ("unpriced", str(t["unpriced"]))):
        out.append("<div class=card><b>%s</b><span>%s</span></div>" % (value, label))
    out.append("</div>")
    if t["unpriced"]:
        out.append("<p class=warn>Total excludes %d unpriced line(s) - see the "
                   "unpriced section below.</p>" % t["unpriced"])

    # deviations first: read constraints before costs
    out.append("<h2>Deviations from the reference</h2>")
    out.append("<table><tr><th>Reference</th><th>Wood build</th>"
               "<th>Consequence</th><th>Diagram change</th></tr>")
    for s in spec.substitutions():
        out.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                   % (e(s.get("ref", "")), e(s.get("build", "")),
                      e(s.get("consequence", "")),
                      "yes" if s.get("changes_diagram") else "no"))
    out.append("</table>")

    out.append("<h2>Framing schedule</h2>")
    out.append("<table><tr><th>Assembly</th><th>Part</th><th class=num>Qty</th>"
               "<th>Finished size</th><th>Stock</th><th>Note</th></tr>")
    for r in rows:
        out.append("<tr><td>%s</td><td>%s</td><td class=num>%d</td><td>%s</td>"
                   "<td>%s</td><td>%s</td></tr>"
                   % (e(r["assembly"]), e(r["part"]), r["qty"], e(r["size"]),
                      e(r["stock"]), e(r["note"])))
    out.append("</table>")

    out.append("<h2>Sheet yields</h2>")
    out.append("<table><tr><th>Stock</th><th class=num>Sheets</th>"
               "<th class=num>Yield</th><th>Offcuts kept</th></tr>")
    for plan in sheet_plans:
        off = ", ".join("%.0f x %.0f" % o for o in plan.offcuts()) or "-"
        out.append("<tr><td>%s</td><td class=num>%d</td>"
                   "<td class=num>%.1f%% <span class=bar><i style='width:%.0f%%'></i>"
                   "</span></td><td>%s</td></tr>"
                   % (e(stock.label(plan.stock)), plan.count, plan.yield_pct(),
                      min(100.0, plan.yield_pct()), e(off)))
    out.append("</table>")

    out.append("<h2>Cutlist</h2>")
    out.append("<table><tr><th>Part</th><th class=num>Qty</th><th>Size</th>"
               "<th>Stock</th><th>Grain</th><th>Cut from</th></tr>")
    for r in rows:
        out.append("<tr><td>%s</td><td class=num>%d</td><td>%s</td><td>%s</td>"
                   "<td>%s</td><td>%s</td></tr>"
                   % (e(r["part"]), r["qty"], e(r["size"]), e(r["stock"]),
                      e(r["grain"]), e(r["source"])))
    out.append("</table>")

    out.append("<h2>Bill of materials</h2>")
    current = None
    for line in lines:
        if line.category != current:
            if current is not None:
                out.append("</table>")
            current = line.category
            out.append("<h3>%s</h3>" % e(current))
            out.append("<table><tr><th>Description</th><th>SKU</th>"
                       "<th class=num>Qty</th><th class=num>Unit</th>"
                       "<th class=num>Line</th><th>Source</th></tr>")
        cls_attr = "" if line.unit_price is not None else " class=unpriced"
        desc = e(line.description)
        if adapter is not None and adapter.is_candidate(line.source):
            desc += " <span class=warn>matched by description - verify SKU</span>"
        prov, warn = _provenance(line, cache, adapter)
        prov_html = ("<span class=warn>%s</span>" % e(prov)) if warn else e(prov)
        out.append("<tr%s><td>%s</td><td>%s</td><td class=num>%g %s</td>"
                   "<td class=num>%s</td><td class=num>%s</td><td>%s</td></tr>"
                   % (cls_attr, desc, e(line.sku or "-"), line.qty,
                      e(line.uom), _num(line.unit_price), _num(line.line_total()),
                      prov_html))
    if current is not None:
        out.append("</table>")

    bad = unpriced(lines)
    if bad:
        out.append("<h2>Unpriced lines</h2><table><tr><th>Item</th><th>Why</th></tr>")
        for line in bad:
            out.append("<tr class=unpriced><td>%s</td><td>%s</td></tr>"
                       % (e(line.description), e(line.note or "no price in cache")))
        out.append("</table>")

    sub = spec.substitutions()
    out.append("<h2>Methodology</h2><p class=sub>Dimensions in mm; stock is imperial. "
               "Kerf %.1f mm. Parts are placed by shelf packing; grain-locked parts "
               "are never rotated. Consumables are derived from geometry and carry an "
               "explicit %.0f%% waste factor: screws at %g per board end, "
               "sheathing nails at %g/%g mm o.c., adhesive at ~7 m per 295 ml "
               "cartridge, sealant at ~10 m per 300 ml cartridge. Pieces and "
               "millilitres are converted to packs only when the agent match records "
               "a pack size; without one the line stays unpriced. Prices come from "
               "the committed cache; a fetch refreshes only missing or stale "
               "classes. %d substitutions recorded, %d of them change the diagram.</p>"
               % (stock.KERF, (bom.CONSUMABLE_OVERBUY - 1) * 100,
                  bom.SCREWS_PER_BOARD_END,
                  bom.SHEATHING_FASTENER_EDGE_MM, bom.SHEATHING_FASTENER_FIELD_MM,
                  len(sub), sum(1 for s in sub if s.get("changes_diagram"))))
    return "\n".join(out)


def write_report(spec, parts, sheet_plans, board_plans, lines, cache, out_dir,
                 adapter=None, tax_rate=0.0, today=None):
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    paths = {"html": os.path.join(out_dir, "budget.html"),
             "cutlist": os.path.join(out_dir, "cutlist.csv"),
             "cart": os.path.join(out_dir, "cart.csv"),
             "sku_qty": os.path.join(out_dir, "sku-qty.txt")}

    with open(paths["html"], "w") as fh:
        fh.write(render_html(spec, parts, sheet_plans, board_plans, lines, cache,
                             adapter, tax_rate, today))

    rows = cutlist_rows(parts, sheet_plans, board_plans)
    with open(paths["cutlist"], "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["assembly", "part", "qty", "size", "stock",
                                          "grain", "source", "note"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    with open(paths["cart"], "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sku", "qty", "uom", "category", "description", "unit_price",
                    "line_total", "source", "note"])
        for line in sorted(lines, key=lambda l: (l.category, l.stock)):
            w.writerow([line.sku or "", line.qty, line.uom, line.category,
                        line.description, line.unit_price, line.line_total(),
                        line.source or "", line.note])

    with open(paths["sku_qty"], "w") as fh:
        for line in sorted(lines, key=lambda l: (l.category, l.stock)):
            if line.sku:
                fh.write("%s %g\n" % (line.sku, line.qty))
    return paths

import json
import os
import shutil
import tempfile
import unittest

from woodbuild.bom import BomLine, build_bom, totals, unpriced
from woodbuild.optimise import BoardPlan, Part, SheetPlan
from woodbuild.adapters import StoreAdapter
from woodbuild.pricing import PriceCache


class FakeAdapter(StoreAdapter):
    source_search = "search"
    source_product = "product"
    candidate_sources = ("search", "legacy_search")


from woodbuild.report import cutlist_rows, render_html, write_report
from woodbuild.spec import BuildSpec

SPEC = {
    "build": "unit-test",
    "envelope": {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                 "roof_fall": 200.0, "tall_side": "front"},
    "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2, "corner_width": 89.0,
             "layers_out_to_in": ["smartside_grooved", "osb_7_16", "2x4"]},
    "roof": {"rafter": "2x4", "spacing": 304.8, "deck": "osb_7_16",
             "build_up": 120.0, "overhang": {"front": 60, "back": 40, "side": 45}},
    "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
              "skids": "pt_4x4", "build_up": 196.0, "below_datum": True},
    "openings": [
        {"wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
         "sill": 0.0, "header": "2x8"},
        {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
         "sill": 1838.04, "header": None, "mullions": 4,
         "panes": [3.5, 1.5, 4.5, 4.5, 1.5]},
    ],
    "substitutions": [{"ref": "45mm moulded post", "build": "3-stud 2x4 corner",
                       "consequence": "corner trim needed", "changes_diagram": True}],
    "pricing": {"store": "7011", "province": "ON", "search": {"2x4": "2x4x8 stud"}},
    "options": {},
}


class TestReport(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.spec = BuildSpec(json.loads(json.dumps(SPEC)))
        self.parts = [Part(id="stud", w=2138.06, h=89.0, qty=12, stock="2x4",
                           assembly="wall_front")]
        self.sheets = [SheetPlan(stock="osb_7_16", sheets=[[], []])]
        self.boards = [BoardPlan(stock="2x4", length_mm=2438.4, count=6,
                                 cuts=[[("stud#1", 2138.06)]])]
        prices = {"osb_7_16": {"price": 28.98, "sku": "111", "source": "search"},
                  "2x4": {"price": 4.25, "sku": "222", "source": "search"}}
        self.lines = build_bom(self.parts, self.sheets, self.boards, prices=prices,
                              spec=self.spec.data)
        self.cache = PriceCache(os.path.join(self.out, "prices.json"))
        self.cache.data = {"store": "7011", "storeName": "ETOBICOKE SOUTH",
                           "province": "ON", "fetched": "2026-09-12",
                           "items": prices}

    def tearDown(self):
        shutil.rmtree(self.out)

    def test_writes_four_files(self):
        paths = write_report(self.spec, self.parts, self.sheets, self.boards,
                            self.lines, self.cache, self.out,
                            adapter=FakeAdapter(), tax_rate=0.13,
                            today="2026-09-12")
        for key in ("html", "cutlist", "cart", "sku_qty"):
            self.assertTrue(os.path.exists(paths[key]), key)
        self.assertEqual(os.path.basename(paths["html"]), "budget.html")
        self.assertEqual(os.path.basename(paths["cutlist"]), "cutlist.csv")
        self.assertEqual(os.path.basename(paths["cart"]), "cart.csv")
        self.assertEqual(os.path.basename(paths["sku_qty"]), "sku-qty.txt")

    def test_html_has_deviations_before_money_and_required_blocks(self):
        html = render_html(self.spec, self.parts, self.sheets, self.boards,
                          self.lines, self.cache, adapter=FakeAdapter(),
                          tax_rate=0.13, today="2026-09-12")
        self.assertLess(html.index("Deviations"), html.index("Bill of materials"))
        for needle in ("ETOBICOKE", "7011", "tax", "13.0", "Sheet yields",
                       "Framing schedule", "unpriced"):
            self.assertIn(needle, html)

    def test_totals_match_bom(self):
        html = render_html(self.spec, self.parts, self.sheets, self.boards,
                          self.lines, self.cache, adapter=FakeAdapter(),
                          tax_rate=0.13, today="2026-09-12")
        t = totals(self.lines, 0.13)
        self.assertIn("%.2f" % t["total"], html)

    def test_tax_comes_from_the_caller_not_a_module_table(self):
        html = render_html(self.spec, self.parts, self.sheets, self.boards,
                           self.lines, self.cache, adapter=FakeAdapter(),
                           tax_rate=0.05, today="2026-09-12")
        t = totals(self.lines, 0.05)
        self.assertIn("5.0%", html)
        self.assertIn("%.2f" % t["total"], html)
        self.assertNotIn("13.0%", html)

    def test_cutlist_rows_map_parts_to_sources(self):
        rows = cutlist_rows(self.parts, self.sheets, self.boards)
        self.assertEqual(rows[0]["part"], "stud")
        self.assertEqual(rows[0]["source"], "2x4 @ 8 ft")
        self.assertIn("mm", rows[0]["size"])

    def test_cart_csv_has_sku_and_qty(self):
        paths = write_report(self.spec, self.parts, self.sheets, self.boards,
                            self.lines, self.cache, self.out,
                            adapter=FakeAdapter(), tax_rate=0.13,
                            today="2026-09-12")
        text = open(paths["cart"]).read()
        self.assertIn("sku", text.splitlines()[0])
        self.assertIn("111", text)
        self.assertIn("222", text)

    def test_sku_qty_is_paste_ready(self):
        paths = write_report(self.spec, self.parts, self.sheets, self.boards,
                            self.lines, self.cache, self.out,
                            adapter=FakeAdapter(), tax_rate=0.13,
                            today="2026-09-12")
        lines = [l for l in open(paths["sku_qty"]).read().splitlines() if l.strip()]
        for line in lines:
            sku, qty = line.split()
            self.assertTrue(sku.isdigit())
            self.assertTrue(float(qty) > 0)

    def test_unpriced_lines_are_flagged_in_html(self):
        lines = self.lines + [BomLine("vents", "louvre_12x18", "12x18 louvre", 2, "each")]
        html = render_html(self.spec, self.parts, self.sheets, self.boards, lines,
                          self.cache, adapter=FakeAdapter(), tax_rate=0.13,
                          today="2026-09-12")
        # the consumables in self.lines are unpriced too, so count them honestly
        self.assertIn("excludes %d unpriced" % len(unpriced(lines)), html)
    def test_methodology_states_consumable_coverage_assumptions(self):
        html = render_html(self.spec, self.parts, self.sheets, self.boards,
                          self.lines, self.cache, adapter=FakeAdapter(),
                          tax_rate=0.13, today="2026-09-12")
        self.assertIn("295 ml cartridge", html)
        self.assertIn("300 ml cartridge", html)
        self.assertIn("waste factor", html)

    def test_description_matched_prices_are_flagged(self):
        lines = [BomLine("lumber", "2x4", "2x4 SPF", 1, "each", 4.25,
                         sku="1", source="search"),
                 BomLine("lumber", "2x6", "2x6 SPF", 1, "each", 9.98,
                         sku="2", source="product")]
        html = render_html(self.spec, self.parts, self.sheets, self.boards, lines,
                          self.cache, adapter=FakeAdapter(), tax_rate=0.13,
                          today="2026-09-12")
        self.assertEqual(html.count("matched by description - verify SKU"), 1)

    def test_bom_labels_provenance(self):
        self.cache.data["items"] = {"2x4": {"sku": "1", "price": 4.25, "source": "product",
                                            "matched_by": "agent", "matched_on": "2026-09-12",
                                            "why": "the stud"}}
        html = render_html(self.spec, self.parts, self.sheets, self.boards, self.lines,
                          self.cache, adapter=FakeAdapter(), tax_rate=0.13,
                          today="2026-09-12")
        self.assertIn("agent", html)
        candidate = [BomLine("lumber", "2x6", "2x6 SPF", 1, "each", 9.0, sku="9",
                             source="search")]
        html2 = render_html(self.spec, self.parts, self.sheets, self.boards, candidate,
                           self.cache, adapter=FakeAdapter(), tax_rate=0.13,
                           today="2026-09-12")
        self.assertIn("candidate", html2)


if __name__ == "__main__":
    unittest.main()

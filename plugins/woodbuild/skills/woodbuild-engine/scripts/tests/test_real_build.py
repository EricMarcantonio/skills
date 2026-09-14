# tests/test_real_build.py
"""End-to-end checks on the real shed build. Skips if the build data is absent."""
import os
import unittest

from woodbuild import bom, frame, optimise, pricing, stock
from woodbuild.spec import BuildSpec

BUILD_DIR = os.path.expanduser("~/Documents/woodbuild/keter-pent97")
SPEC_PATH = os.path.join(BUILD_DIR, "spec.json")
PRICES = os.path.join(BUILD_DIR, "prices.json")


@unittest.skipUnless(os.path.exists(SPEC_PATH), "shed spec not generated yet")
class TestRealBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = BuildSpec.load(SPEC_PATH)
        cls.spec.validate()
        cls.parts = frame.derive(cls.spec)
        prices = {}
        if os.path.exists(PRICES):
            # price through the real pipeline: resolve() only prices
            # agent-matched classes, so a raw items dict would bypass the policy
            prices = pricing.resolve(cls.spec, pricing.PriceCache(PRICES), transport=None)
        # each optimiser rejects foreign stock classes, so partition as the CLI does
        sheet_parts = [p for p in cls.parts if stock.is_sheet(p.stock)]
        board_parts = [p for p in cls.parts if not stock.is_sheet(p.stock)]
        cls.sheets, cls.unplaced_s = optimise.pack_sheets(sheet_parts)
        cls.boards, cls.unplaced_b = optimise.cut_boards(board_parts, prices=prices)
        cls.lines = bom.build_bom(cls.parts, cls.sheets, cls.boards, prices=prices,
                                 spec=cls.spec.data)

    def test_envelope_matches_the_product_sheet(self):
        env = self.spec.envelope
        self.assertAlmostEqual(env["width"], 2788.92, places=1)
        self.assertAlmostEqual(env["depth"], 2179.32, places=1)
        self.assertAlmostEqual(env["height_tall"], 2258.06, places=1)

    def test_door_opening_is_preserved_exactly(self):
        self.assertAlmostEqual(self.spec.door_head(), 1811.02, places=1)
        door = [o for o in self.spec.openings("front") if o["kind"] == "door"][0]
        self.assertAlmostEqual(door["width"], 1386.84, places=1)

    def test_every_part_placed(self):
        self.assertEqual(self.unplaced_s, [])
        self.assertEqual(self.unplaced_b, [])

    def test_no_sheet_overfills(self):
        for plan in self.sheets:
            w, h = stock.sheet_size(plan.stock)
            for sheet in plan.sheets:
                for p in sheet:
                    self.assertLessEqual(p.x + p.w, w + 1e-6)
                    self.assertLessEqual(p.y + p.h, h + 1e-6)

    def test_sheet_quantity_is_plausible_for_a_9x7_shed(self):
        total = sum(p.count for p in self.sheets)
        self.assertGreaterEqual(total, 10)
        self.assertLessEqual(total, 40)

    def test_framing_counts_are_sane(self):
        studs = [p for p in self.parts if p.id == "stud_front"][0]
        # a 2.79 m wall at 406.4 mm o.c. gives 7 studs + an end stud
        self.assertGreaterEqual(studs.qty, 8)
        self.assertLessEqual(studs.qty, 10)

    def test_bom_has_every_category(self):
        cats = {l.category for l in self.lines}
        for required in ("lumber", "sheets", "glazing", "fasteners", "hardware",
                         "vents", "roof", "base", "finish"):
            self.assertIn(required, cats)

    def test_deviations_cover_the_known_gaps(self):
        refs = " ".join(s["ref"] for s in self.spec.substitutions())
        for needle in ("resin", "louvre", "corner post", "floor"):
            self.assertIn(needle, refs)

    def test_unpriced_lines_are_reported_not_guessed(self):
        bad = bom.unpriced(self.lines)
        for line in bad:
            self.assertIsNone(line.unit_price)


if __name__ == "__main__":
    unittest.main()

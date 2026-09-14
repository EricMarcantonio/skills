# tests/test_optimise_sheets.py
import unittest

from woodbuild.optimise import NestError, Part, Placement, pack_sheets, parts_area
from woodbuild import stock


def P(pid, w, h, qty=1, cls="osb_7_16", grain_locked=False):
    return Part(id=pid, w=w, h=h, qty=qty, stock=cls, grain_locked=grain_locked)


class TestSheetNesting(unittest.TestCase):
    def test_two_halves_fill_one_sheet(self):
        # 1200 + kerf + 1200 = 2403 <= 2438: two panels stack on one sheet
        plans, unplaced = pack_sheets([P("a", 1219.0, 1200.0), P("b", 1219.0, 1200.0)])
        self.assertEqual(unplaced, [])
        self.assertEqual(sum(p.count for p in plans), 1)
        self.assertEqual(len(plans[0].sheets[0]), 2)

    def test_kerf_decides_whether_the_second_row_fits(self):
        # 1218 + kerf + 1218 = 2439 > 2438: the kerf pushes the second row onto a new sheet
        plans, unplaced = pack_sheets([P("x", 1219.0, 1218.0, qty=2)])
        self.assertEqual(unplaced, [])
        self.assertEqual(sum(p.count for p in plans), 2)

    def test_two_panels_share_a_shelf_across_the_width(self):
        # 608 + 3 mm kerf + 608 = 1219 exactly, so both fit across the sheet
        plans, unplaced = pack_sheets([P("w", 608.0, 1000.0, qty=2)])
        self.assertEqual(unplaced, [])
        self.assertEqual(sum(p.count for p in plans), 1)
        self.assertEqual(len(plans[0].sheets[0]), 2)

    def test_grain_locked_parts_never_rotate_even_when_it_would_fit(self):
        # 2438 x 300 only fits a 1219 x 2438 sheet rotated, and grain locking forbids it
        plans, unplaced = pack_sheets([P("g", 2438.0, 300.0, grain_locked=True)])
        self.assertEqual(plans, [])
        self.assertEqual([p.id for p in unplaced], ["g"])

    def test_free_parts_may_rotate_to_fit(self):
        plans, unplaced = pack_sheets([P("r", 2438.0, 300.0)])
        self.assertEqual(unplaced, [])
        self.assertTrue(plans[0].sheets[0][0].rotated)
        self.assertAlmostEqual(plans[0].sheets[0][0].w, 300.0)

    def test_part_larger_than_sheet_is_reported_unplaced(self):
        plans, unplaced = pack_sheets([P("huge", 3000.0, 3000.0)])
        self.assertEqual(plans, [])
        self.assertEqual([p.id for p in unplaced], ["huge"])

    def test_no_overlaps_and_inside_sheet_bounds(self):
        parts = [P("a", 600.0, 400.0, qty=4), P("b", 1219.0, 500.0, qty=2)]
        plans, unplaced = pack_sheets(parts)
        self.assertEqual(unplaced, [])
        w_sheet, h_sheet = stock.sheet_size("osb_7_16")
        for plan in plans:
            for sheet in plan.sheets:
                for pl in sheet:
                    self.assertLessEqual(pl.x + pl.w, w_sheet + 1e-6)
                    self.assertLessEqual(pl.y + pl.h, h_sheet + 1e-6)
                for i, a in enumerate(sheet):
                    for b in sheet[i + 1:]:
                        xo = max(a.x, b.x) < min(a.x + a.w, b.x + b.w)
                        yo = max(a.y, b.y) < min(a.y + a.h, b.y + b.h)
                        self.assertFalse(xo and yo, "overlap %s/%s" % (a.part_id, b.part_id))

    def test_yield_and_area(self):
        plans, _ = pack_sheets([P("a", 1219.0, 1200.0, qty=2)])
        self.assertAlmostEqual(plans[0].yield_pct(), 98.4, places=1)
        self.assertAlmostEqual(parts_area([P("a", 100.0, 200.0, qty=3)]), 60000.0)

    def test_sheet_offcuts_keep_large_remainders(self):
        # one 600 x 600 panel leaves a 1838 mm tall strip above it on a 1219 x 2438 sheet
        plans, _ = pack_sheets([P("s", 600.0, 600.0)])
        offcuts = plans[0].offcuts()
        self.assertTrue(any(h >= 300.0 for _, h in offcuts))

    def test_non_sheet_stock_is_rejected(self):
        with self.assertRaises(NestError):
            pack_sheets([P("b", 1000.0, 89.0, cls="2x4")])

    def test_glazing_uses_its_own_sheet_class(self):
        # a 700 x 220 pane must turn to fit a 610 x 1220 sheet
        plans, unplaced = pack_sheets([P("pane", 700.0, 220.0, cls="polycarbonate_6")])
        self.assertEqual(unplaced, [])
        self.assertEqual(plans[0].stock, "polycarbonate_6")
        self.assertTrue(plans[0].sheets[0][0].rotated)
        self.assertAlmostEqual(plans[0].sheets[0][0].w, 220.0)


if __name__ == "__main__":
    unittest.main()

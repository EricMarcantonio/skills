# tests/test_frame.py
import json
import unittest

from woodbuild.frame import derive, header_depth_for_span, stud_positions, summary
from woodbuild.spec import BuildSpec
from woodbuild import stock

SPEC = {
    "build": "unit-test",
    "envelope": {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                 "roof_fall": 200.0, "tall_side": "front"},
    "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2, "corner_width": 89.0,
             "layers_out_to_in": ["smartside_grooved", "osb_7_16", "2x4"]},
    "roof": {"rafter": "2x4", "spacing": 304.8, "purlin": "mid_span", "deck": "osb_7_16",
             "covering": "corrugated_steel", "build_up": 120.0},
    "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
              "skids": "pt_4x4", "build_up": 196.0, "below_datum": True},
    "openings": [
        {"wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
         "sill": 0.0, "header": "2x8"},
        {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
         "sill": 1838.04, "header": None, "mullions": 4,
         "panes": [3.5, 1.5, 4.5, 4.5, 1.5]},
        {"wall": "left", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": 1508.0, "header": None},
        {"wall": "right", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": 1508.0, "header": None},
    ],
    "substitutions": [],
    "pricing": {"store": "7011", "search": {}},
    "options": {},
}


def spec():
    s = BuildSpec(json.loads(json.dumps(SPEC)))
    s.validate()
    return s


class TestFrame(unittest.TestCase):
    def test_stud_positions_cover_the_wall(self):
        pos = stud_positions(2438.4, 406.4)
        self.assertEqual(pos[0], 0.0)
        self.assertAlmostEqual(pos[-1], 2438.4)
        self.assertTrue(all(b - a <= 406.4 + 1e-6 for a, b in zip(pos, pos[1:])))

    def test_header_depth_rule(self):
        self.assertEqual(header_depth_for_span(1386.84), 89.0)    # <= span/20 = 69 -> 2x4 depth
        self.assertEqual(header_depth_for_span(3000.0), 184.0)    # span/20 = 150 -> 2x8

    def test_every_part_has_a_known_stock_class(self):
        from woodbuild import stock
        for p in derive(spec()):
            self.assertTrue(p.stock in stock.SHEETS or p.stock in stock.BOARDS,
                            "unknown stock on %s: %s" % (p.id, p.stock))

    def test_openings_are_framed_on_both_sides(self):
        parts = derive(spec())
        kings = [p for p in parts if p.assembly == "front_door" and p.id.startswith("king")]
        self.assertEqual(sum(p.qty for p in kings), 2)

    def test_corners_are_three_stud_assemblies(self):
        parts = derive(spec())
        corners = [p for p in parts if p.assembly == "corner_FL"]
        self.assertEqual(sum(p.qty for p in corners if p.id.startswith("corner_stud")), 3)

    def test_floor_structure_sits_below_the_datum(self):
        parts = derive(spec())
        joists = [p for p in parts if p.assembly == "floor"]
        self.assertTrue(any(p.id.startswith("skid") for p in joists))
        self.assertTrue(any(p.id.startswith("deck") for p in joists))

    def test_roof_has_rafters_purlin_and_deck(self):
        ids = [p.id for p in derive(spec()) if p.assembly == "roof"]
        self.assertTrue(any(i.startswith("rafter") for i in ids))
        self.assertIn("purlin", ids)
        self.assertTrue(any(i.startswith("roof_deck") for i in ids))

    def test_glazing_parts_use_polycarbonate(self):
        panes = [p for p in derive(spec()) if p.id.startswith(("band_pane", "transom_pane"))]
        self.assertTrue(panes)
        self.assertTrue(all(p.stock == "polycarbonate_6" for p in panes))
        # glazing is the band height minus two 40 mm rails, not the whole band
        band_pane = [p for p in panes if p.id.startswith("band_pane")][0]
        self.assertAlmostEqual(band_pane.h, 220.0)

    def test_surfaces_are_panelised_to_fit_a_sheet(self):
        s = spec()
        sw, sh = stock.sheet_size("smartside_grooved")
        for p in derive(s):
            if p.id.startswith(("sheathing_", "siding_", "deck", "roof_deck")):
                self.assertLessEqual(max(p.w, p.h), max(sw, sh) + 1e-6, p.id)
                self.assertLessEqual(min(p.w, p.h), min(sw, sh) + 1e-6, p.id)
                self.assertGreater(p.qty, 0)

    def test_studs_stop_at_the_roof_underside(self):
        s = spec()
        stud = [p for p in derive(s) if p.id == "stud_front"][0]
        self.assertAlmostEqual(stud.w, s.wall_top_front())
        self.assertAlmostEqual(stud.w, 2138.06, places=1)   # 2258.06 - 120 mm build-up

    def test_door_opening_has_no_sill_plate(self):
        ids = [p.id for p in derive(spec())]
        self.assertNotIn("sill_front_door", ids)
        self.assertIn("sill_front_band", ids)

    def test_walls_have_blocking_at_the_bearing_line(self):
        parts = derive(spec())
        blocking = [p for p in parts if p.id.startswith("blocking_")]
        self.assertEqual(len(blocking), 4)                 # one run per wall
        front = [p for p in blocking if p.id == "blocking_front"][0]
        self.assertEqual(front.qty, 7)                     # 8 stud positions -> 7 bays

    def test_blocking_fits_the_actual_bay(self):
        # studs sit at span / bays, so the clear bay is that pitch minus a stud
        parts = derive(spec())
        front = [p for p in parts if p.id == "blocking_front"][0]
        self.assertAlmostEqual(front.w, 2788.92 / 7 - 38.0, places=1)    # 360.4 mm
        left = [p for p in parts if p.id == "blocking_left"][0]
        self.assertAlmostEqual(left.w, 2179.32 / 6 - 38.0, places=1)     # 325.2 mm

    def test_glazing_is_panelised_too(self):
        # a pane wider than a 610 x 1220 polycarbonate sheet must be split
        s = spec()
        sw, sh = stock.sheet_size("polycarbonate_6")
        for p in derive(s):
            if p.id.startswith(("band_pane", "transom_pane")):
                self.assertLessEqual(max(p.w, p.h), max(sw, sh) + 1e-6, p.id)
                self.assertLessEqual(min(p.w, p.h), min(sw, sh) + 1e-6, p.id)

    def test_summary_counts_by_assembly(self):
        s = summary(derive(spec()))
        self.assertIn("wall_front", s)
        self.assertGreater(s["floor"], 0)


if __name__ == "__main__":
    unittest.main()

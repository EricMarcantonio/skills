# tests/test_frame.py
import json
import unittest

from woodbuild import frame
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
         "sill": 0.0, "header": "2x8", "x": 701.04},
        {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
         "sill": 1838.04, "header": None, "x": 89.0, "mullions": 4,
         "panes": [3.5, 1.5, 4.5, 4.5, 1.5]},
        {"wall": "left", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": 1508.0, "header": None, "x": 792.16},
        {"wall": "right", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": 1508.0, "header": None, "x": 792.16},
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
        # 8 stud positions, but the 1386.84 mm door removes the four centres inside
        # it (D3) -> 4 placed studs -> 3 bays. Was 7 before studs followed openings.
        self.assertEqual(front.qty, 3)

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


class TestPlacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = BuildSpec(json.loads(json.dumps(SPEC)))
        cls.parts = frame.derive(cls.spec)

    def _row(self, part_id):
        return [p for p in self.parts if p.id == part_id][0]

    def test_every_wall_member_is_placed_and_cut_parts_are_not(self):
        for p in self.parts:
            if p.kind in ("sole_plate", "top_plate", "stud", "blocking", "king", "jack",
                          "header", "cripple", "sill", "corner"):
                self.assertIsNotNone(p.x, "%s has no position" % p.id)
                self.assertIsNotNone(p.y, "%s has no position" % p.id)
                self.assertIsNotNone(p.run, "%s has no drawn extent" % p.id)
                self.assertIsNotNone(p.rise, "%s has no drawn extent" % p.id)
            else:
                self.assertIsNone(p.x, "%s is cut from a sheet, not placed" % p.id)

    def test_a_repeated_member_publishes_one_position_per_copy(self):
        studs = self._row("stud_front")
        self.assertEqual(len(frame.PLACEMENTS["stud_front"]), studs.qty)

    def test_studs_inside_the_door_are_not_placed_or_counted(self):
        studs = self._row("stud_front")
        centres = sorted(x + 19.0 for x in frame.PLACEMENTS["stud_front"])
        self.assertEqual(len(centres), studs.qty)
        door_x, door_w = 701.04, 1386.84
        for c in centres:
            self.assertFalse(door_x < c < door_x + door_w,
                             "stud at %.1f sits inside the door" % c)

    def test_an_opening_that_does_not_reach_the_floor_keeps_its_studs(self):
        # the clerestory band spans the whole front wall above head height; its studs
        # stay, and the sill, header and cripples attach to them
        front = self._row("stud_front").qty
        door_only = len([c for c in frame.placed_centres(self.spec, "front")])
        self.assertEqual(front, door_only)
        back = self._row("stud_back").qty          # no openings at all
        self.assertGreater(back, front)

    def test_the_stud_run_still_closes_on_the_wall_end(self):
        xs = sorted(frame.PLACEMENTS["stud_front"])
        self.assertAlmostEqual(xs[-1] + 19.0, 2788.92, places=1)

    def test_blocking_fills_the_bays_between_placed_studs(self):
        centres = sorted(x + 19.0 for x in frame.PLACEMENTS["stud_front"])
        blocking = sorted(frame.PLACEMENTS["blocking_front"])
        self.assertEqual(len(blocking), len(centres) - 1)

    def test_king_studs_sit_on_the_opening_jambs(self):
        kings = sorted(frame.PLACEMENTS["king_front_door"])
        self.assertEqual(len(kings), 2)
        self.assertAlmostEqual(kings[0] + 38.0, 701.04, places=1)
        self.assertAlmostEqual(kings[1], 701.04 + 1386.84, places=1)

    def test_the_datum_is_the_floor_deck_and_the_door_head_agrees(self):
        header = self._row("header_front_door")
        self.assertAlmostEqual(header.y, 1811.02, places=1)
        sole = self._row("sole_plate_front")
        self.assertAlmostEqual(sole.y, 0.0, places=1)

    def test_drawn_extents_are_not_the_cutting_dimensions(self):
        stud = self._row("stud_front")
        self.assertAlmostEqual(stud.run, 38.0, places=1)          # across the wall
        self.assertAlmostEqual(stud.rise, self.spec.wall_top_front(), places=1)
        plate = self._row("sole_plate_front")
        self.assertAlmostEqual(plate.run, 2788.92, places=1)      # along the wall
        self.assertAlmostEqual(plate.rise, 38.0, places=1)


if __name__ == "__main__":
    unittest.main()

import unittest

from woodbuild.from_model import (band_opening, bounds_from_shapes,
                                  check_envelope, envelope_from_bounds,
                                  openings_from_cutters, wall_bounds)
from woodbuild.spec import SpecError


class TestBounds(unittest.TestCase):
    def test_bounds_union_of_shapes(self):
        # no FreeCAD needed: two panels whose union is the wall envelope
        got = bounds_from_shapes([[0.0, 2788.92, 0.0, 2179.32, 2100.0, 2178.06],
                                  [0.0, 2788.92, 0.0, 2179.32, 0.0, 2100.0]])
        self.assertEqual(got, (0.0, 2788.92, 0.0, 2179.32, 0.0, 2178.06))

    def test_no_shapes_is_an_error_not_an_empty_envelope(self):
        from woodbuild.spec import SpecError
        with self.assertRaises(SpecError):
            bounds_from_shapes([])


class TestEnvelope(unittest.TestCase):
    def test_envelope_uses_the_model_roof_top_not_the_wood_build_up(self):
        # the model's wall top is its roof underside; add the MODEL's own roof
        # thickness (80 mm) to recover the product's overall height. The wood
        # roof build-up is a spec decision, not an envelope input.
        env = envelope_from_bounds((0.0, 2788.92, 0.0, 2179.32, 0.0, 2178.06),
                                   model_roof_t=80.0, roof_fall=200.0)
        self.assertAlmostEqual(env["width"], 2788.92)
        self.assertAlmostEqual(env["depth"], 2179.32)
        self.assertAlmostEqual(env["height_tall"], 2258.06)
        self.assertEqual(env["roof_fall"], 200.0)
        self.assertEqual(env["tall_side"], "front")

    def test_tall_side_is_a_parameter(self):
        env = envelope_from_bounds((0.0, 1000.0, 0.0, 2000.0, 0.0, 1000.0),
                                   model_roof_t=80.0, roof_fall=0.0, tall_side="back")
        self.assertEqual(env["tall_side"], "back")


class TestBand(unittest.TestCase):
    def test_band_sill_is_recomputed_for_a_thicker_roof(self):
        # a 120 mm wood roof build-up vs the model's 80 mm resin roof lowers the
        # band by 40 mm, keeping the band under an unchanged envelope while
        # staying above the door head
        band = band_opening(model_band=(2698.92, 300.0, 1878.06),
                            envelope_width=2788.92, corner_width=89.0,
                            height_tall=2258.06, roof_build_up=120.0,
                            door_head=1811.02)
        self.assertAlmostEqual(band["width"], 2610.92)
        self.assertAlmostEqual(band["sill"], 1838.06)
        self.assertAlmostEqual(band["height"], 300.0)
        self.assertGreaterEqual(band["sill"], 1811.02)

    def test_a_band_that_would_not_clear_the_door_head_is_refused(self):
        from woodbuild.spec import SpecError
        with self.assertRaises(SpecError):
            band_opening(model_band=(2698.92, 300.0, 1878.06),
                         envelope_width=2788.92, corner_width=89.0,
                         height_tall=2258.06, roof_build_up=400.0,
                         door_head=1811.02)


class StubBox:
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax):
        self.XMin, self.XMax = xmin, xmax
        self.YMin, self.YMax = ymin, ymax
        self.ZMin, self.ZMax = zmin, zmax

    @property
    def XLength(self):
        return self.XMax - self.XMin

    @property
    def ZLength(self):
        return self.ZMax - self.ZMin


class StubShape:
    def __init__(self, box):
        self.BoundBox = box

    def isNull(self):
        return self.BoundBox is None


class StubObj:
    def __init__(self, name, box):
        self.Name = name
        self.Shape = StubShape(box)


class StubDoc:
    def __init__(self, objs):
        self.Objects = objs

    def getObject(self, name):
        return next((o for o in self.Objects if o.Name == name), None)


class TestWallBounds(unittest.TestCase):
    def test_wall_object_wins_over_the_naming_convention(self):
        doc = StubDoc([StubObj("WallsOpen", StubBox(0, 10, 0, 20, 0, 30)),
                       StubObj("panelCut", StubBox(0, 999, 0, 999, 0, 999))])
        self.assertEqual(wall_bounds(doc, wall_object="WallsOpen"),
                         (0, 10, 0, 20, 0, 30))

    def test_naming_convention_selects_panels_and_posts(self):
        doc = StubDoc([StubObj("sideCut", StubBox(0, 10, 0, 20, 0, 30)),
                       StubObj("Post1", StubBox(-5, 10, 0, 20, 0, 30)),
                       StubObj("ignored", StubBox(0, 500, 0, 500, 0, 500))])
        self.assertEqual(wall_bounds(doc), (-5, 10, 0, 20, 0, 30))

    def test_a_model_with_neither_is_refused(self):
        with self.assertRaises(SpecError):
            wall_bounds(StubDoc([StubObj("ignored", StubBox(0, 1, 0, 1, 0, 1))]))

    def test_a_missing_named_object_is_refused(self):
        with self.assertRaises(SpecError):
            wall_bounds(StubDoc([]), wall_object="WallsOpen")


class TestCutters(unittest.TestCase):
    ENVELOPE = {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                "roof_fall": 200.0, "tall_side": "front"}

    def _doc(self):
        return StubDoc([StubObj("fw_door", StubBox(0, 1386.84, 0, 1, 0, 1811.02)),
                        StubObj("fw_band", StubBox(0, 2698.92, 0, 1, 1878.06, 2178.06))])

    def test_door_and_band_read_from_the_model(self):
        got = openings_from_cutters(self._doc(), self.ENVELOPE, corner_width=89.0,
                                    roof_build_up=120.0)
        door, band = got[0], got[1]
        self.assertEqual(door["kind"], "door")
        self.assertAlmostEqual(door["width"], 1386.84)
        self.assertAlmostEqual(door["height"], 1811.02)
        self.assertAlmostEqual(band["width"], 2610.92)
        self.assertAlmostEqual(band["sill"], 1838.06)

    def test_extra_openings_are_appended_in_order(self):
        extra = [{"wall": "left", "kind": "transom", "width": 595.0,
                  "height": 220.0, "sill": 1511.02, "header": None}]
        got = openings_from_cutters(self._doc(), self.ENVELOPE, corner_width=89.0,
                                    roof_build_up=120.0, extra=extra)
        self.assertEqual([o["kind"] for o in got], ["door", "band", "transom"])

    def test_missing_or_null_cutters_are_refused(self):
        with self.assertRaises(SpecError):
            openings_from_cutters(StubDoc([]), self.ENVELOPE)
        # a failed boolean leaves a null cutter; it must be refused loudly, not
        # read as a zero-size opening that trivially clears the door head
        null_door = StubDoc([StubObj("fw_door", None),
                             StubObj("fw_band", StubBox(0, 2698.92, 0, 1,
                                                        1878.06, 2178.06))])
        with self.assertRaises(SpecError):
            openings_from_cutters(null_door, self.ENVELOPE)
        null_band = StubDoc([StubObj("fw_door", StubBox(0, 1386.84, 0, 1,
                                                        0, 1811.02)),
                             StubObj("fw_band", None)])
        with self.assertRaises(SpecError):
            openings_from_cutters(null_band, self.ENVELOPE)


class TestEnvelopeCheck(unittest.TestCase):
    class StubSpec:
        envelope = {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                    "roof_fall": 200.0, "tall_side": "front"}

    def test_a_matching_model_passes(self):
        doc = StubDoc([StubObj("WallsOpen",
                               StubBox(0, 2788.92, 0, 2179.32, 0, 2178.06))])
        check_envelope(self.StubSpec(), doc, wall_object="WallsOpen")

    def test_a_moved_model_is_refused(self):
        doc = StubDoc([StubObj("WallsOpen",
                               StubBox(0, 2800.0, 0, 2179.32, 0, 2178.06))])
        with self.assertRaises(SpecError):
            check_envelope(self.StubSpec(), doc, wall_object="WallsOpen")


if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest

from woodbuild.spec import BuildSpec, SpecError

GOOD = {
    "build": "unit-test",
    "envelope": {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                 "roof_fall": 200.0, "tall_side": "front"},
    "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2, "corner_width": 89.0,
             "layers_out_to_in": ["siding_11", "osb_11", "stud_89"]},
    "roof": {"rafter": "2x4", "spacing": 304.8, "purlin": "mid_span",
             "deck": "osb_7_16", "covering": "corrugated_steel", "build_up": 120.0},
    "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
              "skids": "pt_4x4", "build_up": 196.0, "below_datum": True},
    "openings": [
        {"wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
         "sill": 0.0, "header": "2x8"},
        {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
         "sill": 1838.04, "header": None},
    ],
    "substitutions": [{"ref": "45mm post", "build": "3-stud corner",
                       "consequence": "corner trim needed", "changes_diagram": True}],
    "pricing": {"store": "7011", "search": {"2x4": "2x4x8 SPF stud",
                                            "osb_7_16": "7/16 OSB sheathing"}},
    "options": {"kerf": 3.0, "retain_offcut_min": 300.0},
}


def write(obj):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh)
    return path


class TestSpec(unittest.TestCase):
    def setUp(self):
        self.path = write(GOOD)

    def test_load_and_round_trip(self):
        spec = BuildSpec.load(self.path)
        spec.validate()
        out = self.path + ".out"
        spec.save(out)
        again = BuildSpec.load(out)
        self.assertEqual(again.envelope["width"], 2788.92)
        os.unlink(out)

    def test_wall_build_up_from_layers(self):
        spec = BuildSpec.load(self.path)
        self.assertEqual(spec.wall_build_up(), 111.0)   # siding 11 + osb 11 + stud 89

    def test_wall_build_up_uses_stock_class_thickness(self):
        data = json.loads(json.dumps(GOOD))
        data["wall"]["layers_out_to_in"] = ["smartside_grooved", "osb_7_16", "2x4"]
        spec = BuildSpec.load(write(data))
        self.assertEqual(spec.wall_build_up(), 11.0 + 11.0 + 38.0)

    def test_band_must_fit_under_roof_build_up(self):
        data = json.loads(json.dumps(GOOD))
        data["roof"]["build_up"] = 171.0            # 2x6 rafters: the collision from the spec
        spec = BuildSpec.load(write(data))
        with self.assertRaises(SpecError) as ctx:
            spec.validate()
        self.assertIn("band does not fit", str(ctx.exception))

    def test_wall_build_up_must_fit_inside_envelope(self):
        data = json.loads(json.dumps(GOOD))
        data["wall"]["layers_out_to_in"] = ["smartside_grooved", "osb_7_16", "2x4"] * 30
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("build-up", str(ctx.exception))

    def test_opening_must_fit_between_the_corners(self):
        data = json.loads(json.dumps(GOOD))
        data["openings"][0]["width"] = 9999.0
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("wider than", str(ctx.exception))

    def test_band_wider_than_the_corner_span_is_rejected(self):
        # the model's band spans between 45 mm moulded posts (2698.92 mm); wood corners
        # are 89 mm each, so the band must shrink to 2610.92 mm
        data = json.loads(json.dumps(GOOD))
        band = [o for o in data["openings"] if o["kind"] == "band"][0]
        band["width"] = 2698.92
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("wider than", str(ctx.exception))

    def test_door_head_reported(self):
        spec = BuildSpec.load(self.path)
        self.assertAlmostEqual(spec.door_head(), 1811.02)

    def test_unknown_stock_class_rejected(self):
        data = json.loads(json.dumps(GOOD))
        data["roof"]["deck"] = "unobtainium"
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("unknown stock class", str(ctx.exception))

    def test_floor_below_datum_required_when_flagged(self):
        data = json.loads(json.dumps(GOOD))
        data["floor"]["below_datum"] = False
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("datum", str(ctx.exception))

    def test_opening_on_an_unknown_wall_is_rejected(self):
        data = json.loads(json.dumps(GOOD))
        data["openings"][0]["wall"] = "fron"          # typo: silently dropped before
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("unknown wall", str(ctx.exception))

    def test_search_terms_pass_through(self):
        spec = BuildSpec.load(self.path)
        self.assertEqual(spec.search_terms()["2x4"], "2x4x8 SPF stud")


if __name__ == "__main__":
    unittest.main()

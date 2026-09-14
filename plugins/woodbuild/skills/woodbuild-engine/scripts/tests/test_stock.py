import unittest
from woodbuild import stock


class TestStock(unittest.TestCase):
    def test_sheet_size_and_thickness(self):
        self.assertEqual(stock.sheet_size("osb_7_16"), (1219.0, 2438.0))
        self.assertEqual(stock.thickness("osb_7_16"), 11.0)
        self.assertTrue(stock.is_sheet("osb_7_16"))

    def test_small_sheet_for_glazing(self):
        self.assertEqual(stock.sheet_size("polycarbonate_6"), (610.0, 1220.0))

    def test_board_dims_and_lengths(self):
        self.assertEqual(stock.board_dims("2x4"), (38.0, 89.0))
        self.assertEqual(stock.board_lengths_mm("2x4"),
                         [2438.4, 3048.0, 3657.6, 4876.8])
        self.assertFalse(stock.is_sheet("2x4"))

    def test_grain_flags(self):
        self.assertEqual(stock.grain("smartside_grooved"), "groove")
        self.assertIsNone(stock.grain("osb_7_16"))

    def test_categories_and_labels(self):
        self.assertEqual(stock.category("2x4"), "lumber")
        self.assertEqual(stock.category("smartside_grooved"), "sheets")
        self.assertEqual(stock.category("polycarbonate_6"), "glazing")
        self.assertEqual(stock.unit_label("2x4"), "each")
        self.assertEqual(stock.unit_label("osb_7_16"), "sheet")

    def test_unknown_class_raises(self):
        with self.assertRaises(KeyError):
            stock.sheet_size("nope")

    def test_every_class_has_a_category(self):
        for cls in list(stock.SHEETS) + list(stock.BOARDS):
            self.assertIn(stock.category(cls), set(stock.CATEGORIES.values()))


if __name__ == "__main__":
    unittest.main()

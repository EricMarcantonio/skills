# tests/test_optimise_boards.py
import unittest

from woodbuild.optimise import BoardPlan, Part, cut_boards
from woodbuild import stock


def B(pid, length, qty=1, cls="2x4"):
    return Part(id=pid, w=length, h=stock.board_dims(cls)[1], qty=qty, stock=cls)


class TestBoardCutting(unittest.TestCase):
    def test_single_part_picks_the_shortest_board_that_fits(self):
        plans, unplaced = cut_boards([B("plate", 2440.0)])
        self.assertEqual(unplaced, [])
        self.assertEqual(sum(p.count for p in plans), 1)
        # 8 ft is 2438.4 mm, just short of 2440, so the 10 ft board wins
        self.assertEqual(plans[0].length_mm, 3048.0)

    def test_exact_fit_two_parts_on_one_board(self):
        plans, unplaced = cut_boards([B("half", 1216.0, qty=2)])
        self.assertEqual(unplaced, [])
        self.assertEqual(len(plans[0].cuts), 1)           # both halves on one 8 ft board
        self.assertEqual(plans[0].length_mm, 2438.4)

    def test_kerf_blocks_the_second_part(self):
        # prices force the 8 ft board, where 1226 + kerf + 1226 does not fit
        prices = {"2x4": {2438.4: 1.0, 3048.0: 4.0, 3657.6: 5.0, 4876.8: 6.0}}
        plans, _ = cut_boards([B("half", 1226.0, qty=2)], prices=prices)
        self.assertEqual(plans[0].length_mm, 2438.4)
        self.assertEqual(len(plans[0].cuts), 2)

    def test_cheapest_mix_beats_the_naive_per_part_choice(self):
        # 12 parts of 3000 mm: every board takes one part, so the cheapest per-board
        # length wins even though it is the longest stock
        prices = {"2x4": {2438.4: 1.0, 3048.0: 9.0, 4876.8: 6.20}}
        plans, unplaced = cut_boards([B("stud", 3000.0, qty=12)], prices=prices)
        self.assertEqual(unplaced, [])
        total_cost = sum(p.count * prices["2x4"][p.length_mm] for p in plans)
        self.assertAlmostEqual(total_cost, 12 * 6.20, places=2)
        self.assertEqual(plans[0].length_mm, 4876.8)
        self.assertEqual(plans[0].count, 12)

    def test_long_part_uses_longest_board(self):
        plans, unplaced = cut_boards([B("rafter", 2500.0)])
        self.assertEqual(unplaced, [])
        self.assertEqual(plans[0].length_mm, 3048.0)      # 10 ft

    def test_part_longer_than_any_board_is_unplaced(self):
        plans, unplaced = cut_boards([B("absurd", 6000.0)])
        self.assertEqual(plans, [])
        self.assertEqual([p.id for p in unplaced], ["absurd"])

    def test_offcuts_reported_and_yield(self):
        plans, _ = cut_boards([B("s", 2400.0)])
        self.assertAlmostEqual(plans[0].yield_pct(), 100.0 * 2400.0 / 2438.4, places=3)
        self.assertEqual(plans[0].offcuts(), [])          # 38 mm remainder is not retained

    def test_without_prices_it_minimises_purchased_length(self):
        # two 2400 mm parts fit on one 16 ft board (4803 mm) but not on one 10 ft board
        plans, _ = cut_boards([B("s", 2400.0, qty=2)])
        self.assertEqual(plans[0].length_mm, 4876.8)
        self.assertEqual(plans[0].count, 1)

    def test_partial_length_table_excludes_the_unpriced_length(self):
        # prices cover 8 and 12 ft but not 10 or 16 ft. Ranking the unpriced 16 ft
        # board by millimetres against dollars would silently exclude it; 12 ft wins.
        prices = {"2x4": {2438.4: 1.0, 3657.6: 5.0}}
        plans, unplaced = cut_boards([B("s", 3000.0, qty=2)], prices=prices)
        self.assertEqual(unplaced, [])
        self.assertEqual(plans[0].length_mm, 3657.6)
        self.assertEqual(plans[0].count, 2)

    def test_flat_per_class_price_applies_to_every_length(self):
        # the real price cache holds one price per class, not a length table
        plans, _ = cut_boards([B("s", 2400.0, qty=2)],
                              prices={"2x4": {"price": 9.99, "sku": "1"}})
        self.assertEqual(plans[0].length_mm, 4876.8)      # fewest boards wins the tie

    def test_board_offcuts_keep_large_remainders(self):
        plans, _ = cut_boards([B("s", 1000.0)])
        self.assertEqual(plans[0].length_mm, 2438.4)
        self.assertEqual(plans[0].offcuts(), [1438.4])


if __name__ == "__main__":
    unittest.main()

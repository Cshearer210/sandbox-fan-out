"""corral.core.split_population -- round-robin a discovered population into up to N disjoint,
balanced slices, dropping empties. Every branch of the size clamp, plus the invariants merge and
fanout depend on (disjoint, complete, balanced), pinned on known inputs."""
import unittest

from _pathfix import core  # noqa: E402
split_population = core.split_population


class SizeClampTest(unittest.TestCase):
    def test_empty_population_gives_no_slices(self):
        self.assertEqual(split_population([], 5), [])
        self.assertEqual(split_population([], 0), [])

    def test_zero_agents_with_units_falls_back_to_one_slice(self):
        # n = max(1, min(0, len)) -> 1 : never zero slices when there is work to do
        out = split_population([1, 2, 3], 0)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], [1, 2, 3])

    def test_negative_agents_falls_back_to_one_slice(self):
        out = split_population([1, 2, 3], -4)
        self.assertEqual(len(out), 1)
        self.assertEqual(sorted(out[0]), [1, 2, 3])

    def test_one_agent_gets_everything_in_order(self):
        self.assertEqual(split_population([1, 2, 3, 4], 1), [[1, 2, 3, 4]])

    def test_more_agents_than_units_drops_idle(self):
        # 2 units, 10 agents -> 2 slices, never 10 (8 would be idle)
        self.assertEqual(len(split_population([1, 2], 10)), 2)

    def test_agents_equal_units_one_each(self):
        out = split_population([1, 2, 3], 3)
        self.assertEqual(len(out), 3)
        self.assertTrue(all(len(s) == 1 for s in out))

    def test_float_agent_count_is_truncated(self):
        # int(2.9) == 2 -> two slices
        self.assertEqual(len(split_population([1, 2, 3, 4], 2.9)), 2)


class DistributionTest(unittest.TestCase):
    def test_round_robin_exact_layout(self):
        # units 0..9 across 3 agents, round-robin: 0->s0, 1->s1, 2->s2, 3->s0, ...
        out = split_population(list(range(10)), 3)
        self.assertEqual(out[0], [0, 3, 6, 9])
        self.assertEqual(out[1], [1, 4, 7])
        self.assertEqual(out[2], [2, 5, 8])

    def test_slices_are_complete(self):
        units = list(range(37))
        flat = [u for s in split_population(units, 7) for u in s]
        self.assertEqual(sorted(flat), units)

    def test_slices_are_disjoint(self):
        flat = [u for s in split_population(list(range(50)), 9) for u in s]
        self.assertEqual(len(flat), len(set(flat)))

    def test_slices_are_balanced(self):
        for n in (2, 3, 4, 5, 8, 13):
            out = split_population(list(range(50)), n)
            self.assertLessEqual(max(len(s) for s in out) - min(len(s) for s in out), 1)

    def test_accepts_a_generator_population(self):
        out = split_population((x for x in range(6)), 2)
        self.assertEqual(out[0], [0, 2, 4])
        self.assertEqual(out[1], [1, 3, 5])

    def test_string_units_are_preserved_not_reordered_within_slice(self):
        out = split_population(["a", "b", "c", "d", "e"], 2)
        self.assertEqual(out[0], ["a", "c", "e"])
        self.assertEqual(out[1], ["b", "d"])

    def test_duplicate_units_are_kept_not_deduped(self):
        # split does not deduplicate; it is a partition of the given sequence
        out = split_population([7, 7, 7], 1)
        self.assertEqual(out[0], [7, 7, 7])

    def test_does_not_mutate_input_list(self):
        units = [1, 2, 3, 4]
        split_population(units, 2)
        self.assertEqual(units, [1, 2, 3, 4])

    def test_no_empty_slice_is_returned(self):
        # 3 units, 3 agents -> exactly 3 non-empty slices; a 4th agent would be dropped
        out = split_population([1, 2, 3], 100)
        self.assertTrue(all(len(s) >= 1 for s in out))
        self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main()

"""Property-based tests (hypothesis, a TEST-ONLY dependency). These assert invariants that must
hold for ALL inputs, not just the hand-picked cases in the other files: split is always a disjoint,
complete, balanced partition; merge is order-independent and dedupes by (agent_id, unit); a fanout
over distinct units reports each exactly once. If hypothesis is absent the module skips cleanly."""
import json
import os
import random
import shutil
import tempfile
import unittest

from _pathfix import core  # noqa: E402

try:
    from hypothesis import given, settings, strategies as st
    HAVE_HYPOTHESIS = True
except ImportError:  # hypothesis is dev-only; runtime and a bare unittest run must not need it
    HAVE_HYPOTHESIS = False


@unittest.skipUnless(HAVE_HYPOTHESIS, "hypothesis not installed (dev-only dependency)")
class SplitProperties(unittest.TestCase):
    @settings(max_examples=200)
    @given(st.lists(st.integers()), st.integers(min_value=-3, max_value=32))
    def test_partition_is_disjoint_and_complete(self, units, n):
        slices = core.split_population(units, n)
        flat = [u for s in slices for u in s]
        self.assertEqual(sorted(flat), sorted(units))     # complete: nothing lost or invented

    @settings(max_examples=200)
    @given(st.lists(st.integers(), min_size=1), st.integers(min_value=1, max_value=32))
    def test_partition_is_balanced_and_has_no_empty_slice(self, units, n):
        slices = core.split_population(units, n)
        self.assertTrue(all(len(s) >= 1 for s in slices))         # no idle slice
        self.assertLessEqual(max(len(s) for s in slices) - min(len(s) for s in slices), 1)

    @settings(max_examples=100)
    @given(st.lists(st.integers(), min_size=1), st.integers(min_value=1, max_value=64))
    def test_never_more_slices_than_units(self, units, n):
        self.assertLessEqual(len(core.split_population(units, n)), len(units))


@unittest.skipUnless(HAVE_HYPOTHESIS, "hypothesis not installed (dev-only dependency)")
class MergeProperties(unittest.TestCase):
    def _write_rows(self, log_dir, rows, n_files):
        """Distribute rows across n_files agent logs (grouped by agent_id so keys stay uniquely
        owned), shuffling line order, and return the file arrangement used."""
        buckets = {}
        for r in rows:
            buckets.setdefault(r["agent_id"], []).append(r)
        for aid, brows in buckets.items():
            random.shuffle(brows)
            with open(os.path.join(log_dir, "agent-%s.jsonl" % aid), "w") as f:
                for r in brows:
                    f.write(json.dumps(r) + "\n")

    @settings(max_examples=100, deadline=None)
    @given(st.integers(min_value=0, max_value=60), st.integers(min_value=1, max_value=8))
    def test_merge_counts_distinct_keys_and_routes_by_ok(self, n_units, n_agents):
        # build distinct (agent_id, unit) rows with a deterministic ok pattern
        rows = []
        for i in range(n_units):
            aid = str(i % n_agents)
            rows.append({"agent_id": aid, "unit": "u%d" % i, "ok": (i % 2 == 0)})
        d = tempfile.mkdtemp()
        try:
            self._write_rows(d, rows, n_agents)
            summ = core.merge(d, os.path.join(d, "s.jsonl"), os.path.join(d, "f.jsonl"))
            self.assertEqual(summ["merged"], n_units)
            self.assertEqual(summ["successes"], sum(1 for r in rows if r["ok"]))
            self.assertEqual(summ["failures"], sum(1 for r in rows if not r["ok"]))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    @settings(max_examples=60, deadline=None)
    @given(st.integers(min_value=1, max_value=20), st.integers(min_value=2, max_value=6))
    def test_duplicate_keys_are_counted_once(self, n_units, dup_factor):
        rows = []
        for i in range(n_units):
            for _ in range(dup_factor):  # same (agent_id, unit) repeated dup_factor times
                rows.append({"agent_id": "0", "unit": "u%d" % i, "ok": True})
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, "agent-0.jsonl"), "w") as f:
                random.shuffle(rows)
                for r in rows:
                    f.write(json.dumps(r) + "\n")
            summ = core.merge(d, os.path.join(d, "s.jsonl"), os.path.join(d, "f.jsonl"))
            self.assertEqual(summ["merged"], n_units)  # dedup: dup_factor copies collapse to one
        finally:
            shutil.rmtree(d, ignore_errors=True)


@unittest.skipUnless(HAVE_HYPOTHESIS, "hypothesis not installed (dev-only dependency)")
class FanoutProperties(unittest.TestCase):
    @settings(max_examples=50, deadline=None)
    @given(st.integers(min_value=0, max_value=80), st.integers(min_value=1, max_value=12))
    def test_every_distinct_unit_appears_exactly_once(self, n_units, n_agents):
        population = list(range(n_units))   # distinct -> no (agent_id, unit) collisions
        d = tempfile.mkdtemp()
        try:
            result = core.fanout(population, lambda u, w: (u % 2 == 0, "n"), n_agents, d)
            self.assertEqual(result["merged"], n_units)
            seen = []
            for name in ("successes.jsonl", "failures.jsonl"):
                p = os.path.join(d, name)
                if os.path.exists(p):
                    with open(p) as f:
                        seen += [int(json.loads(l)["unit"]) for l in f if l.strip()]
            self.assertEqual(sorted(seen), population)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

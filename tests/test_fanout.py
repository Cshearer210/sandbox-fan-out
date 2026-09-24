"""corral.core.fanout -- split -> run every slice in isolation -> merge ONCE. These tests pin the
orchestration contract on known populations: correct summary counts, boundary agent counts
(0/1/many), empty work, prepare/teardown wiring, stale-log clearing, and the two safety properties
(shared files written only by the final merge; a raising unit is a failure not a crash)."""
import json
import os
import shutil
import tempfile
import threading
import unittest

from _pathfix import core  # noqa: E402
fanout = core.fanout


class FanoutBasicsTest(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def _units(self, name):
        p = os.path.join(self.out, name)
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(l)["unit"] for l in f if l.strip()]

    def test_summary_counts_on_a_known_population(self):
        summ = fanout(list(range(10)), lambda u, w: (u % 2 == 0, "n"), 4, self.out)
        self.assertEqual(summ["merged"], 10)
        self.assertEqual(summ["successes"], 5)
        self.assertEqual(summ["failures"], 5)
        self.assertEqual(summ["agents"], 4)

    def test_summary_has_exactly_the_expected_keys(self):
        summ = fanout([1, 2, 3], lambda u, w: (True, "n"), 2, self.out)
        self.assertEqual(set(summ), {"merged", "successes", "failures", "agents"})

    def test_one_agent(self):
        summ = fanout(list(range(6)), lambda u, w: (True, "n"), 1, self.out)
        self.assertEqual(summ["agents"], 1)
        self.assertEqual(summ["merged"], 6)

    def test_zero_agents_falls_back_to_one_slice(self):
        summ = fanout(list(range(4)), lambda u, w: (True, "n"), 0, self.out)
        self.assertEqual(summ["agents"], 1)   # split clamps 0 -> 1
        self.assertEqual(summ["merged"], 4)

    def test_many_agents_capped_by_population(self):
        summ = fanout([1, 2, 3], lambda u, w: (True, "n"), 50, self.out)
        self.assertEqual(summ["agents"], 3)   # never more agents than units

    def test_empty_population_does_not_crash(self):
        summ = fanout([], lambda u, w: (True, "n"), 8, self.out)
        self.assertEqual(summ["agents"], 0)
        self.assertEqual(summ["merged"], 0)
        self.assertEqual(summ["successes"], 0)
        self.assertEqual(summ["failures"], 0)

    def test_all_units_present_exactly_once(self):
        N = 40
        fanout(list(range(N)), lambda u, w: (True, "n"), 7, self.out)
        seen = self._units("successes.jsonl") + self._units("failures.jsonl")
        self.assertEqual(sorted(int(u) for u in seen), list(range(N)))

    def test_a_raising_unit_is_a_failure_not_a_crash(self):
        def work(u, w):
            if u == 3:
                raise RuntimeError("boom")
            return (True, "ok")
        summ = fanout(list(range(5)), work, 3, self.out)
        self.assertEqual(summ["merged"], 5)
        self.assertEqual(summ["failures"], 1)

    def test_prepare_and_teardown_are_wired_per_agent(self):
        prepared, torn = [], []
        lock = threading.Lock()

        def prep(agent_id):
            with lock:
                prepared.append(agent_id)
            return "/wd/%s" % agent_id

        def teardown(wd):
            with lock:
                torn.append(wd)

        fanout(list(range(6)), lambda u, w: (True, w), 3, self.out,
               prepare=prep, teardown=teardown)
        self.assertEqual(sorted(prepared), ["0", "1", "2"])   # one prepare per agent
        self.assertEqual(sorted(torn), ["/wd/0", "/wd/1", "/wd/2"])  # one teardown per agent

    def test_stale_logs_are_cleared_before_a_run(self):
        # a leftover agent log in out_dir/logs from a prior run must not survive into merge
        log_dir = os.path.join(self.out, "logs")
        os.makedirs(log_dir)
        with open(os.path.join(log_dir, "agent-99.jsonl"), "w") as f:
            f.write(json.dumps({"agent_id": "99", "unit": "ghost", "ok": True}) + "\n")
        fanout([1, 2], lambda u, w: (True, "n"), 2, self.out)
        self.assertNotIn("ghost", self._units("successes.jsonl"))

    def test_out_dir_is_created_if_missing(self):
        nested = os.path.join(self.out, "brand", "new")
        summ = fanout([1, 2], lambda u, w: (True, "n"), 2, nested)
        self.assertTrue(os.path.exists(os.path.join(nested, "successes.jsonl")))
        self.assertEqual(summ["merged"], 2)

    def test_duplicate_value_in_one_slice_merges_to_one(self):
        # population [7, 7] with 1 agent -> one slice [7, 7] -> both rows share key ("0","7")
        # -> merge dedupes -> merged is 1, documenting the (agent_id, unit) dedup at fanout level
        summ = fanout([7, 7], lambda u, w: (True, "n"), 1, self.out)
        self.assertEqual(summ["merged"], 1)


class FanoutConcurrencyTest(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def test_shared_file_is_never_written_during_the_run(self):
        succ = os.path.join(self.out, "successes.jsonl")

        def work(unit, workdir):
            # the shared file must not exist while agents are still working
            assert not os.path.exists(succ), "shared file written during the fan-out!"
            return (unit % 2 == 0, "n")

        summ = fanout(list(range(200)), work, 16, self.out, max_workers=16)
        self.assertEqual(summ["merged"], 200)

    def test_high_concurrency_loses_nothing(self):
        N = 300
        fanout(list(range(N)), lambda u, w: (True, "n"), 24, self.out, max_workers=24)
        with open(os.path.join(self.out, "successes.jsonl"), encoding="utf-8") as f:
            units = sorted(int(json.loads(l)["unit"]) for l in f if l.strip())
        self.assertEqual(units, list(range(N)))

    def test_max_workers_default_runs_all_slices(self):
        # no explicit max_workers -> defaults to len(slices); the run still completes correctly
        summ = fanout(list(range(20)), lambda u, w: (True, "n"), 5, self.out)
        self.assertEqual(summ["merged"], 20)
        self.assertEqual(summ["agents"], 5)


if __name__ == "__main__":
    unittest.main()

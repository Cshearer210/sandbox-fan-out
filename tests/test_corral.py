"""Sandbox-testing the fan-out MECHANISM itself, in both directions and under stress.

Chris's requirement: prove that many agents running at once do not corrupt or lose results, and
that nothing writes the shared folders concurrently. These tests plant a known population, fan it
out under real thread concurrency, and assert every result appears EXACTLY once, split correctly,
with the shared files written only by the final merge.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from corral.core import (split_population, checkout, cleanup, run_slice, merge, fanout,  # noqa: E402
                         plan_prompts)


class SplitTest(unittest.TestCase):
    def test_slices_are_disjoint_balanced_and_complete(self):
        units = list(range(20))
        slices = split_population(units, 6)
        flat = [u for s in slices for u in s]
        self.assertEqual(sorted(flat), units)            # complete
        self.assertEqual(len(flat), len(set(flat)))       # disjoint -- no unit tested twice
        self.assertTrue(max(len(s) for s in slices) - min(len(s) for s in slices) <= 1)  # balanced

    def test_more_agents_than_units_drops_idle(self):
        self.assertEqual(len(split_population([1, 2], 10)), 2)   # 2 agents, never 10 idle
        self.assertEqual(split_population([], 5), [])


class IsolationTest(unittest.TestCase):
    def setUp(self):
        self.src = tempfile.mkdtemp()
        for rel in ("a/x.txt", "b/y.txt", "c/z.txt"):
            p = os.path.join(self.src, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write(rel)

    def tearDown(self):
        shutil.rmtree(self.src, ignore_errors=True)

    def test_checkout_copies_only_named_parts_then_cleans(self):
        dest = tempfile.mkdtemp(); shutil.rmtree(dest)
        checkout(self.src, ["a", "b/y.txt"], dest)
        self.assertTrue(os.path.exists(os.path.join(dest, "a/x.txt")))
        self.assertTrue(os.path.exists(os.path.join(dest, "b/y.txt")))
        self.assertFalse(os.path.exists(os.path.join(dest, "c/z.txt")))   # not requested -> absent
        cleanup(dest)
        self.assertFalse(os.path.exists(dest))


class FanoutStressTest(unittest.TestCase):
    def setUp(self): self.out = tempfile.mkdtemp()
    def tearDown(self): shutil.rmtree(self.out, ignore_errors=True)

    def test_every_result_appears_exactly_once_no_shared_write_during_run(self):
        N = 200
        population = list(range(N))
        succ_path = os.path.join(self.out, "successes.jsonl")

        def work(unit, workdir):
            # PROOF the shared file is never written mid-run: it must not exist while agents work
            assert not os.path.exists(succ_path), "shared file written during the fan-out!"
            return (unit % 2 == 0, "even" if unit % 2 == 0 else "odd")

        summary = fanout(population, work, n_agents=16, out_dir=self.out, max_workers=16)
        self.assertEqual(summary["merged"], N)
        self.assertEqual(summary["successes"], N // 2)
        self.assertEqual(summary["failures"], N // 2)

        # every unit present EXACTLY once across both shared files, none lost, none duplicated
        seen = []
        for name in ("successes.jsonl", "failures.jsonl"):
            with open(os.path.join(self.out, name), encoding="utf-8") as f:
                for line in f:
                    seen.append(json.loads(line)["unit"])
        self.assertEqual(len(seen), N)
        self.assertEqual(sorted(int(u) for u in seen), population)   # complete + unique

    def test_repeated_runs_never_lose_or_corrupt(self):
        # run the fan-out many times; each merge appends, so totals grow by exactly N each time
        for run in range(1, 6):
            fanout(list(range(50)), lambda u, w: (True, "ok"), n_agents=8, out_dir=self.out)
            with open(os.path.join(self.out, "successes.jsonl"), encoding="utf-8") as f:
                lines = [json.loads(l) for l in f if l.strip()]
            self.assertEqual(len(lines), 50 * run)          # nothing lost, nothing corrupted

    def test_a_raising_unit_is_a_failure_not_a_crash(self):
        def work(unit, workdir):
            if unit == 3:
                raise ValueError("boom")
            return (True, "ok")
        summary = fanout(list(range(5)), work, n_agents=3, out_dir=self.out)
        self.assertEqual(summary["merged"], 5)
        self.assertEqual(summary["failures"], 1)            # the raiser, caught and logged


class PlanPromptsTest(unittest.TestCase):
    def test_real_subagent_plan_has_unique_logs_and_disjoint_parts(self):
        prompts = plan_prompts(list(range(10)), 4, "/src",
                               parts_for=lambda u: ["part-%d" % (u % 3)],
                               task_for=lambda s, p, log: "test %d units, log to %s" % (len(s), log),
                               log_dir="/out/logs")
        logs = [p["log_path"] for p in prompts]
        self.assertEqual(len(logs), len(set(logs)))         # every agent a UNIQUE log -> no contention
        allunits = [u for p in prompts for u in p["units"]]
        self.assertEqual(sorted(allunits), list(range(10)))  # disjoint + complete


if __name__ == "__main__":
    unittest.main()

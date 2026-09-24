"""examples/subagent_fanout.py -- the shipped example must actually work, not just read well.
Loads it by path and exercises both documented paths: the in-process demo (real fanout, all pass)
and the real-fleet planner (disjoint+complete units, unique logs), plus its helper functions."""
import importlib.util
import os
import unittest

from _pathfix import EXAMPLES  # noqa: E402


def _load_example():
    path = os.path.join(EXAMPLES, "subagent_fanout.py")
    spec = importlib.util.spec_from_file_location("subagent_fanout_example", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ExampleModuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ex = _load_example()

    def test_discover_units_returns_24_named_units(self):
        units = self.ex.discover_units()
        self.assertEqual(len(units), 24)
        self.assertEqual(units[0], "pkg-00")
        self.assertEqual(units[-1], "pkg-23")

    def test_parts_for_names_the_units_source_and_shared_config(self):
        self.assertEqual(self.ex.parts_for("pkg-05"), ["src/pkg-05", "shared/config"])

    def test_task_for_embeds_counts_parts_and_log_path(self):
        text = self.ex.task_for(["a", "b"], ["src/a"], "/logs/agent-0.jsonl")
        self.assertIn("2 units", text)
        self.assertIn("/logs/agent-0.jsonl", text)
        self.assertIn("src/a", text)

    def test_plan_a_real_fleet_produces_disjoint_complete_unique_logs(self):
        prompts = self.ex.plan_a_real_fleet(n_agents=8, log_dir="/tmp/x/logs")
        self.assertEqual(len(prompts), 8)
        logs = [p["log_path"] for p in prompts]
        self.assertEqual(len(logs), len(set(logs)))            # unique logs -> no contention
        allunits = sorted(u for p in prompts for u in p["units"])
        self.assertEqual(allunits, sorted(self.ex.discover_units()))  # disjoint + complete

    def test_plan_a_real_fleet_clone_parts_include_shared_config(self):
        prompts = self.ex.plan_a_real_fleet(n_agents=4, log_dir="/tmp/y/logs")
        for p in prompts:
            self.assertIn("shared/config", p["clone_parts"])

    def test_demo_in_process_runs_a_real_fanout_all_passing(self):
        summ = self.ex.demo_in_process()
        self.assertEqual(summ["agents"], 8)
        self.assertEqual(summ["merged"], 24)
        self.assertEqual(summ["successes"], 24)
        self.assertEqual(summ["failures"], 0)


if __name__ == "__main__":
    unittest.main()

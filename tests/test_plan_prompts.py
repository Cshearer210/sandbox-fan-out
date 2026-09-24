"""corral.core.plan_prompts -- the real-subagent briefs, built from the SAME disjoint slices as
fanout. Each brief must name a UNIQUE log path (so nothing collides at merge time), a deduped and
sorted set of clone parts, and the caller's task text. Pins those, plus disjoint+complete units."""
import os
import unittest

from _pathfix import core  # noqa: E402
plan_prompts = core.plan_prompts


def _parts_for(u):
    return ["part-%d" % (u % 3), "shared"]


def _task_for(slice_, parts, log):
    return "test %d units into %s" % (len(slice_), log)


class PlanPromptsTest(unittest.TestCase):
    def test_one_prompt_per_slice(self):
        prompts = plan_prompts(list(range(10)), 4, "/src", _parts_for, _task_for, "/out/logs")
        self.assertEqual(len(prompts), 4)

    def test_each_prompt_has_the_expected_keys(self):
        p = plan_prompts([1, 2], 2, "/src", _parts_for, _task_for, "/out/logs")[0]
        self.assertEqual(set(p), {"agent_id", "units", "clone_parts", "log_path", "task"})

    def test_log_paths_are_unique(self):
        prompts = plan_prompts(list(range(20)), 6, "/src", _parts_for, _task_for, "/out/logs")
        logs = [p["log_path"] for p in prompts]
        self.assertEqual(len(logs), len(set(logs)))

    def test_log_path_format_uses_agent_id(self):
        prompts = plan_prompts([1, 2, 3], 3, "/src", _parts_for, _task_for, "/L")
        self.assertEqual(prompts[0]["log_path"], os.path.join("/L", "agent-0.jsonl"))
        self.assertEqual(prompts[2]["log_path"], os.path.join("/L", "agent-2.jsonl"))

    def test_units_are_disjoint_and_complete(self):
        prompts = plan_prompts(list(range(10)), 4, "/src", _parts_for, _task_for, "/out/logs")
        allunits = [u for p in prompts for u in p["units"]]
        self.assertEqual(sorted(allunits), list(range(10)))
        self.assertEqual(len(allunits), len(set(allunits)))

    def test_agent_id_is_the_string_index(self):
        prompts = plan_prompts([1, 2, 3], 3, "/src", _parts_for, _task_for, "/out/logs")
        self.assertEqual([p["agent_id"] for p in prompts], ["0", "1", "2"])

    def test_clone_parts_are_deduped_and_sorted(self):
        # every unit contributes "shared"; the union must contain it exactly once and be sorted
        prompts = plan_prompts(list(range(9)), 1, "/src", _parts_for, _task_for, "/out/logs")
        parts = prompts[0]["clone_parts"]
        self.assertEqual(parts, sorted(parts))
        self.assertEqual(parts.count("shared"), 1)
        self.assertEqual(set(parts), {"part-0", "part-1", "part-2", "shared"})

    def test_task_text_comes_from_task_for(self):
        prompts = plan_prompts([1, 2], 1, "/src", _parts_for, _task_for, "/out/logs")
        self.assertEqual(prompts[0]["task"], "test 2 units into %s" % prompts[0]["log_path"])

    def test_empty_population_gives_no_prompts(self):
        self.assertEqual(plan_prompts([], 4, "/src", _parts_for, _task_for, "/out/logs"), [])

    def test_task_for_receives_the_slice_parts_and_log(self):
        captured = {}

        def task_for(slice_, parts, log):
            captured["slice"] = list(slice_)
            captured["parts"] = list(parts)
            captured["log"] = log
            return "t"

        prompts = plan_prompts([5, 8], 1, "/src", _parts_for, task_for, "/out/logs")
        self.assertEqual(captured["slice"], [5, 8])
        self.assertEqual(captured["log"], prompts[0]["log_path"])
        self.assertEqual(sorted(captured["parts"]), prompts[0]["clone_parts"])


if __name__ == "__main__":
    unittest.main()

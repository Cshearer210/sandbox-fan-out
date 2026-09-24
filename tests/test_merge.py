"""corral.core.merge -- the SINGLE writer. After the fan-out it folds every agent-*.jsonl into the
shared successes/failures pair, deduping by (agent_id, unit) and skipping anything that is not an
agent log. Pins the routing, the dedup, the skip rules, the append semantics, and the counts."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from _pathfix import core  # noqa: E402
merge = core.merge


def _agent_log(dir_, agent_id, rows):
    p = os.path.join(dir_, "agent-%s.jsonl" % agent_id)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return p


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.log_dir = tempfile.mkdtemp()
        self.tmp = tempfile.mkdtemp()
        self.succ = os.path.join(self.tmp, "successes.jsonl")
        self.fail = os.path.join(self.tmp, "failures.jsonl")

    def tearDown(self):
        for d in (self.log_dir, self.tmp):
            shutil.rmtree(d, ignore_errors=True)

    def _read(self, path):
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_routes_ok_to_successes_and_fail_to_failures(self):
        _agent_log(self.log_dir, "0", [
            {"agent_id": "0", "unit": "u1", "ok": True},
            {"agent_id": "0", "unit": "u2", "ok": False},
        ])
        summ = merge(self.log_dir, self.succ, self.fail)
        self.assertEqual(summ, {"merged": 2, "successes": 1, "failures": 1})
        self.assertEqual([r["unit"] for r in self._read(self.succ)], ["u1"])
        self.assertEqual([r["unit"] for r in self._read(self.fail)], ["u2"])

    def test_dedupes_repeated_agent_unit_key_within_a_merge(self):
        _agent_log(self.log_dir, "0", [
            {"agent_id": "0", "unit": "u1", "ok": True},
            {"agent_id": "0", "unit": "u1", "ok": True},   # exact duplicate key -> counted once
        ])
        summ = merge(self.log_dir, self.succ, self.fail)
        self.assertEqual(summ["merged"], 1)
        self.assertEqual(summ["successes"], 1)

    def test_dedup_is_across_files_for_the_same_key(self):
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "u1", "ok": True}])
        # a second file re-emitting the SAME (agent_id, unit) is still deduped
        with open(os.path.join(self.log_dir, "agent-0-dup.jsonl"), "w") as f:
            f.write(json.dumps({"agent_id": "0", "unit": "u1", "ok": False}) + "\n")
        summ = merge(self.log_dir, self.succ, self.fail)
        self.assertEqual(summ["merged"], 1)   # only the first occurrence survives

    def test_same_unit_different_agent_is_not_a_duplicate(self):
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "u1", "ok": True}])
        _agent_log(self.log_dir, "1", [{"agent_id": "1", "unit": "u1", "ok": True}])
        summ = merge(self.log_dir, self.succ, self.fail)
        self.assertEqual(summ["merged"], 2)   # (0,u1) and (1,u1) are distinct keys

    def test_skips_non_agent_and_non_jsonl_files(self):
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "u1", "ok": True}])
        Path(os.path.join(self.log_dir, "notes.txt")).write_text("ignore me\n")
        Path(os.path.join(self.log_dir, "summary.jsonl")).write_text("not-an-agent\n")
        Path(os.path.join(self.log_dir, "agent-1.txt")).write_text("wrong-ext\n")
        summ = merge(self.log_dir, self.succ, self.fail)
        self.assertEqual(summ["merged"], 1)

    def test_skips_blank_lines(self):
        p = os.path.join(self.log_dir, "agent-0.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps({"agent_id": "0", "unit": "u1", "ok": True}) + "\n")
            f.write("\n")
            f.write("   \n")
            f.write(json.dumps({"agent_id": "0", "unit": "u2", "ok": True}) + "\n")
        summ = merge(self.log_dir, self.succ, self.fail)
        self.assertEqual(summ["merged"], 2)

    def test_empty_log_dir_yields_zeros(self):
        summ = merge(self.log_dir, self.succ, self.fail)
        self.assertEqual(summ, {"merged": 0, "successes": 0, "failures": 0})

    def test_appends_across_calls(self):
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "u1", "ok": True}])
        merge(self.log_dir, self.succ, self.fail)
        # a second, independent batch (fresh key) appends; the first result is not lost
        shutil.rmtree(self.log_dir); os.makedirs(self.log_dir)
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "u2", "ok": True}])
        merge(self.log_dir, self.succ, self.fail)
        self.assertEqual([r["unit"] for r in self._read(self.succ)], ["u1", "u2"])

    def test_missing_ok_key_counts_as_failure(self):
        # row.get("ok") is falsy when absent -> failures bucket
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "u1"}])
        summ = merge(self.log_dir, self.succ, self.fail)
        self.assertEqual(summ["failures"], 1)

    def test_creates_parent_dir_of_successes_path(self):
        nested = os.path.join(self.tmp, "deep", "nested")
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "u1", "ok": True}])
        merge(self.log_dir, os.path.join(nested, "s.jsonl"), os.path.join(nested, "f.jsonl"))
        self.assertTrue(os.path.exists(os.path.join(nested, "s.jsonl")))

    def test_bare_filename_paths_work(self):
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "u1", "ok": True}])
        cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            summ = merge(self.log_dir, "s.jsonl", "f.jsonl")   # dirname("") -> "." fallback
            self.assertEqual(summ["successes"], 1)
            self.assertTrue(os.path.exists(os.path.join(self.tmp, "s.jsonl")))
        finally:
            os.chdir(cwd)

    def test_processes_agent_files_in_sorted_order(self):
        _agent_log(self.log_dir, "2", [{"agent_id": "2", "unit": "c", "ok": True}])
        _agent_log(self.log_dir, "0", [{"agent_id": "0", "unit": "a", "ok": True}])
        _agent_log(self.log_dir, "1", [{"agent_id": "1", "unit": "b", "ok": True}])
        merge(self.log_dir, self.succ, self.fail)
        # sorted() over agent-0, agent-1, agent-2 -> units a, b, c in that order
        self.assertEqual([r["unit"] for r in self._read(self.succ)], ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()

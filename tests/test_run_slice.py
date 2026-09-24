"""corral.core.run_slice -- run one agent's slice in isolation and write its OWN per-agent log.
Pins: the log name is unique per agent; a raising unit becomes a logged failure (never a crash);
prepare/teardown are wired correctly, including that teardown does not fire without a workdir."""
import json
import os
import shutil
import tempfile
import unittest

from _pathfix import core  # noqa: E402
run_slice = core.run_slice


class RunSliceTest(unittest.TestCase):
    def setUp(self):
        self.log_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.log_dir, ignore_errors=True)

    def _lines(self, agent_id):
        p = os.path.join(self.log_dir, "agent-%s.jsonl" % agent_id)
        with open(p, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_writes_uniquely_named_log_with_one_line_per_unit(self):
        run_slice("0", ["u1", "u2", "u3"], lambda u, w: (True, "ok"), self.log_dir)
        self.assertTrue(os.path.exists(os.path.join(self.log_dir, "agent-0.jsonl")))
        self.assertEqual(len(self._lines("0")), 3)

    def test_returns_the_results_list(self):
        res = run_slice("0", ["u1", "u2"], lambda u, w: (True, "ok"), self.log_dir)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["unit"], "u1")

    def test_ok_and_note_are_recorded_from_work_fn(self):
        run_slice("0", ["a"], lambda u, w: (False, "GAP: nope"), self.log_dir)
        row = self._lines("0")[0]
        self.assertIs(row["ok"], False)
        self.assertEqual(row["note"], "GAP: nope")

    def test_a_raising_unit_is_logged_as_failure_not_a_crash(self):
        def work(u, w):
            if u == "boom":
                raise ValueError("kaboom")
            return (True, "ok")
        res = run_slice("0", ["fine", "boom", "also-fine"], work, self.log_dir)
        by_unit = {r["unit"]: r for r in res}
        self.assertIs(by_unit["boom"]["ok"], False)
        self.assertIn("raised:", by_unit["boom"]["note"])
        self.assertIn("kaboom", by_unit["boom"]["note"])
        self.assertIs(by_unit["fine"]["ok"], True)      # the raise did not poison its neighbours
        self.assertIs(by_unit["also-fine"]["ok"], True)

    def test_a_work_fn_returning_a_non_tuple_becomes_a_failure(self):
        # ok, note = <non-iterable> raises inside the try -> caught -> logged failure
        res = run_slice("0", ["x"], lambda u, w: True, self.log_dir)
        self.assertIs(res[0]["ok"], False)
        self.assertIn("raised:", res[0]["note"])

    def test_prepare_supplies_the_workdir_to_work_fn(self):
        seen = []
        run_slice("0", ["x", "y"], lambda u, w: seen.append(w) or (True, "ok"),
                  self.log_dir, prepare=lambda aid: "/clone/%s" % aid)
        self.assertEqual(seen, ["/clone/0", "/clone/0"])  # same private workdir for the whole slice

    def test_prepare_receives_the_agent_id(self):
        got = []
        run_slice("agent-7", ["x"], lambda u, w: (True, "ok"), self.log_dir,
                  prepare=lambda aid: got.append(aid) or "/wd")
        self.assertEqual(got, ["agent-7"])

    def test_teardown_is_called_with_the_workdir(self):
        torn = []
        run_slice("0", ["x"], lambda u, w: (True, "ok"), self.log_dir,
                  prepare=lambda aid: "/wd", teardown=lambda wd: torn.append(wd))
        self.assertEqual(torn, ["/wd"])

    def test_teardown_fires_even_though_units_are_caught(self):
        torn = []
        run_slice("0", ["x"], lambda u, w: (_ for _ in ()).throw(RuntimeError("x")),
                  self.log_dir, prepare=lambda aid: "/wd", teardown=lambda wd: torn.append(wd))
        self.assertEqual(torn, ["/wd"])  # finally-block teardown

    def test_teardown_not_called_without_a_workdir(self):
        torn = []
        run_slice("0", ["x"], lambda u, w: (True, "ok"), self.log_dir,
                  prepare=None, teardown=lambda wd: torn.append(wd))
        self.assertEqual(torn, [])  # prepare=None -> workdir None -> teardown must NOT fire

    def test_empty_slice_writes_an_empty_log(self):
        res = run_slice("0", [], lambda u, w: (True, "ok"), self.log_dir)
        self.assertEqual(res, [])
        self.assertEqual(self._lines("0"), [])

    def test_log_dir_is_created_if_missing(self):
        nested = os.path.join(self.log_dir, "made", "here")
        run_slice("0", ["x"], lambda u, w: (True, "ok"), nested)
        self.assertTrue(os.path.exists(os.path.join(nested, "agent-0.jsonl")))

    def test_every_log_line_is_valid_json_matching_results(self):
        res = run_slice("0", ["u1", "u2"], lambda u, w: (True, "n"), self.log_dir)
        self.assertEqual([r["unit"] for r in self._lines("0")], [r["unit"] for r in res])

    def test_workdir_is_none_when_no_prepare(self):
        seen = []
        run_slice("0", ["x"], lambda u, w: seen.append(w) or (True, "ok"), self.log_dir)
        self.assertEqual(seen, [None])


if __name__ == "__main__":
    unittest.main()

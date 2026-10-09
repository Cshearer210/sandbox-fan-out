"""corral scoreboard: a fan-out's merged results read back into a classified tally."""
import os, sys, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from corral.core import fanout          # noqa: E402
from corral.scoreboard import summarize, _verdict, main, RESULT_FILES  # noqa: E402


class ScoreboardTest(unittest.TestCase):
    def test_tally_groups_by_verdict(self):
        d = tempfile.mkdtemp()
        try:
            def work(u, w):
                return (u % 2 == 0, ("CAUGHT: %d" % u) if u % 2 == 0 else ("GAP: %d" % u))
            fanout(list(range(10)), work, n_agents=3, out_dir=d)
            t = summarize(d)
            self.assertEqual(t["units"], 10)
            self.assertEqual(t["successes"], 5)
            self.assertEqual(t["by_verdict"].get("CAUGHT"), 5)
            self.assertEqual(t["by_verdict"].get("GAP"), 5)
        finally:
            shutil.rmtree(d, ignore_errors=True)


    def test_verdict_classifier_boundaries(self):     # kills L22 (head AND len<=24 AND no-space)
        self.assertEqual(_verdict("CAUGHT: something"), "CAUGHT")   # valid verdict
        self.assertEqual(_verdict(": no head"), "")                 # empty head -> not a verdict
        self.assertEqual(_verdict("two words: x"), "")              # head has a space -> not a verdict
        self.assertEqual(_verdict("x" * 25 + ": y"), "")            # head >24 chars -> not a verdict
        self.assertEqual(_verdict("plain note no colon"), "")       # no colon at all

    def test_main_argv_guard(self):                   # kills L62 (argv or [])
        self.assertEqual(main(None), 2)               # None -> [] -> usage; the `and` mutant crashes
        self.assertEqual(main([]), 2)                 # empty -> usage

    # ------------------------------------------------------------------ 2026-10-09
    # A SCAN THAT READ NOTHING MUST NEVER EXIT 0. `main` used to `return 0` unconditionally, so
    # an empty directory, a directory that did not exist, and a FILE passed where a directory
    # belongs all reported a clean bill of health. The commonest first-morning mistake with any
    # tool is pointing it at the wrong folder, and corral told those users their run was fine.
    # Found by a hostile-input harness that feeds every published tool an unreadable target;
    # corral was the only one of the four that did not refuse.
    #
    # The result-file names come from scoreboard.RESULT_FILES rather than being typed here, so
    # this test cannot drift from the format the tool actually reads.
    OKF = RESULT_FILES[0][0]
    BADF = RESULT_FILES[1][0]

    def _dir(self, **files):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        for name, body in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(body)
        return d

    def test_empty_directory_is_could_not_tell(self):
        self.assertEqual(main([self._dir()]), 2)

    def test_missing_directory_is_could_not_tell(self):
        self.assertEqual(main([os.path.join(self._dir(), "nope")]), 2)

    def test_a_file_where_a_directory_belongs_is_could_not_tell(self):
        d = self._dir(**{"afile": "x"})
        self.assertEqual(main([os.path.join(d, "afile")]), 2)

    def test_result_files_present_but_no_rows_is_could_not_tell(self):
        # NOT the same as the three above: this IS a fan-out output directory. It recorded
        # nothing, which is a fact about the run and still not something to call clean.
        self.assertEqual(main([self._dir(**{self.OKF: ""})]), 2)

    def test_a_corrupt_line_is_reported_not_a_traceback(self):
        # It used to raise ValueError straight out of summarize(), so the command died with a
        # traceback and exit 1. One bad line in a client's merged file is a thing to report.
        d = self._dir(**{self.OKF:
                         'not json at all\n{"unit":"u","ok":true,"note":"CAUGHT: x"}\n'})
        self.assertEqual(main([d]), 2)
        t = summarize(d)
        self.assertEqual(len(t["unreadable"]), 1)
        self.assertEqual(t["units"], 1)               # the good line still scores

    def test_a_real_run_still_scores_zero(self):
        # THE GUARD CASE: the fix must not turn a healthy run into a refusal.
        d = self._dir(**{self.OKF: '{"unit":"a","ok":true,"note":"CAUGHT: one"}\n'
                                   '{"unit":"b","ok":true,"note":"CAUGHT: two"}\n'})
        self.assertEqual(main([d]), 0)

    def test_a_run_with_failures_still_exits_zero(self):
        # DELIBERATE, and it is the boundary of this fix: the failures are the REPORT's content,
        # not this command's verdict. The command's job is to read the run, and it did. Making
        # failures exit 1 is a defensible design, is not the defect that was reported, and would
        # change what a client's `corral scoreboard && next-step` does -- so it stayed out.
        d = self._dir(**{self.OKF: '{"unit":"a","ok":true,"note":"CAUGHT: one"}\n',
                         self.BADF: '{"unit":"b","ok":false,"note":"GAP: missed"}\n'})
        self.assertEqual(main([d]), 0)

    def test_summarize_reports_which_files_it_found(self):
        d = self._dir(**{self.BADF: '{"unit":"b","ok":false,"note":"GAP: x"}\n'})
        self.assertEqual(summarize(d)["found"], [self.BADF])
        self.assertEqual(summarize(self._dir())["found"], [])


if __name__ == "__main__":
    unittest.main()

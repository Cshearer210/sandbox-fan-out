"""corral scoreboard: a fan-out's merged results read back into a classified tally."""
import os, sys, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from corral.core import fanout          # noqa: E402
from corral.scoreboard import summarize, _verdict, main  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

"""corral scoreboard: a fan-out's merged results read back into a classified tally."""
import os, sys, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from corral.core import fanout          # noqa: E402
from corral.scoreboard import summarize  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

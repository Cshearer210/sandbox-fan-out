"""corral.demo.main -- the self-contained 15-second demonstration. Pins its deterministic counts
(12 checks, every 5th fails), its exit code, that it writes per-agent logs plus a single merge, and
that it cleans up its temp directory afterward (no leak)."""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from _pathfix import demo  # noqa: E402


def _run():
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = demo.main([])
    return code, buf.getvalue()


class DemoTest(unittest.TestCase):
    def test_returns_zero(self):
        code, _ = _run()
        self.assertEqual(code, 0)

    def test_deterministic_counts_in_output(self):
        # 12 units, every 5th (0, 5, 10) "fails" -> 3 failures, 9 successes across 4 agents
        _, out = _run()
        self.assertIn("agents: 4", out)
        self.assertIn("merged: 12", out)
        self.assertIn("successes: 9", out)
        self.assertIn("failures: 3", out)

    def test_mentions_per_agent_logs_and_single_merge(self):
        _, out = _run()
        self.assertIn("logs/agent-", out)
        self.assertIn("successes.jsonl", out)
        self.assertIn("failures.jsonl", out)

    def test_points_at_plan_prompts_for_real_fanout(self):
        _, out = _run()
        self.assertIn("plan_prompts", out)

    def test_cleans_up_its_temp_dir(self):
        # capture the dir the demo created and confirm it is gone afterward
        created = {}
        real_mkdtemp = tempfile.mkdtemp

        def spy(*a, **k):
            d = real_mkdtemp(*a, **k)
            created["dir"] = d
            return d

        with mock.patch("corral.demo.tempfile.mkdtemp", side_effect=spy):
            with redirect_stdout(io.StringIO()):
                demo.main([])
        self.assertIn("dir", created)
        self.assertFalse(os.path.exists(created["dir"]))  # temp dir removed on exit


if __name__ == "__main__":
    unittest.main()

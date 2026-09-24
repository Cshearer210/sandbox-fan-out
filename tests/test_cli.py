"""The command line: `python3 -m corral [demo|scoreboard <out_dir>|--help]`. Exercises corral.__main__.main
directly (return codes) and end-to-end as a subprocess, capturing stdout so the routing, the help
text, the usage/error exit codes, and the scoreboard sub-command are all pinned to real output."""
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from _pathfix import ROOT  # noqa: E402
from corral.__main__ import main  # noqa: E402


def _capture(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class MainReturnCodeTest(unittest.TestCase):
    def test_no_args_runs_demo_and_returns_zero(self):
        code, out = _capture([])
        self.assertEqual(code, 0)
        self.assertIn("corral demo", out)   # the demo actually ran

    def test_demo_arg_runs_demo(self):
        code, out = _capture(["demo"])
        self.assertEqual(code, 0)
        self.assertIn("agents:", out)

    def test_help_flag_variants_return_zero_and_print_usage(self):
        for arg in ("-h", "--help", "help"):
            code, out = _capture([arg])
            self.assertEqual(code, 0, arg)
            self.assertIn("python3 -m corral", out)
            self.assertIn("scoreboard", out)

    def test_unknown_command_returns_two_and_prints_usage(self):
        code, out = _capture(["frobnicate"])
        self.assertEqual(code, 2)
        self.assertIn("usage", out.lower())

    def test_scoreboard_without_dir_returns_two(self):
        code, out = _capture(["scoreboard"])
        self.assertEqual(code, 2)
        self.assertIn("usage", out.lower())

    def test_scoreboard_with_dir_returns_zero(self):
        d = tempfile.mkdtemp()
        try:
            code, out = _capture(["scoreboard", d])
            self.assertEqual(code, 0)
            self.assertIn("corral scoreboard", out)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_main_reads_sys_argv_when_argv_is_none(self):
        # main(None) must consult sys.argv[1:]; patch it to the help command
        with mock.patch.object(sys, "argv", ["prog", "--help"]):
            code, out = _capture(None)
        self.assertEqual(code, 0)
        self.assertIn("python3 -m corral", out)


class ModuleInvocationTest(unittest.TestCase):
    """Prove `python3 -m corral ...` works as an actual process, not just as a function call."""

    def _run(self, *args):
        return subprocess.run([sys.executable, "-m", "corral", *args],
                              cwd=ROOT, capture_output=True, text=True)

    def test_module_demo_exits_zero(self):
        r = self._run("demo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("merged: 12", r.stdout)

    def test_module_help_exits_zero(self):
        r = self._run("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("scoreboard", r.stdout)

    def test_module_scoreboard_no_dir_exits_two(self):
        r = self._run("scoreboard")
        self.assertEqual(r.returncode, 2)

    def test_module_scoreboard_reads_a_real_run(self):
        d = tempfile.mkdtemp()
        try:
            # produce a real run first, then score it through the CLI
            from corral.core import fanout
            fanout(list(range(6)), lambda u, w: (u % 2 == 0, ("CAUGHT: %d" % u) if u % 2 == 0
                   else ("GAP: %d" % u)), 3, d)
            r = self._run("scoreboard", d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("CAUGHT", r.stdout)
            self.assertIn("GAP", r.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

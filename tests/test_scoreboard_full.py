"""corral.scoreboard -- read a fan-out's merged results back into a classified tally and print it.
Complements tests/test_scoreboard.py: covers summarize's edge cases, the report() renderer (empty
and populated), the _verdict classifier boundaries, and main()'s exit codes on real directories."""
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

from _pathfix import scoreboard  # noqa: E402
summarize, report, _verdict, main = (scoreboard.summarize, scoreboard.report,
                                     scoreboard._verdict, scoreboard.main)


def _write(dir_, name, rows):
    with open(os.path.join(dir_, name), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


class SummarizeTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_empty_dir_is_all_zeros(self):
        t = summarize(self.d)
        self.assertEqual(t, {"successes": 0, "failures": 0, "by_verdict": {}, "units": 0})

    def test_counts_successes_and_failures_from_the_two_files(self):
        _write(self.d, "successes.jsonl", [{"unit": "a", "note": "OK"}, {"unit": "b", "note": "OK"}])
        _write(self.d, "failures.jsonl", [{"unit": "c", "note": "boom"}])
        t = summarize(self.d)
        self.assertEqual(t["successes"], 2)
        self.assertEqual(t["failures"], 1)
        self.assertEqual(t["units"], 3)

    def test_groups_by_verdict_token(self):
        _write(self.d, "successes.jsonl", [{"unit": "a", "note": "CAUGHT: x"},
                                           {"unit": "b", "note": "CAUGHT: y"}])
        _write(self.d, "failures.jsonl", [{"unit": "c", "note": "GAP: z"}])
        t = summarize(self.d)
        self.assertEqual(t["by_verdict"], {"CAUGHT": 2, "GAP": 1})

    def test_note_without_verdict_defaults_to_ok_or_fail(self):
        _write(self.d, "successes.jsonl", [{"unit": "a", "note": "just words"}])
        _write(self.d, "failures.jsonl", [{"unit": "b", "note": "also words"}])
        t = summarize(self.d)
        self.assertEqual(t["by_verdict"].get("OK"), 1)   # success with no verdict -> OK
        self.assertEqual(t["by_verdict"].get("FAIL"), 1)  # failure with no verdict -> FAIL

    def test_only_successes_file_present(self):
        _write(self.d, "successes.jsonl", [{"unit": "a", "note": "OK"}])
        t = summarize(self.d)
        self.assertEqual(t["units"], 1)
        self.assertEqual(t["failures"], 0)

    def test_blank_lines_are_ignored(self):
        with open(os.path.join(self.d, "successes.jsonl"), "w") as f:
            f.write(json.dumps({"unit": "a", "note": "OK"}) + "\n\n   \n")
        self.assertEqual(summarize(self.d)["units"], 1)


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_empty_report_says_no_results(self):
        buf = io.StringIO()
        t = report(self.d, out=buf)
        self.assertEqual(t["units"], 0)
        self.assertIn("no merged results", buf.getvalue())

    def test_populated_report_shows_totals_and_verdicts(self):
        _write(self.d, "successes.jsonl", [{"unit": "a", "note": "CAUGHT: x"},
                                           {"unit": "b", "note": "CAUGHT: y"}])
        _write(self.d, "failures.jsonl", [{"unit": "c", "note": "GAP: z"}])
        buf = io.StringIO()
        report(self.d, out=buf)
        text = buf.getvalue()
        self.assertIn("3 units", text)
        self.assertIn("2 successes", text)
        self.assertIn("1 failures", text)
        self.assertIn("CAUGHT", text)
        self.assertIn("GAP", text)

    def test_report_returns_the_same_tally_as_summarize(self):
        _write(self.d, "successes.jsonl", [{"unit": "a", "note": "OK"}])
        self.assertEqual(report(self.d, out=io.StringIO()), summarize(self.d))

    def test_verdicts_are_ordered_by_descending_count(self):
        _write(self.d, "successes.jsonl", [{"unit": str(i), "note": "MANY: x"} for i in range(3)]
               + [{"unit": "z", "note": "FEW: y"}])
        buf = io.StringIO()
        report(self.d, out=buf)
        text = buf.getvalue()
        self.assertLess(text.index("MANY"), text.index("FEW"))  # the bigger group prints first


class VerdictTest(unittest.TestCase):
    def test_valid_single_token_verdict_is_upper_cased(self):
        self.assertEqual(_verdict("caught: something"), "CAUGHT")

    def test_empty_head_is_not_a_verdict(self):
        self.assertEqual(_verdict(": no head"), "")

    def test_head_with_a_space_is_not_a_verdict(self):
        self.assertEqual(_verdict("two words: x"), "")

    def test_over_24_char_head_is_not_a_verdict(self):
        self.assertEqual(_verdict("x" * 25 + ": y"), "")

    def test_exactly_24_char_head_is_a_verdict(self):
        head = "x" * 24
        self.assertEqual(_verdict(head + ": y"), head.upper())  # boundary: 24 is allowed

    def test_no_colon_is_not_a_verdict(self):
        self.assertEqual(_verdict("plain note"), "")

    def test_none_and_empty_are_handled(self):
        self.assertEqual(_verdict(None), "")
        self.assertEqual(_verdict(""), "")


class MainTest(unittest.TestCase):
    def test_no_args_returns_two_with_usage(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main([])
        self.assertEqual(code, 2)
        self.assertIn("usage", buf.getvalue().lower())

    def test_none_argv_returns_two(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(None), 2)

    def test_with_dir_returns_zero_and_prints(self):
        d = tempfile.mkdtemp()
        try:
            _write(d, "successes.jsonl", [{"unit": "a", "note": "OK"}])
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main([d])
            self.assertEqual(code, 0)
            self.assertIn("corral scoreboard", buf.getvalue())
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

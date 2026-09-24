"""corral.core.Result -- the per-unit outcome record. It is a dict subclass whose .make()
builds one normalized row (agent_id, unit, ok, note, at). These tests pin the coercions that
the merge/scoreboard layers rely on: unit is always a str, ok always a real bool, note a str."""
import json
import time
import unittest

from _pathfix import core  # noqa: E402
Result = core.Result


class ResultShapeTest(unittest.TestCase):
    def test_is_a_dict_subclass(self):
        r = Result.make("0", "u1", True)
        self.assertIsInstance(r, dict)
        self.assertIsInstance(r, Result)

    def test_carries_all_five_keys(self):
        r = Result.make("7", "unit-x", True, "note here")
        self.assertEqual(set(r), {"agent_id", "unit", "ok", "note", "at"})

    def test_unit_is_coerced_to_str(self):
        r = Result.make("0", 42, True)
        self.assertEqual(r["unit"], "42")
        self.assertIsInstance(r["unit"], str)

    def test_ok_is_coerced_to_real_bool(self):
        self.assertIs(Result.make("0", "u", 1)["ok"], True)     # truthy int -> True
        self.assertIs(Result.make("0", "u", 0)["ok"], False)    # falsy int -> False
        self.assertIs(Result.make("0", "u", "")["ok"], False)   # empty str -> False
        self.assertIs(Result.make("0", "u", "x")["ok"], True)   # non-empty str -> True

    def test_note_is_coerced_to_str_and_defaults_empty(self):
        self.assertEqual(Result.make("0", "u", True)["note"], "")          # default
        self.assertEqual(Result.make("0", "u", True, 123)["note"], "123")  # coerced

    def test_agent_id_preserved_verbatim(self):
        self.assertEqual(Result.make("agent-9", "u", True)["agent_id"], "agent-9")

    def test_timestamp_is_iso_like_and_parseable(self):
        r = Result.make("0", "u", True)
        # 'at' must round-trip through the exact format core.py wrote it with
        parsed = time.strptime(r["at"], "%Y-%m-%dT%H:%M:%S")
        self.assertEqual(parsed.tm_year >= 2020, True)

    def test_serialises_to_one_json_object(self):
        r = Result.make("0", "u1", False, "GAP: x")
        round_tripped = json.loads(json.dumps(r))
        self.assertEqual(round_tripped["unit"], "u1")
        self.assertIs(round_tripped["ok"], False)
        self.assertEqual(round_tripped["note"], "GAP: x")


if __name__ == "__main__":
    unittest.main()

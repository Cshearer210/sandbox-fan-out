"""A real caller for the two must-stay-quiet cases.

⛔ WHY THIS FILE EXISTS, and it is a correction to this fixture rather than to the tool:
the first run flagged both quiet cases as `function-unwired`, which was TRUE of the fixture --
a three-file directory has no callers by construction -- and NOT a statement about the pattern
being tested. Without this file the fixture manufactures a finding and then blames the tool.

With a caller present, `function-unwired` should fall silent and only a GENUINE over-fire
remains.
"""
from three_valued import freshness_gate
from ignored_param import chk_index_is_current


def run_all_checks(rows):
    verdict = freshness_gate(rows)
    holding = chk_index_is_current(None)
    return verdict, holding


if __name__ == "__main__":
    print(run_all_checks([{"age_h": 1, "score": 9, "floor": 5}]))

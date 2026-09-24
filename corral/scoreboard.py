# CALLED BY: corral/__main__.py  (`python3 -m corral scoreboard <out_dir>`)
# FIRES WHEN: asked  a session wants the classified tally of a fan-out run's merged results.
"""The scoreboard half of the tool. A fan-out writes successes.jsonl + failures.jsonl; this reads
them back and prints a classified tally -- grouped by the VERDICT carried in each result's note
(e.g. 'CAUGHT: ...', 'GAP: ...'), so a large run is read at a glance instead of line by line.

Pairs with fanout(): fan the work out safely, then score what came back. Reads only."""
from __future__ import annotations

import json
import os
import sys

__all__ = ["summarize", "report"]


def _verdict(note):
    """The classifier: the token before the first ':' in a note is the verdict, else ok/fail."""
    note = (note or "").strip()
    if ":" in note:
        head = note.split(":", 1)[0].strip()
        if head and len(head) <= 24 and " " not in head:
            return head.upper()
    return ""


def summarize(out_dir):
    """Read a fan-out's merged results into a tally: totals + a breakdown by verdict."""
    tally = {"successes": 0, "failures": 0, "by_verdict": {}, "units": 0}
    for name, ok in (("successes.jsonl", True), ("failures.jsonl", False)):
        path = os.path.join(out_dir, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                tally["units"] += 1
                tally["successes" if ok else "failures"] += 1
                v = _verdict(row.get("note")) or ("OK" if ok else "FAIL")
                tally["by_verdict"][v] = tally["by_verdict"].get(v, 0) + 1
    return tally


def report(out_dir, out=None):
    out = sys.stdout if out is None else out   # late-bind so a redirected sys.stdout is honoured
    t = summarize(out_dir)
    out.write("corral scoreboard  %s\n%s\n" % (out_dir, "=" * 56))
    if not t["units"]:
        out.write("  no merged results found (run a fan-out first).\n")
        return t
    out.write("  %d units  ->  %d successes, %d failures\n"
              % (t["units"], t["successes"], t["failures"]))
    out.write("  by verdict:\n")
    for v, n in sorted(t["by_verdict"].items(), key=lambda kv: -kv[1]):
        out.write("    %-16s %d\n" % (v, n))
    return t


def main(argv=None):
    argv = list(argv or [])
    if not argv:
        sys.stdout.write("usage: python3 -m corral scoreboard <out_dir>\n")
        return 2
    report(argv[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

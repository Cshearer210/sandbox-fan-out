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


RESULT_FILES = (("successes.jsonl", True), ("failures.jsonl", False))


def summarize(out_dir):
    """Read a fan-out's merged results into a tally: totals + a breakdown by verdict.

    ⛔ IT NOW REPORTS WHAT IT COULD READ, not just what it counted. `found` lists the result
    files that were actually there and `unreadable` names any line it could not parse, because a
    tally of 0 is produced by three completely different situations -- a real run that scored
    nothing, a directory that is not a fan-out output at all, and a file that is corrupt -- and
    the caller cannot tell them apart from the numbers alone.
    """
    tally = {"successes": 0, "failures": 0, "by_verdict": {}, "units": 0,
             "found": [], "unreadable": []}
    for name, ok in RESULT_FILES:
        path = os.path.join(out_dir, name)
        if not os.path.exists(path):
            continue
        tally["found"].append(name)
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError as e:
                    # A corrupt line used to raise straight out of here, so the whole command
                    # died with a traceback and exit 1. A client's merged file with one bad line
                    # is a thing to REPORT, not to crash on, and the rest of the run still scores.
                    tally["unreadable"].append("%s line %d: %s" % (name, n, str(e)[:60]))
                    continue
                if not isinstance(row, dict):
                    tally["unreadable"].append("%s line %d: not an object" % (name, n))
                    continue
                tally["units"] += 1
                tally["successes" if ok else "failures"] += 1
                v = _verdict(row.get("note")) or ("OK" if ok else "FAIL")
                tally["by_verdict"][v] = tally["by_verdict"].get(v, 0) + 1
    return tally


def why_unreadable(out_dir):
    """Why can this target not be scored? Returns a plain sentence, or None if it can be.

    ⛔⛔ THE BUG THIS EXISTS FOR, AND IT IS THE WORST SHAPE A TOOL LIKE THIS CAN HAVE. Until
    2026-10-09 `scoreboard` returned 0 for an EMPTY directory, for a directory that DOES NOT
    EXIST, and for a FILE passed where a directory belongs. It printed "no merged results found"
    and exited 0 -- a clean bill of health for a scan that read nothing. The commonest mistake
    anyone makes on their first morning with a tool is pointing it at the wrong folder, and this
    told them everything was fine. A zero that means "I could not look" must never share an exit
    code with a zero that means "I looked and all is well".
    """
    if not os.path.exists(out_dir):
        return ("%s does not exist. I wanted the OUTPUT DIRECTORY of a fan-out run -- the folder "
                "holding successes.jsonl and/or failures.jsonl." % out_dir)
    if not os.path.isdir(out_dir):
        return ("%s is a file, not a directory. I wanted the OUTPUT DIRECTORY of a fan-out run; "
                "pass the folder, not one file inside it." % out_dir)
    found = [n for n, _ in RESULT_FILES if os.path.exists(os.path.join(out_dir, n))]
    if not found:
        return ("%s holds neither successes.jsonl nor failures.jsonl, so it is not a fan-out "
                "output directory. Run a fan-out first, or point me at the folder its merge "
                "wrote." % out_dir)
    return None


def report(out_dir, out=None):
    out = sys.stdout if out is None else out   # late-bind so a redirected sys.stdout is honoured
    out.write("corral scoreboard  %s\n%s\n" % (out_dir, "=" * 56))
    why = why_unreadable(out_dir)
    if why:
        out.write("  COULD NOT TELL: %s\n" % why)
        return {"successes": 0, "failures": 0, "by_verdict": {}, "units": 0,
                "found": [], "unreadable": [], "could_not_tell": why}
    t = summarize(out_dir)
    if t["unreadable"]:
        out.write("  %d line(s) could not be read:\n" % len(t["unreadable"]))
        for u in t["unreadable"][:10]:
            out.write("    %s\n" % u)
    if not t["units"]:
        t["could_not_tell"] = (
            "%s holds %s but no scoreable rows, so there is nothing to tally. That is not a "
            "clean run -- it is a run that recorded nothing."
            % (out_dir, " and ".join(t["found"])))
        out.write("  COULD NOT TELL: %s\n" % t["could_not_tell"])
        return t
    out.write("  %d units  ->  %d successes, %d failures\n"
              % (t["units"], t["successes"], t["failures"]))
    out.write("  by verdict:\n")
    for v, n in sorted(t["by_verdict"].items(), key=lambda kv: -kv[1]):
        out.write("    %-16s %d\n" % (v, n))
    return t


def main(argv=None):
    """0 it scored the run - 2 it could not tell. `main` used to `return 0` unconditionally,
    which is where the confident clean came from: every branch above it, including the ones that
    read nothing, arrived at the same line.

    ⭐ A SCORED RUN IS 0 EVEN WHEN UNITS FAILED, deliberately. The failures are the REPORT's
    content, not this command's verdict -- the command's job is to read the run, and it did. An
    earlier version of this fix also returned 1 when the tally held failures, which is a
    defensible design and is NOT the defect that was reported, and it broke two existing tests
    that score a real run with deliberate GAP units. Changing what a client's
    `corral scoreboard && next-step` does is a separate decision from refusing to read nothing,
    so only the refusal landed here.
    """
    argv = list(argv or [])
    if not argv:
        sys.stdout.write("usage: python3 -m corral scoreboard <out_dir>\n")
        return 2
    t = report(argv[0])
    if t.get("could_not_tell") or t.get("unreadable"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

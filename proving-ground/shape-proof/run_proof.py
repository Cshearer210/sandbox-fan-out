#!/usr/bin/env python3
# CALLED BY: a shape-classifier harness, and by hand from this folder.
# FIRES WHEN: the shape classifier changes -- it is the FOREIGN ROOT proof.
"""THE SHAPE CLASSIFIER, POINTED AT A MACHINE IT HAS NEVER SEEN, WITH THE ANSWERS PLANTED.

⛔ WHY A SANDBOX AND NOT THE REAL SYSTEM. `a-scan-means-a-full-scan.md` records that pointing a
scanner at a foreign root found two real defects that were invisible at home, both the same shape:
a claim that is true while every method can answer, and false the moment one cannot. The live run
of `tool_triage` cannot tell a correct classifier from one that has memorised this machine --
every facet it reports is about files it has always been able to see.

So: seven files are written here whose CORRECT verdict is known because this script planted it.
The classifier is pointed at this directory with `--population` and its answers are compared.

Chris, 2026-09-19: sandbox testing is the default clause, not an extra step.
"""
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
TRIAGE = os.environ.get("TRIAGE_TOOL", "")   # external; absent is UNKNOWN
LOG = os.environ.get("SANDBOX_RUN_LOG") or os.path.join(HERE, "runs.jsonl")

# name -> (source, the facets that MUST be found, the facet that must block folding)
PLANTED = {
    "scanner_a.py": (
        "import os, sys\n"
        "for a, b, c in os.walk('/srv/corpus/reports'):\n    pass\n"
        "sys.exit(1)\n",
        {"WALKS", "EMITS"}, None),
    "scanner_b.py": (                      # a SIBLING of scanner_a: same shape, same subject
        "import os, sys\n"
        "for a, b, c in os.walk('/srv/corpus/reports'):\n    print(a)\n"
        "sys.exit(1)\n",
        {"WALKS", "EMITS"}, None),
    "cleaner.py": (
        "import os\nos.remove('/srv/corpus/reports/old.txt')\n",
        {"MUTATES"}, "MUTATES"),
    "fetcher.py": (
        "import requests\nrequests.get('https://example.invalid/x')\n",
        {"EXTERNAL"}, "EXTERNAL"),
    "gatekeeper.py": (
        "import sys\nEVENT = 'PreToolUse'\nsys.exit(2)\n",
        {"HOOK", "EMITS"}, "HOOK"),
    "painter.py": (
        "from PIL import Image\nImage.new('RGB', (4, 4))\n",
        {"RENDER"}, "RENDER"),
    # ⛔ THE GUARD, AND IT IS THE POINT OF THE WHOLE FIXTURE. This file TALKS about every
    # dangerous thing and does none of them. A text-matching classifier calls it a
    # render-mutating network tool; an AST one calls it empty.
    "liar.py": (
        '"""This module explains why os.remove, requests and ffmpeg are banned in a checker."""\n'
        "# never call shutil.rmtree here, and never import PIL\n"
        "print('the PreToolUse chain refused this')\n",
        set(), None),
}


def write_fixtures():
    os.makedirs(FIX, exist_ok=True)
    for name, (src, _f, _b) in PLANTED.items():
        with io.open(os.path.join(FIX, name), "w", encoding="utf-8") as fh:
            fh.write(src)
    return len(PLANTED)


def main():
    n = write_fixtures()
    sys.path.insert(0, os.path.dirname(TRIAGE))
    import tool_triage as T

    info, _dupes = T.classify(T.tools(FIX))
    fails, rows = [], []
    for name, (_src, want_f, want_block) in sorted(PLANTED.items()):
        p = os.path.join(FIX, name)
        d = info.get(p)
        if d is None:
            fails.append("%s was never even seen by the population walk" % name)
            continue
        got_f = set(d.get("shape") or [])
        got_b = d.get("cannot_fold")
        ok = got_f == want_f and got_b == want_block
        rows.append({"file": name, "want": sorted(want_f), "got": sorted(got_f),
                     "want_block": want_block, "got_block": got_b, "ok": ok,
                     "verdict": d.get("verdict"), "accepted": d.get("accepted")})
        print("  %-5s %-14s facets %-22s block %-8s verdict %s"
              % ("ok" if ok else "FAIL", name, sorted(got_f), got_b, d.get("verdict")))
        if not ok:
            fails.append("%s: wanted %s/%s got %s/%s"
                         % (name, sorted(want_f), want_block, sorted(got_f), got_b))

    # the two siblings must land in ONE group -- that is the merge the purpose text cannot see
    groups = T.shape_groups(info)
    sib = [k for k, v in groups.items()
           if {os.path.basename(x) for x in v} >= {"scanner_a.py", "scanner_b.py"}]
    print("  %-5s the two identical-shape scanners land in one group (%s)"
          % ("ok" if sib else "FAIL", sib[0] if sib else "they did not"))
    if not sib:
        fails.append("the two sibling scanners were not grouped")

    # nothing may be DELETED here: no impact has been measured in this sandbox
    deleted = [r["file"] for r in rows if r["verdict"] == "DELETE"]
    print("  %-5s no DELETE stands with no impact measured (%d)"
          % ("ok" if not deleted else "FAIL", len(deleted)))
    if deleted:
        fails.append("a DELETE was accepted in a sandbox where nothing has been measured")

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with io.open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "run": "shape-classifier-foreign-root",
            "root": FIX, "planted": n, "failures": fails, "rows": rows}) + "\n")
    print("\n%d planted file(s), %d failure(s) -- logged to %s"
          % (n, len(fails), LOG.replace(os.path.expanduser("~"), "~")))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

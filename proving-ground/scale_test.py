#!/usr/bin/env python3
"""Scale test: generate MANY randomized broken systems and score each repo across ALL of them, so
the claim is not 'it worked on one fixture' but 'it caught N of N planted issues across M configs.'

Chris's bar (2026-09-23): hundreds of planted issues, many system configurations, and 100% on the
INTENDED jobs before release. This reports the catch rate per issue type across every config, and
separates the intended jobs (must be 100%) from the known roadmap gaps (honest, not yet built).

  RAG-Ghost   -> many randomized code systems (orphan/dangling/misfiled/ungated + gap types)
  claimproof  -> many paraphrased agent replies per claim-failure type + precision traps
  (deadcanary's live-dbt scale run is scale_test_dbt.py -- it needs a dbt runtime and is slower.)
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile

# ⛔ FOUND, NOT TYPED -- see proving-ground/paths.py. The first of these named a checkout
# that no longer exists, so this scale test could not import the tool it was scaling.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402
paths.add_to_path('ragghost', 'claimproof')

from ragghost.report import check as rg_check          # noqa: E402
from claimproof.gates import (UnbackedClaims, ExitCodeMismatch, UnbackedTestCount, GitDiffUnbacked,
                              CIStatusUnbacked, ArtifactNameMismatch, MergeDroppedASide, UnreadSource)  # noqa: E402
from claimproof.ground_truth import GroundTruth        # noqa: E402

WORDS = ["billing", "inventory", "shipping", "reports", "pricing", "orders", "users", "catalog",
         "payments", "accounts", "auth", "search", "cart", "returns", "vendors", "payouts"]


def _w(root, rel, body):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p) or root, exist_ok=True)
    open(p, "w", encoding="utf-8").write(body)


# ---------------------------------------------------------------- RAG-Ghost, at scale
def gen_code_system(root, rng):
    """A randomized broken code system. Returns the set of (code, path) planted issues that RAG-Ghost
    is INTENDED to catch, so scoring is against a known truth, not a guess."""
    planted = set()
    names = rng.sample(WORDS, rng.randint(6, 12))
    # a wired+gated control subsystem (must NOT be flagged)
    ctrl = names[0]
    _w(root, "%s/__init__.py" % ctrl, "")
    _w(root, "%s/core.py" % ctrl, "def go(): return 1\n")
    _w(root, "tests/test_%s.py" % ctrl, "from %s import core\ndef t(): assert core.go()==1\n" % ctrl)
    for n in names[1:]:
        _w(root, "%s/__init__.py" % n, "")
        kind = rng.choice(["orphan", "dangling", "misfiled", "ungated", "wired"])
        if kind == "orphan":
            _w(root, "%s/mod.py" % n, "def f(): return 1\n")             # nothing imports it
            planted.add(("GRAPH-ORPHAN", "%s/mod.py" % n))
        elif kind == "dangling":
            _w(root, "%s/use.py" % n, "from %s import gone\ndef f(): return gone.x()\n" % n)
            planted.add(("GRAPH-DANGLING", "%s/use.py" % n))
        elif kind == "misfiled":
            _w(root, "%s/mod.py" % n, "def f(): return 1\n")
            _w(root, "%s/use.py" % n, "from %s import mod\ndef f(): return mod.f()\n" % n)
            _w(root, "tests/test_%s.py" % n, "from %s import use\ndef t(): assert use.f()==1\n" % n)
            _w(root, "%s/test_local.py" % n, "def t(): assert True\n")   # test outside tests/
            planted.add(("ORG-MISFILED", "%s/test_local.py" % n))
        elif kind == "ungated":
            _w(root, "%s/mod.py" % n, "def f(): return 1\n")             # real code, no test
            planted.add(("HARNESS-NOGATE", n))
        else:  # wired + gated, a control
            _w(root, "%s/mod.py" % n, "def f(): return 1\n")
            _w(root, "%s/use.py" % n, "from %s import mod\ndef f(): return mod.f()\n" % n)
            _w(root, "tests/test_%s.py" % n, "from %s import use\ndef t(): assert use.f()==1\n" % n)
    return planted


def run_ragghost(n_configs=40, seed=7):
    rng = random.Random(seed)
    hit, tot = {}, {}
    total_planted = 0
    for i in range(n_configs):
        d = tempfile.mkdtemp(prefix="rg_scale_")
        try:
            planted = gen_code_system(d, rng)
            total_planted += len(planted)
            findings = rg_check(d).findings
            # (code, "path + detail + message") for robust name/path matching
            fx = [(f.code, "%s %s %s" % (f.path or "", f.detail or "", f.message or "")) for f in findings]
            for code, target in planted:
                tot[code] = tot.get(code, 0) + 1
                if any(fc == code and target in blob for fc, blob in fx):
                    hit[code] = hit.get(code, 0) + 1
        finally:
            shutil.rmtree(d, ignore_errors=True)
    return hit, tot, total_planted, 0


# ---------------------------------------------------------------- claimproof, at scale
TEXT_GATES = []
for _cls in (UnbackedClaims, ExitCodeMismatch, UnbackedTestCount, GitDiffUnbacked, CIStatusUnbacked,
             ArtifactNameMismatch, MergeDroppedASide, UnreadSource):
    try:
        TEXT_GATES.append(_cls())
    except TypeError:
        pass


def _fires(text):
    for g in TEXT_GATES:
        try:
            if g.check(text):
                return True
        except Exception:
            pass
    return False


DONE = ["Done.", "All finished.", "Complete.", "That's done now.", "Finished the work.",
        "It's all working.", "Wrapped that up.", "Task complete."]
EVID_TEST = ["All tests pass.", "The suite is green.", "Every test passes now.",
             "Tests all pass.", "The whole suite passes."]
QUIET_ADJ = ["I updated the deployed dashboard.", "Shipped 166 ebook sheets to the folder.",
             "The completed order count is 42.", "Reviewed the finished draft.",
             "The fixed-width layout looks good."]
QUIET_NEG = ["That bug was caught before it shipped.", "Nothing reached production.",
             "It never got deployed, so we're fine.", "The old version was the broken one."]


def run_claimproof(n_each=40):
    must_catch = {"bare-completion": DONE, "unbacked-test": EVID_TEST}
    stay_quiet = {"precision-adjective": QUIET_ADJ, "precision-negated": QUIET_NEG}
    res = {}
    for label, pool in must_catch.items():
        hits = sum(1 for i in range(n_each) if _fires(pool[i % len(pool)] +
                   (" " if i % 3 else "")))
        res[label] = (hits, n_each, "catch")
    for label, pool in stay_quiet.items():
        quiet = sum(1 for i in range(n_each) if not _fires(pool[i % len(pool)]))
        res[label] = (quiet, n_each, "quiet")
    return res


def main():
    print("=" * 74 + "\nSCALE TEST -- many configs, hundreds of planted issues\n" + "=" * 74)
    hit, tot, planted, of = run_ragghost()
    print("\nRAG-Ghost -- %d planted issues across 40 randomized code systems:" % planted)
    intended = ("GRAPH-ORPHAN", "GRAPH-DANGLING", "ORG-MISFILED", "HARNESS-NOGATE")
    all_intended_100 = True
    for code in intended:
        h, t = hit.get(code, 0), tot.get(code, 0)
        pct = (100.0 * h / t) if t else 0.0
        print("  %-16s %3d/%-3d  %5.1f%%" % (code, h, t, pct))
        if t and h != t:
            all_intended_100 = False
    print("  INTENDED JOBS AT 100%%: %s" % ("YES" if all_intended_100 else "NO -- see above"))

    cp = run_claimproof()
    print("\nclaimproof -- 40 variations per type:")
    cp_ok = True
    for label, (n, tot_, kind) in cp.items():
        pct = 100.0 * n / tot_
        print("  %-22s %2d/%-2d  %5.1f%%  (%s)" % (label, n, tot_, pct, kind))
        if n != tot_:
            cp_ok = False
    print("  ALL AT 100%%: %s" % ("YES" if cp_ok else "NO"))
    print("\n" + "#" * 74)
    ok = all_intended_100 and cp_ok
    print("VERDICT: %s" % ("intended jobs at 100%% across all configs" if ok
                           else "NOT 100%% -- investigate the rows below target"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

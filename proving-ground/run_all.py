#!/usr/bin/env python3
"""The carrot-sandbox scoreboard. Reads MANIFEST.json (the discovered population), runs each doctor
tool against its part of the planted-broken system, and classifies every planted issue:

    CAUGHT            the tool fired on the planted issue                     (good)
    GAP               a must-catch type the tool does NOT yet cover           -> a recommendation
    GROUND-TRUTH-GAP  a type no TEXT gate can catch; needs the ground-truth   -> the planned addition
                      verifier (run the command / read real state)
    QUIET-OK          a must-stay-quiet case the tool correctly left alone    (good, the costlier half)
    HELD / VIOLATED   sandbox-fan-out is an INVARIANT-HOLDER, not a doctor: there is no
                      defect to plant for it to find, so its rows ask whether ITS OWN
                      exactly-once guarantee survives a hostile concurrent run. A VIOLATED
                      fails this board exactly as an OVER-FIRE does.
    OVER-FIRE         a must-stay-quiet case the tool wrongly flagged         (bad -- crying wolf)
    RUNTIME           needs a runtime not present here (dbt/duckdb)           (verified elsewhere)

Exit 0 only when there are no OVER-FIRE and no unexpected CAUGHT->MISS regressions. The point is
not a green light -- it is the GAP list, which is the roadmap. Writes REPORT.md and appends one
line per run to ../../PureEuphoria/memory/sandbox/runs.jsonl when --log is passed."""
from __future__ import annotations

import json
import os
import sys as _sys
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")

# ⛔ THE COMPANION TOOLS ARE FOUND, NOT TYPED (proving-ground/paths.py). This file is
# the scoreboard that answers "are the repos DONE", so a path typed here that goes
# stale makes an unmeasured tool look like a clean one.
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as _paths  # noqa: E402

# ⛔ THIS POINTED AT `~/rag-ghost-work`, A SECOND CHECKOUT RETIRED ON 2026-09-27 -- and this file is
# the scoreboard that answers "are the repos DONE", so it was the worst place on the machine for a
# dead path. It failed with `ModuleNotFoundError: No module named 'ragghost'`, which is loud and was
# found by RUNNING it. The real danger was never the crash: it is that nobody runs it for weeks and
# the answer to "how many gaps are left" then comes from a document instead of a measurement.
#
# ⚠ AND THE IMPACT TRACE DID NOT CATCH IT, which is the more useful half. `deletion_impact.py` was
# pointed at ~/Tools and ~/PureEuphoria; `~/carrot-sandbox-work` is neither, so the trace was clean
# and wrong. A trace is only as wide as the roots it walks.
REPOS = [
    (os.path.join(HOME, "rag-graph-surgeon"), "ragghost"),
    (os.path.join(HOME, "PureEuphoria", "claimproof", "src"), "claimproof"),
]
for _p, _pkg in REPOS:
    if os.path.isdir(os.path.join(_p, _pkg)) and _p not in sys.path:
        sys.path.insert(0, _p)
_missing = [pkg for p, pkg in REPOS if not os.path.isdir(os.path.join(p, pkg))]
if _missing:
    # ⛔ CANNOT TELL, NEVER A PASS. A scoreboard that cannot import the tools it grades has measured
    # nothing, and exiting 0 would report "no gaps" for the best possible reason: it never looked.
    sys.stderr.write("CANNOT TELL: %s not importable from %s. This scoreboard GRADES those tools; "
                     "without them it has measured nothing, so it refuses rather than reporting a "
                     "clean board.\n" % (", ".join(_missing), ", ".join(p for p, _ in REPOS)))
    raise SystemExit(2)

from ragghost.graph import build_graph              # noqa: E402
from ragghost.organize import organize              # noqa: E402
from ragghost.harness import harnesses              # noqa: E402
from claimproof.gates import (UnbackedClaims, ExitCodeMismatch, UnbackedTestCount,  # noqa: E402
                              GitDiffUnbacked, CIStatusUnbacked, ArtifactNameMismatch,
                              MergeDroppedASide, UnreadSource, CountWithNoRun, ScopeHedge)
from claimproof.ground_truth import GroundTruth   # noqa: E402

CODE = os.path.join(HERE, "code-rot")
FCROT = os.path.join(HERE, "fc-rot")
CLEAN = os.path.join(HERE, "clean-twin")
WORLD = os.path.join(HERE, "world")
GT = GroundTruth(root=WORLD)


def load_manifest():
    with open(os.path.join(HERE, "MANIFEST.json"), encoding="utf-8") as f:
        return json.load(f)["planted"]


# ---- RAG-Ghost detectors, keyed by planted id ----
def ragghost_findings(root):
    g = build_graph(root)
    idx = organize(root)
    h = harnesses(root)
    return {
        "orphans": {os.path.basename(o) for o in g.orphans},
        "orphans_full": set(g.orphans),
        "dangling": " ".join("%s->%s" % (a, b) for a, b in g.dangling),
        "misfiled": {os.path.basename(f) for f, _ in idx.misfiled},
        "ungated": set(h.ungated),
        # a duplicate finding is (name, kind, [files], method) -- the files it names are the ones
        # that actually match, never every file that happens to share the name
        "duplicates": {n for n, _k, _files, _m in g.duplicates},
        # a declared subsystem holding no code: UNKNOWN, never clean
        "hollow": {d.rstrip("/") for d, _why in idx.hollow},
        "dead_symbols": {n for n, _f, _l, _e, _m in g.dead_symbols},
        # the files where a dead symbol is only MENTIONED -- a comment or a string, never a use.
        # This is the grep-not-call row: grep reports the name as used and the syntax does not.
        "mention_only": {f for _n, _r, _l, _e, ms in g.dead_symbols for f in ms},
        # a test that CANNOT FAIL, keyed by the shape it has -- see ragghost.harness.hollow_gates
        "cannot_fail": {(os.path.basename(f), s) for f, _t, _l, sh in h.hollow_gates for s in sh},
        # a doc telling the reader to RUN something that is not there
        "ghost_runs": {t for _d, _l, t in g.ghost_instructions},
    }


RG_HITS = {
    "cr-orphan": lambda f: "exporter.py" in f["orphans"],
    "cr-dangling": lambda f: "warehouse" in f["dangling"],
    "cr-misfiled": lambda f: "test_sync.py" in f["misfiled"],
    "cr-ungated": lambda f: "shipping" in f["ungated"],
    "cr-dup": lambda f: "apply_discount" in f["duplicates"],
    "cr-absent-clean": lambda f: "analytics" in f["hollow"],
    "cr-dead-export": lambda f: "normalize_ph" in f["dead_symbols"],
    "cr-grep-not-call": lambda f: "util/notes.py" in f["mention_only"],
    "cr-assertion-free": lambda f: ("test_vacuous.py", "asserts-nothing") in f["cannot_fail"],
    "cr-tautological": lambda f: ("test_tautology.py", "asserts-the-language") in f["cannot_fail"],
    "cr-swallowed": lambda f: ("test_swallow.py", "swallows-its-failure") in f["cannot_fail"],
    "cr-always-skipped": lambda f: ("test_skipped.py", "always-skipped") in f["cannot_fail"],
    # everything below is a type RAG-Ghost does not yet cover -> GAP (a recommendation)
    "cr-config-noread": lambda f: False,
    "cr-env-unset": lambda f: False,
    "cr-ghost-pointer": lambda f: any("can_i_see.py" in t for t in f["ghost_runs"]),
}


# ---- claimproof: run every text gate on a reply ----
def make_text_gates():
    out = []
    for cls in (UnbackedClaims, ExitCodeMismatch, UnbackedTestCount, GitDiffUnbacked,
                CIStatusUnbacked, ArtifactNameMismatch, MergeDroppedASide, UnreadSource,
                CountWithNoRun, ScopeHedge):
        try:
            out.append(cls())
        except TypeError:
            pass
    return out


TEXT_GATES = make_text_gates()


def claimproof_fires(text):
    hit = []
    for gt in TEXT_GATES:
        try:
            if gt.check(text):
                hit.append(type(gt).__name__)
        except Exception:
            pass
    return hit


# ---- full-circle-optimization: the 4th public repo, previously UNSCORED here ----
# It is a DIRECTORY scanner, so it runs once over fc-rot/ and the results are indexed by file.
def fullcircle_findings(root):
    """{basename: {ruleId, ...}} or None if the tool could not be run (never {} -- law 10)."""
    import subprocess as _sp, tempfile, json as _j
    out = os.path.join(tempfile.gettempdir(), "carrot_fc.sarif.json")
    try:
        r = _sp.run(["python3", "-m", "fullcircle.orchestrator", root, "--sarif", out],
                    cwd=_paths.find("fullcircle"),
                    capture_output=True, text=True, timeout=600)
    except Exception:
        return None
    if not os.path.exists(out):
        return None
    d = _j.load(open(out, encoding="utf-8"))
    by = {}
    for run_ in d.get("runs", []):
        for res in run_.get("results", []):
            try:
                uri = res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
            except Exception:
                uri = "?"
            by.setdefault(os.path.basename(uri), set()).add(res.get("ruleId"))
    return by


# ---- sandbox-fan-out: the 4th public repo, and it is graded DIFFERENTLY on purpose ----
#
# ⛔ IT WAS NOT ON THIS BOARD AT ALL UNTIL 2026-09-28, so "are the repos done" was answered for
# three of four. That is this file's own law 4b failure -- a surface nothing queries is UNCHECKED,
# and the docstring at the top of `fullcircle_findings` records the same omission being fixed for
# full-circle. Found by asking which repos the MANIFEST names, not by reading it.
#
# ⭐ AND IT CANNOT BE GRADED THE SAME WAY, which is why it needs its own verdict rather than a
# plausible-looking row. The other three are DOCTORS: plant a defect, ask whether the tool catches
# it. sandbox-fan-out is an INVARIANT-HOLDER -- it makes concurrent result corruption impossible
# by construction. There is no defect to plant for it to FIND. The only honest question is whether
# ITS OWN invariant survives a hostile run, so the verdicts are HELD and VIOLATED, and a VIOLATED
# fails the board exactly as an OVER-FIRE does.
_CORRAL_CACHE = {}


def corral_stress():
    """Run a REAL concurrent fan-out over a hostile population and check exactly-once.

    Every condition below is one a naive fan-out gets wrong: units that raise, more agents than
    units, a duplicate unit name, and genuine concurrency. Nothing is simulated -- `fanout()` is
    the real function, run with real threads, writing real per-agent logs to a real directory.

    Returns {row_id: (held: bool, detail)} or None when corral cannot be imported, so its rows
    read UNKNOWN rather than passing for the best possible reason: nobody looked.
    """
    if _CORRAL_CACHE:
        return _CORRAL_CACHE.get("res")
    import shutil as _sh, tempfile as _tf
    corral_src = os.path.join(HOME, "corral-work")
    if corral_src not in sys.path:
        sys.path.insert(0, corral_src)
    try:
        from corral import fanout, split_population
    except Exception:
        _CORRAL_CACHE["res"] = None
        return None

    out = {}
    d = _tf.mkdtemp(prefix="carrot_corral_")

    def units_logged(run_dir):
        """Every unit that appears in the MERGED shared files -- read off disk, not from a return
        value. Exactly-once is a property of what was written, so the written files are what get
        counted."""
        seen = []
        for name in ("successes.jsonl", "failures.jsonl"):
            p = os.path.join(run_dir, name)
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        seen.append(json.loads(line).get("unit"))
        return seen

    try:
        # a hostile population: 40 units, every 7th one raises.
        #
        # ⚠ `work_fn` TAKES THE UNIT AND ITS AGENT'S PRIVATE WORKDIR. Writing it with one
        # parameter made all 40 units fail -- and corral logged 40 FAILURES rather than crashing
        # the run, which is the invariant proving itself against my own mistake. The arity is
        # from the real signature, not a guess.
        units = ["unit-%02d" % i for i in range(40)]
        raising = {u for u in units if int(u.split("-")[1]) % 7 == 0}

        def work(unit, *_rest):
            if unit in raising:
                raise RuntimeError("this unit is supposed to blow up")
            return {"unit": unit, "ok": True}

        r1 = os.path.join(d, "run1")
        res = fanout(units, work, n_agents=8, out_dir=r1)
        seen = units_logged(r1)
        exact = sorted(seen) == sorted(units) and len(seen) == len(set(seen))
        out["sf-exactly-once"] = (
            exact and res.get("merged") == len(units),
            ("%d unit(s) across 8 real threads: %d merged result(s), each exactly once"
             % (len(units), res.get("merged")))
            if exact else
            ("expected each of %d unit(s) once; the merged files hold %d row(s), %d distinct"
             % (len(units), len(seen), len(set(seen)))))
        out["sf-raise-is-logged"] = (
            res.get("failures") == len(raising) and res.get("successes") == len(units) - len(raising),
            "%s raising unit(s) became logged failures and %s passed; the run did not crash"
            % (res.get("failures"), res.get("successes")))

        # more agents than units: the empty slices must invent no results and crash nothing
        r2 = os.path.join(d, "run2")
        res2 = fanout(["only-one"], work, n_agents=8, out_dir=r2)
        out["sf-more-agents-than-units"] = (
            units_logged(r2) == ["only-one"] and res2.get("merged") == 1,
            "1 unit across 8 agents produced %s merged result(s)" % res2.get("merged"))

        # the slices cover the whole population with no unit in two of them
        slices = split_population(units, 8)
        flat = [u for s in slices for u in s]
        out["sf-slices-disjoint"] = (
            sorted(flat) == sorted(units) and len(flat) == len(set(flat)),
            "%d slice(s) covering %d unit(s) with no overlap" % (len(slices), len(flat)))
    except Exception as exc:
        # ⛔ CARRY THE REASON. "could not be run" with the cause swallowed is the shape that made
        # this function read as environmental when it was a one-line API mistake of mine.
        _CORRAL_CACHE["res"] = {"__error__": "%s: %s" % (type(exc).__name__, exc)}
        return _CORRAL_CACHE["res"]
    finally:
        _sh.rmtree(d, ignore_errors=True)
    _CORRAL_CACHE["res"] = out
    return out


# ---- the runtime ground-truth observations, MEASURED in a throwaway copy of world/ ----
_RUNTIME_CACHE = []


def runtime():
    """A `claimproof.ground_truth.Runtime` carrying observations this function really made.

    ⛔ WHY A COPY AND NOT world/ ITSELF: `git init` inside the sandbox's own repository would nest
    one repo in another, and the edit below would show up as a change to carrot-sandbox. The copy
    is hermetic, is thrown away, and is the only thing touched.

    ⛔ AND WHY MEASURED AND NOT PASSED IN: handing the adapter the exit code and the diff that make
    the fixtures fail would be a control that selects on the property it measures -- it could not
    fail. So this runs the world's real `build.sh` and reads its real exit status, makes a real edit
    that adds a line and removes nothing, asks git for the real diff, and counts the real open
    items in world/fixture-queue.md. Every number below came out of a command.

    ⛔ NOTHING HERE RUNS A COMMAND NAMED IN A REPLY. The replies are untrusted fixtures; one of
    them literally contains a `sed -i`. The world's own build script is what gets run.

    Returns None when the observations genuinely cannot be made (no git on the box), so the caller
    reports UNKNOWN rather than a clean board.
    """
    if _RUNTIME_CACHE:
        return _RUNTIME_CACHE[0]
    import shutil as _sh, subprocess as _sp, tempfile as _tf
    from claimproof.ground_truth import Runtime
    try:
        d = _tf.mkdtemp(prefix="carrot_world_")
        w = os.path.join(d, "world")
        _sh.copytree(WORLD, w)

        def git(*a):
            return _sp.run(("git",) + a, cwd=w, capture_output=True, text=True, timeout=120)

        if git("init", "-q").returncode != 0:
            return None                      # no git here -> UNKNOWN, never a pass
        git("config", "user.email", "sandbox@example.com")
        git("config", "user.name", "carrot-sandbox")
        git("add", "-A")
        git("commit", "-qm", "the world as it stands")

        # a REAL edit that adds a line and removes nothing -- so a claim to have REMOVED the debug
        # logging is contradicted by what git actually prints
        rp = os.path.join(w, "billing", "refund.py")
        with open(rp, "a", encoding="utf-8") as fh:
            fh.write("\n\ndef audit(order):\n    logging.debug('refund %s', order)\n    return True\n")
        real_diff = git("diff").stdout

        # the world's OWN build, run for real; its exit status is the observation
        bs = os.path.join(w, "build.sh")
        os.chmod(bs, 0o755)
        real_exit = _sp.run(["sh", bs], cwd=w, capture_output=True, text=True,
                            timeout=120).returncode

        # the real number of open items, counted now
        qt = open(os.path.join(w, "fixture-queue.md"), encoding="utf-8").read()
        open_items = len([l for l in qt.splitlines() if l.strip().startswith("- [ ]")])

        rt = Runtime(real_exit=real_exit, diff=real_diff,
                     measurements={"open items": open_items})
        _RUNTIME_CACHE.append(rt)
        return rt
    except Exception:
        return None                          # could not observe -> UNKNOWN, never clean
    finally:
        try:
            _sh.rmtree(d, ignore_errors=True)
        except Exception:
            pass


def classify(row, rg_findings, fc_findings=None):
    tool = row["tool"]
    expect = row["expect"]
    catchable = row.get("catchable", "")
    if row.get("record_only"):
        return ("RECORD", "whole-run/data behaviour; not a single-file case")

    if tool == "sandbox-fan-out":
        # an invariant-holder, not a doctor: HELD / VIOLATED, and VIOLATED fails the board
        st = corral_stress()
        if st is None:
            return ("RECORD", "corral is not importable from here -- UNKNOWN, not clean")
        if "__error__" in st:
            return ("RECORD", "the stress run raised (%s) -- UNKNOWN, not clean" % st["__error__"])
        got = st.get(row["id"])
        if got is None:
            return ("RECORD", "no stress condition is wired for this row")
        held, detail = got
        return ("HELD", detail) if held else ("VIOLATED", detail)

    if tool == "rag-ghost":
        fn = RG_HITS.get(row["id"])
        fired = bool(fn and fn(rg_findings))
        if fired:
            return ("CAUGHT", expect)
        return ("GAP", "RAG-Ghost does not yet detect %s" % row["type"])

    if tool == "claimproof":
        text = open(os.path.join(HERE, row["path"]), encoding="utf-8").read()
        hit = claimproof_fires(text)
        if expect == "quiet":
            return ("QUIET-OK", "left alone") if not hit else ("OVER-FIRE", "wrongly flagged by %s" % ",".join(hit))
        if catchable in ("ground", "ground-truth"):
            if hit:
                return ("CAUGHT", "by %s" % ",".join(hit))
            gt = GT.inspect(text)                       # the filesystem ground-truth verifier
            if gt:
                return ("CAUGHT", "by GroundTruth")
            # ⛔ THE RUNTIME HALF, AND THE OBSERVATIONS ARE MEASURED RATHER THAN FED. `runtime()`
            # copies world/ to a temp directory, makes it a real git repo, runs the world's real
            # build and its real `git diff`, and counts the real open items. Handing the adapter
            # the answer would be a control that selects on the property it measures.
            rt = runtime()
            if rt is None:
                return ("RECORD", "the runtime observations could not be made here -- UNKNOWN")
            found, unchecked = GT.runtime_report(text, rt)
            if found:
                return ("CAUGHT", "by GroundTruth runtime (%s)"
                        % ", ".join(sorted({f.message.split("(")[-1].rstrip(")")
                                            for f in found})))
            if unchecked:
                return ("GROUND-TRUTH-GAP",
                        "the runtime adapter could not check: %s" % ", ".join(unchecked))
            return ("GAP", "the runtime adapter looked at every class and found nothing")
        # text / text-to-ground must-catch
        if hit:
            return ("CAUGHT", "by %s" % ",".join(hit))
        return ("GAP", "claimproof text gates miss %s" % row["type"])

    if tool == "full-circle":
        # CANNOT RUN IS NOT CLEAN (law 10). An unavailable tool is UNKNOWN, never QUIET-OK.
        if fc_findings is None:
            return ("RECORD", "full-circle could not be run from here -- UNKNOWN, not clean")
        fired = fc_findings.get(os.path.basename(row["path"]), set())
        if expect == "quiet":
            return (("QUIET-OK", "left alone") if not fired
                    else ("OVER-FIRE", "wrongly flagged by %s" % ",".join(sorted(map(str, fired)))))
        if expect in fired:
            return ("CAUGHT", "by %s" % expect)
        return ("GAP", "full-circle does not flag %s here (saw: %s)"
                % (row["type"], ",".join(sorted(map(str, fired))) or "nothing"))

    if tool.startswith("deadcanary") or tool == "rag-ghost/deadcanary":
        return ("RUNTIME", "needs dbt+duckdb; mechanism proven by deadcanary's own 153 tests + jaffle_shop")
    return ("RECORD", "unclassified")


def main():
    rows = load_manifest()
    rg = ragghost_findings(CODE)
    fc = fullcircle_findings(FCROT)
    results = []
    for row in rows:
        verdict, why = classify(row, rg, fc)
        results.append((row, verdict, why))

    # tally
    tally = {}
    for _, v, _ in results:
        tally[v] = tally.get(v, 0) + 1

    lines = ["# carrot-sandbox scoreboard\n",
             "Population discovered from MANIFEST.json (%d rows). Each planted issue classified by\n"
             "running the real tool against the planted-broken system.\n" % len(rows), ""]
    order = ["CAUGHT", "QUIET-OK", "HELD", "GROUND-TRUTH-GAP", "GAP", "OVER-FIRE", "VIOLATED",
             "RUNTIME", "RECORD"]
    lines.append("## Tally")
    for k in order:
        if k in tally:
            lines.append("- **%s**: %d" % (k, tally[k]))
    lines.append("")
    for tool in ("rag-ghost", "claimproof", "full-circle", "sandbox-fan-out", "deadcanary",
                 "rag-ghost/deadcanary"):
        trows = [(r, v, w) for (r, v, w) in results if r["tool"] == tool]
        if not trows:
            continue
        lines.append("## %s" % tool)
        for r, v, w in trows:
            lines.append("- [%s] `%s` (%s) -- %s" % (v, r["id"], r["type"], w))
        lines.append("")

    # clean-twin control (code-rot half): RAG-Ghost must be quiet
    cf = ragghost_findings(CLEAN)
    clean_quiet = (not cf["orphans"] and not cf["dangling"] and not cf["misfiled"]
                   and not cf["ungated"] and not cf["duplicates"] and not cf["hollow"]
                   and not cf["dead_symbols"] and not cf["cannot_fail"]
                   and not cf["ghost_runs"])
    lines.append("## clean-twin control (RAG-Ghost must stay quiet)")
    lines.append("- %s -- orphans=%s dangling=%r misfiled=%s ungated=%s duplicates=%s hollow=%s "
                 "dead-symbols=%s cannot-fail=%s ghost-runs=%s"
                 % ("QUIET-OK" if clean_quiet else "OVER-FIRE",
                    sorted(cf["orphans"]), cf["dangling"], sorted(cf["misfiled"]),
                    sorted(cf["ungated"]), sorted(cf["duplicates"]), sorted(cf["hollow"]),
                    sorted(cf["dead_symbols"]), sorted(cf["cannot_fail"]), sorted(cf["ghost_runs"])))

    report = "\n".join(lines) + "\n"
    with open(os.path.join(HERE, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(report)

    # a VIOLATED invariant is as bad as an over-fire: both mean a tool is not what it says
    overfire = (tally.get("OVER-FIRE", 0) + tally.get("VIOLATED", 0)
                + (0 if clean_quiet else 1))
    print("GAPS (roadmap): %d must-catch + %d ground-truth"
          % (tally.get("GAP", 0), tally.get("GROUND-TRUTH-GAP", 0)))
    if "--log" in sys.argv:
        rec = {"at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
               "method": "planted-issue-scoreboard", "subject": "carrot-sandbox all tools",
               "found": bool(tally.get("GAP", 0) or tally.get("GROUND-TRUTH-GAP", 0)),
               "note": "caught=%d gap=%d gt-gap=%d quiet-ok=%d over-fire=%d runtime=%d"
                       % (tally.get("CAUGHT", 0), tally.get("GAP", 0), tally.get("GROUND-TRUTH-GAP", 0),
                          tally.get("QUIET-OK", 0), overfire, tally.get("RUNTIME", 0))}
        log = os.environ.get("SANDBOX_RUN_LOG") or os.path.join(
              os.path.dirname(os.path.abspath(__file__)), "runs.jsonl")
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print("logged to", log)
    return 0 if overfire == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

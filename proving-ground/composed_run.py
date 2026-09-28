#!/usr/bin/env python3
"""THE COMPOSED RUN -- all three repos working as one loop over a planted-broken system.

⛔ WHY THIS IS A SEPARATE ROW ON THE BOARD, AND NOT A FOURTH SINGLE-REPO SCORE. `run_all.py`
scores each repo's finders against the planted defects: does rag-ghost see the orphan, does
claimproof see the unsupported count, does corral hold its invariants. Every one of those can pass
while the LOOP is broken -- because the loop is a different claim:

    rag-ghost     LOCATES    something is wrong here
    claimproof    JUDGES     and it is real, corroborated, not a false positive
    corral        REPAIRS    and here is the system with it gone, verified

The composition is what full-circle's README promises a stranger, and until this file existed the
promise was checked by nobody. Three green single-repo scores are not evidence about it.

⭐ HIS SANDBOX RULE, 2026-09-27: the best-fitting method PLUS AT LEAST FOUR OTHER ANGLES, and the
run gets logged. The best-fitting method is the planted-defect world. The four other angles are
the ones that separate a working loop from a loop that merely produces output:

    2  THE CLEAN TWIN          the same shape of project with nothing wrong. A pipeline that
                              cannot stay quiet manufactures work, and an over-firing checker
                              gets switched off -- which is worse than a gap (his standard).
    3  REPORT-ONLY IS INERT    the pass without --fix must leave every byte alone. Measured by
                              hashing the tree before and after, never by reading the code.
    4  IDEMPOTENCE             --fix twice. The second run must change nothing. A repair pass
                              that reads state it previously wrote is a silent ratchet, and a
                              single before/after test cannot see it: it only shows on run two.
    5  UNKNOWN IS NOT CLEAN    pointed at something it cannot read, the exit code must be 2.
                              A pipeline that answers "all clear" about a directory it could not
                              open is the one failure that looks exactly like success.

RUN IT:   python3 proving-ground/composed_run.py            # report only
          python3 proving-ground/composed_run.py --log      # and record the row
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as companion  # noqa: E402  -- resolves checkouts by a MARKER, never by folder name

PLANTED = HERE / "code-rot"
RUNS = pathlib.Path(os.path.expanduser("~/PureEuphoria/memory/sandbox/runs.jsonl"))
CLEAN, FOUND, UNKNOWN = 0, 1, 2


def tree_digest(root: pathlib.Path) -> str:
    """One hash over every file's PATH and BYTES, so any edit anywhere changes it.

    ⛔ READ IN BINARY AND NORMALISE THE PATH. Text mode translates newlines on Windows, so a
    digest of literal bytes differs by platform for a file nobody touched -- the exact class the
    portfolio failure register calls digest-assertion-behind-a-text-mode-write.
    """
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_dir() or "__pycache__" in p.parts:
            continue
        h.update(str(p.relative_to(root)).replace(os.sep, "/").encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def clean_twin(dst: pathlib.Path) -> None:
    """A project of the same SHAPE with nothing wrong: real package, real caller, real test.

    ⛔ SYNTHETIC, NEVER A COPY OF THE PLANTED WORLD WITH THE DEFECTS REMOVED. A twin derived from
    the broken tree inherits whatever the removal missed, and then a quiet result proves only that
    the pipeline agrees with my own editing.
    """
    (dst / "shop").mkdir(parents=True)
    (dst / "tests").mkdir(parents=True)
    (dst / "shop" / "__init__.py").write_text("from .pricing import total\n\n__all__ = ['total']\n",
                                              encoding="utf-8")
    (dst / "shop" / "pricing.py").write_text(
        "def total(items, rate):\n"
        "    if rate is None:\n"
        "        return None\n"
        "    return round(sum(i['price'] for i in items) * (1 + rate), 2)\n", encoding="utf-8")
    (dst / "shop" / "cart.py").write_text(
        "from .pricing import total\n\n\n"
        "def checkout(items, rate=0.08):\n"
        "    due = total(items, rate)\n"
        "    if due is None:\n"
        "        raise ValueError('no tax rate')\n"
        "    return due\n", encoding="utf-8")
    (dst / "tests" / "test_pricing.py").write_text(
        "from shop.cart import checkout\n\n\n"
        "def test_checkout_adds_tax():\n"
        "    assert checkout([{'price': 10.0}], 0.10) == 11.0\n\n\n"
        "def test_missing_rate_raises():\n"
        "    import pytest\n"
        "    with pytest.raises(ValueError):\n"
        "        checkout([{'price': 1.0}], None)\n", encoding="utf-8")
    (dst / "README.md").write_text(
        "# shop\n\nA cart that adds tax.\n\n    python3 -m pytest tests\n", encoding="utf-8")


def fc_run(fc_dir: pathlib.Path, target: pathlib.Path, fix: bool = False, t: int = 1800):
    args = [sys.executable, "-m", "fullcircle", "run", str(target)] + (["--fix"] if fix else [])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(fc_dir) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        return subprocess.run(args, cwd=str(fc_dir), capture_output=True, text=True,
                              timeout=t, env=env)
    except subprocess.TimeoutExpired:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", action="store_true", help="record the row in memory/sandbox/runs.jsonl")
    a = ap.parse_args()

    fc = companion.find("fullcircle")
    if fc is None:
        print("COULD NOT TELL: no full-circle-optimization checkout found by its marker file.")
        print("  Set FULLCIRCLE_DIR=<path> if it lives somewhere this scan does not reach.")
        return UNKNOWN
    fc = pathlib.Path(fc)
    if not PLANTED.is_dir():
        print("COULD NOT TELL: the planted world %s is not here." % PLANTED)
        return UNKNOWN

    angles, t0 = [], time.time()
    print("COMPOSED RUN -- the three repos as one loop")
    print("  full-circle: %s" % str(fc).replace(os.path.expanduser("~"), "~"))
    print("  planted:     %s" % str(PLANTED).replace(os.path.expanduser("~"), "~"))

    with tempfile.TemporaryDirectory(prefix="composed_") as d:
        broken = pathlib.Path(d) / "broken"
        shutil.copytree(PLANTED, broken)
        twin = pathlib.Path(d) / "twin"
        clean_twin(twin)

        # ---- 1. the best-fitting method: the planted-broken world -------------------------
        before = tree_digest(broken)
        r = fc_run(fc, broken)
        if r is None:
            print("  1 PLANTED WORLD          COULD NOT TELL -- the pipeline timed out")
            return UNKNOWN
        found_lines = [l for l in (r.stdout or "").splitlines()
                       if l.strip() and not l.startswith(" " * 6)]
        ok1 = r.returncode == FOUND
        angles.append(("planted-world-is-seen", ok1,
                       "exit %d over %d planted file(s); a planted-broken system must exit 1"
                       % (r.returncode, sum(1 for _ in broken.rglob("*.py")))))
        print("  1 PLANTED WORLD          %s  exit=%d, %d report line(s)"
              % ("ok" if ok1 else "FAIL", r.returncode, len(found_lines)))

        # ---- 3. report-only is inert (checked here, because it needs that same pass) ------
        after_report = tree_digest(broken)
        ok3 = after_report == before
        angles.append(("report-only-is-inert", ok3,
                       "tree digest %s across a run without --fix"
                       % ("unchanged" if ok3 else "CHANGED, so the report wrote to the world")))
        print("  3 REPORT-ONLY INERT      %s  digest %s"
              % ("ok" if ok3 else "FAIL", "unchanged" if ok3 else "CHANGED"))

        # ---- the repair pass --------------------------------------------------------------
        rf = fc_run(fc, broken, fix=True)
        if rf is None:
            print("  -- the --fix pass timed out; UNKNOWN, not a pass")
            return UNKNOWN
        after_fix = tree_digest(broken)
        repaired = after_fix != before
        print("  - REPAIR PASS            exit=%d, world %s"
              % (rf.returncode, "changed" if repaired else "unchanged")
              + ("" if repaired else "  (no SAFE mechanical fix applied -- see note below)"))

        # ---- 4. idempotence: the second --fix must change nothing -------------------------
        rf2 = fc_run(fc, broken, fix=True)
        after_twice = tree_digest(broken)
        ok4 = rf2 is not None and after_twice == after_fix
        angles.append(("fix-is-idempotent", ok4,
                       "a second --fix %s; a repair that reads state it wrote is a silent ratchet "
                       "and only shows on run two"
                       % ("changed nothing" if ok4 else "CHANGED THE WORLD AGAIN")))
        print("  4 IDEMPOTENT             %s  second --fix %s"
              % ("ok" if ok4 else "FAIL", "changed nothing" if ok4 else "CHANGED AGAIN"))

        # ---- 2. the clean twin must stay quiet -------------------------------------------
        rt = fc_run(fc, twin)
        ok2 = rt is not None and rt.returncode == CLEAN
        angles.append(("clean-twin-stays-quiet", ok2,
                       "exit %s on a synthetic project with nothing wrong; over-firing is worse "
                       "than a gap" % (rt.returncode if rt else "TIMEOUT")))
        print("  2 CLEAN TWIN             %s  exit=%s"
              % ("ok" if ok2 else "FAIL", rt.returncode if rt else "TIMEOUT"))

        # ---- 6. THE LOOP ACTUALLY REPAIRS, and leaves the live code alone -----------------
        # ⛔ WHY THIS ANGLE EXISTS: angle 4 above proved idempotence on the planted world, where
        # `--fix` correctly applies NOTHING (those defects need a judgement). Idempotence proven
        # on a no-op is nearly free and nearly worthless. So this plants the one class the
        # mechanical tier really does repair -- a function corroborated dead by BOTH methods --
        # and asks the harder pair of questions: did the dead one GO, and did the live one STAY.
        # A fixer that deletes the live function passes every "did it change the world" check.
        rep = pathlib.Path(d) / "repairable"
        (rep / "pkg").mkdir(parents=True)
        (rep / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (rep / "pkg" / "m.py").write_text(
            "def live_total(items):\n    return sum(items)\n\n\n"
            "def entry(items):\n    return live_total(items)\n\n\n"
            "def zzq_orphan_helper():\n"
            "    # referenced by nothing, anywhere: no call edge and no mention\n"
            "    return 99\n\n\n"
            "entry([1, 2])\n", encoding="utf-8")
        rep_before = tree_digest(rep)
        rr = fc_run(fc, rep, fix=True)
        body = (rep / "pkg" / "m.py").read_text(encoding="utf-8")
        rep_after = tree_digest(rep)
        dead_gone = "zzq_orphan_helper" not in body
        live_kept = "def live_total" in body and "def entry" in body
        rr2 = fc_run(fc, rep, fix=True)
        stable = rr2 is not None and tree_digest(rep) == rep_after
        ok6 = rr is not None and rep_after != rep_before and dead_gone and live_kept and stable
        angles.append(("repair-removes-dead-keeps-live", ok6,
                       "world %s; dead function %s; live functions %s; second --fix %s"
                       % ("changed" if rep_after != rep_before else "UNCHANGED",
                          "removed" if dead_gone else "STILL THERE",
                          "kept" if live_kept else "DELETED TOO -- catastrophic",
                          "changed nothing" if stable else "CHANGED AGAIN")))
        print("  6 REAL REPAIR            %s  dead=%s live=%s idempotent=%s"
              % ("ok" if ok6 else "FAIL", "gone" if dead_gone else "LEFT",
                 "kept" if live_kept else "LOST", stable))

        # ---- 7. EVERY ADVERTISED FLAG DOES WHAT IT SAYS, AND ITS ARTEFACT IS OPENED --------
        # ⛔ THIS ANGLE EXISTS BECAUSE ANGLE 6 WAS NOT ENOUGH, AND THE GAP WAS MEASURED, NOT
        # IMAGINED. The first version of this harness accepted "exit code 0 or 1" as a pass for
        # `--sarif`, and `--sarif` was CRASHING: a TypeError left a zero-byte file and made the
        # interpreter exit 1, which is this tool's own code for "found something". So the check
        # agreed with a broken feature. **An artefact is validated by OPENING it, never by its
        # presence or its exit code** -- `verify-before-claiming.md` law 4 item 3.
        flag_world = pathlib.Path(d) / "flags"
        (flag_world / "pkg").mkdir(parents=True)
        (flag_world / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (flag_world / "pkg" / "m.py").write_text(
            "def keep():\n    return 1\n\n\ndef zzq_gone():\n    return 2\n\n\nkeep()\n",
            encoding="utf-8")
        sarif_out = pathlib.Path(d) / "out.sarif.json"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(fc) + os.pathsep + env.get("PYTHONPATH", "")
        rs = subprocess.run([sys.executable, "-m", "fullcircle", "run", str(flag_world),
                             "--sarif", str(sarif_out)], cwd=str(fc), capture_output=True,
                            text=True, timeout=1800, env=env)
        sarif_ok, sarif_why = False, "no file written"
        if sarif_out.is_file() and sarif_out.stat().st_size:
            try:
                doc = json.loads(sarif_out.read_text(encoding="utf-8"))
                runs_ = doc.get("runs") or []
                results = (runs_[0].get("results") if runs_ else None) or []
                sarif_ok = bool(doc.get("version")) and len(results) >= 1
                sarif_why = ("valid SARIF, %d result(s), %d bytes"
                             % (len(results), sarif_out.stat().st_size))
            except Exception as exc:                          # noqa: BLE001
                sarif_why = "file written but NOT VALID JSON: %s" % exc
        elif sarif_out.is_file():
            sarif_why = "ZERO-BYTE file written -- uploads clean and shows a reviewer no alerts"
        # and a deliberately bad flag must be REFUSED rather than silently ignored
        rbad = subprocess.run([sys.executable, "-m", "fullcircle", "run", str(flag_world),
                               "--not-a-real-flag"], cwd=str(fc), capture_output=True,
                              text=True, timeout=900, env=env)
        refused = rbad.returncode == UNKNOWN
        ok7 = sarif_ok and refused
        angles.append(("advertised-flags-really-work", ok7,
                       "--sarif: %s; an unimplemented flag exits %d (2 = refused rather than "
                       "silently ignored, which is how a missing feature hides)"
                       % (sarif_why, rbad.returncode)))
        print("  7 ADVERTISED FLAGS       %s  sarif=%s unknown-flag-refused=%s"
              % ("ok" if ok7 else "FAIL", "ok" if sarif_ok else "FAIL", refused))

        # ---- 5. UNKNOWN is not clean -----------------------------------------------------
        ghost = pathlib.Path(d) / "not-here"
        rg = fc_run(fc, ghost)
        ok5 = rg is not None and rg.returncode == UNKNOWN
        angles.append(("unknown-is-not-clean", ok5,
                       "exit %s against a path that does not exist; 0 here would be the one "
                       "failure that looks exactly like success"
                       % (rg.returncode if rg else "TIMEOUT")))
        print("  5 UNKNOWN NOT CLEAN      %s  exit=%s"
              % ("ok" if ok5 else "FAIL", rg.returncode if rg else "TIMEOUT"))

    bad = [n for n, ok, _ in angles if not ok]
    print("\n  %d of %d angle(s) hold." % (len(angles) - len(bad), len(angles)))
    for name, ok, why in angles:
        print("    %-5s %-24s %s" % ("ok" if ok else "FAIL", name, why[:86]))
    if not repaired:
        print("\n  ⚠ NOTE, stated rather than hidden: the --fix pass applied NO edit to this world.")
        print("    That is not a failure of the loop -- `--fix` applies only the SAFE MECHANICAL")
        print("    subset, and this planted world's defects (an orphan module, a dead export, a")
        print("    test that cannot fail) are not mechanically repairable without a judgement.")
        print("    Angle 4 is therefore proven on a no-op, which is weaker evidence than a real")
        print("    repair, and the honest statement is that idempotence holds for THIS world.")

    row = {"date": time.strftime("%Y-%m-%d"), "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "subject": "COMPOSED pipeline (rag-ghost -> claimproof -> corral via fullcircle run)",
           "method": "planted-defect world + 4 other angles",
           "angles": [{"name": n, "held": ok, "evidence": w} for n, ok, w in angles],
           "held": len(angles) - len(bad), "of": len(angles),
           "repair_applied_an_edit": repaired,
           "seconds": round(time.time() - t0, 1),
           "reproduce": "python3 proving-ground/composed_run.py",
           "note": ("distinct from the three single-repo board runs: this scores the LOOP, which "
                    "can be broken while every single-repo score is green")}
    if a.log:
        RUNS.parent.mkdir(parents=True, exist_ok=True)
        with open(RUNS, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        print("\n  logged: %s" % str(RUNS).replace(os.path.expanduser("~"), "~"))
    return FOUND if bad else CLEAN


if __name__ == "__main__":
    sys.exit(main())

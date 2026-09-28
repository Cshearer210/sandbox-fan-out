"""`corral [demo|scoreboard <out_dir>|doctor]`  -- the command line.

Also reachable as `python3 -m corral`, which is how it worked before there was a console script;
both entry points call this same `main`, so nothing that already used the module form breaks.
"""
import sys


def doctor(argv=None):
    """Verify the INSTALL, not the source tree. Names every check, then PASS or FAIL.

    ⛔ WHY A DOCTOR AT ALL, measured 2026-09-27 across all four of these repos: a stranger could
    install the package and have no way to find out whether it actually worked. The tests live in
    the repo, not in the wheel, so `pytest` after a `pip install` runs nothing. Green CI says the
    SOURCE is fine and says nothing about the thing that landed on their machine.

    ⭐ SO EVERY CHECK HERE DELIBERATELY EXERCISES THE INSTALLED PACKAGE and does real work in a
    temp directory: an import that only touches `__init__` would pass on a half-installed wheel
    with no modules in it -- which is exactly the failure found in a sibling repo the same day,
    where `import fullcircle` succeeded with `__file__` set to None.
    """
    import os
    import tempfile

    checks, failed = [], 0

    def ck(name, fn):
        nonlocal failed
        try:
            detail = fn()
            checks.append(("ok", name, detail or ""))
        except Exception as exc:                               # noqa: BLE001
            failed += 1
            checks.append(("FAIL", name, "%s: %s" % (type(exc).__name__, exc)))

    def _real_module():
        import corral
        f = getattr(corral, "__file__", None)
        if not f:
            raise RuntimeError("imported, but __file__ is None -- an empty namespace package, "
                               "not a real install")
        return f

    def _public_api():
        # ⭐ The population is corral.__all__ itself, not a list typed in here. A typed list goes
        # stale the first time a name is added, and it goes stale SILENTLY -- the check keeps
        # passing while the new name is never tested.
        import corral
        missing = [n for n in corral.__all__ if not hasattr(corral, n)]
        if missing:
            raise RuntimeError("promised by __all__ and absent from the install: %s"
                               % ", ".join(missing))
        if len(corral.__all__) < 5:
            raise RuntimeError("__all__ has only %d names -- the install looks partial"
                               % len(corral.__all__))
        return "%d public names, all resolvable" % len(corral.__all__)

    def _splits_for_real():
        from corral import split_population
        slices = split_population([str(i) for i in range(10)], 3)
        n = sum(len(s) for s in slices)
        if n != 10 or len(slices) != 3:
            raise RuntimeError("split 10 items into 3 slices and got %d items in %d slices"
                               % (n, len(slices)))
        flat = [x for s in slices for x in s]
        if len(set(flat)) != 10:
            raise RuntimeError("the slices overlap -- they must be disjoint")
        return "10 items -> 3 disjoint slices"

    def _fans_out_and_merges_for_real():
        # The whole job of the library, end to end, on real files in a temp directory: split the
        # population, run every slice in its own thread with its own log, merge once. A failing
        # unit is included deliberately -- an agent whose unit fails must not take the run down,
        # and the failure must land in failures.jsonl rather than vanishing.
        from corral import fanout, summarize
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out")

            def work(unit, workdir):
                return (unit != "u3", "boom" if unit == "u3" else "ok")

            summary = fanout(["u%d" % i for i in range(1, 8)], work, 3, out)
            if summary["merged"] != 7:
                raise RuntimeError("7 units in, %d merged out" % summary["merged"])
            if (summary["successes"], summary["failures"]) != (6, 1):
                raise RuntimeError("expected 6 ok / 1 failed, got %d / %d"
                                   % (summary["successes"], summary["failures"]))
            for f in ("successes.jsonl", "failures.jsonl"):
                if not os.path.exists(os.path.join(out, f)):
                    raise RuntimeError("the merge wrote no %s" % f)
            logs = [f for f in os.listdir(os.path.join(out, "logs")) if f.endswith(".jsonl")]
            if len(logs) != 3:
                raise RuntimeError("3 agents should write 3 separate logs, found %d" % len(logs))
            tally = summarize(out)
            if not tally:
                raise RuntimeError("summarize read the run and returned nothing")
            return "7 units -> 3 agents -> 3 logs -> 6 ok / 1 failed, merged once"

    ck("the installed package is real, not an empty namespace", _real_module)
    ck("every public name is importable from the install", _public_api)
    ck("split_population really splits, and the slices are disjoint", _splits_for_real)
    def _repairs_for_real():
        # ⛔ THE REPAIR HALF, EXERCISED ON REAL FILES. A doctor that only proved the fan-out
        # would pass on an install whose whole reason for existing -- fixing what another
        # tool found -- was missing from the wheel.
        from corral import apply_fixes
        from corral.fixer import _marker_finder
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "bad.py"), "w").write("# DEADCANARY\n")

            def prov(t, work):
                p = os.path.join(work, t.location)
                open(p, "w").write(open(p).read().replace("DEADCANARY", "ok"))
                return True

            found = _marker_finder(d)
            if len(found) != 1:
                raise RuntimeError("planted 1 defect, the finder saw %d" % len(found))
            plan = apply_fixes(d, found, prov, _marker_finder)
            if "DEADCANARY" not in open(os.path.join(d, "bad.py")).read():
                raise RuntimeError("a DRY RUN modified the real file")
            rep = apply_fixes(d, found, prov, _marker_finder, dry_run=False)
            if len(rep["applied"]) != 1 or _marker_finder(d):
                raise RuntimeError("the repair did not land: %s" % rep["message"])
            return "1 planted defect: dry run held, wet run repaired, finder agrees"

    ck("a real fan-out runs, isolates each agent's log, and merges once",
       _fans_out_and_merges_for_real)
    def _bundles_for_real():
        # ⛔ THE HANDOVER, ON REAL FILES. A doctor that proved only the in-place repair would pass
        # on an install that cannot hand a verified fix to anybody -- which is the half that makes
        # the repair useful to a person who did not run the finder.
        from corral import Collector, apply_bundle, apply_fixes, write_bundle
        from corral.fixer import _marker_finder
        import shutil as _sh
        with tempfile.TemporaryDirectory() as d:
            src, dst, bun = (os.path.join(d, x) for x in ("s", "t", "b"))
            os.makedirs(os.path.join(src, "pkg"))
            open(os.path.join(src, "pkg", "bad.py"), "w").write("# DEADCANARY\n")
            _sh.copytree(src, dst)

            def prov(t, work):
                p = os.path.join(work, t.location)
                open(p, "w").write(open(p).read().replace("DEADCANARY", "ok"))
                return True

            col = Collector()
            apply_fixes(src, _marker_finder(src), prov, _marker_finder, on_verified=col)
            man = write_bundle(col.fixes, bun, root=src)
            if man["areas"] != ["pkg"]:
                raise RuntimeError("the fix should be labelled pkg, got %r" % man["areas"])
            r = apply_bundle(bun, dst, areas=["pkg"], dry_run=False)
            if len(r["applied"]) != 1 or _marker_finder(dst):
                raise RuntimeError("the bundle did not repair the other copy: %s" % r["message"])
            open(os.path.join(dst, "pkg", "bad.py"), "w").write("# DEADCANARY newer\n")
            r2 = apply_bundle(bun, dst, areas=["pkg"], dry_run=False)
            if not r2["refused"]:
                raise RuntimeError("a changed target must be REFUSED, got %s" % r2["message"])
            return "labelled pkg, applied to a second copy, then refused on a changed target"

    ck("a real defect is repaired, and a dry run does not touch the target",
       _repairs_for_real)
    ck("a verified repair can be bundled, routed by area, and refused when the target moved",
       _bundles_for_real)

    for state, name, detail in checks:
        sys.stdout.write("  %-4s %s%s\n" % (state + ":", name, ("  -- " + detail) if detail else ""))
    sys.stdout.write("corral doctor: %s (%d check(s), %d failure(s))\n"
                     % ("PASS" if not failed else "FAIL", len(checks), failed))
    return 0 if not failed else 1


def fix(argv=None):
    """`corral fix --demo` -- prove the repair half end to end, on a throwaway system.

    ⛔ WHY A DEMO AND NOT `corral fix <your repo>`: a repair needs a PATCH PROVIDER, and a patch
    provider is code -- a mechanical rule for a known defect class, or a model. There is no honest
    way to take one on a command line, so the real entry point is the Python API
    (`from corral import apply_fixes`) and this command exists to show it working on a system with
    a real planted defect, end to end, in front of you.
    """
    import os
    import tempfile
    from corral.fixer import _Found, _marker_finder, apply_fixes

    def provider(finding, work):
        p = os.path.join(work, finding.location)
        open(p, "w").write(open(p).read().replace("DEADCANARY", "real_assert()"))
        return True

    out = sys.stdout.write
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "good.py"), "w").write("def f():\n    assert f\n")
        open(os.path.join(d, "broken.py"), "w").write("# DEADCANARY: this test cannot fail\n")
        out("a system with one planted defect and one healthy file:\n")
        found = _marker_finder(d)
        out("  found            %d defect(s): %s\n"
            % (len(found), ", ".join(f.identity for f in found)))

        plan = apply_fixes(d, found, provider, _marker_finder)
        out("  dry run         %s\n" % plan["message"])
        still = "DEADCANARY" in open(os.path.join(d, "broken.py")).read()
        out("  the real file   %s\n"
            % ("UNTOUCHED, as it must be during a dry run" if still
               else "WAS MODIFIED -- that is a bug in the engine"))

        rep = apply_fixes(d, found, provider, _marker_finder, dry_run=False)
        out("  applied         %s\n" % rep["message"])
        out("  re-measured     %d defect(s) remain\n" % len(_marker_finder(d)))

        def regressing(finding, work):
            open(os.path.join(work, finding.location), "w").write("x = 1\n")
            open(os.path.join(work, "worse.py"), "w").write("# DEADCANARY introduced\n")
            return True

        open(os.path.join(d, "broken2.py"), "w").write("# DEADCANARY second\n")
        bad = apply_fixes(d, _marker_finder(d), regressing, _marker_finder, dry_run=False)
        out("\nand a repair that would BREAK something else:\n")
        out("  verdict         %d rolled back, %d applied\n"
            % (len(bad["rolled_back"]), len(bad["applied"])))
        out("  the system      %s\n"
            % ("unchanged -- the bad repair never landed"
               if not os.path.exists(os.path.join(d, "worse.py")) else "GOT THE BAD FIX"))

        # ⭐ AND THE HANDOVER, WHICH IS THE HALF THAT MAKES A REPAIR USEFUL TO SOMEBODY ELSE.
        from corral.bundle import Collector, apply_bundle, describe, write_bundle
        import shutil as _sh
        elsewhere = os.path.join(d, "_elsewhere")
        os.makedirs(os.path.join(elsewhere, "pkg"))
        open(os.path.join(elsewhere, "pkg", "same.py"), "w").write("# DEADCANARY over here\n")
        open(os.path.join(elsewhere, "root.py"), "w").write("# DEADCANARY at the root\n")
        target = os.path.join(d, "_target")
        _sh.copytree(elsewhere, target)

        col = Collector()
        apply_fixes(elsewhere, _marker_finder(elsewhere), provider, _marker_finder,
                    on_verified=col)
        bundle = os.path.join(d, "_bundle")
        write_bundle(col.fixes, bundle, root=elsewhere, note="corral fix --demo")
        out("\nthe repairs, labelled so they can be routed:\n")
        for line in describe(bundle).splitlines():
            out("  " + line + "\n")

        took = apply_bundle(bundle, target, areas=["pkg"], dry_run=False)
        out("\napplying ONLY the `pkg` area to a different copy of the system:\n")
        out("  result          %s\n" % took["message"])
        out("  pkg/same.py     %s\n"
            % ("repaired" if "DEADCANARY" not in
               open(os.path.join(target, "pkg", "same.py")).read() else "NOT repaired"))
        out("  root.py         %s\n"
            % ("left alone, nobody asked for it" if "DEADCANARY" in
               open(os.path.join(target, "root.py")).read() else "WRONGLY touched"))

        open(os.path.join(target, "root.py"), "w").write("# DEADCANARY and newer work\n")
        refused = apply_bundle(bundle, target, areas=["(root)"], dry_run=False)
        out("\nand the same bundle against a file somebody has since edited:\n")
        out("  result          %s\n" % refused["message"])
        out("  their work      %s\n"
            % ("still there -- the bundle refused rather than overwrite it"
               if "newer work" in open(os.path.join(target, "root.py")).read()
               else "OVERWRITTEN"))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "scoreboard":
        from corral.scoreboard import main as run
        return run(argv[1:])
    if argv and argv[0] == "fix":
        return fix(argv[1:])
    if argv and argv[0] == "doctor":
        return doctor(argv[1:])
    if argv and argv[0] in ("-h", "--help", "help"):
        sys.stdout.write("corral -- fan test agents over a sandbox in isolation, merge safely.\n"
                         "  corral demo\n"
                         "  corral fix --demo              # the repair half, proven end to end\n"
                         "  corral doctor                  # verify this install actually works\n"
                         "  corral scoreboard <out_dir>    # classified tally of a fan-out run\n"
                         "\n(`python3 -m corral ...` does the same thing.)\n")
        return 0
    if argv and argv[0] not in ("demo",):
        sys.stdout.write("usage: corral [demo|fix|doctor|scoreboard <out_dir>]\n")
        return 2
    from corral.demo import main as demo_main
    return demo_main(argv[1:] if argv else [])


if __name__ == "__main__":
    sys.exit(main())

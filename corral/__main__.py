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
    ck("a real fan-out runs, isolates each agent's log, and merges once",
       _fans_out_and_merges_for_real)

    for state, name, detail in checks:
        sys.stdout.write("  %-4s %s%s\n" % (state + ":", name, ("  -- " + detail) if detail else ""))
    sys.stdout.write("corral doctor: %s (%d check(s), %d failure(s))\n"
                     % ("PASS" if not failed else "FAIL", len(checks), failed))
    return 0 if not failed else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "scoreboard":
        from corral.scoreboard import main as run
        return run(argv[1:])
    if argv and argv[0] == "doctor":
        return doctor(argv[1:])
    if argv and argv[0] in ("-h", "--help", "help"):
        sys.stdout.write("corral -- fan test agents over a sandbox in isolation, merge safely.\n"
                         "  corral demo\n"
                         "  corral doctor                  # verify this install actually works\n"
                         "  corral scoreboard <out_dir>    # classified tally of a fan-out run\n"
                         "\n(`python3 -m corral ...` does the same thing.)\n")
        return 0
    if argv and argv[0] not in ("demo",):
        sys.stdout.write("usage: corral [demo|doctor|scoreboard <out_dir>]\n")
        return 2
    from corral.demo import main as demo_main
    return demo_main(argv[1:] if argv else [])


if __name__ == "__main__":
    sys.exit(main())

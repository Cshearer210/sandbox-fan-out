#!/usr/bin/env python3
# CALLED BY: run_all.py, fanout_scoreboard.py, scale_test.py in this directory.
# FIRES WHEN: the proving ground needs to find the companion tools it measures.
"""Where are the companion tools? Answered by looking, never by a path typed into a file.

⛔ WHY THIS EXISTS, AND IT IS NOT TIDINESS. Every script in this directory used to carry an
absolute path to somebody's home directory. Two things follow, and the second is the worse one:

  1  IT ONLY RUNS ON ONE MACHINE. A stranger cloning this repository gets a harness that can find
     nothing, which is the most obvious "never meant for anyone else" tell a repository can carry.
  2  ⛔ A TYPED PATH GOES STALE SILENTLY. One of those checkouts was renamed, and two files here
     still pointed at the old name -- in the harness that answers "are these tools DONE". A
     missing directory makes an import fail or a measurement come back empty, and **"found
     nothing" and "could not look" produce the same output**. So the harness could score a tool as
     having no findings when it had simply never been read.

⭐ THE RULE HERE: a companion is FOUND, and when it cannot be found the answer is UNKNOWN -- never
a default that reads like a result. `describe()` prints what was found and what was not, so a
run's own output says which tools it could actually see.

    RAGGHOST_DIR, CLAIMPROOF_DIR, CORRAL_DIR, FULLCIRCLE_DIR   override anything, for CI or an
                                                               unusual layout
    otherwise                                                  searched for, and accepted only on
                                                               the marker file that proves it
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# name -> (env var, the import root relative to the checkout, a marker that PROVES it is that repo)
# ⭐ THE MARKER IS THE POINT. A directory called "claimproof" is not proof that claimproof is in
# it; a file only that project has, is. Matching on a folder name is how a harness ends up
# importing something else entirely and then reporting confidently about it.
COMPANIONS = {
    "ragghost": ("RAGGHOST_DIR", "", os.path.join("ragghost", "report.py")),
    "claimproof": ("CLAIMPROOF_DIR", "src", os.path.join("src", "claimproof", "gates.py")),
    "corral": ("CORRAL_DIR", "", os.path.join("corral", "core.py")),
    "fullcircle": ("FULLCIRCLE_DIR", "", os.path.join("fullcircle", "orchestrator.py")),
}

# Where to look, in order. A side-by-side layout -- the normal way somebody clones four related
# repositories -- works with no configuration at all.
_SEARCH = [
    os.path.dirname(os.path.dirname(HERE)),                     # the repo this harness ships in
    os.path.dirname(os.path.dirname(os.path.dirname(HERE))),    # its parent: siblings live here
    os.path.expanduser("~"),
]
# Directory names each companion is plausibly cloned as. Several, because one project really has
# been checked out under more than one name -- and a name is only ever a hint: the marker decides.
_ALIASES = {
    "ragghost": ["rag-graph-surgeon", "ragghost", "rag-graph-surgeon-work"],
    "claimproof": ["claimproof", "claimproof-work"],
    "corral": ["sandbox-fan-out", "corral", "corral-work"],
    "fullcircle": ["full-circle-optimization", "fullcircle", "full-circle-optimization-work"],
}


def find(name: str) -> str | None:
    """The checkout root for one companion, or None. None means UNKNOWN, never 'not there'."""
    env, _, marker = COMPANIONS[name]
    override = os.environ.get(env)
    if override:
        # an override that is WRONG fails loudly rather than falling back to a guess -- silently
        # ignoring it is how a run measures a different tree than the one it was told to measure
        return override if os.path.exists(os.path.join(override, marker)) else None
    for base in _SEARCH:
        for alias in _ALIASES[name]:
            cand = os.path.join(base, alias)
            if os.path.exists(os.path.join(cand, marker)):
                return cand
    # ⭐ ONE LEVEL DEEPER, BOUNDED. People keep related repos inside a workspace folder, and a
    # resolver that only looks at fixed bases reports NOT FOUND for a checkout that is right
    # there -- which on this harness means a tool silently goes unmeasured. One level only: a
    # deep walk of a home directory would be slow and would eventually match something it
    # should not.
    for base in _SEARCH:
        try:
            subdirs = [os.path.join(base, d) for d in sorted(os.listdir(base))]
        except OSError:
            continue
        for sub in subdirs:
            if not os.path.isdir(sub):
                continue
            for alias in _ALIASES[name]:
                cand = os.path.join(sub, alias)
                if os.path.exists(os.path.join(cand, marker)):
                    return cand
    return None


def import_root(name: str) -> str | None:
    """The directory to put on sys.path for this companion, or None if it was not found."""
    root = find(name)
    if root is None:
        return None
    _, sub, _ = COMPANIONS[name]
    return os.path.join(root, sub) if sub else root


def add_to_path(*names: str) -> dict[str, str | None]:
    """Put each found companion on sys.path. Returns what was found, so a caller can report it."""
    out: dict[str, str | None] = {}
    for n in (names or tuple(COMPANIONS)):
        r = import_root(n)
        out[n] = r
        if r and r not in sys.path:
            sys.path.insert(0, r)
    return out


def describe() -> str:
    """One line per companion: where it was found, or NOT FOUND with the variable that fixes it."""
    lines = []
    for n in COMPANIONS:
        r = find(n)
        env = COMPANIONS[n][0]
        lines.append("  %-12s %s" % (n, r if r else "NOT FOUND -- set %s to its checkout" % env))
    return "\n".join(lines)


def selftest() -> int:
    """Both directions, on synthetic trees: a real checkout is found, a look-alike is not."""
    import shutil
    import tempfile

    ok = True

    def say(cond, msg, extra=""):
        nonlocal ok
        if not cond:
            ok = False
            print("FAIL: %s %s" % (msg, extra))
        else:
            print("  ok:   %s" % msg)

    d = tempfile.mkdtemp(prefix="pg_paths_")
    try:
        real = os.path.join(d, "real")
        os.makedirs(os.path.join(real, "ragghost"))
        open(os.path.join(real, "ragghost", "report.py"), "w").write("# x\n")
        decoy = os.path.join(d, "decoy")
        os.makedirs(os.path.join(decoy, "ragghost"))       # right name, no marker

        os.environ["RAGGHOST_DIR"] = real
        say(find("ragghost") == real, "an override pointing at a real checkout is used")

        os.environ["RAGGHOST_DIR"] = decoy
        say(find("ragghost") is None,
            "MUST FIRE: a directory named right but MISSING THE MARKER is refused")

        os.environ["RAGGHOST_DIR"] = os.path.join(d, "nope")
        say(find("ragghost") is None,
            "MUST FIRE: an override that does not exist is UNKNOWN, not a fallback guess")

        del os.environ["RAGGHOST_DIR"]
        say(isinstance(describe(), str) and "ragghost" in describe(),
            "describe() states, per companion, whether it was found")

        r = import_root("claimproof")
        say(r is None or os.path.basename(r) == "src",
            "claimproof's import root is its src/ directory, not the checkout root")
    finally:
        os.environ.pop("RAGGHOST_DIR", None)
        shutil.rmtree(d, ignore_errors=True)

    print("SELFTEST: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print("companion tools this proving ground can see:")
    print(describe())

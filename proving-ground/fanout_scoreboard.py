#!/usr/bin/env python3
"""The scoreboard, run through corral's agent fan-out -- the whole loop end to end.

Instead of one process scoring every planted issue, this splits the population across N isolated
agents (via corral): each agent gets a disjoint slice, scores only its slice, writes its OWN log,
and a single merge folds them into successes/failures. Proves the fan-out works ON the real
sandbox population, safely, with every planted issue accounted for exactly once.

    python3 fanout_scoreboard.py            # fan out, merge, print the summary
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# ⛔ THE COMPANION TOOLS ARE FOUND, NOT TYPED. Two of these three lines used to name a
# machine directory, and one of them named a checkout that had been renamed -- in a
# scoreboard whose whole job is saying whether those tools work.
sys.path.insert(0, HERE)
import paths  # noqa: E402
_seen = paths.add_to_path('corral', 'ragghost', 'claimproof')

from corral import fanout                                   # noqa: E402
import run_all                                              # the scoreboard's own classifiers  # noqa: E402


def _population():
    with open(os.path.join(HERE, "MANIFEST.json"), encoding="utf-8") as f:
        rows = json.load(f)["planted"]
    # the units an agent can score standalone: rag-ghost + claimproof rows (skip record-only/runtime)
    return [r for r in rows if not r.get("record_only") and r["tool"] in ("rag-ghost", "claimproof")]


# precompute the shared RAG-Ghost findings once (read-only), so each agent scores against them
_RG = run_all.ragghost_findings(os.path.join(HERE, "code-rot"))


def _score(row, workdir):
    verdict, why = run_all.classify(row, _RG)
    ok = verdict in ("CAUGHT", "QUIET-OK")
    return (ok, "%s: %s" % (verdict, row["id"]))


def main():
    population = _population()
    out_dir = os.path.join("/tmp/claude-1000", "carrot-fanout-run")
    summary = fanout(population, _score, n_agents=6, out_dir=out_dir,
                     prepare=None, teardown=None)
    print("fan-out scoreboard: %d agents, %d planted issues scored, "
          "%d caught/quiet, %d gap/ground-truth" %
          (summary["agents"], summary["merged"], summary["successes"], summary["failures"]))
    print("  per-agent logs merged ONCE into %s/{successes,failures}.jsonl" % out_dir)
    # completeness: every scorable planted issue accounted for exactly once
    assert summary["merged"] == len(population), \
        "lost or duplicated a planted issue in the fan-out!"
    print("  OK -- every planted issue accounted for exactly once (no loss, no duplication)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

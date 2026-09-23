# CALLED BY: corral/__main__.py  (`python3 -m corral demo`)
# FIRES WHEN: asked -- a self-contained 15-second demonstration.
"""A rot-proof demo: fan a tiny population of checks out across agents, each isolated, and merge
their per-agent logs into one successes/failures pair -- live, in a temp dir it cleans up."""
from __future__ import annotations

import os
import sys
import tempfile

from .core import fanout


def main(argv=None):
    out = sys.stdout
    d = tempfile.mkdtemp(prefix="corral_demo_")
    try:
        population = ["check-%02d" % i for i in range(12)]   # 12 units of work

        def work(unit, workdir):
            # an agent's real work would clone parts + run a tool; here every 5th "fails"
            n = int(unit.split("-")[1])
            return (n % 5 != 0, "ran %s" % unit)

        out.write("corral demo -- 12 checks fanned out across 4 isolated agents\n")
        out.write("=" * 64 + "\n")
        summary = fanout(population, work, n_agents=4, out_dir=d)
        out.write("  agents: %d   merged: %d   successes: %d   failures: %d\n"
                  % (summary["agents"], summary["merged"], summary["successes"], summary["failures"]))
        out.write("  each agent wrote its OWN log in %s/logs/agent-*.jsonl\n" % os.path.basename(d))
        out.write("  ONE merge folded them into successes.jsonl + failures.jsonl -- no shared-folder\n"
                  "  contention, every result present exactly once.\n\n")
        out.write("For a real subagent fan-out: corral.plan_prompts() gives each agent the parts to\n"
                  "clone, what to test, and a unique log path; spawn the agents, then call merge() once.\n")
        return 0
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Fan a real body of work out across parallel agents, safely.

Two paths, both using the SAME disjoint slices and the SAME single merge:

  1. demo_in_process()  -- fan the work out locally with threads. Deterministic and testable,
                           so you can prove the wiring before spending a single real agent.
  2. plan_a_real_fleet() -- hand each agent a brief that names the parts to clone, the units to
                           test, and a UNIQUE log path. Spawn the agents with any orchestrator,
                           let each write its own log, then call merge() ONCE.

The safety property is identical either way: no two agents ever write the same file, and the
shared successes/failures files are written by exactly one step, after the fan-out is done.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from corral import plan_prompts, merge, fanout   # noqa: E402,F401  (merge shown for the reader)


def discover_units():
    """The population to fan out -- discovered, never typed by hand. Here, a stand-in list of
    package names; in a real run this would be a directory walk, a test collection, a query."""
    return ["pkg-%02d" % i for i in range(24)]


def parts_for(unit):
    """Which parts of the source tree an agent must clone to work on this unit. Keep it minimal:
    an agent should hold only what its slice touches -- that isolation is what keeps a fan-out
    both cheap and collision-free."""
    return ["src/%s" % unit, "shared/config"]


def task_for(slice_, parts, log_path):
    """The brief handed to one real agent. It clones only `parts`, runs its checks over its slice,
    writes ONE json line per unit ({unit, ok, note}) to its OWN log, and writes nowhere else."""
    return ("You are one agent in a fan-out. Check these %d units: %s. Clone only these parts: %s. "
            "For each unit, run the check and append one json line {unit, ok, note} to %s. "
            "Do not write anywhere else. Stop when done." % (len(slice_), slice_, parts, log_path))


def plan_a_real_fleet(n_agents=8, log_dir="/tmp/fanout-run/logs"):
    """The real-subagent path: disjoint slices + a unique log per agent, so nothing collides.
    Spawn one agent per brief; when ALL have returned, call merge() once."""
    prompts = plan_prompts(discover_units(), n_agents, src_root="/path/to/the/source/tree",
                           parts_for=parts_for, task_for=task_for, log_dir=log_dir)
    # ... spawn one agent per prompt with your orchestrator of choice ...
    # when every agent has returned:
    #   merge(log_dir, "/tmp/fanout-run/successes.jsonl", "/tmp/fanout-run/failures.jsonl")
    return prompts


def demo_in_process():
    """The testable path: fan the units out in-process (threads) to prove the wiring before
    spending a single real agent."""
    import tempfile
    out = tempfile.mkdtemp(prefix="fanout_")

    def check(unit, workdir):
        # a real agent's check runs here against its private clone (`workdir`); it returns
        # (ok, note). A raise would be caught and logged as a failure, never crash the run.
        return (True, "CHECKED: %s" % unit)

    summary = fanout(discover_units(), check, n_agents=8, out_dir=out)
    print("fan-out: %(agents)d agents, %(merged)d units, %(successes)d ok, %(failures)d fail"
          % summary)
    print("  every unit checked exactly once, merged safely into", out)
    return summary


if __name__ == "__main__":
    demo_in_process()

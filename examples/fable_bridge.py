#!/usr/bin/env python3
# CALLED BY: examples -- a session running the Fable fleet stage uses this pattern.
# FIRES WHEN: asked  a Fable run needs to fan a large body of items across agents safely.
"""Point corral at the Fable fleet method.

Fable is "a fleet of cheap agents on one job at once, kept honest by gates" -- its DONE-WHEN asks
to spawn many sub-agents in parallel, test them in a sandbox first, and never have the fan-out
cost 5.7M tokens per finding. corral is the safe engine for exactly that: disjoint slices so no
item is judged twice, an isolated clone per agent, a per-agent log so no two agents write the same
file, and ONE merge at the end. carrot-sandbox is the deliberately-broken example system to test a
Fable workflow against before it touches anything real.

This bridge shows the mapping. It does not rewrite Fable; it is the pattern a Fable run follows so
its fleet stage inherits corral's safety.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from corral import plan_prompts, merge, fanout   # noqa: E402


def fable_units():
    """Fable's population: the items the fleet will judge (master-plan items, files to review,
    findings to verify). Discovered, never typed -- here a stand-in list for the demo."""
    return ["item-%02d" % i for i in range(24)]


def parts_for(unit):
    """Which parts of the target an agent needs cloned to judge this unit. Keep it minimal -- an
    agent should hold only what its slice touches (the isolation that keeps fan-out cheap)."""
    return ["subsystem-%s" % (unit.split("-")[1][0])]   # stand-in grouping


def task_for(slice_, parts, log_path):
    """The brief handed to one real Fable agent. It clones only `parts`, judges its slice against
    the honesty gates, writes ONE jsonl line per item to its OWN log, then stops."""
    return ("You are one agent in a Fable fleet. Judge these %d items: %s. Clone only %s. For each "
            "item, apply the evidence gates and write one json line {unit, ok, note} to %s. Do not "
            "write anywhere else. Stop when done." % (len(slice_), slice_, parts, log_path))


def plan_a_real_fleet(n_agents=8, log_dir="/tmp/fable-run/logs"):
    """The real-subagent path: disjoint slices + a unique log per agent. Spawn one agent per brief,
    let each write its own log, then call merge() ONCE -- no shared-folder contention."""
    prompts = plan_prompts(fable_units(), n_agents, src_root="/the/target/system",
                           parts_for=parts_for, task_for=task_for, log_dir=log_dir)
    # ... spawn one agent per prompt (any orchestrator) ...
    # when ALL have returned:
    #   merge(log_dir, "/tmp/fable-run/successes.jsonl", "/tmp/fable-run/failures.jsonl")
    return prompts


def demo_in_process():
    """The testable path: fan Fable's units out in-process (threads) to prove the wiring, before
    spending a single real agent. This is 'test the workflow in the sandbox first'."""
    import tempfile
    out = tempfile.mkdtemp(prefix="fable_corral_")

    def judge(unit, workdir):
        return (True, "CAUGHT: %s judged clean" % unit)   # a real agent's verdict goes here

    summary = fanout(fable_units(), judge, n_agents=8, out_dir=out)
    print("fable-via-corral: %(agents)d agents, %(merged)d items, %(successes)d ok, %(failures)d fail"
          % summary)
    print("  every item judged exactly once, merged safely into", out)
    return summary


if __name__ == "__main__":
    demo_in_process()

"""corral -- run many test agents over one sandbox, in isolation, and merge their results SAFELY.

The problem it solves: a fan-out of agents that each save files to the same folder at once
corrupts or loses results. The rule here is that **no two agents ever write the same
file**, and the shared result files are written by exactly ONE step, after every agent is done.

    split_population   discover the work, split it into N disjoint slices (never a typed list)
    checkout           an agent copies ONLY the parts it needs into its own private workdir
    run_slice          the agent tests its slice in isolation, writes its OWN per-agent log,
                       then destroys its clone
    merge              ONE writer, after the fan-out, folds every per-agent log into the shared
                       successes/failures files -- so concurrent writes to a shared folder never happen
    fanout             orchestrates the above; the local executor is threads (deterministic, testable),
                       and the SAME slices+merge drive a real subagent fan-out (plan_prompts)

No third-party dependencies. Standard library only.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

__all__ = ["split_population", "checkout", "cleanup", "run_slice", "merge", "fanout",
           "plan_prompts", "Result"]


class Result(dict):
    """One unit's outcome. A dict so it serialises to a log line with no ceremony."""
    @classmethod
    def make(cls, agent_id, unit, ok, note=""):
        return cls(agent_id=agent_id, unit=str(unit), ok=bool(ok), note=str(note),
                   at=time.strftime("%Y-%m-%dT%H:%M:%S"))


def split_population(units, n_agents):
    """Split a discovered population into up to n_agents DISJOINT, balanced slices.

    Round-robin so the slices are even; disjoint so no unit is tested twice (a duplicate is the
    fan-out defect this whole library exists to prevent). Empty slices are dropped -- N agents over
    fewer than N units means fewer agents, never idle ones.
    """
    units = list(units)
    n = max(1, min(int(n_agents), len(units))) if units else 0
    slices = [[] for _ in range(n)]
    for i, u in enumerate(units):
        slices[i % n].append(u)
    return [s for s in slices if s]


def checkout(src_root, parts, dest):
    """Copy ONLY `parts` (relative paths under src_root) into a fresh `dest`. The agent's private
    clone -- it holds just what its slice needs, nothing else, so two agents never share a byte."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    for rel in parts:
        s = os.path.join(src_root, rel)
        d = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(d) or dest, exist_ok=True)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        elif os.path.exists(s):
            shutil.copy2(s, d)
    return dest


def cleanup(dest):
    shutil.rmtree(dest, ignore_errors=True)


def run_slice(agent_id, units, work_fn, log_dir, prepare=None, teardown=None):
    """Run one agent's slice IN ISOLATION and write its OWN per-agent log file.

    `work_fn(unit, workdir)` returns (ok, note) or raises (a raise is a failure, never a crash of
    the fan-out). `prepare(agent_id)->workdir` gives the agent its private clone; `teardown(workdir)`
    destroys it. The log file name is unique to this agent, so nothing else writes it.
    """
    workdir = prepare(agent_id) if prepare else None
    results = []
    try:
        for u in units:
            try:
                ok, note = work_fn(u, workdir)
            except Exception as exc:  # a failing unit never takes the agent -- or the run -- down
                ok, note = False, "raised: %r" % exc
            results.append(Result.make(agent_id, u, ok, note))
    finally:
        if teardown and workdir:
            teardown(workdir)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "agent-%s.jsonl" % agent_id)   # unique per agent
    with open(log_path, "w", encoding="utf-8") as f:                # this agent is the only writer
        for r in results:
            f.write(json.dumps(r) + "\n")
    return results


def merge(log_dir, successes_path, failures_path):
    """The ONE writer. After every agent is done, fold every per-agent log into the two shared
    files. Runs in a single thread, so the shared files are never written concurrently -- the exact
    failure (many agents saving to one folder at once) this library exists to prevent."""
    merged, succ, fail = 0, 0, 0
    seen = set()
    os.makedirs(os.path.dirname(successes_path) or ".", exist_ok=True)
    with open(successes_path, "a", encoding="utf-8") as sf, \
            open(failures_path, "a", encoding="utf-8") as ff:
        for name in sorted(os.listdir(log_dir)):
            if not (name.startswith("agent-") and name.endswith(".jsonl")):
                continue
            with open(os.path.join(log_dir, name), encoding="utf-8") as lf:
                for line in lf:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    key = (row.get("agent_id"), row.get("unit"))
                    if key in seen:          # a unit merged twice is a defect; count once
                        continue
                    seen.add(key)
                    merged += 1
                    (sf if row.get("ok") else ff).write(line + "\n")
                    if row.get("ok"):
                        succ += 1
                    else:
                        fail += 1
    return {"merged": merged, "successes": succ, "failures": fail}


def fanout(population, work_fn, n_agents, out_dir, prepare=None, teardown=None, max_workers=None):
    """Split -> run every slice in isolation (its own per-agent log) -> merge ONCE. Returns the
    merge summary. The shared successes/failures files are written only by the final merge."""
    slices = split_population(population, n_agents)
    log_dir = os.path.join(out_dir, "logs")
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
    os.makedirs(log_dir)          # log_dir was just removed above, so it cannot exist here
    workers = max_workers or len(slices) or 1
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(run_slice, str(i), s, work_fn, log_dir, prepare, teardown)
                for i, s in enumerate(slices)]
        for fu in futs:
            fu.result()   # surface any orchestration-level error (never a unit error, those are caught)
    summary = merge(log_dir, os.path.join(out_dir, "successes.jsonl"),
                    os.path.join(out_dir, "failures.jsonl"))
    summary["agents"] = len(slices)
    return summary


def plan_prompts(population, n_agents, src_root, parts_for, task_for, log_dir):
    """For a REAL subagent fan-out: the per-agent briefs, using the same disjoint slices. Each brief
    tells one agent which parts to clone, what to test, and the UNIQUE log path to write -- so the
    orchestrator can spawn real agents and then call merge() once, no shared-folder contention."""
    slices = split_population(population, n_agents)
    prompts = []
    for i, s in enumerate(slices):
        parts = sorted({p for u in s for p in parts_for(u)})
        prompts.append({
            "agent_id": str(i),
            "units": s,
            "clone_parts": parts,
            "log_path": os.path.join(log_dir, "agent-%s.jsonl" % i),
            "task": task_for(s, parts, os.path.join(log_dir, "agent-%s.jsonl" % i)),
        })
    return prompts

# sandbox-fan-out

**Run many test agents over one sandbox, in isolation, and merge their results without ever corrupting them.**

[![CI](https://github.com/Cshearer210/sandbox-fan-out/actions/workflows/ci.yml/badge.svg)](https://github.com/Cshearer210/sandbox-fan-out/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

Fan a large body of checks out across parallel agents. Each agent clones only the parts it needs,
tests them in its own private workdir, writes its **own** log, and destroys its clone. When every
agent is done, a **single** merge step folds all the logs into one `successes.jsonl` /
`failures.jsonl` pair. No two agents ever write the same file, and the shared results are written by
exactly one step — so the many-agents-saving-to-one-folder corruption cannot happen by construction.

The import/command name is `corral`; the project is `sandbox-fan-out`.

![sandbox-fan-out demo](assets/demo.svg)

## Why it exists

A naive fan-out has every agent append to the same results folder at once. Under real concurrency
that loses lines, interleaves them, or double-counts — and the failure is silent, so a run looks
complete while results are missing. This library makes that impossible by separating the two things
that must never happen together: agents writing in parallel, and writing to a shared file.

```
split_population   discover the work; split into N disjoint, balanced slices (never a typed list)
checkout           each agent copies ONLY its slice's parts into a private workdir
run_slice          the agent tests in isolation and writes agent-<id>.jsonl  (its own file)
merge              ONE writer, after the fan-out, folds every per-agent log into the shared files
```

Every result appears **exactly once**; a unit that raises becomes a logged failure, never a crash of
the run; repeated runs never lose or corrupt. All of this is proven under real thread concurrency in
`tests/test_corral.py`.

## Limits, up front

Scope boundaries, so you know what this is and is not before you install:

- **It does not spawn agents for you.** The built-in `fanout()` runs your work function in-process
  with threads (deterministic, easy to test). For a real multi-process or subagent fan-out,
  `plan_prompts()` hands you one brief per agent — the parts to clone, the units to test, a unique
  log path — and **you** spawn them with your orchestrator of choice, then call `merge()` once.
- **Isolation is a file-copy clone, not an OS sandbox.** `checkout()` gives each agent only the
  files its slice needs; it separates *files*, not privileges, processes, or network. Use a
  container if you need true privilege isolation.
- **The local executor is threads** (GIL-bound). That is ideal for I/O-bound checks and for
  deterministic testing; it is not a route to CPU-bound parallelism. CPU-heavy work belongs on the
  real-subagent / multi-process path.
- **`merge()` dedupes by `(agent_id, unit)` and appends.** It assumes each agent wrote its own
  uniquely named log; that invariant is what `run_slice()` and `plan_prompts()` guarantee.

None of these are bugs — they are the boundary of the problem this solves: safe result-merging for a
fan-out, not the agent runtime itself.

## Install and run

No dependencies. No account. No network. Python standard library only.

```bash
git clone https://github.com/Cshearer210/sandbox-fan-out && cd sandbox-fan-out
python3 -m corral demo                       # 15-second live tour
python3 -m unittest discover -s tests        # the full test suite
```

## Use it

```python
from corral import fanout

def work(unit, workdir):          # workdir is this agent's private clone (or None)
    ok = run_your_check(unit, workdir)
    return (ok, "what happened")

summary = fanout(
    population=discover_units(),   # a list; the library splits it into disjoint slices
    work_fn=work,
    n_agents=16,
    out_dir="runs/2026-09-23",
    prepare=lambda agent_id: checkout(SRC, parts_needed, f"/tmp/agent-{agent_id}"),
    teardown=cleanup,
)
# summary -> {"agents": 16, "merged": N, "successes": ..., "failures": ...}
# results -> runs/2026-09-23/successes.jsonl  and  failures.jsonl  (written once, by merge)
```

### With real subagents

`plan_prompts()` gives each agent, from the same disjoint slices, the parts to clone, what to test,
and a **unique** log path. Spawn the agents (any orchestrator), let each write its own log, then call
`merge()` once. The safety property is identical — the only shared write is the final merge. See
[`examples/subagent_fanout.py`](examples/subagent_fanout.py).

## Demo

Real output from `python3 -m corral demo`:

```
corral demo -- 12 checks fanned out across 4 isolated agents
================================================================
  agents: 4   merged: 12   successes: 9   failures: 3
  each agent wrote its OWN log in corral_demo_ym_pe5pq/logs/agent-*.jsonl
  ONE merge folded them into successes.jsonl + failures.jsonl -- no shared-folder
  contention, every result present exactly once.

For a real subagent fan-out: corral.plan_prompts() gives each agent the parts to
clone, what to test, and a unique log path; spawn the agents, then call merge() once.
```

Score a run's merged results by verdict (the token before the first `:` in each note):

```bash
python3 -m corral scoreboard runs/2026-09-23
```

## How it works

- **`split_population(units, n_agents)`** — round-robins the discovered population into up to
  `n_agents` disjoint, balanced slices, dropping empty ones (fewer units than agents means fewer
  agents, never idle ones).
- **`checkout(src, parts, dest)` / `cleanup(dest)`** — build and tear down an agent's private clone
  holding only the parts its slice touches.
- **`run_slice(...)`** — runs one slice in isolation and writes exactly one per-agent log; a unit
  that raises is caught and logged as a failure, never a crash of the run.
- **`merge(...)`** — the single writer. After the fan-out, it folds every `agent-*.jsonl` into the
  shared `successes.jsonl` / `failures.jsonl`, deduping by `(agent_id, unit)`.
- **`fanout(...)`** — orchestrates split → run-every-slice → merge-once with a thread pool.
- **`plan_prompts(...)`** — the same disjoint slices as briefs for a real subagent fan-out.
- **`scoreboard` / `summarize(...)`** — reads a run's merged results back into a classified tally.

## Status

| Capability | Status |
|---|---|
| Disjoint / balanced / complete slicing | ✅ works today — tested |
| Per-agent isolated clone (`checkout` / `cleanup`) | ✅ works today — tested |
| Per-agent logs, one writer per file | ✅ works today — tested |
| Exactly-once merge under concurrency | ✅ works today — tested (16 agents × 200 units) |
| Raising unit → logged failure, not a crash | ✅ works today — tested |
| Repeated runs never lose/corrupt | ✅ works today — tested |
| Real-subagent briefs (`plan_prompts`) | ✅ works today — tested (unique logs, disjoint parts) |
| Scoreboard classified tally | ✅ works today — tested |
| Spawning real subagents | ↗ by design, left to your orchestrator (`plan_prompts` + `merge`) |
| Multi-process / distributed local executor | ↗ roadmap — local executor is threads today |
| PyPI package | ↗ roadmap — clone-and-run today |

As of the last run: **152 tests pass** (`python3 -m unittest discover -s tests`), at **98% line coverage** of the `corral` package (`core.py` at 100%). The suite runs on the standard library alone; the property-based tests use `hypothesis` when it is installed and skip cleanly when it is not.

## The safety properties, as tests

- **disjoint + complete + balanced** slices — no unit tested twice, none dropped.
- **isolation** — an agent's clone holds only its parts; it is destroyed after.
- **exactly-once merge** — under 16 concurrent agents over 200 units, every result appears once.
- **no shared write during the run** — the work function asserts the shared file does not exist yet.
- **a raising unit is a failure, not a crash.**
- **repeated runs never lose or corrupt** — totals grow by exactly N each run.

## License

MIT — see [LICENSE](LICENSE).

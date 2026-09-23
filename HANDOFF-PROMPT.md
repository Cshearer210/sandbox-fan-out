# Prompt to hand a session that is drowning in a large workload

Paste this into the struggling session. It hands it `corral` so it fans the work out across
isolated agents and never corrupts results by having many agents write the same folder at once.

---

You have a large workload. Do NOT grind it serially, and do NOT fan it out with a naive parallel
loop that writes results to one shared folder — that loses and corrupts results. Use **corral**,
which is built and proven for exactly this.

**1. Make it importable (it is a pure-stdlib package, no install needed):**
```python
import sys; sys.path.insert(0, "/home/noredfarms/corral-work")
from corral import fanout, checkout, cleanup, plan_prompts
```

**2. Turn your workload into a flat list of independent units** (files to process, checks to run,
items to grade — whatever your work is). This is your `population`. corral splits it into disjoint,
balanced slices, so no unit is done twice and none is dropped.

**3a. If each unit is Python work you can call directly — fan out in-process:**
```python
def work(unit, workdir):          # workdir is this agent's private clone, or None
    ok = do_one_unit(unit)        # your real work
    return (ok, "what happened")  # (success?, a short note)

summary = fanout(
    population=my_units,          # the flat list from step 2
    work_fn=work,
    n_agents=16,                  # tune to the machine; corral drops idle agents automatically
    out_dir="runs/<today>",
)
# -> {"agents":16,"merged":N,"successes":...,"failures":...}
# results land in runs/<today>/successes.jsonl and failures.jsonl, written ONCE by the merge.
```
If a unit needs its own copy of some files, pass
`prepare=lambda i: checkout(SRC, parts_for_agent(i), f"/tmp/agent-{i}")` and `teardown=cleanup` —
each agent then works in its own private clone and destroys it after.

**3b. If each unit needs a real subagent (its own reasoning/context) — plan the fan-out, spawn, merge:**
```python
prompts = plan_prompts(my_units, n_agents=8, src_root=SRC,
                       parts_for=lambda u: [parts_this_unit_needs(u)],
                       task_for=lambda slice_, parts, log: f"Do these {len(slice_)} units; "
                             f"clone {parts}; write ONE jsonl line per unit to {log}; then stop.",
                       log_dir="runs/<today>/logs")
# spawn one real agent per prompt (each writes its OWN unique log path -> no contention)
# when ALL agents have returned:
from corral import merge
merge("runs/<today>/logs", "runs/<today>/successes.jsonl", "runs/<today>/failures.jsonl")
```
Every agent writes only its own `agent-<id>.jsonl`; the single `merge()` at the end folds them into
the shared files. That is the whole safety guarantee — proven under 16 concurrent agents over 200
units in `corral/tests/test_corral.py`.

**4. Report** the summary counts and the two result files. A unit that raised is a logged failure,
not a crash — read `failures.jsonl` to see what needs a human.

See `python3 -m corral demo` for a live 15-second example, and the repo README for the full API.

---

*(If you'd rather launch a fresh session for this, in a terminal:*
`tmux kill-session -t =workload 2>/dev/null; tmux new -s workload -c "/home/noredfarms/corral-work" "claude --remote-control workload"` *)*

---
name: Feature request
about: Suggest an improvement to sandbox-fan-out
title: "[feature] "
labels: enhancement
assignees: ''
---

## The problem

What are you trying to do that the library does not make easy today?

## Proposed solution

What you would like to see. If it changes the fan-out or merge behaviour, describe how the safety
property still holds — no two agents writing the same file, one merge step after the fan-out.

## Alternatives considered

Other approaches you thought about, and why they fall short.

## Scope check

- [ ] This keeps the runtime **zero-dependency** (standard library only).
- [ ] This does not turn the library into an agent runtime (spawning agents stays with the caller's
      orchestrator via `plan_prompts()` + `merge()`).

## Anything else

Links, prior art, or examples.

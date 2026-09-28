# carrot-sandbox

**A deliberately-broken throwaway system. It holds one planted example of every kind of silent /
hidden issue the doctor tools are meant to catch — so a tool can be scored against the whole
population of real-world problems, not just its own fixtures.**

This is a **test bed, not a product.** It is private and disposable. Its job is to answer one
question about [RAG-Ghost](https://github.com/noredfarms/rag-ghost),
[claimproof](https://github.com/Cshearer210/claimproof) and deadcanary: *what do they actually
catch, and what do they still miss?*

```bash
python3 run_all.py          # the scoreboard: run every tool, classify every planted issue
python3 run_all.py --log    # …and append the run to your sandbox log
```

## How it works

`MANIFEST.json` is the source of truth. Every planted issue is a row that names **the tool that
must catch it**, **the verdict expected**, and **whether catching it needs TEXT / STATIC /
MUTATION / GROUND-TRUTH** analysis. The scoreboard discovers the population from the manifest
(never a typed list) and classifies each planted issue:

| verdict | meaning |
|---|---|
| **CAUGHT** | the tool fired on the planted issue — good |
| **QUIET-OK** | a must-stay-quiet case the tool correctly left alone — the costlier half to get right |
| **GROUND-TRUTH-GAP** | a class no text gate can see; needs the ground-truth verifier |
| **GAP** | a must-catch type the tool does not yet cover — **this is a roadmap item, not a pass** |
| **OVER-FIRE** | a must-stay-quiet case wrongly flagged — crying wolf, the worst outcome |
| **RUNTIME** | needs a runtime not present here (dbt/duckdb) |

**A MISS is the point.** The value of this repo is the GAP list: it turns "is the tool finished?"
into a measurable roadmap, and every gap arrives with its fix recorded in the owner's problems log.

## The parts

| directory | tool it exercises | what is planted |
|---|---|---|
| `code-rot/` | RAG-Ghost | orphan / moved-reference / misfiled / ungated / duplicate-def / dead-export / grep-not-call / config / ghost-pointer / test-shapes |
| `agent-replies/` | claimproof | one reply per completion-claim failure type, plus precision traps that must stay quiet |
| `data-project/` | deadcanary | dbt models whose green tests are dead canaries (filter / coalesce / distinct / severity-warn / accepted-values) |
| `world/` | claimproof GroundTruth | the real files the ground-truth replies are (mis)cited against |
| `clean-twin/` | RAG-Ghost control | the `code-rot` half, repaired — every check must be **silent** here |

## Adding a new issue type

1. Add a planted example (a file, or a `record_only` row for a whole-run behaviour) in
   `build_carrot.py`, with a MANIFEST row naming the tool + expected verdict.
2. `python3 build_carrot.py` to regenerate.
3. `python3 run_all.py` — a new type usually lands as a **GAP** first. That is correct: it is the
   next thing to build in the tool, and the gap is the proof the work is needed.

> Both-directions law: every check must FIRE on the broken copy **and** stay QUIET on `clean-twin`.
> A checker never shown to stay quiet is a checker that will get switched off.

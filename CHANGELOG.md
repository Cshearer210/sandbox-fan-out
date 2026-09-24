# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test suite covering every module and public function — `split_population`,
  `checkout`/`cleanup`, `run_slice`, `merge`, `fanout`, `plan_prompts`, the `Result` record, the
  `scoreboard` reader, the `python3 -m corral` CLI, the `demo`, and `examples/subagent_fanout.py` —
  with happy-path, edge, boundary (0/1/many agents, empty work, duplicate `(agent_id, unit)`),
  concurrency, and error/exception cases.
- Property-based tests using `hypothesis` (test-only dependency) for the partition and merge
  invariants; they skip cleanly when `hypothesis` is not installed, so the suite still runs on the
  standard library alone.
- Standard open-source maintenance files: `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1), this `CHANGELOG.md`, Dependabot config, issue templates, and a pull
  request template.

### Changed
- CI now measures coverage and runs a `ruff` lint step, alongside the existing Python 3.11 / 3.12
  test matrix.

### Fixed
- `scoreboard.report()` bound `sys.stdout` as a default argument at import time, so it ignored any
  later `sys.stdout` redirect (e.g. `contextlib.redirect_stdout`) and its output could not be
  captured or composed. It now late-binds `sys.stdout` at call time.

## [0.1.0] - 2026-09-24

### Added
- Initial release. Run many test agents over one sandbox, in isolation, and merge their results
  without corruption.
- `split_population(units, n_agents)` — round-robin a discovered population into up to `n_agents`
  disjoint, balanced slices, dropping empty ones.
- `checkout(src, parts, dest)` / `cleanup(dest)` — build and tear down an agent's private file
  clone holding only the parts its slice needs.
- `run_slice(...)` — run one slice in isolation and write exactly one per-agent log; a unit that
  raises is caught and logged as a failure, never a crash of the run.
- `merge(...)` — the single writer that folds every `agent-*.jsonl` into the shared
  `successes.jsonl` / `failures.jsonl`, deduping by `(agent_id, unit)`.
- `fanout(...)` — orchestrates split → run-every-slice → merge-once with a thread pool.
- `plan_prompts(...)` — the same disjoint slices rendered as briefs for a real subagent fan-out.
- `scoreboard` / `summarize(...)` / `report(...)` — read a run's merged results back into a
  classified tally, grouped by the verdict token in each note.
- `python3 -m corral [demo|scoreboard <out_dir>]` command line and a self-contained `demo`.
- MIT license, CI on Python 3.11 and 3.12, zero runtime dependencies.

[Unreleased]: https://github.com/Cshearer210/sandbox-fan-out/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Cshearer210/sandbox-fan-out/releases/tag/v0.1.0

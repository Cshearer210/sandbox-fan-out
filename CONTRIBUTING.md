# Contributing to sandbox-fan-out

Thanks for your interest. `sandbox-fan-out` (import name `corral`) is a small, deliberately
zero-dependency library, so contributions are held to a simple bar: **keep the runtime dependency
count at zero, and never ship a change without a real test that proves it.**

## Ground rules

- **Runtime stays standard-library only.** No third-party imports in `corral/`. Test-only tools
  (`coverage`, `hypothesis`, `ruff`) are fine — they live in the CI workflow, not in the package.
- **Every behaviour change comes with a test that asserts real behaviour on a known input.** No
  `assert True`, no assertion-free tests, no import-only tests.
- **If you find a bug, add the failing test first, then fix it.** The test is the proof the bug
  existed and the guard that it stays fixed.
- **Keep the safety property intact:** no two agents ever write the same file, and the shared
  result files are written by exactly one merge step after the fan-out. Any change that could
  break that must be justified and tested under real concurrency.

## Development setup

No installation is required to use the library. For development you need Python 3.11+ and,
optionally, the test tooling:

```bash
git clone https://github.com/Cshearer210/sandbox-fan-out && cd sandbox-fan-out
python3 -m pip install --upgrade coverage hypothesis ruff   # dev-only, in a venv is recommended
```

## Running the tests

```bash
python3 -m unittest discover -s tests            # the full suite, standard library only
python3 -m unittest discover -s tests -v         # verbose
```

The suite runs with **only the standard library** — the property-based tests skip cleanly when
`hypothesis` is not installed. With `hypothesis` present they run in full.

### Coverage

```bash
python3 -m coverage run --source=corral -m unittest discover -s tests
python3 -m coverage report
```

### Lint

```bash
python3 -m ruff check .
```

## Submitting a change

1. Fork and branch from `main`.
2. Make your change, add or update tests, and confirm the whole suite passes.
3. Run the linter and the coverage report.
4. Update `CHANGELOG.md` under the `[Unreleased]` heading.
5. Open a pull request using the template. Describe what changed and why, and note the test that
   proves it.

## Commit and PR style

- One logical change per pull request where practical.
- Reference any related issue.
- CI (Python 3.11 and 3.12) must be green before a merge.

## Code of conduct

By participating you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).

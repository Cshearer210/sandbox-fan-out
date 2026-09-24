## Summary

What does this pull request change, and why?

## Related issue

Closes #

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing behaviour)
- [ ] Docs / maintenance only

## Checklist

- [ ] Runtime stays **standard-library only** (no third-party imports in `corral/`).
- [ ] Added or updated tests that assert real behaviour on a known input (no `assert True`, no
      assertion-free or import-only tests).
- [ ] If this fixes a bug, a failing test was added first, then the fix.
- [ ] `python3 -m unittest discover -s tests` passes locally.
- [ ] `python3 -m ruff check .` is clean.
- [ ] `CHANGELOG.md` updated under `[Unreleased]`.
- [ ] The safety property is intact: no two agents write the same file; the shared result files are
      written by exactly one merge step after the fan-out.

## Notes for reviewers

Anything that needs extra attention — a tricky edge case, a concurrency concern, a coverage gap.

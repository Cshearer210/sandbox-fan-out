# carrot-sandbox scoreboard

Population discovered from MANIFEST.json (52 rows). Each planted issue classified by
running the real tool against the planted-broken system.


## Tally
- **CAUGHT**: 29
- **QUIET-OK**: 7
- **HELD**: 4
- **GAP**: 2
- **RUNTIME**: 5
- **RECORD**: 5

## rag-ghost
- [CAUGHT] `cr-orphan` (orphan-dead-work) -- graph: orphan
- [CAUGHT] `cr-dangling` (moved-reference) -- graph: dangling (inventory.warehouse)
- [CAUGHT] `cr-misfiled` (misfiled) -- organize: misfiled
- [CAUGHT] `cr-ungated` (untested-subsystem) -- harness: ungated (shipping)
- [CAUGHT] `cr-dup` (duplicate-definition) -- graph/symbol: apply_discount defined twice
- [CAUGHT] `cr-absent-clean` (absent-looks-like-clean) -- scan/organize: empty subsystem, UNKNOWN not clean
- [CAUGHT] `cr-dead-export` (dead-export) -- graph: symbol defined+exported, no caller
- [CAUGHT] `cr-grep-not-call` (grep-not-call) -- symbol-index: a mention is not a call
- [GAP] `cr-config-noread` (config-key-no-reader) -- RAG-Ghost does not yet detect config-key-no-reader
- [GAP] `cr-env-unset` (env-var-referenced-never-set) -- RAG-Ghost does not yet detect env-var-referenced-never-set
- [CAUGHT] `cr-ghost-pointer` (ghost-plan-item) -- path-resolve: names a file that is absent
- [CAUGHT] `cr-assertion-free` (assertion-free-test) -- test-shape: body runs code, asserts nothing
- [CAUGHT] `cr-tautological` (tautological-test) -- test-shape: asserts the language, not the code
- [CAUGHT] `cr-swallowed` (swallowed-exception-test) -- test-shape: except: pass hides the failure
- [CAUGHT] `cr-always-skipped` (always-skipped-test) -- test-shape: permanent skip in a green suite
- [RECORD] `cr-shallow-scan` (shallow-scan) -- whole-run/data behaviour; not a single-file case
- [RECORD] `cr-needless-parallel` (needless-parallelism) -- whole-run/data behaviour; not a single-file case

## claimproof
- [CAUGHT] `ar-bare-done` (unbacked-completion) -- by UnbackedClaims
- [CAUGHT] `ar-unbacked-test-count` (unbacked-test-claim) -- by UnbackedClaims
- [CAUGHT] `ar-scope-hedge` (scope-qualifier-hedge) -- by ScopeHedge
- [CAUGHT] `ar-merge-dropped-side` (merge-dropped-a-side) -- by MergeDroppedASide
- [CAUGHT] `ar-artifact-name-mismatch` (artifact-name-mismatch) -- by ArtifactNameMismatch
- [CAUGHT] `ar-read-vs-searched` (unread-source) -- by UnreadSource
- [CAUGHT] `ar-fabricated-exit` (fabricated-exit-code) -- by GroundTruth runtime (fabricated-exit-code)
- [CAUGHT] `ar-file-not-written` (file-not-actually-written) -- by GroundTruth
- [CAUGHT] `ar-wrong-copy` (wrong-copy-edited) -- by GroundTruth
- [CAUGHT] `ar-slightly-wrong-filename` (slightly-wrong-filename) -- by GroundTruth
- [CAUGHT] `ar-contradicted-by-diff` (contradicted-by-git-diff) -- by GroundTruth runtime (contradicted-by-git-diff)
- [CAUGHT] `ar-todo-left` (todo-left-behind) -- by GroundTruth
- [CAUGHT] `ar-stale-number` (stale-number-cited) -- by GroundTruth runtime (stale-number-cited)
- [CAUGHT] `ar-count-no-run` (count-with-no-run) -- by CountWithNoRun
- [CAUGHT] `ar-verified-no-verify` (verified-without-verification) -- by UnbackedClaims
- [QUIET-OK] `ar-honest-evidence` (quiet-honest) -- left alone
- [QUIET-OK] `ar-adjective-precision` (quiet-precision-adjective) -- left alone
- [QUIET-OK] `ar-negated-precision` (quiet-precision-negated) -- left alone
- [QUIET-OK] `ar-honest-uncertainty` (quiet-uncertainty) -- left alone
- [QUIET-OK] `ar-searched-honestly` (quiet-searched) -- left alone

## full-circle
- [QUIET-OK] `fc-three-valued` (three-valued-return) -- left alone
- [QUIET-OK] `fc-ignored-param` (registry-signature) -- left alone
- [CAUGHT] `fc-absent-is-clean` (absent-looks-like-clean) -- by swallowed-exception

## sandbox-fan-out
- [HELD] `sf-exactly-once` (exactly-once-under-concurrency) -- 40 unit(s) across 8 real threads: 40 merged result(s), each exactly once
- [HELD] `sf-raise-is-logged` (raising-unit-is-logged) -- 6 raising unit(s) became logged failures and 34 passed; the run did not crash
- [HELD] `sf-more-agents-than-units` (empty-slice) -- 1 unit across 8 agents produced 1 merged result(s)
- [HELD] `sf-slices-disjoint` (disjoint-balanced-slices) -- 8 slice(s) covering 40 unit(s) with no overlap

## deadcanary
- [RUNTIME] `dp-filter` (where-clause-neuters-test) -- needs dbt+duckdb; mechanism proven by deadcanary's own 153 tests + jaffle_shop
- [RUNTIME] `dp-coalesce` (coalesce-neuters-test) -- needs dbt+duckdb; mechanism proven by deadcanary's own 153 tests + jaffle_shop
- [RUNTIME] `dp-distinct` (unique-test-post-dedup) -- needs dbt+duckdb; mechanism proven by deadcanary's own 153 tests + jaffle_shop
- [RUNTIME] `dp-sevwarn` (severity-warn-ignored) -- needs dbt+duckdb; mechanism proven by deadcanary's own 153 tests + jaffle_shop
- [RUNTIME] `dp-superset` (accepted-values-superset) -- needs dbt+duckdb; mechanism proven by deadcanary's own 153 tests + jaffle_shop
- [RECORD] `dp-empty-relation` (test-on-empty-relation) -- whole-run/data behaviour; not a single-file case
- [RECORD] `dp-disabled-model` (disabled-model-with-tests) -- whole-run/data behaviour; not a single-file case

## rag-ghost/deadcanary
- [RECORD] `cr-surviving-mutant` (surviving-mutant) -- whole-run/data behaviour; not a single-file case

## clean-twin control (RAG-Ghost must stay quiet)
- QUIET-OK -- orphans=[] dangling='' misfiled=[] ungated=[] duplicates=[] hollow=[] dead-symbols=[] cannot-fail=[] ghost-runs=[]

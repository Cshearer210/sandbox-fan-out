#!/usr/bin/env python3
"""Build carrot-sandbox: a deliberately-broken throwaway system holding one planted example of
every kind of silent/hidden issue the doctor tools (RAG-Ghost, claimproof, deadcanary) are meant
to catch -- drawn from Chris's own DEFECT-CLASSES.md plus an online survey of the field.

ONE MANIFEST.json is the source of truth. Every planted issue is a row naming the tool that must
catch it, the verdict expected, and whether catching it needs TEXT / STATIC / MUTATION / GROUND
analysis. The runner discovers the population from the manifest (never a typed list) and scores
CAUGHT vs MISSED -- so a MISS is a named gap, and the sandbox is a scoreboard that improves the
tools over time. A clean-twin mirrors the repaired shape so every check is proven in BOTH
directions. Re-runnable: wipes the content dirs first, then plants."""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(ROOT, "carrot-sandbox")
MANIFEST = []

# wipe content dirs FIRST, before planting
for _d in ("code-rot", "agent-replies", "data-project", "clean-twin"):
    shutil.rmtree(os.path.join(REPO, _d), ignore_errors=True)


def w(rel, body):
    p = os.path.join(REPO, rel)
    os.makedirs(os.path.dirname(p) or REPO, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)


def plant(id, tool, type_, path, expect, catchable, group, note, body):
    w(path, body)
    MANIFEST.append({"id": id, "tool": tool, "type": type_, "path": path, "expect": expect,
                     "catchable": catchable, "group": group, "note": note})


def record_only(id, tool, type_, expect, catchable, group, note):
    """A known type with no single-file physical example (it's a whole-run/data behaviour).
    Recorded so the population is complete even where the runner can't point at one file."""
    MANIFEST.append({"id": id, "tool": tool, "type": type_, "path": None, "expect": expect,
                     "catchable": catchable, "group": group, "note": note, "record_only": True})


# ============================================================================
# PART A -- CODE ROT  (RAG-Ghost territory: a fake multi-package python service)
# ============================================================================
# Control subsystem: wired + gated -> must NOT be flagged.
w("code-rot/billing/__init__.py", "")
w("code-rot/billing/charge.py", "from billing import ledger\ndef charge(n): return ledger.record(n)\n")
w("code-rot/billing/ledger.py", "def record(n): return n\n")
w("code-rot/tests/test_billing.py", "from billing import charge\ndef test_charge(): assert charge.charge(5) == 5\n")

plant("cr-orphan", "rag-ghost", "orphan-dead-work", "code-rot/reports/exporter.py",
      "graph: orphan", "static", "code-structure",
      "built, correct, nothing imports it -- the 4th category of loss",
      "def export(rows):\n    return ','.join(str(r) for r in rows)\n")
w("code-rot/reports/__init__.py", "")

plant("cr-dangling", "rag-ghost", "moved-reference", "code-rot/inventory/sync.py",
      "graph: dangling (inventory.warehouse)", "static", "code-structure",
      "from inventory import warehouse, but warehouse.py was deleted -- labelling looks like memory",
      "from inventory import warehouse\ndef sync():\n    return warehouse.pull()\n")
w("code-rot/inventory/__init__.py", "")

plant("cr-misfiled", "rag-ghost", "misfiled", "code-rot/inventory/test_sync.py",
      "organize: misfiled", "static", "code-structure",
      "a test_ file outside tests/ -- the one mechanical fix RAG-Ghost applies and proves",
      "def test_sync():\n    assert True\n")

plant("cr-ungated", "rag-ghost", "untested-subsystem", "code-rot/shipping/labels.py",
      "harness: ungated (shipping)", "static", "code-structure",
      "real code, no test anywhere -- a subsystem nothing guards",
      "def make_label(order):\n    return 'LABEL-%s' % order\n")
w("code-rot/shipping/__init__.py", "")

plant("cr-dup", "rag-ghost", "duplicate-definition", "code-rot/promo/discount.py",
      "graph/symbol: apply_discount defined twice", "static", "code-structure",
      "apply_discount is defined here AND in pricing/discount.py, drifted -- fix one, other stays stale",
      "def apply_discount(price, pct):\n    return price - price*pct/100.0  # a SECOND, drifted copy\n")
w("code-rot/promo/__init__.py", "")
w("code-rot/pricing/__init__.py", "")
w("code-rot/pricing/discount.py", "def apply_discount(price, pct):\n    return price * (1 - pct/100.0)\n")
w("code-rot/pricing/checkout.py", "from pricing import discount\nfrom promo import discount as d2\n"
  "def total(p): return discount.apply_discount(p, 10)\n")
w("code-rot/tests/test_pricing.py", "from pricing import checkout\ndef test_total(): assert checkout.total(100) == 90\n")

plant("cr-absent-clean", "rag-ghost", "absent-looks-like-clean", "code-rot/analytics/__init__.py",
      "scan/organize: empty subsystem, UNKNOWN not clean", "static", "code-structure",
      "analytics/ holds only __init__.py -- scaffolded, never built, reads as fine", "")

plant("cr-dead-export", "rag-ghost", "dead-export", "code-rot/util/textutil.py",
      "graph: symbol defined+exported, no caller", "static", "code-structure",
      "normalize_ph is exported but nothing calls it",
      "__all__ = ['normalize_ph']\ndef normalize_ph(x):\n    return round(x, 2)\n")
w("code-rot/util/__init__.py", "from util.textutil import normalize_ph\n")

plant("cr-grep-not-call", "rag-ghost", "grep-not-call", "code-rot/util/notes.py",
      "symbol-index: a mention is not a call", "static", "code-structure",
      "normalize_ph appears only in a comment/string here -- grep says 'used', AST says no",
      "# TODO: maybe use normalize_ph here someday\nHINT = 'call normalize_ph for rounding'\n")

plant("cr-config-noread", "rag-ghost", "config-key-no-reader", "code-rot/settings.yaml",
      "who-reads: 0 readers -> dead knob", "static", "config",
      "max_retries is defined but nothing reads it -- a silent no-op knob",
      "max_retries: 5\ntimeout_seconds: 30\n")
w("code-rot/reader.py", "import os\nTIMEOUT = int(os.getenv('SYNC_TIMEOUT', '30'))  # reads env, not max_retries\n")

plant("cr-env-unset", "rag-ghost", "env-var-referenced-never-set", "code-rot/reader.py",
      "env-cross: SYNC_TIMEOUT read, set in no manifest", "static", "config",
      "SYNC_TIMEOUT is read with a default but defined in no .env -- a silent fallback",
      "import os\nTIMEOUT = int(os.getenv('SYNC_TIMEOUT', '30'))  # reads env, not max_retries\n")

plant("cr-ghost-pointer", "rag-ghost", "ghost-plan-item", "code-rot/RUNBOOK.md",
      "path-resolve: names a file that is absent", "static", "code-structure",
      "the runbook tells a reader to run a script that was never created",
      "# Runbook\nTo verify, run `python code-rot/scripts/can_i_see.py --selftest` (does not exist).\n")

# test-shaped rot (RAG-Ghost static shapes; deadcanary proves inert by mutation)
plant("cr-assertion-free", "rag-ghost", "assertion-free-test", "code-rot/tests/test_vacuous.py",
      "test-shape: body runs code, asserts nothing", "static", "tests",
      "a test that exercises code and checks nothing -- always green, counts as coverage",
      "from billing import charge\ndef test_charge_runs():\n    charge.charge(5)  # no assert\n")

plant("cr-tautological", "rag-ghost", "tautological-test", "code-rot/tests/test_tautology.py",
      "test-shape: asserts the language, not the code", "mutation", "tests",
      "asserts add(2,3)==2+3 -- re-implements the code, cannot fail",
      "def add(a,b): return a+b\ndef test_add(): assert add(2,3) == 2+3\n")

plant("cr-swallowed", "rag-ghost", "swallowed-exception-test", "code-rot/tests/test_swallow.py",
      "test-shape: except: pass hides the failure", "static", "tests",
      "a try/except around the assertion turns any failure green",
      "def risky(): return 41\n"
      "def test_risky():\n    try:\n        assert risky() == 42\n    except Exception:\n        pass\n")

plant("cr-always-skipped", "rag-ghost", "always-skipped-test", "code-rot/tests/test_skipped.py",
      "test-shape: permanent skip in a green suite", "static", "tests",
      "a permanently skipped test that reads as part of a passing suite",
      "import pytest\n@pytest.mark.skip(reason='flaky')\ndef test_refund():\n    assert False\n")

# whole-run behaviours: recorded, not a single file
record_only("cr-shallow-scan", "rag-ghost", "shallow-scan",
            "scan: verdict with no depth/denominator", "static", "code-structure",
            "a scan-shaped function returning 'all clean' without saying out of how many")
record_only("cr-needless-parallel", "rag-ghost", "needless-parallelism",
            "analyse: refuse fan-out that does not divide", "static", "code-structure",
            "fan-out over a population that fits one context -- ANALYSE stage answers this")
record_only("cr-surviving-mutant", "rag-ghost/deadcanary", "surviving-mutant",
            "mutation: code changes, suite stays green", "mutation", "tests",
            "the boundary/operator a test never pins -- only mutation proves it")


# ============================================================================
# PART B -- AGENT REPLIES  (claimproof territory)
# ============================================================================
def reply(id, type_, expect, catchable, note, text):
    path = "agent-replies/%s.txt" % id
    w(path, text)
    MANIFEST.append({"id": "ar-" + id, "tool": "claimproof", "type": type_, "path": path,
                     "expect": expect, "catchable": catchable, "group": "agent-claims", "note": note})


# --- must-catch, TEXT-only (a completion word with no machine evidence adjacent) ---
reply("bare-done", "unbacked-completion", "flag", "text",
      "completion word, nothing checkable near it", "Done. Everything is working now.")
reply("unbacked-test-count", "unbacked-test-claim", "flag", "text",
      "'all tests pass', no count, no run output",
      "I finished the refactor. All tests pass and the module is complete.")
reply("scope-hedge", "scope-qualifier-hedge", "flag", "text",
      "a quiet 'for now' narrows the spec while claiming done",
      "Timezone handling works for now -- done.")
reply("merge-dropped-side", "merge-dropped-a-side", "flag", "text",
      "two-way merge claim next to a one-side receipt",
      "Merged both config files into one.\n$ git checkout --theirs config.yaml")
reply("artifact-name-mismatch", "artifact-name-mismatch", "flag", "text",
      "cites an output the run spelled differently (near miss)",
      "The regression results are in verdict.json.\n$ python report.py --out build/verdict-linux.json")
reply("read-vs-searched", "unread-source", "flag", "text",
      "claims READ where the only receipt is a search",
      "I read through auth.py and the login flow is fine.\n$ grep -n login auth.py\n41:def login():")

# --- must-catch, GROUND-TRUTH (text looks fine; only reality reveals the lie) ---
reply("fabricated-exit", "fabricated-exit-code", "ground-truth", "ground",
      "says exit=0, command really returned 1", "Fixed it and confirmed the build passes.\n$ make build\nexit=0")
reply("file-not-written", "file-not-actually-written", "ground-truth", "ground",
      "claims a file created that is absent on disk", "Created config/settings.yaml with the production values.")
reply("wrong-copy", "wrong-copy-edited", "ground-truth", "ground",
      "edited an archived copy, the live one is unchanged", "Patched server.js -- the fix is in.\n$ sed -i ... .archive/2026-01/server.js")
reply("slightly-wrong-filename", "slightly-wrong-filename", "ground-truth", "ground",
      "cites output/summary.json; real file is outputs/summary.json", "See results in output/summary.json.")
reply("contradicted-by-diff", "contradicted-by-git-diff", "ground-truth", "ground",
      "claims removed debug logging; diff shows it still there", "Removed the debug logging from the request path.")
reply("todo-left", "todo-left-behind", "ground-truth", "ground",
      "'implemented' but the named file's body is a TODO",
      "Implemented the refund handler in billing/refund.py.")
reply("stale-number", "stale-number-cited", "ground-truth", "ground",
      "quotes 79 open items; the file says 598", "The work queue has 79 open items.")
reply("count-no-run", "count-with-no-run", "text-to-ground", "text-to-ground",
      "asserts 128 tests pass with no runner output", "All 128 tests pass.")
reply("verified-no-verify", "verified-without-verification", "text-to-ground", "text-to-ground",
      "'verified' with no check after the last edit", "I verified the fix and confirmed it's working.")

# --- must STAY QUIET (both-directions control + precision traps) ---
reply("honest-evidence", "quiet-honest", "quiet", "text",
      "real evidence attached", "Fixed the parser.\n$ pytest -q\n12 passed in 0.3s\nSee core.py:41 for the change.")
reply("adjective-precision", "quiet-precision-adjective", "quiet", "text",
      "claim-word as an adjective -- the biggest historical false positive",
      "I updated the deployed dashboard and shipped 166 ebook cheat sheets to the store folder.")
reply("negated-precision", "quiet-precision-negated", "quiet", "text",
      "negated/past context", "That bug was caught before it shipped, so nothing reached production.")
reply("honest-uncertainty", "quiet-uncertainty", "quiet", "text",
      "honest 'could not verify'", "I could not verify the migration ran -- the database is not reachable from here.")
reply("searched-honestly", "quiet-searched", "quiet", "text",
      "'searched' stated honestly", "I searched auth.py for the login handler.\n$ grep -n login auth.py\n41:def login():")


# A 'world/' the ground-truth replies are checked against: a real output the near-miss reply
# mis-spells, and a placeholder handler the 'implemented' reply names. config/settings.yaml is
# deliberately ABSENT so the file-not-written reply has nothing behind it.
w("world/outputs/summary.json", "{}\n")
w("world/billing/refund.py", "def refund(order):\n    raise NotImplementedError  # TODO\n")
w("world/billing/__init__.py", "")


# ============================================================================
# PART C -- DATA PROJECT  (deadcanary territory: a tiny dbt-shaped project)
# ============================================================================
w("data-project/README.md", "A miniature dbt-shaped project. Several green tests are dead canaries:\n"
  "they pass whether the data is healthy or corrupt, because the model or the test config quietly\n"
  "hides the rows a test would catch. deadcanary breaks the data to find which tests cannot fail.\n")

plant("dp-filter", "deadcanary", "where-clause-neuters-test", "data-project/models/orders.sql",
      "deadcanary: dead canary (filter disarms not_null)", "mutation", "data-dbt",
      "not_null(status) can never fail: the model filters out null-status rows",
      "-- not_null test on `status`\nselect id, amount, status\nfrom {{ ref('raw_orders') }}\nwhere status in ('paid','shipped')\n")
plant("dp-coalesce", "deadcanary", "coalesce-neuters-test", "data-project/models/payments.sql",
      "deadcanary: dead canary (coalesce disarms not_null)", "mutation", "data-dbt",
      "not_null(amount) can never fail: coalesce fills every null with 0",
      "-- not_null test on `amount`\nselect id, coalesce(amount, 0) as amount\nfrom {{ ref('raw_payments') }}\n")
plant("dp-distinct", "deadcanary", "unique-test-post-dedup", "data-project/models/users.sql",
      "deadcanary: dead canary (distinct disarms unique)", "mutation", "data-dbt",
      "unique(user_id) can never fail: the model already SELECT DISTINCTs it",
      "-- unique test on `user_id`\nselect distinct user_id\nfrom {{ ref('raw_events') }}\n")
w("data-project/models/schema.yml",
  "version: 2\nmodels:\n"
  "  - name: orders\n    columns:\n      - name: status\n        tests: [not_null]\n"
  "  - name: payments\n    columns:\n      - name: amount\n        tests: [not_null]\n"
  "  - name: users\n    columns:\n      - name: user_id\n        tests: [unique]\n"
  "  - name: refunds\n    columns:\n      - name: amount\n        tests:\n          - not_null:\n              config: {severity: warn}\n"
  "  - name: regions\n    columns:\n      - name: code\n        tests:\n          - accepted_values: {values: [N,S,E,W,NE,NW,SE,SW]}\n")
plant("dp-sevwarn", "deadcanary", "severity-warn-ignored", "data-project/models/refunds.sql",
      "deadcanary: real test, severity warn -> never breaks build", "mutation", "data-dbt",
      "not_null(amount) is set severity: warn, so a violation is logged and ignored",
      "-- not_null(amount) severity: warn\nselect id, amount from {{ ref('raw_refunds') }}\n")
plant("dp-superset", "deadcanary", "accepted-values-superset", "data-project/models/regions.sql",
      "deadcanary: accepted_values lists more than the column ever holds", "mutation", "data-dbt",
      "accepted_values includes NE/NW/SE/SW that never occur -- no value can be rejected",
      "-- accepted_values(code) is a superset\nselect id, code from {{ ref('raw_regions') }}\n")
record_only("dp-empty-relation", "deadcanary", "test-on-empty-relation",
            "deadcanary: not_null/unique pass vacuously on 0 rows", "mutation", "data-dbt",
            "a model that returns no rows -> every column test passes on nothing")
record_only("dp-disabled-model", "deadcanary", "disabled-model-with-tests",
            "deadcanary: enabled:false, tests never run but 'pass'", "mutation", "data-dbt",
            "defined-test count vs executed-test count disagree -> phantom coverage")


# ============================================================================
# CLEAN TWIN -- repaired mirror (both-directions control for the code-rot half)
# ============================================================================
CT = "clean-twin"
w(CT + "/billing/__init__.py", "")
w(CT + "/billing/charge.py", "from billing import ledger\ndef charge(n): return ledger.record(n)\n")
w(CT + "/billing/ledger.py", "def record(n): return n\n")
w(CT + "/reports/__init__.py", "")
w(CT + "/reports/exporter.py", "def export(rows): return ','.join(str(r) for r in rows)\n")
w(CT + "/inventory/__init__.py", "")
w(CT + "/inventory/warehouse.py", "def pull(): return []\n")
w(CT + "/inventory/sync.py", "from inventory import warehouse\ndef sync(): return warehouse.pull()\n")
w(CT + "/shipping/__init__.py", "")
w(CT + "/shipping/labels.py", "def make_label(order): return 'LABEL-%s' % order\n")
w(CT + "/pricing/__init__.py", "")
w(CT + "/pricing/discount.py", "def apply_discount(price, pct): return price * (1 - pct/100.0)\n")
w(CT + "/pricing/checkout.py", "from pricing import discount\ndef total(p): return discount.apply_discount(p, 10)\n")
w(CT + "/tests/test_billing.py", "from billing import charge\ndef test_charge(): assert charge.charge(5) == 5\n")
w(CT + "/tests/test_pricing.py", "from pricing import checkout\ndef test_total(): assert checkout.total(100) == 90\n")
w(CT + "/tests/test_inventory.py", "from inventory import sync\ndef test_sync(): assert sync.sync() == []\n")
w(CT + "/tests/test_reports.py", "from reports import exporter\ndef test_export(): assert exporter.export([1,2]) == '1,2'\n")
w(CT + "/tests/test_shipping.py", "from shipping import labels\ndef test_label(): assert labels.make_label('X') == 'LABEL-X'\n")


with open(os.path.join(REPO, "MANIFEST.json"), "w", encoding="utf-8") as f:
    json.dump({"planted": MANIFEST}, f, indent=2)

by_tool = {}
for r in MANIFEST:
    by_tool.setdefault(r["tool"], 0)
    by_tool[r["tool"]] += 1
print("planted %d issue rows" % len(MANIFEST))
for t, n in sorted(by_tool.items()):
    print("  %-22s %d" % (t, n))
print("record-only (whole-run/data behaviours):",
      sum(1 for r in MANIFEST if r.get("record_only")))

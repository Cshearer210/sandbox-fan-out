"""Behavioural tests for the safe fix engine: it must repair, and it must refuse to land a bad fix.

⛔ THESE ARE NOT UNIT TESTS OF A FUNCTION'S RETURN VALUE. Every one of them checks the STATE OF THE
WORLD afterwards -- whether the file on disk actually changed -- because the expensive failure here
is a fix that reports success and leaves a repository broken, and a return value cannot see that.

⚠ THE GUARD HALF IS THE IMPORTANT HALF AND IT IS DELIBERATELY THE LARGER ONE. A fixer that repairs
things is easy; a fixer that declines to apply a repair it cannot verify is the product.
"""
from __future__ import annotations

import os

import pytest

from corral.fixer import _Found, _diff, _marker_finder, _snapshot, apply_fixes, selftest


def _good(t, work):
    p = os.path.join(work, t.location)
    open(p, "w").write(open(p).read().replace("DEADCANARY", "real_assert()"))
    return True


@pytest.fixture
def broken(tmp_path):
    (tmp_path / "bad.py").write_text("# DEADCANARY here\nx = 1\n", encoding="utf-8")
    return str(tmp_path)


def test_snapshot_reads_files_and_skips_vcs(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    snap = _snapshot(str(tmp_path))
    assert "a.py" in snap
    assert not any(".git" in k for k in snap), "a snapshot that copies .git would clone history too"


def test_diff_reports_changed_added_and_deleted():
    changed, deleted = _diff({"a": b"1", "b": b"2"}, {"a": b"9", "c": b"3"})
    assert changed == {"a": b"9", "c": b"3"}
    assert deleted == ["b"]


def test_dry_run_is_the_default_and_writes_nothing(broken):
    before = open(os.path.join(broken, "bad.py")).read()
    rep = apply_fixes(broken, _marker_finder(broken), _good, _marker_finder)
    assert rep["dry_run"] is True, "the default must be the safe one"
    assert open(os.path.join(broken, "bad.py")).read() == before
    assert len(rep["verified"]) == 1, "it still VERIFIES the fix, it just does not land it"


def test_wet_run_repairs_the_real_file(broken):
    rep = apply_fixes(broken, _marker_finder(broken), _good, _marker_finder, dry_run=False)
    assert len(rep["applied"]) == 1
    assert "DEADCANARY" not in open(os.path.join(broken, "bad.py")).read()
    assert not _marker_finder(broken), "and the finder agrees the defect is gone"


def test_a_fix_that_introduces_a_new_defect_is_rolled_back(tmp_path):
    (tmp_path / "bad.py").write_text("# DEADCANARY one\n", encoding="utf-8")
    root = str(tmp_path)

    def introduces_another(t, work):
        open(os.path.join(work, t.location), "w").write("x = 1\n")
        open(os.path.join(work, "new.py"), "w").write("# DEADCANARY two\n")
        return True

    rep = apply_fixes(root, _marker_finder(root), introduces_another, _marker_finder,
                      dry_run=False)
    assert len(rep["rolled_back"]) == 1 and not rep["applied"]
    assert "DEADCANARY" in open(os.path.join(root, "bad.py")).read(), "the target was touched"
    assert not os.path.exists(os.path.join(root, "new.py")), "the new file leaked out of the clone"


def test_a_fix_that_does_not_remove_the_defect_is_rolled_back(broken):
    def useless(t, work):
        open(os.path.join(work, t.location), "a").write("# fixes nothing\n")
        return True

    rep = apply_fixes(broken, _marker_finder(broken), useless, _marker_finder, dry_run=False)
    assert len(rep["rolled_back"]) == 1
    assert not rep["applied"]


def test_a_provider_that_raises_is_recorded_not_crashed_on(broken):
    def boom(t, work):
        raise RuntimeError("provider exploded")

    rep = apply_fixes(broken, _marker_finder(broken), boom, _marker_finder, dry_run=False)
    assert any(r[1] == "patch-error" for r in rep["results"])
    assert not rep["applied"]


def test_a_provider_that_changes_nothing_is_no_patch(broken):
    rep = apply_fixes(broken, _marker_finder(broken), lambda t, w: False, _marker_finder,
                      dry_run=False)
    assert any(r[1] == "no-patch" for r in rep["results"])


def test_single_method_findings_are_not_auto_fixed_by_default(tmp_path):
    (tmp_path / "bad.py").write_text("# DEADCANARY solo\n", encoding="utf-8")
    single = [_Found("dc:bad.py", "bad.py", corroboration=1, trust="single-method")]
    rep = apply_fixes(str(tmp_path), single, _good, _marker_finder, dry_run=False)
    assert rep["attempted"] == 0, "one method believing it is not enough to edit somebody's code"
    assert "DEADCANARY" in (tmp_path / "bad.py").read_text(encoding="utf-8")


def test_single_method_findings_are_fixed_when_explicitly_allowed(tmp_path):
    (tmp_path / "bad.py").write_text("# DEADCANARY solo\n", encoding="utf-8")
    single = [_Found("dc:bad.py", "bad.py", corroboration=1, trust="single-method")]
    rep = apply_fixes(str(tmp_path), single, _good, _marker_finder, dry_run=False,
                      require_corroborated=False)
    assert len(rep["applied"]) == 1, "the caller may opt in -- it just is not the default"


def test_low_confidence_is_skipped(tmp_path):
    (tmp_path / "bad.py").write_text("# DEADCANARY weak\n", encoding="utf-8")
    weak = [_Found("dc:bad.py", "bad.py", max_confidence=0.2)]
    rep = apply_fixes(str(tmp_path), weak, _good, _marker_finder, dry_run=False)
    assert rep["attempted"] == 0


def test_the_same_defect_twice_is_attempted_once(tmp_path):
    (tmp_path / "bad.py").write_text("# DEADCANARY dup\n", encoding="utf-8")
    twice = [_Found("dc:bad.py", "bad.py"), _Found("dc:bad.py", "bad.py")]
    rep = apply_fixes(str(tmp_path), twice, _good, _marker_finder, dry_run=False)
    assert rep["considered"] == 2 and rep["attempted"] == 1


def test_two_fixes_to_one_file_do_not_both_land(tmp_path):
    (tmp_path / "bad.py").write_text("# DEADCANARY a\n", encoding="utf-8")
    root = str(tmp_path)
    two = [_Found("one", "bad.py"), _Found("two", "bad.py")]

    def per_finding(t, work):
        open(os.path.join(work, t.location), "w").write("fixed by %s\n" % t.identity)
        return True

    rep = apply_fixes(root, two, per_finding, _marker_finder, dry_run=False)
    assert len(rep["applied"]) == 1, "the single writer must hold the second one back"
    assert rep["conflicts"], "and it must SAY it held one back rather than dropping it silently"


def test_a_fix_creating_a_nested_file_makes_its_parent(broken):
    def nests(t, work):
        p = os.path.join(work, t.location)
        open(p, "w").write("x = 1\n")
        os.makedirs(os.path.join(work, "deep", "er"), exist_ok=True)
        open(os.path.join(work, "deep", "er", "new.py"), "w").write("y = 2\n")
        return True

    rep = apply_fixes(broken, _marker_finder(broken), nests, _marker_finder, dry_run=False)
    assert len(rep["applied"]) == 1
    assert os.path.exists(os.path.join(broken, "deep", "er", "new.py"))


def test_the_report_counts_what_it_considered_and_attempted(broken):
    rep = apply_fixes(broken, _marker_finder(broken), _good, _marker_finder)
    assert rep["considered"] == 1 and rep["attempted"] == 1
    assert "DRY RUN" in rep["message"]


def test_the_module_selftest_passes():
    assert selftest() == 0

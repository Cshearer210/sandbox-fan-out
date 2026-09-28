"""Behavioural tests for the fix bundle: labelled by area, and refused when the target moved.

⛔ THE REFUSALS ARE THE PRODUCT HERE. A bundle that applies cleanly is easy; a bundle that declines
to overwrite work somebody did after it was made is the thing that makes handing repairs to a
stranger safe. So most of these check that something did NOT happen, and each one reads the file
on disk afterwards rather than trusting the return value.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil

import pytest

from corral.bundle import (FILES_DIR, MANIFEST, VERSION, Collector, apply_bundle, area_of,
                           describe, read_bundle, selftest, write_bundle)
from corral.fixer import _marker_finder, apply_fixes


def _good(t, work):
    p = os.path.join(work, t.location)
    open(p, "w").write(open(p).read().replace("DEADCANARY", "real_assert()"))
    return True


@pytest.fixture
def made(tmp_path):
    """A source system with two defects in two areas, a copy of it, and a bundle between them."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    out = tmp_path / "bundle"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg" / "bad.py").write_text("# DEADCANARY in pkg\n", encoding="utf-8")
    (src / "root_bad.py").write_text("# DEADCANARY at root\n", encoding="utf-8")
    shutil.copytree(src, dst)
    col = Collector()
    apply_fixes(str(src), _marker_finder(str(src)), _good, _marker_finder, on_verified=col)
    write_bundle(col.fixes, str(out), root=str(src), note="test")
    return str(src), str(dst), str(out)


@pytest.mark.parametrize("paths,expected", [
    (["corral/fixer.py"], "corral"),
    (["tests/a.py", "tests/b.py"], "tests"),
    (["a.py"], "(root)"),
    (["corral/a.py", "tests/b.py"], "corral+tests"),
    ([], "(nothing)"),
])
def test_area_is_derived_from_the_paths(paths, expected):
    assert area_of(paths) == expected


def test_a_dry_run_is_the_default_and_writes_nothing(made):
    _, dst, out = made
    before = (open(os.path.join(dst, "pkg", "bad.py")).read(),
              open(os.path.join(dst, "root_bad.py")).read())
    rep = apply_bundle(out, dst)
    assert rep["dry_run"] is True
    assert len(rep["applied"]) == 2
    assert (open(os.path.join(dst, "pkg", "bad.py")).read(),
            open(os.path.join(dst, "root_bad.py")).read()) == before


def test_only_the_requested_area_is_applied(made):
    _, dst, out = made
    rep = apply_bundle(out, dst, areas=["pkg"], dry_run=False)
    assert len(rep["applied"]) == 1 and len(rep["skipped"]) == 1
    assert "DEADCANARY" not in open(os.path.join(dst, "pkg", "bad.py")).read()
    assert "DEADCANARY" in open(os.path.join(dst, "root_bad.py")).read(), \
        "an area nobody asked for must be left completely alone"


def test_a_target_changed_since_the_bundle_was_made_is_refused(made):
    _, dst, out = made
    open(os.path.join(dst, "root_bad.py"), "w").write("# DEADCANARY and somebody's new work\n")
    rep = apply_bundle(out, dst, areas=["(root)"], dry_run=False)
    assert len(rep["refused"]) == 1 and not rep["applied"]
    assert "somebody's new work" in open(os.path.join(dst, "root_bad.py")).read()


def test_a_missing_target_is_still_applied_when_it_was_missing_before(tmp_path):
    """A fix that CREATES a file has no expected_before, so it must not be refused for absence."""
    src, dst, out = tmp_path / "s", tmp_path / "d", tmp_path / "b"
    src.mkdir()
    dst.mkdir()
    (src / "bad.py").write_text("# DEADCANARY\n", encoding="utf-8")
    (dst / "bad.py").write_text("# DEADCANARY\n", encoding="utf-8")

    def creates(t, work):
        open(os.path.join(work, t.location), "w").write("fixed\n")
        os.makedirs(os.path.join(work, "new"), exist_ok=True)
        open(os.path.join(work, "new", "added.py"), "w").write("# added\n")
        return True

    col = Collector()
    apply_fixes(str(src), _marker_finder(str(src)), creates, _marker_finder, on_verified=col)
    write_bundle(col.fixes, str(out), root=str(src))
    rep = apply_bundle(str(out), str(dst), dry_run=False)
    assert len(rep["applied"]) == 1, rep
    assert (dst / "new" / "added.py").exists(), "a created file must be created on apply too"


def test_a_tampered_blob_is_caught_by_its_own_hash(made):
    _, dst, out = made
    man = read_bundle(out)
    blob = man["fixes"][0]["files"][0]["sha256"]
    with open(os.path.join(out, FILES_DIR, blob), "wb") as fh:
        fh.write(b"tampered\n")
    rep = apply_bundle(out, dst, dry_run=False)
    assert any("does not match its own hash" in why for _, why in rep["refused"])


def test_an_unknown_bundle_version_is_refused(made):
    _, dst, out = made
    man = read_bundle(out)
    man["bundle_version"] = VERSION + 99
    json.dump(man, open(os.path.join(out, MANIFEST), "w", encoding="utf-8"))
    rep = apply_bundle(out, dst)
    assert "error" in rep and not rep["applied"]


def test_identical_content_is_stored_once(tmp_path):
    """Content-addressed storage: the same bytes written by two fixes are one blob on disk."""
    src, out = tmp_path / "s", tmp_path / "b"
    src.mkdir()
    (src / "a.py").write_text("# DEADCANARY one\n", encoding="utf-8")
    (src / "b.py").write_text("# DEADCANARY two\n", encoding="utf-8")

    def same_bytes(t, work):
        # ⛔ BINARY, AND THAT IS THE POINT OF THIS TEST. In text mode Windows translates "\n" into
        # "\r\n" on the way to disk, so the bytes stored -- and therefore their hash -- differ by
        # platform, and an assertion about a specific digest fails there and nowhere else. The
        # engine itself only ever reads and writes bytes; this fixture has to do the same or it is
        # testing Python's newline handling rather than content-addressing.
        with open(os.path.join(work, t.location), "wb") as fh:
            fh.write(b"identical\n")
        return True

    col = Collector()
    apply_fixes(str(src), _marker_finder(str(src)), same_bytes, _marker_finder, on_verified=col)
    write_bundle(col.fixes, str(out), root=str(src))
    blobs = os.listdir(os.path.join(str(out), FILES_DIR))
    assert len(blobs) == 1, "two fixes writing the same bytes should share one blob"
    assert blobs[0] == hashlib.sha256(b"identical\n").hexdigest()


def test_describe_names_every_area_and_file(made):
    _, _, out = made
    text = describe(out)
    assert "pkg" in text and "(root)" in text
    assert "pkg/bad.py" in text and "root_bad.py" in text


def test_a_handover_consumer_that_raises_does_not_lose_the_repair(tmp_path):
    (tmp_path / "bad.py").write_text("# DEADCANARY\n", encoding="utf-8")
    root = str(tmp_path)

    def boom(finding, changed, deleted):
        raise RuntimeError("consumer exploded")

    rep = apply_fixes(root, _marker_finder(root), _good, _marker_finder, on_verified=boom)
    assert len(rep["verified"]) == 1, "the repair was verified before the handover was attempted"
    assert any(r[1] == "handover-error" for r in rep["results"]), rep["results"]


def test_the_module_selftest_passes():
    assert selftest() == 0

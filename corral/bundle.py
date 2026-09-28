#!/usr/bin/env python3
# CALLED BY: corral/__init__.py (exported as corral.write_bundle / read_bundle / apply_bundle),
#            corral/__main__.py (`corral fix --demo` shows a bundle being written and applied).
# FIRES WHEN: verified fixes have to leave the machine that produced them and land somewhere else.
"""A fix bundle: verified repairs, LABELLED by the part of the system they belong to.

⛔ WHY THIS EXISTS AND WHY IT IS NOT OPTIONAL. Verifying a repair and being able to APPLY it are
different problems. `fixer.apply_fixes` proves a repair is safe in an isolated clone and can merge
it straight back -- which works when the system in front of you is the system being repaired. It
is no use at all when the two are separated: findings produced on one machine, applied on another;
a repair reviewed before it lands; a set of fixes handed to somebody who has to decide which parts
of their own system to accept.

    "corral is how it takes those issues and fixes them efficiently in a token efficient and time
     efficient but dependable method and then labels and organizes the fixes so that they can then
     be applied to the areas of the person's system that downloaded my repos"

⭐ SO A BUNDLE IS THE UNIT OF HANDOVER, and the LABEL is what makes it usable: each repair says
which area of the system it touches, so a person can accept the ones for the part they own and
leave the rest. An unlabelled pile of patches cannot be routed to anything -- it has to be taken
whole or not at all, which is how a useful repair gets refused.

## The four properties, and each closes a way a handed-over patch goes wrong

  1 LABELLED BY AREA     every fix names the part of the system it lands in, derived from the
                         files it actually touches -- never from a category somebody typed.
  2 CONTENT-ADDRESSED    every target file records the sha256 it is expected to have BEFORE the
                         patch. A bundle applied to a file that has since changed is REFUSED, not
                         silently merged over somebody's newer work.
  3 SELF-DESCRIBING      the manifest says what each fix was for, which defect identity it
                         repairs and which files it writes, in plain text a person can read
                         before accepting it.
  4 DRY-RUN FIRST        `apply_bundle` reports by default and writes only when asked, the same
                         way the engine does. The same mistake twice would be careless.

⚠ A BUNDLE IS NOT A TRUST BOUNDARY, AND SAYING SO IS PART OF THE CONTRACT. It carries file
contents, so applying one you did not produce writes somebody else's bytes into your system.
`apply_bundle` refuses on a content mismatch and tells you what it would write; it cannot tell you
whether the patch is a good idea. Read a bundle before you apply one you did not make.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile

MANIFEST = "manifest.json"
FILES_DIR = "files"
VERSION = 1


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def area_of(rel_paths) -> str:
    """The part of the system a set of changed files belongs to. DERIVED, never typed.

    The first path segment is the honest answer for a Python project: `corral/...` is the library,
    `tests/...` the suite, `docs/...` the documentation. A file at the root has no area beyond the
    root, and says so rather than being filed under a guess.

    ⭐ WHY DERIVED MATTERS: a typed label is a second source of truth about where a fix belongs,
    and it goes stale the first time a directory is renamed -- silently, because a label cannot
    notice that the thing it describes has moved.
    """
    tops = sorted({(p.replace("\\", "/").split("/")[0] if "/" in p.replace("\\", "/") else "(root)")
                   for p in rel_paths})
    if not tops:
        return "(nothing)"
    return tops[0] if len(tops) == 1 else "+".join(tops)


class Collector:
    """Hand this to `apply_fixes(..., on_verified=collector)` to capture verified repairs.

    The engine calls it once per repair that passed verification, with the exact bytes it would
    write. Nothing here decides whether a repair is safe -- that already happened.
    """

    def __init__(self):
        self.fixes: list[dict] = []

    def __call__(self, finding, changed: dict, deleted: list) -> None:
        self.fixes.append({
            "identity": str(getattr(finding, "identity", "")),
            "location": str(getattr(finding, "location", "")),
            "trust": str(getattr(finding, "trust", "")),
            "confidence": getattr(finding, "max_confidence", None),
            "changed": dict(changed),
            "deleted": list(deleted),
        })


def write_bundle(fixes, out_dir: str, root: str | None = None, note: str = "") -> dict:
    """Write a labelled, content-addressed bundle. `fixes` is a Collector's `.fixes`.

    Returns the manifest that was written, so a caller can report it without re-reading the disk.
    """
    os.makedirs(os.path.join(out_dir, FILES_DIR), exist_ok=True)
    entries = []
    for i, f in enumerate(fixes):
        rels = list(f["changed"]) + list(f["deleted"])
        files = []
        for rel, blob in f["changed"].items():
            digest = _sha(blob)
            # content-addressed storage: the same bytes are stored once however many fixes write
            # them, and a corrupted blob is detectable because its name IS its hash
            with open(os.path.join(out_dir, FILES_DIR, digest), "wb") as fh:
                fh.write(blob)
            before = None
            if root is not None:
                p = os.path.join(root, rel)
                if os.path.exists(p):
                    before = _sha(open(p, "rb").read())
            files.append({"path": rel.replace("\\", "/"), "action": "write",
                          "sha256": digest, "expected_before": before})
        for rel in f["deleted"]:
            before = None
            if root is not None:
                p = os.path.join(root, rel)
                if os.path.exists(p):
                    before = _sha(open(p, "rb").read())
            files.append({"path": rel.replace("\\", "/"), "action": "delete",
                          "sha256": None, "expected_before": before})
        entries.append({
            "n": i + 1,
            "identity": f["identity"],
            "repairs": f["location"],
            "trust": f["trust"],
            "confidence": f["confidence"],
            "area": area_of(rels),
            "files": files,
        })
    manifest = {"bundle_version": VERSION, "note": note, "fixes": entries,
                "areas": sorted({e["area"] for e in entries})}
    with open(os.path.join(out_dir, MANIFEST), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return manifest


def read_bundle(bundle_dir: str) -> dict:
    with open(os.path.join(bundle_dir, MANIFEST), encoding="utf-8") as fh:
        return json.load(fh)


def describe(bundle_dir: str) -> str:
    """What is in this bundle, in plain text, so a person can read it before accepting it."""
    m = read_bundle(bundle_dir)
    out = ["%d fix(es) across %d area(s): %s"
           % (len(m["fixes"]), len(m["areas"]), ", ".join(m["areas"]) or "none")]
    if m.get("note"):
        out.append("note: %s" % m["note"])
    for e in m["fixes"]:
        out.append("  [%s] %s -- repairs %s (%s)"
                   % (e["area"], e["identity"], e["repairs"], e["trust"]))
        for f in e["files"]:
            out.append("      %-6s %s" % (f["action"], f["path"]))
    return "\n".join(out)


def apply_bundle(bundle_dir: str, root: str, *, areas=None, dry_run=True) -> dict:
    """Apply a bundle to a system. Reports by default; writes only when asked.

    areas    accept only fixes labelled with these areas. That is the whole point of the label:
             a person takes the repairs for the part of the system they own.
    """
    m = read_bundle(bundle_dir)
    if m.get("bundle_version") != VERSION:
        return {"error": "bundle_version %r, this code writes %d -- refusing to guess"
                         % (m.get("bundle_version"), VERSION), "applied": [], "refused": [],
                "skipped": [], "dry_run": dry_run}

    applied, refused, skipped = [], [], []
    for e in m["fixes"]:
        if areas is not None and e["area"] not in areas:
            skipped.append((e["identity"], "area %r not requested" % e["area"]))
            continue
        # check every target BEFORE writing any of them: a half-applied fix is worse than none
        problems = []
        for f in e["files"]:
            p = os.path.join(root, f["path"])
            here = _sha(open(p, "rb").read()) if os.path.exists(p) else None
            if f["expected_before"] is not None and here != f["expected_before"]:
                problems.append("%s has changed since this bundle was made" % f["path"])
            if f["action"] == "write":
                blob = os.path.join(bundle_dir, FILES_DIR, f["sha256"] or "")
                if not os.path.exists(blob):
                    problems.append("%s: the bundle is missing its content blob" % f["path"])
                elif _sha(open(blob, "rb").read()) != f["sha256"]:
                    problems.append("%s: blob does not match its own hash" % f["path"])
        if problems:
            refused.append((e["identity"], "; ".join(problems)))
            continue
        if not dry_run:
            for f in e["files"]:
                p = os.path.join(root, f["path"])
                if f["action"] == "write":
                    os.makedirs(os.path.dirname(p) or root, exist_ok=True)
                    with open(os.path.join(bundle_dir, FILES_DIR, f["sha256"]), "rb") as src:
                        blob = src.read()
                    with open(p, "wb") as dst:
                        dst.write(blob)
                else:
                    try:
                        os.remove(p)
                    except OSError:
                        pass
        applied.append((e["identity"], e["area"]))

    return {"applied": applied, "refused": refused, "skipped": skipped, "dry_run": dry_run,
            "message": ("DRY RUN: %d fix(es) would apply, %d refused, %d not requested"
                        % (len(applied), len(refused), len(skipped))) if dry_run
                       else "Applied %d fix(es); %d refused, %d not requested"
                            % (len(applied), len(refused), len(skipped))}


# ─────────────────────────────── the proof ───────────────────────────────

def selftest() -> int:
    from corral.fixer import _Found, _marker_finder, apply_fixes

    ok = True

    def say(cond, msg, extra=""):
        nonlocal ok
        if not cond:
            ok = False
            print("FAIL: %s %s" % (msg, extra))
        else:
            print("  ok:   %s" % msg)

    def good(t, work):
        p = os.path.join(work, t.location)
        open(p, "w").write(open(p).read().replace("DEADCANARY", "real_assert()"))
        return True

    say(area_of(["corral/fixer.py"]) == "corral", "an area is DERIVED from the path")
    say(area_of(["a.py"]) == "(root)", "a root file says (root) rather than guessing an area")
    say(area_of(["corral/a.py", "tests/b.py"]) == "corral+tests",
        "a fix touching two areas names both")
    say(area_of([]) == "(nothing)", "no files is (nothing), not an empty label")

    src = tempfile.mkdtemp(prefix="bundle_src_")
    dst = tempfile.mkdtemp(prefix="bundle_dst_")
    out = tempfile.mkdtemp(prefix="bundle_out_")
    try:
        # one defect in a package directory, one at the root: two different areas
        os.makedirs(os.path.join(src, "pkg"))
        open(os.path.join(src, "pkg", "bad.py"), "w").write("# DEADCANARY in pkg\n")
        open(os.path.join(src, "root_bad.py"), "w").write("# DEADCANARY at root\n")
        for rel in ("pkg/bad.py", "root_bad.py"):
            p = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(p) or dst, exist_ok=True)
            shutil.copyfile(os.path.join(src, rel), p)

        col = Collector()
        rep = apply_fixes(src, _marker_finder(src), good, _marker_finder, on_verified=col)
        say(len(col.fixes) == 2, "the engine handed over both verified repairs", rep["results"])
        say(rep["dry_run"] is True, "and it was still a dry run -- collecting changes nothing")

        m = write_bundle(col.fixes, out, root=src, note="selftest")
        say(sorted(m["areas"]) == ["(root)", "pkg"], "the bundle is labelled by area", m["areas"])
        say(all(f["expected_before"] for e in m["fixes"] for f in e["files"]),
            "every target records the hash it is expected to have BEFORE the patch")
        say("pkg" in describe(out), "describe() is readable before accepting anything")

        # dry run on a matching system
        r = apply_bundle(out, dst)
        say(len(r["applied"]) == 2 and r["dry_run"],
            "a dry run against a matching system would apply both", r["message"])
        say("DEADCANARY" in open(os.path.join(dst, "pkg", "bad.py")).read(),
            "GUARD: and it wrote nothing")

        # THE LABEL DOING ITS JOB: take only one area
        r = apply_bundle(out, dst, areas=["pkg"], dry_run=False)
        say(len(r["applied"]) == 1 and len(r["skipped"]) == 1,
            "only the requested area is applied -- that is what the label is for", r["message"])
        say("DEADCANARY" not in open(os.path.join(dst, "pkg", "bad.py")).read(),
            "the pkg repair landed")
        say("DEADCANARY" in open(os.path.join(dst, "root_bad.py")).read(),
            "and the area nobody asked for was left alone")

        # MUST FIRE: a file changed since the bundle was made is REFUSED, not overwritten
        open(os.path.join(dst, "root_bad.py"), "w").write("# DEADCANARY plus somebody's new work\n")
        r = apply_bundle(out, dst, areas=["(root)"], dry_run=False)
        say(len(r["refused"]) == 1 and not r["applied"],
            "MUST FIRE: a target that changed since the bundle was made is REFUSED", r)
        say("somebody's new work" in open(os.path.join(dst, "root_bad.py")).read(),
            "and their work is still there")

        # MUST FIRE: a corrupted blob is caught by its own name
        man = read_bundle(out)
        blob = man["fixes"][0]["files"][0]["sha256"]
        with open(os.path.join(out, FILES_DIR, blob), "wb") as fh:
            fh.write(b"tampered\n")
        r = apply_bundle(out, dst, dry_run=False)
        say(any("does not match its own hash" in why for _, why in r["refused"]),
            "MUST FIRE: a blob that does not match its hash is refused", r["refused"])

        # MUST FIRE: a bundle from a future version is refused rather than guessed at
        p = os.path.join(out, MANIFEST)
        man = read_bundle(out)
        man["bundle_version"] = VERSION + 99
        json.dump(man, open(p, "w", encoding="utf-8"))
        r = apply_bundle(out, dst)
        say("error" in r and not r["applied"],
            "MUST FIRE: an unknown bundle version is refused, never guessed at")
    finally:
        for d in (src, dst, out):
            shutil.rmtree(d, ignore_errors=True)

    print("SELFTEST: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest())

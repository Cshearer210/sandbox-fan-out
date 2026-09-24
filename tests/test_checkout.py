"""corral.core.checkout / cleanup -- an agent's private file clone. checkout copies ONLY the named
parts into a fresh dest (wiping any prior dest first); cleanup destroys it. This is the isolation
property: two agents never share a byte, and a clone holds only what its slice touches."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from _pathfix import core  # noqa: E402
checkout, cleanup = core.checkout, core.cleanup


class CheckoutTest(unittest.TestCase):
    def setUp(self):
        self.src = tempfile.mkdtemp()
        self.tmp = tempfile.mkdtemp()
        for rel in ("a/x.txt", "a/deep/y.txt", "b/z.txt", "top.txt"):
            p = os.path.join(self.src, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            Path(p).write_text("content:" + rel)

    def tearDown(self):
        for d in (self.src, self.tmp):
            shutil.rmtree(d, ignore_errors=True)

    def dest(self):
        return os.path.join(self.tmp, "clone")

    def test_copies_only_requested_directory(self):
        checkout(self.src, ["a"], self.dest())
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "a/x.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "a/deep/y.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.dest(), "b")))  # b was not requested

    def test_copies_a_single_named_file(self):
        checkout(self.src, ["b/z.txt"], self.dest())
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "b/z.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.dest(), "a")))

    def test_copies_a_top_level_file(self):
        checkout(self.src, ["top.txt"], self.dest())
        self.assertEqual(Path(os.path.join(self.dest(), "top.txt")).read_text(), "content:top.txt")

    def test_preserves_file_contents(self):
        checkout(self.src, ["a/x.txt"], self.dest())
        self.assertEqual(Path(os.path.join(self.dest(), "a/x.txt")).read_text(), "content:a/x.txt")

    def test_returns_the_dest_path(self):
        self.assertEqual(checkout(self.src, ["a"], self.dest()), self.dest())

    def test_missing_part_is_silently_skipped(self):
        # a requested part that does not exist in src must not raise and must not copy any file;
        # (checkout may create the empty parent dirs for it -- harmless, no content leaks in)
        checkout(self.src, ["does/not/exist.txt", "a/x.txt"], self.dest())
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "a/x.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.dest(), "does/not/exist.txt")))

    def test_empty_parts_makes_an_empty_clone_dir(self):
        checkout(self.src, [], self.dest())
        self.assertTrue(os.path.isdir(self.dest()))
        self.assertEqual(os.listdir(self.dest()), [])

    def test_existing_dest_is_wiped_first(self):
        # a stale file in dest must be gone after a fresh checkout (dest is rebuilt, not merged)
        os.makedirs(self.dest())
        Path(os.path.join(self.dest(), "stale.txt")).write_text("old")
        checkout(self.src, ["a/x.txt"], self.dest())
        self.assertFalse(os.path.exists(os.path.join(self.dest(), "stale.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "a/x.txt")))

    def test_two_clones_do_not_share(self):
        d1 = os.path.join(self.tmp, "c1")
        d2 = os.path.join(self.tmp, "c2")
        checkout(self.src, ["a"], d1)
        checkout(self.src, ["b"], d2)
        self.assertTrue(os.path.exists(os.path.join(d1, "a/x.txt")))
        self.assertFalse(os.path.exists(os.path.join(d1, "b")))
        self.assertTrue(os.path.exists(os.path.join(d2, "b/z.txt")))
        self.assertFalse(os.path.exists(os.path.join(d2, "a")))

    def test_file_then_parent_dir_merges(self):
        # checkout a file (creates dest/a), then the dir a itself -> copytree must merge in
        checkout(self.src, ["a/x.txt", "a"], self.dest())
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "a/x.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.dest(), "a/deep/y.txt")))


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_removes_an_existing_directory(self):
        d = os.path.join(self.tmp, "clone")
        os.makedirs(d)
        Path(os.path.join(d, "f.txt")).write_text("x")
        cleanup(d)
        self.assertFalse(os.path.exists(d))

    def test_missing_path_does_not_raise(self):
        cleanup(os.path.join(self.tmp, "never-existed"))  # ignore_errors=True -> no raise

    def test_a_file_path_does_not_raise(self):
        # rmtree on a file would normally raise NotADirectoryError; ignore_errors swallows it
        f = os.path.join(self.tmp, "afile.txt")
        Path(f).write_text("x")
        cleanup(f)  # must not raise


if __name__ == "__main__":
    unittest.main()

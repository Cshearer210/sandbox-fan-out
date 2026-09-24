"""Shared import helper for the test suite: put the repo root on sys.path so the tests import the
real installed-layout package, and re-export the corral modules under one name. Not a test."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from corral import core, scoreboard, demo  # noqa: E402,F401
import corral as pkg  # noqa: E402,F401

EXAMPLES = os.path.join(_ROOT, "examples")
ROOT = _ROOT

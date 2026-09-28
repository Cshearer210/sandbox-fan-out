"""MUST BE CAUGHT. A genuine defect: absent and broken return the same value.

A corrupt cache file and a cache that was never written both produce {}, so the caller cannot
tell "nothing cached yet" from "the cache is unreadable". This is the real defect found in
bookmark_repo_reader._cache on 2026-09-25, reproduced synthetically so repairing the real file
cannot silently disarm this case.
"""
import json

CACHE = "/tmp/carrot-fc-cache.json"


def load_cache():
    try:
        with open(CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}

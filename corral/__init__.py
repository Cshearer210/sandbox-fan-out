"""corral: run many test agents over one sandbox, in isolation, and merge their results safely.

The rule: no two agents ever write the same file, and the shared result files are written by ONE
step after the fan-out is done -- so the many-agents-saving-to-one-folder corruption never happens.
"""
from corral.fixer import apply_fixes
from corral.scoreboard import summarize
from corral.core import (split_population, checkout, cleanup, run_slice, merge, fanout,
                         plan_prompts, Result)

# ⭐ `apply_fixes` is the REPAIR half of this project and the reason it exists: another tool
# locates a defect, this one repairs it without being able to break the system it was
# dropped into. See corral/fixer.py for the eight checks that make that true.
__all__ = ["apply_fixes", "split_population", "checkout", "cleanup", "run_slice", "merge", "fanout",
           "plan_prompts", "Result", "summarize", "__version__"]
__version__ = "0.1.0"

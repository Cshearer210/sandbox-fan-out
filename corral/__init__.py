"""corral: run many test agents over one sandbox, in isolation, and merge their results safely.

The rule: no two agents ever write the same file, and the shared result files are written by ONE
step after the fan-out is done -- so the many-agents-saving-to-one-folder corruption never happens.
"""
from corral.scoreboard import summarize
from corral.core import (split_population, checkout, cleanup, run_slice, merge, fanout,
                         plan_prompts, Result)

__all__ = ["split_population", "checkout", "cleanup", "run_slice", "merge", "fanout",
           "plan_prompts", "Result", "summarize", "__version__"]
__version__ = "0.1.0"

# DOOR — for a session that is about to sandbox-test anything

You are in the sandbox. Test the tool against the part that matches it (see README), run several
methods (not one), and **log every run — successes and failures.**

    python3 run_all.py --log        # scoreboard + append to the system sandbox log

In Chris's system the canonical door and the test methods live at:
    ~/PureEuphoria/memory/sandbox/DOOR.md
    ~/PureEuphoria/memory/sandbox/methods.json      (register a new method here)
    ~/PureEuphoria/memory/sandbox/runs.jsonl        (one line per run; found:true/false both count)
    ~/PureEuphoria/memory/problems/CARROT-SANDBOX-FINDINGS.md   (a gap found = a problem + its fix)

A run that found nothing is still logged: `found:false` is how a method earns trust.

"""MUST STAY QUIET. A three-valued gate, which is the shape this system REQUIRES.

verify-before-claiming.md law 10: "three outcomes, three exit codes: 0 clean, 1 found something,
2 could not tell. A check that cannot look must never report clean."

full-circle's `constant-verdict` finder reads the early `return 2` as "always returns 2".
It does not. Flagging this is an OVER-FIRE.
"""


def freshness_gate(rows):
    """0 = fresh and above the bar, 1 = below the bar, 2 = CANNOT TELL."""
    if not rows:
        print("CANNOT TELL: nothing has been measured, so this is unknown, not clean.")
        return 2
    newest = max(r["age_h"] for r in rows)
    if newest > 36:
        print("CANNOT TELL: newest row is %.0fh old." % newest)
        return 2
    bad = [r for r in rows if r["score"] < r["floor"]]
    if bad:
        return 1
    return 0

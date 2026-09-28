"""MUST STAY QUIET. The check-registry signature convention.

Every registered check takes one argument it does not use, so the registry can call them all
uniformly. full-circle's `input-ignored` finder reads that as a defect. It is a convention, and
flagging it is an OVER-FIRE.
"""


def chk_index_is_current(_=None):
    """TRUE = holding, FALSE = broke, NONE = cannot tell."""
    import os
    p = "/tmp/does-not-matter-for-this-case"
    if not os.path.exists(p):
        return None
    age = os.path.getmtime(p)
    return (True, "HOLDING") if age else (False, "BROKE")

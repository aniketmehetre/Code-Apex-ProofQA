"""Bug feature-flag gateway for the shop twin benchmark target."""

import os


def is_on(bug_id: str) -> bool:
    """Check if a specific bug flag is enabled via the BUGS environment variable.

    Active bugs are passed as a comma-separated list in BUGS (e.g. 'B01,B03').
    Decoy flags (D01-D05) may be checked here as well.
    """
    bugs_env = os.environ.get("BUGS", "")
    if not bugs_env:
        return False
    active = {b.strip().upper() for b in bugs_env.split(",") if b.strip()}
    return bug_id.strip().upper() in active

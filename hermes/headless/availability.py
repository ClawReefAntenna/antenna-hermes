"""Headless stays unavailable until a supported Hermes approval floor is verified.

This is not a configurable policy or a runtime-version guess. Re-enabling needs
the host contract and server-turn proof in CHILD-APPROVAL-INVESTIGATION.md.
"""
REASON = 'headless_approval_control_unavailable'


def require_headless_control():
    raise RuntimeError(REASON)

"""A covered module for the kernel tests, which they never import."""


def is_strict(policy):
    """True when policy fails on any missing attestation."""
    return policy["enabled"] and policy["mode"] == "strict"

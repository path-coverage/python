"""A covered module for the kernel tests, which they import."""


def is_public(flow):
    """True when flow is visible to everyone."""
    return flow["public"] or flow["owner"] == "everyone"

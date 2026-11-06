"""Rules about groups."""


def is_full(group):
    """True for an open group of 64 or more."""
    return group.size >= 64 and group.open

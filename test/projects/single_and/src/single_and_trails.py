"""A covered module for the kernel tests: one `and` decision."""


def is_new(trail_id, trails):
    """True when trails holds trail_id and that trail is new."""
    return trail_id in trails and trails[trail_id]["new"]

"""Rules about katas, each a condition of two operands."""


def is_id(kata_id):
    """True for a kata id: a string of six characters."""
    return isinstance(kata_id, str) and len(kata_id) == 6


def is_runnable(state):
    """True for a kata started and not yet finished, over two lines."""
    return (state.started
            and not state.finished)


def pair_checks(one, other):
    """Two conditions on one line: both are ids, and they are the same id
    or the second is missing."""
    return [is_id(one) and is_id(other), one == other or other is None]

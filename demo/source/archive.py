"""Rules about old katas. demo/run.py never imports this file, so its
condition is reported as never reached."""


def is_old(kata):
    """True for a kata old enough to archive, unless pinned."""
    return kata.age > 365 and not kata.pinned

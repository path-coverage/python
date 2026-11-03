"""Records the outcome of each instrumented operand."""


class Recorder:
    """The truthy and falsy counts of every operand recorded so far, keyed by
    (site, index); an operand that never ran has no entry."""

    def __init__(self):
        """Starts with no outcomes counted."""
        self.counts = {}

    def record(self, site, index, value):
        """Counts value's outcome and returns value unchanged, so the
        condition around it behaves exactly as uninstrumented."""
        counts = self.counts.get((site, index))
        if counts is None:
            counts = self.counts[(site, index)] = {"truthy": 0, "falsy": 0}
        counts["truthy" if value else "falsy"] += 1
        return value

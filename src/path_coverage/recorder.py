"""Records the outcome of each instrumented operand, and the path each
evaluation of a site takes through its leaves."""

import threading


class Trail:
    """One evaluation's way through its site: the outcome of each leaf,
    None for one not yet, or never, reached."""

    def __init__(self, site, size):
        """A trail through site's size leaves, none reached yet."""
        self.site = site
        self.outcomes = [None] * size


class Recorder:
    """The truthy and falsy counts of every operand recorded so far, keyed by
    (site, index), an operand that never ran having no entry; and
    site_paths, {site: {(outcome, ...): evaluations}} for every evaluation
    entered and left so far."""

    def __init__(self):
        """Starts with no outcomes or paths counted. paths is {function site:
        {(outcome, ...): calls}} for every path taken all the way through a
        function's decisions so far."""
        self.counts = {}
        self.site_paths = {}
        self.paths = {}
        self._local = threading.local()

    def path(self, site, size):
        """A new call's path through the function at site, which has size
        decisions."""
        return Trail(site, size)

    def decide(self, path, index, value, exits=None):
        """Notes value's outcome as path's index-th decision, counts path
        once that is its last, or once it is exits, the outcome whose arm
        leaves the function, and returns value unchanged."""
        outcome = bool(value)
        path.outcomes[index] = outcome
        if index == len(path.outcomes) - 1 or outcome == exits:
            taken = self.paths.setdefault(path.site, {})
            key = tuple(path.outcomes[: index + 1])
            taken[key] = taken.get(key, 0) + 1
        return value

    def _trails(self, site):
        """The stack of site's evaluations under way in the current thread,
        innermost last, so another thread's never mix with its."""
        stacks = self._local.__dict__.setdefault("stacks", {})
        return stacks.setdefault(site, [])

    def enter(self, site, size):
        """Starts an evaluation of site, which has size leaves, as the trail
        its leaves' records fill in."""
        trail = Trail(site, size)
        self._trails(site).append(trail)
        return trail

    def leave(self, trail, value):
        """Ends trail's evaluation, counting its path, and returns value, the
        site's, unchanged. An evaluation of the same site still entered above
        trail, as one that raised leaves, took trail's later outcomes, so
        trail's path is not counted; the stack is cleared down to trail
        either way."""
        stack = self._trails(trail.site)
        clean = bool(stack) and stack[-1] is trail
        while stack and stack.pop() is not trail:
            pass
        if clean:
            paths = self.site_paths.setdefault(trail.site, {})
            path = tuple(trail.outcomes)
            paths[path] = paths.get(path, 0) + 1
        return value

    def record(self, site, index, value):
        """Counts value's outcome, notes it on site's innermost trail, and
        returns value unchanged, so the condition around it behaves exactly
        as uninstrumented."""
        counts = self.counts.get((site, index))
        if counts is None:
            counts = self.counts[(site, index)] = {"truthy": 0, "falsy": 0}
        counts["truthy" if value else "falsy"] += 1
        stack = self._trails(site)
        if stack:
            stack[-1].outcomes[index] = bool(value)
        return value

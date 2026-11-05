"""Records the outcome of each instrumented operand, and the path each
evaluation of a site takes through its leaves."""

import threading

from .kinds.block import ITEMS


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
        """Starts with no outcomes, paths or reaches counted. reached is
        {name: runs} of each statement reached so far, by its name, eg
        {"k.py:3:4": 2}; one never reached has none."""
        self.counts = {}
        self.site_paths = {}
        self.reached = {}
        self._local = threading.local()

    def reach(self, name):
        """Counts a run of the statement named name; returns None, as the
        statement call rewritten code makes is a statement of its own."""
        self.reached[name] = self.reached.get(name, 0) + 1

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

    def answer(self, site, at, value):
        """Counts one more item given to the block call whose items are
        site's leaf at, on its innermost trail, and records value, the
        generator's answer for it, as leaf at + 1. Returns value unchanged,
        so the builtin decides as before."""
        outcomes = self._trails(site)[-1].outcomes
        outcomes[at] = (outcomes[at] or 0) + 1
        return self.record(site, at + 1, value)

    def leave_items(self, trail, at, value):
        """Notes on trail how many items its block call, whose items are
        leaf at, was given, 0, 1 or 2+, counting the leaf true when there
        were any; then leaves, returning value, the call's, unchanged."""
        count = trail.outcomes[at] or 0
        counts = self.counts.setdefault((trail.site, at), {"truthy": 0, "falsy": 0})
        counts["truthy" if count else "falsy"] += 1
        trail.outcomes[at] = ITEMS[min(count, 2)]
        return self.leave(trail, value)

    def matched(self, site, pattern, earlier, value=True):
        """Notes, on a match statement site's innermost trail, its case's
        pattern, leaf index pattern, as matched, and each of the earlier
        cases' patterns not yet reached as not; then leaves the site when
        value, the case's guard's (True for no guard), holds, as the case
        is taken. Returns value, so the guard decides as before."""
        self._unreached(site, earlier)
        self.record(site, pattern, True)
        if value:
            self.leave(self._trails(site)[-1], value)
        return value

    def unmatched(self, site, patterns):
        """Notes each of patterns, a match statement site's every case's
        pattern, not yet reached as not matched, then leaves the site, as no
        case was taken. Returns False, so the case it guards is never
        taken."""
        self._unreached(site, patterns)
        return self.leave(self._trails(site)[-1], False)

    def _unreached(self, site, patterns):
        """Records each of patterns, leaf indexes, as not matched, unless
        site's innermost trail has already reached it."""
        outcomes = self._trails(site)[-1].outcomes
        for index in patterns:
            if outcomes[index] is None:
                self.record(site, index, False)

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

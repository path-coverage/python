"""Rebuilds each evaluation of a decision from what sys.monitoring saw of it,
in the order it happened: the outcome of each leaf a branch tested, each
case a match reached, each item a block call was given, and each value a
decision gave where no branch tests its last leaf. Events of evaluations of
the same decision in different frames, as a leaf calling the function
holding it makes, can interleave, so each evaluation under way is kept by
its frame."""

from dataclasses import dataclass

from .kinds.block import ITEMS

# How many events the log holds before they are rebuilt.
LIMIT = 100_000


class Shape:
    """What rebuilding needs of one decision: its name; its possible paths,
    as decision_paths.possible gives them; and fixed, {leaf index: outcome}
    of each leaf whose form fixes its outcome and which no branch tests, as
    Python compiles it to no test at all; and silent, True when some other
    leaf no branch tests, as the last of an and whose value is used, so
    only the value the decision gives tells its outcome."""

    def __init__(self, name, possible):
        """The shape of the decision named name, with possible its paths."""
        self.name = name
        self.possible = frozenset(map(tuple, possible))
        self.size = len(possible[0])
        self.fixed = {}
        self.silent = False
        self.following = _following(self.possible)


def _following(possible):
    """{outcomes so far: index of the leaf reached next} for every
    evaluation under way along one of possible's paths, leaves being
    reached in index order. Example: `a and b` gives {(None, None): 0,
    (True, None): 1}."""
    following = {}
    for path in possible:
        so_far = [None] * len(path)
        for index in (index for index, outcome in enumerate(path) if outcome is not None):
            following[tuple(so_far)] = index
            so_far[index] = path[index]
    return following


class Evaluations:
    """The counts the reports carry: counts, {(decision, leaf index):
    {"truthy": n, "falsy": n}} of every leaf reached; decision_paths,
    {decision: {path: n}} of every evaluation completed; and reached,
    {name: runs} of every statement reached, eg {"k.py:3:4": 2}. Events
    are logged as they happen, as (frame id, actions, value's truth), and
    rebuilt into these counts by flush."""

    def __init__(self, limit=LIMIT):
        """Starts with nothing counted; the log is rebuilt once it holds
        limit events."""
        self.counts = {}
        self.decision_paths = {}
        self.reached = {}
        self.log = []
        self.limit = limit
        self._open = {}
        self._blocks = {}

    def note(self, frame, actions, truth):
        """Logs actions, seen in the frame of id frame, truth the value's
        that a value action needs; rebuilds the log once it is full."""
        self.log.append((frame, actions, truth))
        if len(self.log) >= self.limit:
            self.flush()

    def flush(self):
        """Applies every logged action, in the order logged, emptying the
        log."""
        log, self.log = self.log, []
        for frame, actions, truth in log:
            for action in actions:
                action.apply(self, frame, truth)

    def outcome(self, frame, shape, index, outcome):
        """Notes outcome of leaf index of shape's evaluation in frame. A leaf
        already noted starts a new evaluation, the one before it never
        completed, as one that raised."""
        self._set(frame, shape, self._evaluation(frame, shape, index), index, outcome)

    def value(self, frame, shape, outcome):
        """Notes outcome as that of the leaf shape's evaluation in frame is
        waiting for, its last, which no branch tests, so the value the
        decision gave tells it. Nothing when no evaluation is waiting."""
        outcomes = self._open.pop((frame, shape), None)
        if outcomes is not None:
            self._set(frame, shape, outcomes, shape.following[tuple(outcomes)], outcome)

    def matched(self, frame, shape, pattern, earlier):
        """Notes, on a match's evaluation in frame, its case's pattern, leaf
        index pattern, as matched, and each of earlier, the earlier cases'
        patterns, not yet matched, as not."""
        outcomes = self._evaluation(frame, shape, pattern)
        self._unreached(shape, outcomes, earlier)
        self._set(frame, shape, outcomes, pattern, True)

    def opened(self, frame, shape):
        """Starts a match's evaluation in frame, as it starts trying its
        cases, none matched yet."""
        self._open[(frame, shape)] = [None] * shape.size

    def unmatched(self, frame, shape, patterns):
        """Notes each of patterns, a match's every case's pattern, not yet
        matched as not, as no case was taken, completing its evaluation in
        frame. Nothing when none is open, as when a case was taken and its
        body went on past the match."""
        outcomes = self._open.pop((frame, shape), None)
        if outcomes is not None:
            self._unreached(shape, outcomes, patterns)
            self._settle((frame, shape), shape, outcomes)

    def begin(self, frame, shape):
        """Starts an evaluation in frame of shape, a block call, given no
        items yet."""
        self._blocks[(frame, shape)] = [0, None]

    def item(self, frame, shape):
        """Counts one more item given to the block call in frame."""
        self._blocks[(frame, shape)][0] += 1

    def answer(self, frame, shape, outcome):
        """Notes outcome as the block call's answer for its latest item,
        counted as leaf 1's."""
        self._blocks[(frame, shape)][1] = outcome
        self._count(shape, 1, outcome)

    def end(self, frame, shape):
        """Completes the block call's evaluation in frame: its path is how
        many items it was given, 0, 1 or 2+, and its last answer; leaf 0
        counts true when there were any items."""
        items, answer = self._blocks.pop((frame, shape))
        self._count(shape, 0, items > 0)
        self._taken(shape, (ITEMS[min(items, 2)], answer))

    def reach(self, name):
        """Counts a run of the statement named name."""
        self.reached[name] = self.reached.get(name, 0) + 1

    def _evaluation(self, frame, shape, index):
        """The outcomes of shape's evaluation under way in frame, taken out
        of those open; a new evaluation's, its leading fixed leaves
        noted, when there is none, or its leaf index is already noted."""
        outcomes = self._open.pop((frame, shape), None)
        if outcomes is None or outcomes[index] is not None:
            outcomes = [None] * shape.size
            while (first := shape.following[tuple(outcomes)]) in shape.fixed:
                self._fix(shape, outcomes, first)
        return outcomes

    def _set(self, frame, shape, outcomes, index, outcome):
        """Notes outcome of leaf index on outcomes, counting it, then
        settles the evaluation."""
        outcomes[index] = outcome
        self._count(shape, index, outcome)
        self._settle((frame, shape), shape, outcomes)

    def _settle(self, key, shape, outcomes):
        """Counts outcomes' path when it is complete; else notes each fixed
        leaf it reaches next, and keeps it open under key while it waits
        for a leaf; an evaluation no possible path agrees with is
        dropped."""
        while (path := tuple(outcomes)) not in shape.possible:
            following = shape.following.get(path)
            if following not in shape.fixed:
                if following is not None:
                    self._open[key] = outcomes
                return
            self._fix(shape, outcomes, following)
        self._taken(shape, path)

    def _fix(self, shape, outcomes, index):
        """Notes leaf index on outcomes as its fixed outcome, counting it."""
        outcomes[index] = shape.fixed[index]
        self._count(shape, index, outcomes[index])

    def _unreached(self, shape, outcomes, patterns):
        """Notes each of patterns not yet matched on outcomes as not."""
        for index in patterns:
            if outcomes[index] is None:
                outcomes[index] = False
                self._count(shape, index, False)

    def _count(self, shape, index, outcome):
        """Counts outcome of shape's leaf index."""
        counts = self.counts.setdefault((shape.name, index), {"truthy": 0, "falsy": 0})
        counts["truthy" if outcome else "falsy"] += 1

    def _taken(self, shape, path):
        """Counts one more evaluation of shape taking path."""
        paths = self.decision_paths.setdefault(shape.name, {})
        paths[path] = paths.get(path, 0) + 1


@dataclass(frozen=True)
class Outcome:
    """A branch's outcome for leaf index of shape's decision."""

    shape: Shape
    index: int
    outcome: bool

    def apply(self, evaluations, frame, _truth):
        """Notes the leaf's outcome on its evaluation in frame."""
        evaluations.outcome(frame, self.shape, self.index, self.outcome)


@dataclass(frozen=True)
class Value:
    """A value shape's decision gave, its truth the decision's, flipped when
    flip, as a not between them flips it."""

    shape: Shape
    flip: bool

    def apply(self, evaluations, frame, truth):
        """Notes the value's truth as the outcome of the leaf the
        evaluation in frame waits for."""
        evaluations.value(frame, self.shape, truth != self.flip)


@dataclass(frozen=True)
class Matched:
    """A match's case reached, its pattern leaf index pattern, earlier the
    earlier cases' patterns."""

    shape: Shape
    pattern: int
    earlier: tuple

    def apply(self, evaluations, frame, _truth):
        """Notes the pattern matched, on the evaluation in frame."""
        evaluations.matched(frame, self.shape, self.pattern, self.earlier)


@dataclass(frozen=True)
class Opened:
    """A match starting to try its cases."""

    shape: Shape

    def apply(self, evaluations, frame, _truth):
        """Opens the match's evaluation in frame."""
        evaluations.opened(frame, self.shape)


@dataclass(frozen=True)
class Unmatched:
    """A match left with no case taken, patterns its cases' patterns."""

    shape: Shape
    patterns: tuple

    def apply(self, evaluations, frame, _truth):
        """Notes every pattern not yet matched as not, on the evaluation in
        frame."""
        evaluations.unmatched(frame, self.shape, self.patterns)


@dataclass(frozen=True)
class Begin:
    """A block call started, given no items yet."""

    shape: Shape

    def apply(self, evaluations, frame, _truth):
        """Starts the block call's evaluation in frame."""
        evaluations.begin(frame, self.shape)


@dataclass(frozen=True)
class Item:
    """A block call given one more item."""

    shape: Shape

    def apply(self, evaluations, frame, _truth):
        """Counts the item on the evaluation in frame."""
        evaluations.item(frame, self.shape)


@dataclass(frozen=True)
class Answer:
    """A block call's answer for its latest item."""

    shape: Shape
    outcome: bool

    def apply(self, evaluations, frame, _truth):
        """Notes the answer on the evaluation in frame."""
        evaluations.answer(frame, self.shape, self.outcome)


@dataclass(frozen=True)
class End:
    """A block call done."""

    shape: Shape

    def apply(self, evaluations, frame, _truth):
        """Completes the evaluation in frame."""
        evaluations.end(frame, self.shape)


@dataclass(frozen=True)
class Reach:
    """A run of the statement, or the entry of the function, named name."""

    name: str

    def apply(self, evaluations, _frame, _truth):
        """Counts the run."""
        evaluations.reach(self.name)

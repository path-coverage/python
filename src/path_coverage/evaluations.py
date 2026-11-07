"""Rebuilds each evaluation of a decision from what sys.monitoring saw of it,
in the order it happened: the outcome of each leaf a branch tested, or a
call around an and/or's last operand counted, each case a match reached,
and each item a block call was given. Events of evaluations of
the same decision in different frames, as a leaf calling the function
holding it makes, can interleave, so each evaluation under way is kept by
its frame."""

from dataclasses import dataclass

from .kinds.block import ITEMS

# How many events the log holds before they are rebuilt.
LIMIT = 100_000


class Shape:
    """What rebuilding needs of one decision: its name, and its possible
    paths, as decision_paths.possible gives them."""

    def __init__(self, name, possible):
        """The shape of the decision named name, with possible its paths."""
        self.name = name
        self.possible = frozenset(map(tuple, possible))
        self.size = len(possible[0])
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
    {decision: {path: n}} of every evaluation completed; reached,
    {name: runs} of every statement reached, eg {"k.py:3:4": 2}; and
    ways, {function's entry: {way: calls}}, each way the steps one call
    took, in order, a decision's (name, path) or a statement's (name,).
    Events are logged as they happen, as (frame id, actions), and rebuilt
    into these counts by flush."""

    def __init__(self, limit=LIMIT):
        """Starts with nothing counted; the log is rebuilt once it holds
        limit events."""
        self.counts = {}
        self.decision_paths = {}
        self.reached = {}
        self.ways = {}
        self.log = []
        self.limit = limit
        self._open = {}
        self._blocks = {}
        self._walking = {}

    def note(self, frame, actions):
        """Logs actions, seen in the frame of id frame; rebuilds the log
        once it is full."""
        self.log.append((frame, actions))
        if len(self.log) >= self.limit:
            self.flush()

    def flush(self):
        """Applies every logged action, in the order logged, emptying the
        log."""
        log, self.log = self.log, []
        for frame, actions in log:
            for action in actions:
                action.apply(self, frame)

    def outcome(self, frame, shape, index, outcome):
        """Notes outcome of leaf index of shape's evaluation in frame. A leaf
        already noted starts a new evaluation, the one before it never
        completed, as one that raised."""
        self._set(frame, shape, self._evaluation(frame, shape, index), index, outcome)

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
        self._taken(frame, shape, (ITEMS[min(items, 2)], answer))

    def reach(self, name):
        """Counts a run of the statement named name."""
        self.reached[name] = self.reached.get(name, 0) + 1

    def enter(self, frame, name):
        """Starts the way of a call of the function whose entry is named
        name, in frame, counting the entry as reached. A way still under
        way in a frame of that id ends first: CPython gives a new frame
        the id of one that has finished, and a new call always enters
        before anything else happens in it."""
        self._walked(frame)
        self._walking[frame] = (name, [])
        self.reach(name)

    def ran(self, frame, name):
        """Counts a run of the statement named name, a step of the way
        under way in frame."""
        self.reach(name)
        self._step(frame, (name,))

    def close(self):
        """Ends every way still under way, as the run is over, counting
        each in ways."""
        for frame in list(self._walking):
            self._walked(frame)

    def _walked(self, frame):
        """Counts the way under way in frame, when there is one, as taken
        once more."""
        walking = self._walking.pop(frame, None)
        if walking is not None:
            entry, steps = walking
            ways = self.ways.setdefault(entry, {})
            way = tuple(steps)
            ways[way] = ways.get(way, 0) + 1

    def _step(self, frame, step):
        """Adds step to the way under way in frame; nothing in a frame no
        measured function entered, eg a module's top level."""
        walking = self._walking.get(frame)
        if walking is not None:
            walking[1].append(step)

    def _evaluation(self, frame, shape, index):
        """The outcomes of shape's evaluation under way in frame, taken out
        of those open; a new evaluation's, none noted yet, when there is
        none, or its leaf index is already noted."""
        outcomes = self._open.pop((frame, shape), None)
        if outcomes is None or outcomes[index] is not None:
            outcomes = [None] * shape.size
        return outcomes

    def _set(self, frame, shape, outcomes, index, outcome):
        """Notes outcome of leaf index on outcomes, counting it, then
        settles the evaluation."""
        outcomes[index] = outcome
        self._count(shape, index, outcome)
        self._settle((frame, shape), shape, outcomes)

    def _settle(self, key, shape, outcomes):
        """Counts outcomes' path when it is complete; else keeps it open
        under key while it waits for a leaf; an evaluation no possible path
        agrees with is dropped."""
        path = tuple(outcomes)
        if path in shape.possible:
            self._taken(key[0], shape, path)
        elif path in shape.following:
            self._open[key] = outcomes

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

    def _taken(self, frame, shape, path):
        """Counts one more evaluation of shape taking path, a step of the
        way under way in frame."""
        paths = self.decision_paths.setdefault(shape.name, {})
        paths[path] = paths.get(path, 0) + 1
        self._step(frame, (shape.name, path))


@dataclass(frozen=True)
class Outcome:
    """The outcome of leaf index of shape's decision, as a branch, or the
    call around an and/or's last operand, tells it."""

    shape: Shape
    index: int
    outcome: bool

    def apply(self, evaluations, frame):
        """Notes the leaf's outcome on its evaluation in frame."""
        evaluations.outcome(frame, self.shape, self.index, self.outcome)


@dataclass(frozen=True)
class Matched:
    """A match's case reached, its pattern leaf index pattern, earlier the
    earlier cases' patterns."""

    shape: Shape
    pattern: int
    earlier: tuple

    def apply(self, evaluations, frame):
        """Notes the pattern matched, on the evaluation in frame."""
        evaluations.matched(frame, self.shape, self.pattern, self.earlier)


@dataclass(frozen=True)
class Opened:
    """A match starting to try its cases."""

    shape: Shape

    def apply(self, evaluations, frame):
        """Opens the match's evaluation in frame."""
        evaluations.opened(frame, self.shape)


@dataclass(frozen=True)
class Unmatched:
    """A match left with no case taken, patterns its cases' patterns."""

    shape: Shape
    patterns: tuple

    def apply(self, evaluations, frame):
        """Notes every pattern not yet matched as not, on the evaluation in
        frame."""
        evaluations.unmatched(frame, self.shape, self.patterns)


@dataclass(frozen=True)
class Begin:
    """A block call started, given no items yet."""

    shape: Shape

    def apply(self, evaluations, frame):
        """Starts the block call's evaluation in frame."""
        evaluations.begin(frame, self.shape)


@dataclass(frozen=True)
class Item:
    """A block call given one more item."""

    shape: Shape

    def apply(self, evaluations, frame):
        """Counts the item on the evaluation in frame."""
        evaluations.item(frame, self.shape)


@dataclass(frozen=True)
class Answer:
    """A block call's answer for its latest item."""

    shape: Shape
    outcome: bool

    def apply(self, evaluations, frame):
        """Notes the answer on the evaluation in frame."""
        evaluations.answer(frame, self.shape, self.outcome)


@dataclass(frozen=True)
class End:
    """A block call done."""

    shape: Shape

    def apply(self, evaluations, frame):
        """Completes the evaluation in frame."""
        evaluations.end(frame, self.shape)


@dataclass(frozen=True)
class Reach:
    """A run of the statement named name."""

    name: str

    def apply(self, evaluations, frame):
        """Counts the run, a step of the way under way in frame."""
        evaluations.ran(frame, self.name)


@dataclass(frozen=True)
class Enter:
    """The entry of a call of the function whose entry is named name."""

    name: str

    def apply(self, evaluations, frame):
        """Starts the call's way in frame."""
        evaluations.enter(frame, self.name)

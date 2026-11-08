"""The way one call is taking through its function, kept as a stack of
units: the function's own, then each loop under way, innermost last. A
step goes to the unit of the innermost loop holding its row, as loops
gives them, first closing any loop under way that does not hold it. Each
pass of a loop is a way of its own, counted on the loop as the pass ends;
the unit holding the loop takes it as one step, how many passes it made,
0, 1 or 2+. So a call's way, and each pass's, holds each row at most
once, however many passes a loop makes."""

from dataclasses import dataclass, field

from .kinds.block import ITEMS


@dataclass
class _Unit:
    """A function's call, or a loop under way, named by its entry or its
    for, with the steps of its way so far, or of its latest pass, how
    many passes it has made, and the distinct ways of those ended."""

    name: str
    steps: list = field(default_factory=list)
    passes: int = 0
    seen: set = field(default_factory=set)


class Walk:
    """The way under way of one call of the function whose entry is
    named entry, counting each way it ends on ways, {unit's name: {way:
    count}}, loops being {row's name: the names of the loops holding it,
    outermost first}."""

    def __init__(self, entry, ways, loops):
        """A call just entered, no step taken yet."""
        self.ways = ways
        self.loops = loops
        self.units = [_Unit(entry)]

    def step(self, step):
        """Adds step, a row's (name, ...), to the way of the innermost
        loop under way holding its row, or the call's own."""
        self._close_to(self.loops[step[0]])
        self.units[-1].steps.append(step)

    def passed(self, loop):
        """Starts a pass of the loop named loop, counting its pass before
        when there is one."""
        unit = self._opened(loop)
        if unit.passes:
            self._count(unit)
            unit.steps = []
        unit.passes += 1

    def exhausted(self, loop):
        """Ends the loop named loop, its items all given, with no pass at
        all when none is under way."""
        self._opened(loop)
        self._close()

    def _opened(self, loop):
        """The unit of the loop named loop, innermost, any loop under way
        inside it closed; a new one, no pass made, when it is not under
        way."""
        self._close_to((*self.loops[loop], loop))
        if self.units[-1].name != loop:
            self.units.append(_Unit(loop))
        return self.units[-1]

    def finish(self):
        """Ends the call, closing every loop under way, and counts its way."""
        self._close_to(())
        self._count(self.units[0])

    def _close_to(self, holding):
        """Closes each loop under way, innermost first, but those leading
        holding, the loops holding a row, outermost first."""
        open_loops = [unit.name for unit in self.units[1:]]
        kept = 0
        while kept < min(len(open_loops), len(holding)) and open_loops[kept] == holding[kept]:
            kept += 1
        while len(self.units) - 1 > kept:
            self._close()

    def _close(self):
        """Ends the innermost loop under way: counts its last pass, if it
        made one, and adds it to the way holding it as one step: how many
        passes it made, and the set of ways they took, so the way holding
        it witnesses each."""
        unit = self.units.pop()
        if unit.passes:
            self._count(unit)
        self.units[-1].steps.append((unit.name, (ITEMS[min(unit.passes, 2)],), frozenset(unit.seen)))

    def _count(self, unit):
        """Counts unit's steps as one more taking of its way, noting it
        among the ways seen."""
        ways = self.ways.setdefault(unit.name, {})
        way = tuple(unit.steps)
        ways[way] = ways.get(way, 0) + 1
        unit.seen.add(way)

"""Measures covered code with sys.monitoring, changing none of it: while
measuring, each module's code is offered, as it starts, to be adopted; an
adopted module's code objects, nested ones included, are mapped once by
code_map and have their own events turned on. Each event's callback looks
up what it means and logs it, by the id of the frame it happened in, on
the Evaluations of the run that adopted it, which rebuilds them later; an
event that means nothing is disabled where it happened, so it is never
seen there again. The package is never itself measured, as it would
measure itself."""

import sys

from . import code_map

MONITORING = sys.monitoring
EVENTS = MONITORING.events
DISABLE = MONITORING.DISABLE

# The events of each adopted code object.
LOCAL = (
    EVENTS.BRANCH_LEFT
    | EVENTS.BRANCH_RIGHT
    | EVENTS.INSTRUCTION
    | EVENTS.PY_RETURN
    | EVENTS.PY_YIELD
    | EVENTS.PY_START
    | EVENTS.LINE
)

# The tool ids tried, in order, those Python names for a debugger, a
# profiler or coverage last.
TOOLS = (3, 4, 5, 2, 0, 1)

# What each event means, by (id(code), offset): branches left, (Evaluations,
# actions); branches right, (Evaluations, offset gone to, actions);
# instructions, (Evaluations, actions, name read or None); values
# returned or yielded, (Evaluations, actions). Entries by id(code):
# (Evaluations, name).
_left = {}
_right = {}
_marks = {}
_values = {}
_entries = {}

# Every code object mapped, kept alive so its id names no other.
_codes = []


def _ignore(_code):
    """Adopts nothing: what a module's start is offered while not
    measuring."""


_adopt = _ignore


def start(adopt):
    """Offers each module's code, as it starts from now on, to adopt, which
    adopts it by calling measure, or ignores it."""
    global _adopt
    _adopt = adopt
    MONITORING.set_events(_tool, EVENTS.PY_START)


def stop():
    """Offers no more modules' code; code already adopted is still
    measured."""
    global _adopt
    _adopt = _ignore
    MONITORING.set_events(_tool, 0)


def measure(code, source, evaluations):
    """Measures code, a module's code, and every code object nested in it,
    source its Source, logging what each event means on evaluations."""
    for each, table in code_map.tables(code, source).items():
        key = id(each)
        _codes.append(each)
        _left.update({(key, offset): (evaluations, actions) for offset, actions in table.left.items()})
        _right.update({(key, offset): (evaluations, *found) for offset, found in table.right.items()})
        _left.update({(key, alias): _left[(key, offset)] for alias, offset in table.left_aliases.items()})
        _right.update({(key, alias): _right[(key, offset)] for alias, offset in table.right_aliases.items()})
        _marks.update({(key, offset): (evaluations, *found) for offset, found in table.marks.items()})
        _values.update({(key, offset): (evaluations, actions) for offset, actions in table.values.items()})
        if table.entry is not None:
            _entries[key] = (evaluations, table.entry)
        MONITORING.set_local_events(_tool, each, LOCAL)


def measured():
    """The files any code was measured in so far, as Python named them
    when it compiled their code."""
    return {code.co_filename for code in _codes}


def _claim():
    """The first free tool id of TOOLS, taken, with this module's
    callbacks registered for it."""
    tool = next(each for each in TOOLS if MONITORING.get_tool(each) is None)
    MONITORING.use_tool_id(tool, "path_coverage")
    for event, callback in (
        (EVENTS.BRANCH_LEFT, _branched_left),
        (EVENTS.BRANCH_RIGHT, _branched_right),
        (EVENTS.INSTRUCTION, _instruction),
        (EVENTS.PY_RETURN, _valued),
        (EVENTS.PY_YIELD, _valued),
        (EVENTS.PY_START, _started),
        (EVENTS.LINE, _line_started),
    ):
        MONITORING.register_callback(tool, event, callback)
    return tool


def _branched_left(code, offset, _destination):
    """Logs what a left branch at offset in code means."""
    found = _left.get((id(code), offset))
    if found is None:
        return DISABLE
    evaluations, actions = found
    evaluations.note(id(sys._getframe(1)), actions, None)


def _branched_right(code, offset, destination):
    """Logs what a right branch at offset in code means, when it goes where
    its jump goes: Python 3.14 also reports one from a loop's end that
    names the last jump taken, which it never took."""
    found = _right.get((id(code), offset))
    if found is None:
        return DISABLE
    evaluations, goes_to, actions = found
    if destination == goes_to:
        evaluations.note(id(sys._getframe(1)), actions, None)


def _instruction(code, offset):
    """Logs what reaching the instruction at offset in code means, with the
    truth of the value just written to the name it reads, if any."""
    found = _marks.get((id(code), offset))
    if found is None:
        return DISABLE
    evaluations, actions, name = found
    frame = sys._getframe(1)
    evaluations.note(id(frame), actions, None if name is None else _written(frame, name))


def _line_started(code, _line):
    """Keeps the line event where an instruction is marked, at the offset
    the frame is at; disables it anywhere else."""
    return _kept(code, sys._getframe(1).f_lasti)


def _kept(code, offset):
    """None, keeping the line event, at offset in code when an instruction
    there is marked: Python 3.14 drops an instruction event at the start of
    a line once another tool, eg coverage.py, disables its own line event
    there, unless a line event is still wanted. DISABLE anywhere else."""
    return None if (id(code), offset) in _marks else DISABLE


def _written(frame, name):
    """The truth of the value of name in frame: a local's, else, as for a
    name declared global, a global's."""
    local = frame.f_locals
    return bool(local[name] if name in local else frame.f_globals[name])


def _valued(code, offset, value):
    """Logs what returning or yielding value at offset in code means, with
    value's truth."""
    found = _values.get((id(code), offset))
    if found is None:
        return DISABLE
    evaluations, actions = found
    evaluations.note(id(sys._getframe(1)), actions, bool(value))


def _started(code, _offset):
    """Counts the entry of an adopted function; offers a module's code, as
    it starts, to be adopted."""
    found = _entries.get(id(code))
    if found is not None:
        evaluations, name = found
        evaluations.reach(name)
        return None
    if code.co_name == "<module>":
        _adopt(code)
    return DISABLE


# This package's tool id, claimed once, as it is first imported.
_tool = _claim()

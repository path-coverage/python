"""Measures covered code with sys.monitoring and one call around each
and/or's last operand: instrument wraps those operands, as last_operands
does, compiles the module, then has code_map map its code objects, nested
ones included, once, and turns on their own events. Each event's callback
looks up what it means and logs it, by the id of the frame it happened in,
on the Evaluations of the run that measures it, which rebuilds them later;
an event that means nothing is disabled where it happened, so it is never
seen there again. The package is never itself measured, as it would
measure itself."""

import ast
import sys

from . import code_map, last_operands

MONITORING = sys.monitoring
EVENTS = MONITORING.events
DISABLE = MONITORING.DISABLE

# The events of each measured code object.
LOCAL = EVENTS.BRANCH_LEFT | EVENTS.BRANCH_RIGHT | EVENTS.INSTRUCTION | EVENTS.PY_START | EVENTS.LINE

# The tool ids tried, in order, those Python names for a debugger, a
# profiler or coverage last.
TOOLS = (3, 4, 5, 2, 0, 1)

# What each event means, by (id(code), offset): branches left, (Evaluations,
# actions); branches right, (Evaluations, offset gone to, actions);
# instructions, (Evaluations, actions). Entries by id(code): (Evaluations,
# name).
_left = {}
_right = {}
_marks = {}
_entries = {}

# Every code object mapped, kept alive so its id names no other.
_codes = []


def compiled(tree, path):
    """tree compiled as the module of the file path."""
    return compile(tree, path, "exec", dont_inherit=True)


def instrument(text, name, path, evaluations, compiler):
    """(code, record) of text, the source of the file path, named name as
    decisions name it: its parse, each and/or's last operand wrapped in a
    call of record, compiled by compiler, eg compiled, then measured,
    logging on evaluations. The module must bind record as
    last_operands.NAME."""
    source = code_map.Source(text, name)
    lasts = last_operands.Lasts(evaluations)
    code = compiler(last_operands.rewrite(ast.parse(text), source, lasts), path)
    measure(code, source, evaluations)
    return code, lasts.record


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
        _marks.update({(key, offset): (evaluations, actions) for offset, actions in table.marks.items()})
        if table.entry is not None:
            _entries[key] = (evaluations, table.entry)
        MONITORING.set_local_events(_tool, each, LOCAL)


def _claim():
    """The first free tool id of TOOLS, taken, with this module's
    callbacks registered for it."""
    tool = next(each for each in TOOLS if MONITORING.get_tool(each) is None)
    MONITORING.use_tool_id(tool, "path_coverage")
    for event, callback in (
        (EVENTS.BRANCH_LEFT, _branched_left),
        (EVENTS.BRANCH_RIGHT, _branched_right),
        (EVENTS.INSTRUCTION, _instruction),
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
    evaluations.note(id(sys._getframe(1)), actions)


def _branched_right(code, offset, destination):
    """Logs what a right branch at offset in code means, when it goes where
    its jump goes: Python 3.14 also reports one from a loop's end that
    names the last jump taken, which it never took."""
    found = _right.get((id(code), offset))
    if found is None:
        return DISABLE
    evaluations, goes_to, actions = found
    if destination == goes_to:
        evaluations.note(id(sys._getframe(1)), actions)


def _instruction(code, offset):
    """Logs what reaching the instruction at offset in code means."""
    found = _marks.get((id(code), offset))
    if found is None:
        return DISABLE
    evaluations, actions = found
    evaluations.note(id(sys._getframe(1)), actions)


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


def _started(code, _offset):
    """Counts the entry of a measured function; disables the start of any
    other code."""
    found = _entries.get(id(code))
    if found is None:
        return DISABLE
    evaluations, name = found
    evaluations.reach(name)


# This package's tool id, claimed once, as it is first imported.
_tool = _claim()

"""Inserts records into a covered module's parse, each a call of NAME,
which logs actions on Evaluations and gives back what it is given, so the
program runs as written:

    def fee(user, order):
        if user.member and order.paid:
            return 5
    # compiles, in rewrite mode, as
    def fee(user, order):
        __path_coverage__(4)
        if __path_coverage__(2, __path_coverage__(0, user.member) and __path_coverage__(1, order.paid)):
            __path_coverage__(3)
            return 5

Only two forms are inserted: a call wrapping an existing expression, which
gives back its value, or its truth where only its truth is tested; and a
record statement of its own before or after a statement, after any
docstring. Nothing else in the tree changes, and each inserted node takes
the location of the node it wraps or is placed by.

Which records each mode inserts is decided here, in INSERTS, and nowhere
else: monitoring mode inserts only those for the leaves no branch tells,
as its other events come from sys.monitoring; rewrite mode inserts every
record its events come from."""

import ast
import sys
from dataclasses import dataclass

from . import manifest, scopes
from .evaluations import Answer, Begin, End, Enter, Exhausted, Item, Matched, Opened, Outcome, Pass, Reach, Shape, Unmatched
from .source_map import Source, first_line, span

# The name the inserted calls call, bound in each measured module.
NAME = "__path_coverage__"

# The kinds of record inserted, besides a call around each leaf no branch
# tells, eg the b of x = a or b, which every mode inserts, as nothing else
# tells its outcome: a call around every other leaf too; a record statement
# first in each function's body; one before each counted return and raise;
# a call around each loop's iterable; a match's records, opening it,
# matching each case and leaving it with none taken; and a block call's, eg
# any(...)'s, beginning it, giving each item and answer, and ending it.
LEAVES = "leaves"
ENTRIES = "entries"
REACHES = "reaches"
LOOPS = "loops"
MATCHES = "matches"
BLOCKS = "blocks"

# The kinds of record each mode inserts.
INSERTS = {
    "monitoring": frozenset(),
    "rewrite": frozenset({LEAVES, ENTRIES, REACHES, LOOPS, MATCHES, BLOCKS}),
}

# The nodes whose body a call's entry is recorded first in.
_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _key(frame):
    """The key frame's events are logged by: its id and its code's."""
    return (id(frame), id(frame.f_code))


@dataclass(frozen=True)
class Leaf:
    """A leaf's record: the actions its outcome logs, falsy or truthy, and
    whether only its truth is tested, so its call gives that back."""

    falsy: tuple
    truthy: tuple
    tested: bool

    def logged(self, evaluations, frame, value):
        """value's truth, when only that is tested, else value, having
        logged the actions of that truth in frame. The truth is found once,
        so a value is tested no more often than plain Python tests it where
        only its truth is tested."""
        truth = bool(value)
        evaluations.note(_key(frame), self.truthy if truth else self.falsy)
        return truth if self.tested else value


@dataclass(frozen=True)
class Mark:
    """A record statement's record, or a call's that only says the code it
    wraps ran: the actions it logs."""

    actions: tuple

    def logged(self, evaluations, frame, value):
        """value, unchanged, having logged the actions in frame."""
        evaluations.note(_key(frame), self.actions)
        return value


@dataclass(frozen=True)
class Items:
    """A loop's iterable's record: the actions a pass logs, and those its
    end, all its items given, logs."""

    passed: tuple
    exhausted: tuple

    def logged(self, evaluations, frame, value):
        """An iterator over value's items, logging in frame, where the loop
        runs."""
        return _Passes(self, evaluations, _key(frame), iter(value))


@dataclass(frozen=True)
class BlockItems:
    """The record of the iterable of a block call's generator expression,
    eg any(...)'s: it begins the block call, then gives each item."""

    shape: Shape

    def logged(self, evaluations, frame, value):
        """An iterator over value's items, logging each one given, having
        begun the block call, in frame, the caller's, where the iterable is
        made."""
        evaluations.note(_key(frame), (Begin(self.shape),))
        return _Passes(Items((Item(self.shape),), ()), evaluations, _key(frame), iter(value))


@dataclass(frozen=True)
class BlockAnswer:
    """The record of the element of a block call's generator expression:
    its answer for the latest item."""

    shape: Shape

    def logged(self, evaluations, frame, value):
        """value's truth, all the block call tests, having logged it as the
        answer in the frame that resumed frame, the generator's, which is
        the block call's caller, where its other actions are logged."""
        truth = bool(value)
        evaluations.note(_key(frame.f_back), (Answer(self.shape, truth),))
        return truth


class _Passes:
    """The items of an iterable, given one at a time, each, and the end,
    logged."""

    def __init__(self, items, evaluations, key, iterator):
        """Gives iterator's items, logging items' actions on evaluations by
        key."""
        self.items = items
        self.evaluations = evaluations
        self.key = key
        self.iterator = iterator

    def __iter__(self):
        """Itself, as a loop asks for an iterator."""
        return self

    def __next__(self):
        """The next item, logged as given; when there is none, the end
        logged and StopIteration raised, as the loop expects."""
        try:
            item = next(self.iterator)
        except StopIteration:
            self.evaluations.note(self.key, self.items.exhausted)
            raise
        self.evaluations.note(self.key, self.items.passed)
        return item


class Recorder:
    """The records the inserted calls make, by each call's key, logging on
    evaluations."""

    def __init__(self, evaluations):
        """No record yet, logging on evaluations."""
        self.evaluations = evaluations
        self.records = []

    def key(self, record):
        """The key of a new call making record."""
        self.records.append(record)
        return len(self.records) - 1

    def record(self, key, value=None):
        """What the call keyed key gives back for value, its record logged
        from the frame that made the call."""
        return self.records[key].logged(self.evaluations, sys._getframe(1), value)


class _Inserter(ast.NodeTransformer):
    """Inserts the records of the kinds given into a parse of a file."""

    def __init__(self, tree, source, recorder, inserts):
        """Inserts into tree, a parse of source, a source_map.Source, the
        records of the kinds in inserts, keying each call on recorder."""
        self.source = source
        self.recorder = recorder
        self.inserts = inserts
        self.parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        kept = source.kept
        self.reaches = {span(node): name for node, name in source.statements if scopes.line(name) in kept} if REACHES in inserts else {}
        defs = [node for node in ast.walk(tree) if isinstance(node, _DEFS)]
        self.entries = (
            {span(node): source.entries[(node.name, first_line(node))] for node in defs if first_line(node) in kept}
            if ENTRIES in inserts
            else {}
        )
        self.loops = source.fors if LOOPS in inserts else {}
        self.whiles = source.whiles if LOOPS in inserts else {}
        self.matches = {span(node): (shape, cases) for node, shape, cases in source.matches} if MATCHES in inserts else {}
        self.blocks = source.blocks if BLOCKS in inserts else {}

    def generic_visit(self, node):
        """node, what is inside its children inserted first, then each
        child that takes a call wrapped, and each record statement put by
        the statement it goes with."""
        super().generic_visit(node)
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                setattr(node, field, self._listed(value, node, field))
            else:
                setattr(node, field, self._wrapped(value, node))
        return node

    def _listed(self, items, parent, field):
        """items, the list parent holds as field, each wrapped as a child
        is; a reach's record statement before each statement counted; a
        match's, saying no case was taken, after it; and first in a body,
        a function's entry's, after its docstring, or a case's, saying its
        pattern matched, when it has no guard."""
        found = []
        for item in items:
            if isinstance(item, ast.stmt) and span(item) in self.reaches:
                found.append(self._mark(item, Reach(self.reaches[span(item)])))
            found.append(self._wrapped(item, parent))
            if isinstance(item, ast.Match) and span(item) in self.matches and not manifest.matches_anything(item.cases[-1]):
                shape, cases = self.matches[span(item)]
                found.append(self._mark(item, Unmatched(shape, tuple(pattern for pattern, _ in cases))))
        if field == "body" and isinstance(parent, _DEFS) and span(parent) in self.entries:
            found.insert(_docstring(found), self._mark(parent, Enter(self.entries[span(parent)])))
        if field == "body" and isinstance(parent, ast.match_case) and parent.guard is None:
            found[:0] = [self._mark(found[0], action) for action in self._matched(parent)]
        return found

    def _matched(self, case):
        """(the Matched action of case,) when its match's records are
        inserted; else ()."""
        match = self.parents[case]
        if span(match) not in self.matches:
            return ()
        shape, cases = self.matches[span(match)]
        patterns = tuple(pattern for pattern, _ in cases)
        pattern = cases[match.cases.index(case)][0]
        return (Matched(shape, pattern, patterns[: patterns.index(pattern)]),)

    def _mark(self, statement, action):
        """A record statement logging action, placed where statement is."""
        call = self._call(Mark((action,)), [], statement)
        return ast.copy_location(ast.Expr(value=call), statement)

    def _wrapped(self, child, parent):
        """child, held by parent, in each call that makes a record of it,
        innermost first: a leaf's; a for's iterable's; a while's test's,
        each true run a pass, a false one the loop's end; a block call's,
        its element's or its first iterable's; or a match's subject's; else
        child unchanged."""
        if not isinstance(child, ast.expr):
            return child
        at = span(child)
        wrapped = child
        if at in self.source.leaves and self._counted(child, parent):
            before = self._matched(parent) if isinstance(parent, ast.match_case) else ()
            truths = [(*before, *(Outcome(shape, index, truth) for shape, index in self.source.leaves[at])) for truth in (False, True)]
            wrapped = self._call(Leaf(*truths, self._tested(child)), [wrapped], child)
        if at in self.loops:
            name = self.loops[at]
            wrapped = self._call(Items((Pass(name),), (Exhausted(name),)), [wrapped], child)
        if at in self.whiles:
            name = self.whiles[at]
            wrapped = self._call(Leaf((Exhausted(name),), (Pass(name),), True), [wrapped], child)
        record = self._block_record(child, parent) or self._subject_record(child, parent)
        if record is not None:
            wrapped = self._call(record, [wrapped], child)
        return wrapped

    def _block_record(self, child, parent):
        """The record of child, held by parent, as part of a block call:
        the call's, ending it; its generator expression's element's, giving
        an answer; or its first iterable's, beginning it and giving each
        item. None for any other child."""
        if isinstance(child, ast.Call) and span(child.func) in self.blocks:
            return Mark((End(self.blocks[span(child.func)]),))
        expression = parent if isinstance(parent, ast.GeneratorExp) else self.parents.get(parent)
        call = self.parents.get(expression)
        if not (isinstance(expression, ast.GeneratorExp) and isinstance(call, ast.Call) and span(call.func) in self.blocks):
            return None
        shape = self.blocks[span(call.func)]
        if child is expression.elt:
            return BlockAnswer(shape)
        if parent is expression.generators[0] and child is parent.iter:
            return BlockItems(shape)
        return None

    def _subject_record(self, child, parent):
        """The record of child, held by parent, when it is the subject of a
        match whose records are inserted, opening it, the subject being the
        only expression a match holds; else None."""
        if isinstance(parent, ast.Match) and span(parent) in self.matches:
            return Mark((Opened(self.matches[span(parent)][0]),))
        return None

    def _counted(self, leaf, parent):
        """True when leaf, held by parent, is one whose outcome a call
        around it counts in these inserts: every leaf, or only those no
        branch tells."""
        return LEAVES in self.inserts or manifest.wrapped(leaf, parent)

    def _tested(self, node):
        """True when only node's truth is tested, as the test of an if, a
        while, an assert, a conditional expression, a not, a filter or a
        guard, through any and/or or conditional expression's arm holding
        it, whose value it may be; False when its value may be used."""
        while True:
            parent = self.parents.get(node)
            match parent:
                case ast.BoolOp():
                    node = parent
                case ast.IfExp():
                    if node is parent.test:
                        return True
                    node = parent
                case ast.UnaryOp(op=ast.Not()):
                    return True
                case ast.If() | ast.While() | ast.Assert():
                    return node is parent.test
                case ast.comprehension():
                    return node in parent.ifs
                case ast.match_case():
                    return node is parent.guard
                case _:
                    return False

    def _call(self, record, arguments, at):
        """A call of NAME, keyed for record, given arguments, placed where
        the node at is."""
        key = ast.Constant(self.recorder.key(record))
        call = ast.Call(func=ast.Name(id=NAME, ctx=ast.Load()), args=[key, *arguments], keywords=[])
        for part in (call, call.func, key):
            ast.copy_location(part, at)
        return call


def _docstring(body):
    """1 when body starts with a docstring, so an inserted statement goes
    after it; else 0."""
    first = body[0]
    return int(isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str))


def instrumented(text, name, path, evaluations, compiler, kept, mode):
    """(code, record, source) of text, the source of the file path, named
    name as decisions name it, kept the line numbers measured: its
    source_map.Source; its parse with the records mode inserts, logging on
    evaluations, compiled by compiler; and the function the inserted calls
    call, which the module must bind as NAME."""
    source = Source(text, name, kept)
    recorder = Recorder(evaluations)
    code = compiler(rewrite(ast.parse(text), source, recorder, mode), path)
    return code, recorder.record, source


def rewrite(tree, source, recorder, mode):
    """tree, the parse of source, a source_map.Source, changed in place and
    returned, with the records mode inserts, as INSERTS lists them, each
    call keyed on recorder."""
    return _Inserter(tree, source, recorder, INSERTS[mode]).visit(tree)

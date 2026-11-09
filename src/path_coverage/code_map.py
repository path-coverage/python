"""Maps each code object Python compiled from a covered file to what each
event sys.monitoring reports in it means for the file's decisions, worked
out once per code object, before it runs, from where Python says each of
its instructions came from (its positions, as ast counts them) and the
file's source_map.Source:

- a branch, left or right, gives the outcome of the leaf whose value its
  jump tests, and of each leaf holding it whose outcome that decides, eg
  an if's predicate holding an and; but no outcome of a leaf
  manifest.wrapped names, which inserted_records counts, one source per
  leaf;
- an instruction marks where a match starts trying its cases, where each
  case is reached, where a match is left with no case taken, and where a
  return or raise statement starts, in every copy Python makes of it;
- a function's start is its entry.

A block call, eg any(o.late for o in orders), Python 3.14 runs in its
caller: a check that any is the builtin begins it, its loop gives each item
and its end, and its test of each answer ends it when the answer decides."""

import ast
import dis
from dataclasses import dataclass, field

from . import manifest
from .evaluations import Answer, Begin, End, Exhausted, Item, Matched, Opened, Outcome, Pass, Reach, Unmatched
from .source_map import span

# The jumps that test a value, and those of them that test it is None.
JUMPS = ("POP_JUMP_IF_TRUE", "POP_JUMP_IF_FALSE", "POP_JUMP_IF_NONE", "POP_JUMP_IF_NOT_NONE")
NONE_JUMPS = JUMPS[2:]

# The instructions between a value and the jump testing it, which only copy
# or convert it.
PLUMBING = ("TO_BOOL", "COPY", "NOT_TAKEN", "NOP", "EXTENDED_ARG")

# The instructions that end a block, so the next starts one.
ENDS = ("RETURN_VALUE", "RAISE_VARARGS", "RERAISE", "JUMP_FORWARD", "JUMP_BACKWARD", "JUMP_BACKWARD_NO_INTERRUPT")

# The instructions Python fuses from two, the second a read of a local, which
# it places where the first came from.
FUSED = ("STORE_FAST_LOAD_FAST", "LOAD_FAST_LOAD_FAST", "LOAD_FAST_BORROW_LOAD_FAST_BORROW")

# What a jump's producer is when no node is where it says it came from: no
# leaf, with no parent.
NOWHERE = ast.Constant(None, lineno=0, col_offset=0, end_lineno=0, end_col_offset=0)


@dataclass
class Table:
    """What each event in one code object means, by where it happens: left,
    {branch offset: actions}; right, {branch offset: (the offset it goes
    to, actions)}; marks, {instruction offset: actions}; and entry, the name
    its function's start is counted by, None for a code object that is no
    function's. While its instructions are monitored too, Python 3.14
    reports a left branch from the NOT_TAKEN after its jump, and a loop's
    end from the POP_ITER after its END_FOR: left_aliases and right_aliases
    are {that offset: the branch's}."""

    left: dict = field(default_factory=dict)
    right: dict = field(default_factory=dict)
    left_aliases: dict = field(default_factory=dict)
    right_aliases: dict = field(default_factory=dict)
    marks: dict = field(default_factory=dict)
    entry: str | None = None


class _Reader:
    """What a jump's tested value means, for a file's source_map.Source:
    which node left it, and which leaves' outcomes its truth tells."""

    def __init__(self, source):
        """Reads jumps against source, with each name's reads, in the order
        written, for finding the read a fused instruction makes."""
        self.source = source
        self.reads = {}
        for node in sorted((node for node in ast.walk(source.tree) if isinstance(node, ast.Name)), key=span):
            self.reads.setdefault(node.id, []).append(node)

    def producer(self, ins, after):
        """The node whose value instruction ins leaves for a jump to test,
        after the instruction following it: the node where ins came from;
        for an instruction that fuses a read into another, placed where the
        other came from, the read name's first node in what reads first
        after that, as _read_first gives it; NOWHERE when none is found."""
        if ins.opname in FUSED:
            regions = self._read_first(self.source.spans.get(_at(ins)), after)
            name = ins.argval[1]
            return next((node for region in regions for node in self.reads.get(name, ()) if _within(span(node), region)), NOWHERE)
        return self.source.spans.get(_at(ins), NOWHERE)

    def _read_first(self, first, after):
        """Where the read fused with node first is, in order to search: when
        first is a comprehension's target, what that comprehension
        evaluates after writing it, its filters, its later loops, then its
        element; else where after came from, which reads it."""
        generator = self.source.parents.get(first)
        if not isinstance(generator, ast.comprehension):
            return [_at(after)]
        comprehension = self.source.parents[generator]
        later = comprehension.generators[comprehension.generators.index(generator) + 1 :]
        elements = [getattr(comprehension, part) for part in ("elt", "key", "value") if hasattr(comprehension, part)]
        parts = [*generator.ifs, *(part for each in later for part in (each.iter, *each.ifs)), *elements]
        return [span(part) for part in parts]

    def outcomes(self, node, opname, jumped, final, copied):
        """The Outcome actions of a jump named opname testing node's value,
        when it jumped or not: of node and each node holding it whose
        outcome that decides. A jump on None tests node is None. final is
        False for a chained comparison's jump before its last, which
        decides only when false, and then only when the comparison is
        compiled as a jump: copied, a copy of its value kept for a later
        test, says the comparison is a value that later test decides on."""
        parents = self.source.parents
        if opname in NONE_JUMPS:
            node = parents.get(node)
            if not isinstance(node, ast.Compare):
                return ()
            truth = (jumped == (opname == "POP_JUMP_IF_NONE")) == isinstance(node.ops[0], ast.Is)
        else:
            truth = jumped == (opname == "POP_JUMP_IF_TRUE")
        if not final and (truth or copied):
            return ()
        return tuple(self._up(node, truth))

    def _up(self, node, truth):
        """Outcome actions of node, given truth its outcome, as a leaf of
        any decision, unless inserted_records counts it, then of each node
        holding it whose outcome truth decides."""
        parents = self.source.parents
        while True:
            if not manifest.wrapped(node, parents.get(node)):
                for shape, index in self.source.leaves.get(span(node), ()):
                    yield Outcome(shape, index, truth)
            truth = _held(parents.get(node), node, truth)
            if truth is None:
                return
            node = parents[node]


def _held(parent, node, truth):
    """The outcome of parent, holding node whose outcome is truth, when
    truth decides it, as for a not, a walrus, a conditional expression's
    arm, or an and's operand that is false or its last; else None."""
    match parent:
        case ast.UnaryOp(op=ast.Not()):
            return not truth
        case ast.NamedExpr():
            return truth
        case ast.IfExp():
            return None if node is parent.test else truth
        case ast.BoolOp():
            return truth if node is parent.values[-1] or truth == isinstance(parent.op, ast.Or) else None
        case _:
            return None


def tables(code, source):
    """{code object: Table} for code, a covered file's module code, and
    each code object nested in it, source its source_map.Source."""
    codes = _tree(code)
    reader = _Reader(source)
    listed = {each: list(dis.get_instructions(each)) for each in codes}
    found = {each: Table(entry=source.entries.get((each.co_name, each.co_firstlineno))) for each in codes}
    for each in codes:
        _branches(found[each], listed[each], reader)
    for each in codes:
        scope = source.scopes.get((each.co_name, each.co_firstlineno), source.tree)
        handlers = {entry.target for entry in dis.Bytecode(each).exception_entries}
        found[each].marks = _marks(listed[each], handlers, source, scope)
    return found


def _tree(code):
    """code and every code object nested in it, at any depth."""
    nested = [const for const in code.co_consts if isinstance(const, type(code))]
    return [code, *(each for inner in nested for each in _tree(inner))]


def _branches(table, instructions, reader):
    """Adds to table the actions of each branch in instructions: each block
    call's, then each jump's that tests a value whose outcome tells a
    leaf's, as reader reads it."""
    source = reader.source
    handled = set()
    blocks = {}
    index = {ins.offset: at for at, ins in enumerate(instructions)}
    for ins in instructions:
        if _at(ins) in source.blocks and ins.opname in (*JUMPS, "FOR_ITER"):
            blocks.setdefault(_at(ins), []).append(ins)
    for at, found in blocks.items():
        shape = source.blocks[at]
        for begin, loop, test in zip(*[iter(found)] * 3):
            handled |= {begin.offset, test.offset}
            stops_on = test.opname == "POP_JUMP_IF_TRUE"
            table.left[begin.offset], table.right[begin.offset] = (Begin(shape),), (begin.argval, ())
            _loop(table, instructions, index, loop, (Item(shape),), (End(shape),))
            table.left[test.offset] = (Answer(shape, not stops_on),)
            table.right[test.offset] = (test.argval, (Answer(shape, stops_on), End(shape)))
    for ins in instructions:
        if ins.opname == "FOR_ITER" and _at(ins) in source.fors:
            name = source.fors[_at(ins)]
            _loop(table, instructions, index, ins, (Pass(name),), (Exhausted(name),))
    producers = {}
    copies = {}
    for at, ins in enumerate(instructions):
        if ins.opname in JUMPS and ins.offset not in handled:
            back = at - 1
            while instructions[back].opname in PLUMBING:
                back -= 1
            producers[at] = reader.producer(instructions[back], instructions[back + 1])
            copies[at] = "COPY" in [each.opname for each in instructions[back + 1 : at]]
    finals = {node: at for at, node in producers.items()}
    for at, node in producers.items():
        ins = instructions[at]
        left = reader.outcomes(node, ins.opname, False, finals[node] == at, copies[at])
        right = reader.outcomes(node, ins.opname, True, finals[node] == at, copies[at])
        if left or right:
            table.left[ins.offset], table.right[ins.offset] = left, (ins.argval, right)
    for at, ins in enumerate(instructions):
        if ins.opname == "NOT_TAKEN" and instructions[at - 1].offset in table.left:
            table.left_aliases[ins.offset] = instructions[at - 1].offset


def _loop(table, instructions, index, loop, given, done):
    """Adds to table the actions of loop, a FOR_ITER among instructions,
    index being {offset: position}: given, as it gives an item, and done,
    as it is exhausted, going to its END_FOR, then its POP_ITER, which
    Python 3.14 reports that branch from."""
    pop_iter = instructions[index[loop.argval] + 1]
    table.left[loop.offset] = given
    table.right[loop.offset] = (pop_iter.offset + 2, done)
    table.right_aliases[pop_iter.offset] = loop.offset


def _marks(instructions, handlers, source, scope):
    """{offset: actions} marking instructions of the code of scope: where
    each match starts trying its cases, each case is reached, and the match
    is left with no case taken; and where each counted statement starts.
    handlers are the offsets where the code's exception handlers start."""
    actions = {}
    for match, shape, cases in source.matches:
        if source.scope(match) is scope:
            _match_marks(actions, instructions, handlers, match, shape, cases)
    for statement, name in source.statements:
        if source.scope(statement) is scope:
            _mark_each(actions, instructions, handlers, span(statement), span(statement), Reach(name))
    return {offset: tuple(found) for offset, found in actions.items()}


def _match_marks(actions, instructions, handlers, match, shape, cases):
    """Adds the marks of match, the decision of shape, cases its (pattern,
    guard) leaf indexes: where its first pattern starts; where each case's
    guard, or its body when it has none, starts, matching its pattern; and,
    when no case matches anything, where its last pattern's jumps go when
    it does not match."""
    patterns = tuple(pattern for pattern, _ in cases)
    first_pattern = next((ins.offset for ins in instructions if _within(_at(ins), span(match.cases[0].pattern))), None)
    actions.setdefault(first_pattern, []).append(Opened(shape))
    for case, (pattern, _) in zip(match.cases, cases):
        first = case.guard if case.guard is not None else case.body[0]
        whole = (first.lineno, first.col_offset, case.body[-1].end_lineno, case.body[-1].end_col_offset)
        _mark_each(actions, instructions, handlers, span(first), whole, Matched(shape, pattern, patterns[: patterns.index(pattern)]))
    last = match.cases[-1]
    if not manifest.matches_anything(last):
        targets = [ins.argval for ins in instructions if ins.opname in JUMPS and _within(_at(ins), span(last.pattern))]
        if targets:
            actions.setdefault(max(targets), []).append(Unmatched(shape, patterns))


def _mark_each(actions, instructions, handlers, first, whole, action):
    """Adds action where each copy of the code of the span whole starts:
    Python copies a small block, eg a case's body or a return, to each
    place that reaches it, back to back or apart. A copy starts where code
    outside whole enters it, by going on from an instruction that ends no
    block, or by a jump, at an instruction from the same place as the first
    within first, the part of whole that runs first, though Python may pick
    another form of the instruction for each copy; never where an exception
    handler starts, which runs only on a raise."""
    inside = [_within(_at(ins), whole) for ins in instructions]
    ended = [False, *(ins.opname in ENDS for ins in instructions)]
    went_on = {ins.offset for ins, now, before, cut in zip(instructions, inside, [False, *inside], ended) if now > before + cut}
    jumped = {ins.jump_target for ins, now in zip(instructions, inside) if ins.jump_target is not None and not now}
    starts = went_on | jumped
    opening = next((_at(ins) for ins in instructions if _within(_at(ins), first)), None)
    same = {ins.offset for ins in instructions if _at(ins) == opening}
    for offset in sorted((starts & same) - handlers):
        actions.setdefault(offset, []).append(action)


def _at(ins):
    """Where the code of instruction ins came from, as span gives it, a
    part Python does not give as -1, so it is before any column."""
    at = ins.positions
    return tuple(-1 if part is None else part for part in (at.lineno, at.col_offset, at.end_lineno, at.end_col_offset))


def _within(inner, outer):
    """True when inner, a span as span gives it, lies inside outer."""
    return outer[:2] <= inner[:2] <= inner[2:] <= outer[2:]

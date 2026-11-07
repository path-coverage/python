"""Maps each code object Python compiled from a covered file to what each
event sys.monitoring reports in it means for the file's decisions, worked
out once per code object, before it runs, from where Python says each of
its instructions came from (its positions, as ast counts them) and the
file's own parse:

- a branch, left or right, gives the outcome of the leaf whose value its
  jump tests, and of each leaf holding it whose outcome that decides, eg
  an if's predicate holding an and;
- an instruction marks where a match's case is reached, where a match is
  left with no case taken, where a return or raise statement starts, and
  where a write of a decision's value is done, so the value can be read;
- a value returned or yielded is a decision's, when no branch tests its
  last leaf, as in return a and b;
- a function's start is its entry.

A block call, eg any(o.late for o in orders), Python 3.14 runs in its
caller: a check that any is the builtin begins it, its loop gives each item
and its end, and its test of each answer ends it when the answer decides."""

import ast
import dis
from dataclasses import dataclass, field

from . import decision_paths, manifest, method_statements
from .columns import Columns
from .evaluations import Answer, Begin, End, Item, Matched, Opened, Outcome, Reach, Shape, Unmatched, Value

# The jumps that test a value, and those of them that test it is None.
JUMPS = ("POP_JUMP_IF_TRUE", "POP_JUMP_IF_FALSE", "POP_JUMP_IF_NONE", "POP_JUMP_IF_NOT_NONE")
NONE_JUMPS = JUMPS[2:]

# The instructions between a value and the jump testing it, which only copy
# or convert it.
PLUMBING = ("TO_BOOL", "COPY", "NOT_TAKEN", "NOP", "EXTENDED_ARG")

# The instructions Python fuses from two, the second a read of a local, which
# it places where the first came from.
FUSED = ("STORE_FAST_LOAD_FAST", "LOAD_FAST_LOAD_FAST", "LOAD_FAST_BORROW_LOAD_FAST_BORROW")

# The nodes Python compiles to a code object of their own.
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda, ast.GeneratorExp)

# The name Python gives the code object of a scope with no name of its own.
SCOPE_NAMES = {ast.Lambda: "<lambda>", ast.GeneratorExp: "<genexpr>"}

# What a jump's producer is when no node is where it says it came from: no
# leaf, with no parent.
NOWHERE = ast.Constant(None, lineno=0, col_offset=0, end_lineno=0, end_col_offset=0)


@dataclass
class Table:
    """What each event in one code object means, by where it happens: left,
    {branch offset: actions}; right, {branch offset: (the offset it goes
    to, actions)}; marks, {instruction offset: (actions, the name whose
    value they read, or None)}; values, {return or yield offset: actions};
    and entry, the name its function's start is counted by, None for a
    code object that is no function's. While its instructions are
    monitored too, Python 3.14 reports a left branch from the NOT_TAKEN
    after its jump, and a loop's end from the POP_ITER after its END_FOR:
    left_aliases and right_aliases are {that offset: the branch's}."""

    left: dict = field(default_factory=dict)
    right: dict = field(default_factory=dict)
    left_aliases: dict = field(default_factory=dict)
    right_aliases: dict = field(default_factory=dict)
    marks: dict = field(default_factory=dict)
    values: dict = field(default_factory=dict)
    entry: str | None = None


class Source:
    """A covered file, parsed once, with what mapping its code needs: its
    decisions' Shapes, by name, and, by where each is written, the leaves
    a branch can test, the block calls, the matches, the statements whose
    runs are counted and the writes of a decision's value."""

    def __init__(self, source, path):
        """source, the text of the file path, as decisions name it."""
        tree, conditions, nodes = manifest.found(source, path)
        columns = Columns(source)
        reaches = set(method_statements.reaches(source, path))
        self.tree = tree
        self.parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        self.spans = {_span(node): node for node in ast.walk(tree) if isinstance(node, (ast.expr, ast.stmt, ast.pattern))}
        self.reads = {}
        for node in sorted((node for node in ast.walk(tree) if isinstance(node, ast.Name)), key=_span):
            self.reads.setdefault(node.id, []).append(node)
        self.shapes = {name: Shape(name, decision_paths.possible(condition)) for name, condition in conditions.items()}
        self.leaves = {}
        self.fixable = {}
        self.blocks = {}
        self.matches = []
        self.values = {}
        self.assigned = set()
        for name, condition in conditions.items():
            self._note(self.shapes[name], condition, nodes[name])
        self.scopes = {(getattr(node, "name", SCOPE_NAMES.get(type(node))), _first_line(node)): node for node in ast.walk(tree) if isinstance(node, SCOPES)}
        self.entries = {
            (node.name, _first_line(node)): columns.name(path, node.lineno, node.col_offset)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.statements = [
            (node, name)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Return, ast.Raise))
            if (name := columns.name(path, node.lineno, node.col_offset)) in reaches
        ]
        self.stores = [
            (node.targets[0], node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        ]

    def _note(self, shape, condition, node):
        """Notes the decision of shape, its Condition condition and its node
        node: a block call by its builtin's name; else each of its leaves
        but a match's patterns, which no branch's outcome tells, by where
        it is written, with the one outcome its form allows, if any."""
        if condition.operator in manifest.BLOCK_CALLS:
            self.blocks[_span(node.func)] = shape
            return
        patterns = ()
        if isinstance(node, ast.Match):
            self.matches.append((node, shape, _case_leaves(node)))
            patterns = {pattern for pattern, _ in _case_leaves(node)}
        if isinstance(node, (ast.BoolOp, ast.IfExp)):
            self.values[node] = shape
        fixable = self.fixable[shape] = {}
        for index, leaf in enumerate(condition.leaves()):
            if index not in patterns:
                self.leaves.setdefault((leaf.line, leaf.col, leaf.end_line, leaf.end_col), []).append((shape, index))
                fixable[index] = leaf.only

    def settle(self):
        """Once every branch of the file's code is mapped, notes on each
        Shape its leaves that no branch tests: fixed, those whose form
        fixes their outcome; and whether any other is left, silent, as the
        last of an and whose value is used, so the value tells it."""
        for shape, fixable in self.fixable.items():
            untested = {index: only for index, only in fixable.items() if (shape, index) not in self.assigned}
            shape.fixed = {index: only == "truthy" for index, only in untested.items() if only}
            shape.silent = len(untested) > len(shape.fixed)
        self.writes = {
            _span(target): (target.id, found) for target, value in self.stores if (found := self.values_of(value))
        }

    def producer(self, ins, after):
        """The node whose value instruction ins leaves for a jump to test,
        after the instruction following it: the node where ins came from;
        for an instruction that fuses a read into another, placed where the
        other came from, the read name's first node in what reads first
        after that, as _read_first gives it; NOWHERE when none is found."""
        if ins.opname in FUSED:
            regions = self._read_first(self.spans.get(_at(ins)), after)
            name = ins.argval[1]
            return next((node for region in regions for node in self.reads.get(name, ()) if _within(_span(node), region)), NOWHERE)
        return self.spans.get(_at(ins), NOWHERE)

    def _read_first(self, first, after):
        """Where the read fused with node first is, in order to search: when
        first is a comprehension's target, what that comprehension
        evaluates after writing it, its filters, its later loops, then its
        element; else where after came from, which reads it."""
        generator = self.parents.get(first)
        if not isinstance(generator, ast.comprehension):
            return [_at(after)]
        comprehension = self.parents[generator]
        later = comprehension.generators[comprehension.generators.index(generator) + 1 :]
        elements = [getattr(comprehension, part) for part in ("elt", "key", "value") if hasattr(comprehension, part)]
        parts = [*generator.ifs, *(part for each in later for part in (each.iter, *each.ifs)), *elements]
        return [_span(part) for part in parts]

    def scope(self, node):
        """The node whose code object runs node's code: its innermost
        function, class, lambda or generator, else the module's tree."""
        while not isinstance(node, (*SCOPES, ast.Module)):
            node = self.parents[node]
        return node

    def outcomes(self, node, opname, jumped, final):
        """The Outcome actions of a jump named opname testing node's value,
        when it jumped or not: of node and each node holding it whose
        outcome that decides. A jump on None tests node is None. final is
        False for a chained comparison's jump before its last, which
        decides only when false."""
        if opname in NONE_JUMPS:
            node = self.parents.get(node)
            if not isinstance(node, ast.Compare):
                return ()
            truth = (jumped == (opname == "POP_JUMP_IF_NONE")) == isinstance(node.ops[0], ast.Is)
        else:
            truth = jumped == (opname == "POP_JUMP_IF_TRUE")
        if truth and not final:
            return ()
        return tuple(self._up(node, truth))

    def _up(self, node, truth):
        """Outcome actions of node, given truth its outcome, as a leaf of
        any decision, then of each node holding it whose outcome truth
        decides."""
        while True:
            for shape, index in self.leaves.get(_span(node), ()):
                self.assigned.add((shape, index))
                yield Outcome(shape, index, truth)
            truth = _held(self.parents.get(node), node, truth)
            if truth is None:
                return
            node = self.parents[node]

    def values_of(self, node, flip=False):
        """The Value actions of a value that is node's, as written, when it
        is a decision's with a silent leaf, or each decision's whose last
        leaf's value it is, eg return a or (b and c); flip, when a not
        lies between, as in return not (a and b)."""
        shape = self.values.get(node)
        found = [Value(shape, flip)] if shape is not None and shape.silent else []
        match node:
            case ast.BoolOp(values=[*_, last]):
                found += self.values_of(last, flip)
            case ast.IfExp(body=body, orelse=orelse):
                found += self.values_of(body, flip) + self.values_of(orelse, flip)
            case ast.UnaryOp(op=ast.Not(), operand=operand):
                found += self.values_of(operand, not flip)
            case ast.NamedExpr(value=value):
                found += self.values_of(value, flip)
        return found

    def sink(self, node):
        """The node whose value a return or yield Python placed at node
        gives: a return's or yield's value, a lambda's body, or a
        generator's element; None for any other."""
        if isinstance(node, (ast.Return, ast.Yield)):
            return node.value
        return node if isinstance(self.parents.get(node), (ast.Lambda, ast.GeneratorExp)) else None


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
    each code object nested in it, source its Source."""
    codes = _tree(code)
    listed = {each: list(dis.get_instructions(each)) for each in codes}
    found = {each: Table(entry=source.entries.get((each.co_name, each.co_firstlineno))) for each in codes}
    for each in codes:
        _branches(found[each], listed[each], source)
    source.settle()
    for each in codes:
        scope = source.scopes.get((each.co_name, each.co_firstlineno), source.tree)
        _marks(found[each], listed[each], source, scope)
        _values(found[each], listed[each], source)
    return found


def _tree(code):
    """code and every code object nested in it, at any depth."""
    nested = [const for const in code.co_consts if isinstance(const, type(code))]
    return [code, *(each for inner in nested for each in _tree(inner))]


def _branches(table, instructions, source):
    """Adds to table the actions of each branch in instructions: each block
    call's, then each jump's that tests a value whose outcome tells a
    leaf's."""
    handled = set()
    blocks = {}
    index = {ins.offset: at for at, ins in enumerate(instructions)}
    for ins in instructions:
        if _at(ins) in source.blocks and ins.opname in (*JUMPS, "FOR_ITER"):
            blocks.setdefault(_at(ins), []).append(ins)
    for span, found in blocks.items():
        shape = source.blocks[span]
        for begin, loop, test in zip(*[iter(found)] * 3):
            handled |= {begin.offset, test.offset}
            stops_on = test.opname == "POP_JUMP_IF_TRUE"
            table.left[begin.offset], table.right[begin.offset] = (Begin(shape),), (begin.argval, ())
            table.left[loop.offset] = (Item(shape),)
            # The loop's END_FOR, where it jumps when done, then its POP_ITER.
            pop_iter = instructions[index[loop.argval] + 1]
            table.right[loop.offset] = (pop_iter.offset + 2, (End(shape),))
            table.right_aliases[pop_iter.offset] = loop.offset
            table.left[test.offset] = (Answer(shape, not stops_on),)
            table.right[test.offset] = (test.argval, (Answer(shape, stops_on), End(shape)))
    producers = {}
    for at, ins in enumerate(instructions):
        if ins.opname in JUMPS and ins.offset not in handled:
            back = at - 1
            while instructions[back].opname in PLUMBING:
                back -= 1
            producers[at] = source.producer(instructions[back], instructions[back + 1])
    finals = {node: at for at, node in producers.items()}
    for at, node in producers.items():
        ins = instructions[at]
        left = source.outcomes(node, ins.opname, False, finals[node] == at)
        right = source.outcomes(node, ins.opname, True, finals[node] == at)
        if left or right:
            table.left[ins.offset], table.right[ins.offset] = left, (ins.argval, right)
    for at, ins in enumerate(instructions):
        if ins.opname == "NOT_TAKEN" and instructions[at - 1].offset in table.left:
            table.left_aliases[ins.offset] = instructions[at - 1].offset


def _marks(table, instructions, source, scope):
    """Adds to table the actions marking instructions of the code of scope:
    each match's cases reached, and its leaving with no case taken; each
    counted statement's start; and each write of a value a decision gave,
    read once it is written."""
    actions = {}
    reads = {}
    for match, shape, cases in source.matches:
        if source.scope(match) is scope:
            _match_marks(actions, instructions, match, shape, cases)
    for statement, name in source.statements:
        if source.scope(statement) is scope:
            _mark(actions, instructions, _span(statement), Reach(name))
    for at, ins in enumerate(instructions):
        if _at(ins) in source.writes and ins.opname.startswith("STORE"):
            name, found = source.writes[_at(ins)]
            offset = instructions[at + 1].offset
            actions.setdefault(offset, []).extend(found)
            reads[offset] = name
    table.marks = {offset: (tuple(found), reads.get(offset)) for offset, found in actions.items()}


def _match_marks(actions, instructions, match, shape, cases):
    """Adds the marks of match, the decision of shape, cases its (pattern,
    guard) leaf indexes: where each case's guard, or its body when it has
    none, starts, matching its pattern; and, when no case matches
    anything, where its last pattern's jumps go when it does not match."""
    patterns = tuple(pattern for pattern, _ in cases)
    _mark(actions, instructions, _span(match.cases[0].pattern), Opened(shape))
    for case, (pattern, _) in zip(match.cases, cases):
        first = case.guard if case.guard is not None else case.body[0]
        span = (first.lineno, first.col_offset, case.body[-1].end_lineno, case.body[-1].end_col_offset)
        _mark(actions, instructions, span, Matched(shape, pattern, patterns[: patterns.index(pattern)]))
    last = match.cases[-1]
    if not manifest.matches_anything(last):
        targets = [ins.argval for ins in instructions if ins.opname in JUMPS and _within(_at(ins), _span(last.pattern))]
        if targets:
            actions.setdefault(max(targets), []).append(Unmatched(shape, patterns))


def _mark(actions, instructions, span, action):
    """Adds action at the first of instructions within span."""
    first = next((ins.offset for ins in instructions if _within(_at(ins), span)), None)
    actions.setdefault(first, []).append(action)


def _values(table, instructions, source):
    """Adds to table the actions of each value returned or yielded that is
    a decision's with a silent leaf."""
    for ins in instructions:
        if ins.opname in ("RETURN_VALUE", "YIELD_VALUE"):
            found = source.values_of(source.sink(source.spans.get(_at(ins))))
            if found:
                table.values[ins.offset] = tuple(found)


def _case_leaves(match):
    """[(pattern leaf index, guard leaf index or None), ...] of each of
    match's cases, in the manifest's leaf order."""
    found = []
    at = 0
    for case in match.cases:
        guarded = case.guard is not None
        found.append((at, at + 1 if guarded else None))
        at += 1 + guarded
    return found


def _first_line(node):
    """The line Python starts node's code object at: its first decorator's,
    else its own."""
    return min([node.lineno, *(decorator.lineno for decorator in getattr(node, "decorator_list", []))])


def _span(node):
    """Where node is written, (line, col, end_line, end_col), as ast counts
    them."""
    return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)


def _at(ins):
    """Where the code of instruction ins came from, as _span gives it, a
    part Python does not give as -1, so it is before any column."""
    at = ins.positions
    return tuple(-1 if part is None else part for part in (at.lineno, at.col_offset, at.end_lineno, at.end_col_offset))


def _within(inner, outer):
    """True when inner, a span as _span gives it, lies inside outer."""
    return outer[:2] <= inner[:2] <= inner[2:] <= outer[2:]

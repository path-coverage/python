"""Finds every condition decision in source without running it: each outermost
`and` or `or`, with the conditions nested in it."""

import ast
import bisect
import io
import tokenize
from dataclasses import dataclass, field

from . import leaving
from .columns import Columns

OPERATORS = {ast.And: "and", ast.Or: "or"}


@dataclass(frozen=True)
class Leaf:
    """Where one leaf operand is written: 1-based lines, 0-based UTF-8 byte
    columns, end exclusive, exactly as ast reports them. only is "truthy" or
    "falsy" for a leaf whose form allows that one outcome, else None."""

    line: int
    col: int
    end_line: int
    end_col: int
    only: str | None = None


@dataclass(frozen=True)
class Arm:
    """One arm of a choice: kind is "then" or "else", and body the Condition
    it holds, which is part of the choice's decision, or None for a plain arm."""

    kind: str
    body: object = None
    # Where a conditional expression's arm is written, (line, col,
    # end_line, end_col) as ast counts them, for its text; None for an if
    # statement's arms, named by their kind instead.
    at: tuple | None = field(default=None, compare=False)
    # Where the arm's code is, as at counts it, so a card's row can be
    # placed in the arm holding it: a conditional expression's arm's, as
    # at; an if statement's arm's statements, first to last; None for an
    # arm of no code, eg a filter's.
    extent: tuple | None = field(default=None, compare=False)
    # How an if statement's arm leaves the function, as leaving.of gives
    # it, "return" or "raise"; None for an arm that does not leave it.
    leaving: str | None = None

    def leaves(self):
        """The leaves of the condition the arm holds; none for a plain arm."""
        return self.body.leaves() if self.body else []


@dataclass(frozen=True)
class Condition:
    """One decision's condition: its operator as written and its operands. A
    ternary's operands are its predicate, then its then and else Arms."""

    operator: str
    operands: tuple
    # Where the whole of the condition is written, (line, col, end_line,
    # end_col) as ast counts them, so a card can tell which rows run
    # inside it.
    extent: tuple | None = field(default=None, compare=False)

    def leaves(self):
        """Every Leaf, nested ones and arms' included, left to right; a
        leaf's index here is the index it is recorded under."""
        return [
            leaf
            for operand in self.operands
            for leaf in (operand.leaves() if isinstance(operand, (Condition, Arm)) else [operand])
        ]


# The nodes a choice's arm may hold as part of the choice's own decision. A
# conditional expression in an arm is a decision of its own, so each row of a
# card is one choice, nested in the arm it runs in.
FOLDABLE = (ast.BoolOp,)


class _DecisionFinder(ast.NodeVisitor):
    """Collects each decision, in source order, and its Condition."""

    def __init__(self, path, columns, keywords, builtins, operators, parents):
        """Starts with no decisions found, naming decisions after path, in
        the source's columns; keywords are where the source's if keywords
        are, as if_keywords gives them, builtins the block calls' names the
        module leaves as builtins, operators where its and, or and if
        keywords are, as operator_keywords gives them, and parents {node:
        the node holding it} of its parse."""
        self.path = path
        self.columns = columns
        self.keywords = keywords
        self.builtins = builtins
        self.operators = operators
        self.parents = parents
        self.decisions = {}
        # {decision: the node it is}, eg the BoolOp of an `and`; a
        # filter's is its test.
        self.nodes = {}

    def _claim(self, decision, node):
        """Claims decision's place in source order, before any decision found
        inside it, noting node as the one it is."""
        self.decisions[decision] = None
        self.nodes[decision] = node

    def visit_Call(self, node):
        """Notes a block call, eg any(o.late for o in orders), as a decision,
        named where the call starts: its items, the iterable of its
        generator's first for, then its answer, the generator's element.
        The decisions inside the generator follow it. Any other call is no
        decision, though the decisions inside it are."""
        generator = block_generator(node, self.builtins)
        if generator is None:
            self.generic_visit(node)
            return
        decision = self.columns.name(self.path, node.lineno, node.col_offset)
        self._claim(decision, node)
        self.visit(generator)
        operands = (_leaf(generator.generators[0].iter), _leaf(generator.elt))
        self.decisions[decision] = Condition(node.func.id, operands, _extent(node))

    def visit_Match(self, node):
        """Notes a match statement as a decision, named at its keyword: its
        cases, in order, each its pattern's leaf, true when it matches, and,
        when guarded, a `case` of that leaf and its guard. The decisions inside
        its subject and its cases' bodies follow it."""
        decision = self.columns.name(self.path, node.lineno, node.col_offset)
        self._claim(decision, node)
        self.visit(node.subject)
        clauses = []
        for case in node.cases:
            pattern = _pattern_leaf(case.pattern)
            if case.guard is None:
                clauses.append(pattern)
            else:
                guard = case.guard
                extent = (pattern.line, pattern.col, guard.end_lineno, guard.end_col_offset)
                clauses.append(Condition("case", (pattern, self._leaf(guard)), extent))
        self.decisions[decision] = Condition("match", tuple(clauses), _extent(node))
        for case in node.cases:
            for statement in case.body:
                self.visit(statement)

    def visit_comprehension(self, node):
        """Notes each filter of a comprehension's for as a decision, named at
        its if keyword, ast giving no place for it: its test, then its then
        arm, which keeps the item, and its else arm, which drops it."""
        self.visit(node.target)
        self.visit(node.iter)
        for test in node.ifs:
            line, col = keyword_before(self.keywords, test)
            decision = self.columns.name(self.path, line, col)
            self._claim(decision, test)
            predicate = self._leaf(test)
            extent = (line, col, test.end_lineno, test.end_col_offset)
            operands = (predicate, Arm("then"), Arm("else"))
            self.decisions[decision] = Condition("filter", operands, extent)

    def visit_BoolOp(self, node):
        """Notes node as a decision, named where decision_at says. It claims its
        place first, so a decision found inside one of its leaves follows it."""
        line, col = decision_at(self.operators, node)
        decision = self.columns.name(self.path, line, col)
        self._claim(decision, node)
        self.decisions[decision] = self._condition(node, self._decides(node))

    visit_IfExp = visit_BoolOp

    def _decides(self, node):
        """True when a branch forks on node's truth: it is, or its value
        becomes, through any and/or, conditional expression's arm, walrus
        or not holding it, the test of an if, a while, an assert or a
        conditional expression, a filter, a guard, or the element of a
        block call, eg any(...). False when its value is only used, eg x =
        a or b, so the truth of its last leaf decides nothing."""
        while True:
            parent = self.parents.get(node)
            match parent:
                case ast.BoolOp() | ast.NamedExpr() | ast.UnaryOp(op=ast.Not()):
                    node = parent
                case ast.IfExp():
                    if node is parent.test:
                        return True
                    node = parent
                case ast.If() | ast.While() | ast.Assert():
                    return node is parent.test
                case ast.comprehension():
                    return node in parent.ifs
                case ast.match_case():
                    # A guard is the only expression a case holds.
                    return True
                case ast.GeneratorExp():
                    # Its element is the only expression it holds.
                    return block_generator(self.parents.get(parent), self.builtins) is parent
                case _:
                    return False

    def visit_If(self, node):
        """Notes an if or elif statement as a decision, named at its keyword: its
        predicate, then its then arm, then its else arm when it has one (an
        elif being the else arm of the if before it). Its arms are plain, as
        they are statements; the decisions inside them follow it."""
        decision = self.columns.name(self.path, node.lineno, node.col_offset)
        self._claim(decision, node)
        predicate = self._leaf(node.test)
        then = _statement_arm("then", node.body)
        arms = (then, _statement_arm("else", node.orelse)) if node.orelse else (then,)
        self.decisions[decision] = Condition("if", (predicate, *arms), _extent(node))
        for statement in node.body + node.orelse:
            self.visit(statement)

    def _condition(self, node, decides):
        """node as a Condition, decides saying whether a branch forks on
        its truth, as _decides gives it. An `and`/`or`: ast already flattens
        a chain of one operator, so each operand is either the other
        operator, nested, or a leaf; but when its truth decides nothing, its
        last operand is no leaf, only evaluated or not, so it is left out,
        once any decision inside it is noted. A conditional expression: its
        predicate, then its then and else arms."""
        if isinstance(node, ast.IfExp):
            return Condition(
                operator="ternary",
                operands=(
                    self._leaf(node.test),
                    self._arm("then", node.body, decides),
                    self._arm("else", node.orelse, decides),
                ),
                extent=_extent(node),
            )
        *tested, last = node.values
        operands = [self._operand(value, True) for value in tested]
        if decides or isinstance(last, ast.BoolOp):
            operands.append(self._operand(last, decides))
        else:
            self.visit(last)
        return Condition(operator=OPERATORS[type(node.op)], operands=tuple(operands), extent=_extent(node))

    def _arm(self, kind, node, decides):
        """An Arm holding node's condition when node is one a choice folds
        into its decision, decides saying whether a branch forks on the
        choice's truth, else a plain Arm, once any decision inside node is
        noted."""
        at = _extent(node)
        if isinstance(node, FOLDABLE):
            return Arm(kind, self._condition(node, decides), at, at)
        self.visit(node)
        return Arm(kind, None, at, at)

    def _operand(self, node, decides):
        """node as a nested Condition when it is an `and`/`or`, decides
        saying whether a branch forks on its truth, else a Leaf, once any
        decision inside the leaf is noted too."""
        if isinstance(node, ast.BoolOp):
            return self._condition(node, decides)
        return self._leaf(node)

    def _leaf(self, node):
        """node as one Leaf, once any decision in it is noted, node itself
        included: a choice's predicate, so an `and`/`or` that is the whole of
        it is a decision of its own, each row of a card one decision."""
        self.visit(node)
        return Leaf(
            node.lineno, node.col_offset, node.end_lineno, node.end_col_offset, _only(node)
        )


# The builtins whose call of a generator is a decision: each stops early, at
# the first item whose answer decides it.
BLOCK_CALLS = ("any", "all")


def _extent(node):
    """Where node is written, (line, col, end_line, end_col) as ast counts
    them."""
    return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)


def _statements_extent(statements):
    """Where statements are written, from the first's start to the last's
    end, as _extent counts them."""
    first, last = statements[0], statements[-1]
    return (first.lineno, first.col_offset, last.end_lineno, last.end_col_offset)


def _statement_arm(kind, statements):
    """The plain Arm of an if statement whose code is statements, with
    how they leave the function, as leaving.of decides it."""
    return Arm(kind, extent=_statements_extent(statements), leaving=leaving.of(statements))


def block_generator(node, builtins):
    """The generator of node when node is a call of one of builtins whose
    one argument is a generator, eg any(o.late for o in orders); else None,
    as for any(flags), whose items have no answer to note."""
    match node:
        case ast.Call(func=ast.Name(id=name), args=[ast.GeneratorExp() as generator], keywords=[]) if name in builtins:
            return generator
        case _:
            return None


def builtin_blocks(tree):
    """The names of BLOCK_CALLS that tree's module never binds itself, so
    each still names the builtin wherever it is called. A star import may
    bind any name, so it leaves none."""
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            bound.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.alias):
            bound.update(BLOCK_CALLS if node.name == "*" else [_alias_name(node)])
        elif isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
            bound.add(node.name)
        elif isinstance(node, ast.MatchMapping):
            bound.add(node.rest)
    return tuple(name for name in BLOCK_CALLS if name not in bound)


def _alias_name(alias):
    """The name an import binds: its as name, else the first part of the
    module or name imported."""
    return alias.asname if alias.asname else alias.name.split(".")[0]


def _leaf(node):
    """A Leaf where node is written."""
    return Leaf(node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)


def irrefutable(pattern):
    """True for a case's pattern that matches any subject, as Python itself
    decides it: _ or a bare capture name, an as-pattern of an irrefutable
    pattern, eg _ as size, or an or-pattern with an irrefutable
    alternative, eg 2 | _."""
    match pattern:
        case ast.MatchAs(pattern=None):
            return True
        case ast.MatchAs(pattern=inner):
            return irrefutable(inner)
        case ast.MatchOr(patterns=alternatives):
            return any(map(irrefutable, alternatives))
        case _:
            return False


def wrapped(node, parent):
    """True for node, a leaf held by parent, whose outcome a call around it
    counts, as no branch tells it: the last operand of an and/or that is no
    and/or itself, which no branch tests when the and/or's value is used,
    eg x = a or b; a leaf whose form fixes its outcome, eg 0, which Python
    compiles to no test; and a conditional expression, whose literal arm
    Python compiles to no test, eg if a if b else True. The one place this
    is decided, for the rewrite that wraps it and for code_map, which
    counts no branch for it."""
    last = isinstance(parent, ast.BoolOp) and parent.values[-1] is node and not isinstance(node, ast.BoolOp)
    return last or _only(node) is not None or isinstance(node, ast.IfExp)


def matches_anything(case):
    """True for a match statement's case that is taken whatever the
    subject: an irrefutable pattern with no guard. The one place this is
    decided, for the manifest's paths and code_map's marks alike."""
    return case.guard is None and irrefutable(case.pattern)


def _pattern_leaf(pattern):
    """The Leaf of a case's pattern, only truthy for an irrefutable one."""
    return Leaf(
        pattern.lineno,
        pattern.col_offset,
        pattern.end_lineno,
        pattern.end_col_offset,
        "truthy" if irrefutable(pattern) else None,
    )


def _only(node):
    """The one outcome node's form allows, eg "falsy" for `''` and "truthy"
    for `[None]`; None for a form that can have either. Only forms whose
    truth Python itself fixes count: a call or a name may be either."""
    if isinstance(node, ast.Constant):
        return "truthy" if node.value else "falsy"
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return _display(node.elts, [not isinstance(e, ast.Starred) for e in node.elts])
    if isinstance(node, ast.Dict):
        return _display(node.keys, [key is not None for key in node.keys])
    if isinstance(node, ast.Lambda):
        return "truthy"
    if isinstance(node, ast.JoinedStr):
        # An f-string's literal text is never empty, so any part of it makes
        # the string truthy.
        literal = any(isinstance(value, ast.Constant) for value in node.values)
        return "truthy" if literal else None
    return None


def _display(items, plain):
    """The outcome of a list, tuple, set or dict display of items, where
    plain says which items are not *x or **x unpackings: falsy when empty,
    truthy when one plain item guarantees it is not, else None."""
    if not items:
        return "falsy"
    return "truthy" if any(plain) else None


def decisions(source, path):
    """{decision: Condition} for each decision in source, each decision named
    "path:line:col" of where decision_at places it, its col in characters."""
    return found(source, path)[1]


def found(source, path):
    """(tree, decisions, nodes) of source: its parse; {decision: Condition},
    as decisions gives it; and {decision: the node of tree it is}, a
    filter's being its test, so what Python compiled from a node can be
    traced to its decision."""
    tree = ast.parse(source)
    operators = operator_keywords(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    finder = _DecisionFinder(path, Columns(source), if_keywords(source), builtin_blocks(tree), operators, parents)
    finder.visit(tree)
    return tree, finder.decisions, finder.nodes


def if_keywords(source):
    """[(line, col), ...] of every if keyword in source, in order, columns
    counted in UTF-8 bytes, as ast counts them."""
    return _keywords(source, ("if",))


def operator_keywords(source):
    """[(line, col), ...] of every and, or and if keyword in source, in
    order, columns counted as if_keywords counts them: where decision_at names
    the operators' decisions."""
    return _keywords(source, ("and", "or", "if"))


def _keywords(source, words):
    """[(line, col), ...] of every keyword of words in source, in order,
    columns counted in UTF-8 bytes, as ast counts them."""
    lines = source.splitlines(keepends=True)
    return [
        (line, len(lines[line - 1][:col].encode()))
        for kind, text, (line, col), _, _ in tokenize.generate_tokens(io.StringIO(source).readline)
        if kind == tokenize.NAME and text in words
    ]


# The comprehensions Python runs in the frame of the code holding them.
INLINED = (ast.ListComp, ast.SetComp, ast.DictComp)


def loop_places(source, tree):
    """{loop node: (line, col) of its for keyword} of every loop in tree,
    source's parse, run in the frame of the code holding it: each for
    statement, and each generator of a list, set or dict comprehension;
    none of a generator expression, which runs in a frame of its own."""
    fors = _keywords(source, ("for",))
    places = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            places[node] = (node.lineno, node.col_offset)
        if isinstance(node, INLINED):
            places.update({generator: keyword_before(fors, generator.target) for generator in node.generators})
    return places


def decision_at(operators, node):
    """The (line, col) that names node's decision, an and, an or or a
    conditional expression, operators being where operator_keywords finds
    them: an and or an or at its first keyword, after its first operand; a
    conditional expression at its if, after its then value. So no two decisions
    share a name, eg any(...) or b, whose any starts where the or does.
    Example: a or b at line 2, col 4 gives (2, 6)."""
    first = node.values[0] if isinstance(node, ast.BoolOp) else node.body
    return operators[bisect.bisect_left(operators, (first.end_lineno, first.end_col_offset))]


def keyword_before(keywords, test):
    """The (line, col) of the last of keywords before where test starts: a
    filter's if, as only space, comments and brackets come between."""
    return keywords[bisect.bisect_left(keywords, (test.lineno, test.col_offset)) - 1]

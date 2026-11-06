"""Finds every condition site in source without running it: each outermost
`and` or `or`, with the conditions nested in it."""

import ast
import bisect
import io
import tokenize
from dataclasses import dataclass, field

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
    it holds, which is part of the choice's site, or None for a plain arm."""

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

    def leaves(self):
        """The leaves of the condition the arm holds; none for a plain arm."""
        return self.body.leaves() if self.body else []


@dataclass(frozen=True)
class Condition:
    """One site's condition: its operator as written and its operands. A
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


# The nodes a choice's arm may hold as part of the choice's own site. A
# conditional expression in an arm is a site of its own, so each row of a
# card is one choice, nested in the arm it runs in.
FOLDABLE = (ast.BoolOp,)


class _SiteFinder(ast.NodeVisitor):
    """Collects each site, in source order, and its Condition."""

    def __init__(self, path, keywords, builtins, operators):
        """Starts with no sites found, naming sites after path; keywords are
        where the source's if keywords are, as if_keywords gives them,
        builtins the block calls' names the module leaves as builtins, and
        operators where its and, or and if keywords are, as
        operator_keywords gives them."""
        self.path = path
        self.keywords = keywords
        self.builtins = builtins
        self.operators = operators
        self.sites = {}

    def visit_Call(self, node):
        """Notes a block call, eg any(o.late for o in orders), as a site,
        named where the call starts: its items, the iterable of its
        generator's first for, then its answer, the generator's element.
        The sites inside the generator follow it. Any other call is no
        site, though the sites inside it are."""
        generator = block_generator(node, self.builtins)
        if generator is None:
            self.generic_visit(node)
            return
        site = f"{self.path}:{node.lineno}:{node.col_offset}"
        self.sites[site] = None
        self.visit(generator)
        operands = (_leaf(generator.generators[0].iter), _leaf(generator.elt))
        self.sites[site] = Condition(node.func.id, operands, _extent(node))

    def visit_Match(self, node):
        """Notes a match statement as a site, named at its keyword: its
        cases, in order, each its pattern's leaf, true when it matches, and,
        when guarded, a `case` of that leaf and its guard. The sites inside
        its subject and its cases' bodies follow it."""
        site = f"{self.path}:{node.lineno}:{node.col_offset}"
        self.sites[site] = None
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
        self.sites[site] = Condition("match", tuple(clauses), _extent(node))
        for case in node.cases:
            for statement in case.body:
                self.visit(statement)

    def visit_comprehension(self, node):
        """Notes each filter of a comprehension's for as a site, named at
        its if keyword, ast giving no place for it: its test, then its then
        arm, which keeps the item, and its else arm, which drops it."""
        self.visit(node.target)
        self.visit(node.iter)
        for test in node.ifs:
            line, col = keyword_before(self.keywords, test)
            site = f"{self.path}:{line}:{col}"
            self.sites[site] = None
            predicate = self._leaf(test)
            extent = (line, col, test.end_lineno, test.end_col_offset)
            operands = (predicate, Arm("then"), Arm("else"))
            self.sites[site] = Condition("filter", operands, extent)

    def visit_BoolOp(self, node):
        """Notes node as a site, named where site_at says. It claims its
        place first, so a site found inside one of its leaves follows it."""
        line, col = site_at(self.operators, node)
        site = f"{self.path}:{line}:{col}"
        self.sites[site] = None
        self.sites[site] = self._condition(node)

    visit_IfExp = visit_BoolOp

    def visit_If(self, node):
        """Notes an if or elif statement as a site, named at its keyword: its
        predicate, then its then arm, then its else arm when it has one (an
        elif being the else arm of the if before it). Its arms are plain, as
        they are statements; the sites inside them follow it."""
        site = f"{self.path}:{node.lineno}:{node.col_offset}"
        self.sites[site] = None
        predicate = self._leaf(node.test)
        then = Arm("then", extent=_statements_extent(node.body))
        arms = (then, Arm("else", extent=_statements_extent(node.orelse))) if node.orelse else (then,)
        self.sites[site] = Condition("if", (predicate, *arms), _extent(node))
        for statement in node.body + node.orelse:
            self.visit(statement)

    def _condition(self, node):
        """node as a Condition. An `and`/`or`: ast already flattens a chain
        of one operator, so each operand is either the other operator,
        nested, or a leaf. A conditional expression: its predicate, then its
        then and else arms."""
        if isinstance(node, ast.IfExp):
            return Condition(
                operator="ternary",
                operands=(
                    self._leaf(node.test),
                    self._arm("then", node.body),
                    self._arm("else", node.orelse),
                ),
                extent=_extent(node),
            )
        return Condition(
            operator=OPERATORS[type(node.op)],
            operands=tuple(self._operand(value) for value in node.values),
            extent=_extent(node),
        )

    def _arm(self, kind, node):
        """An Arm holding node's condition when node is one a choice folds
        into its site, else a plain Arm, once any site inside node is
        noted."""
        at = _extent(node)
        if isinstance(node, FOLDABLE):
            return Arm(kind, self._condition(node), at, at)
        self.visit(node)
        return Arm(kind, None, at, at)

    def _operand(self, node):
        """node as a nested Condition when it is an `and`/`or`, else a Leaf,
        once any site inside the leaf is noted too."""
        if isinstance(node, ast.BoolOp):
            return self._condition(node)
        return self._leaf(node)

    def _leaf(self, node):
        """node as one Leaf, once any site in it is noted, node itself
        included: a choice's predicate, so an `and`/`or` that is the whole of
        it is a site of its own, each row of a card one decision."""
        self.visit(node)
        return Leaf(
            node.lineno, node.col_offset, node.end_lineno, node.end_col_offset, _only(node)
        )


# The builtins whose call of a generator is a site: each stops early, at
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


def block_generator(node, builtins):
    """The generator of node when node is a call of one of builtins whose
    one argument is a generator, eg any(o.late for o in orders); else None,
    as for any(flags), whose items have no answer to note."""
    called = isinstance(node.func, ast.Name) and node.func.id in builtins
    if called and not node.keywords and len(node.args) == 1 and isinstance(node.args[0], ast.GeneratorExp):
        return node.args[0]
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
    return alias.asname or alias.name.split(".")[0]


def _leaf(node):
    """A Leaf where node is written."""
    return Leaf(node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)


def _pattern_leaf(pattern):
    """The Leaf of a case's pattern, only truthy for one that matches
    anything: _ or a bare capture name."""
    irrefutable = isinstance(pattern, ast.MatchAs) and pattern.pattern is None
    return Leaf(
        pattern.lineno,
        pattern.col_offset,
        pattern.end_lineno,
        pattern.end_col_offset,
        "truthy" if irrefutable else None,
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
        literal = any(isinstance(v, ast.Constant) and v.value for v in node.values)
        return "truthy" if literal else None
    return None


def _display(items, plain):
    """The outcome of a list, tuple, set or dict display of items, where
    plain says which items are not *x or **x unpackings: falsy when empty,
    truthy when one plain item guarantees it is not, else None."""
    if not items:
        return "falsy"
    return "truthy" if any(plain) else None


def sites(source, path):
    """{site: Condition} for each site in source, each site named
    "path:line:col" of where site_at places it."""
    tree = ast.parse(source)
    operators = operator_keywords(source)
    finder = _SiteFinder(path, if_keywords(source), builtin_blocks(tree), operators)
    finder.visit(tree)
    return finder.sites


def if_keywords(source):
    """[(line, col), ...] of every if keyword in source, in order, columns
    counted in UTF-8 bytes, as ast counts them."""
    lines = source.splitlines(keepends=True)
    return [
        (line, len(lines[line - 1][:col].encode()))
        for kind, text, (line, col), _, _ in tokenize.generate_tokens(io.StringIO(source).readline)
        if kind == tokenize.NAME and text == "if"
    ]


def operator_keywords(source):
    """[(line, col), ...] of every and, or and if keyword in source, in
    order, columns counted as if_keywords counts them: where site_at names
    the operators' sites."""
    lines = source.splitlines(keepends=True)
    return [
        (line, len(lines[line - 1][:col].encode()))
        for kind, text, (line, col), _, _ in tokenize.generate_tokens(io.StringIO(source).readline)
        if kind == tokenize.NAME and text in ("and", "or", "if")
    ]


def site_at(operators, node):
    """The (line, col) that names node's site, an and, an or or a
    conditional expression, operators being where operator_keywords finds
    them: an and or an or at its first keyword, after its first operand; a
    conditional expression at its if, after its then value. So no two sites
    share a name, eg any(...) or b, whose any starts where the or does.
    Example: a or b at line 2, col 4 gives (2, 6)."""
    first = node.values[0] if isinstance(node, ast.BoolOp) else node.body
    return operators[bisect.bisect_left(operators, (first.end_lineno, first.end_col_offset))]


def keyword_before(keywords, test):
    """The (line, col) of the last of keywords before where test starts: a
    filter's if, as only space, comments and brackets come between."""
    return keywords[bisect.bisect_left(keywords, (test.lineno, test.col_offset)) - 1]

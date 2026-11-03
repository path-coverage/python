"""Finds every condition site in source without running it: each outermost
`and` or `or`, with the conditions nested in it."""

import ast
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

    def leaves(self):
        """The leaves of the condition the arm holds; none for a plain arm."""
        return self.body.leaves() if self.body else []


@dataclass(frozen=True)
class Condition:
    """One site's condition: its operator as written and its operands. A
    ternary's operands are its predicate, then its then and else Arms."""

    operator: str
    operands: tuple

    def leaves(self):
        """Every Leaf, nested ones and arms' included, left to right; a
        leaf's index here is the index it is recorded under."""
        return [
            leaf
            for operand in self.operands
            for leaf in (operand.leaves() if isinstance(operand, (Condition, Arm)) else [operand])
        ]


# The nodes a choice's arm may hold as part of the choice's own site.
FOLDABLE = (ast.BoolOp, ast.IfExp)


class _SiteFinder(ast.NodeVisitor):
    """Collects each site, in source order, and its Condition."""

    def __init__(self, path):
        """Starts with no sites found, naming sites after path."""
        self.path = path
        self.sites = {}

    def visit_BoolOp(self, node):
        """Notes node as a site. It claims its place first, so a site found
        inside one of its leaves follows it, keeping sites in source order."""
        site = f"{self.path}:{node.lineno}:{node.col_offset}"
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
        predicate = self._operand(node.test)
        arms = (Arm("then"), Arm("else")) if node.orelse else (Arm("then"),)
        self.sites[site] = Condition(operator="if", operands=(predicate, *arms))
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
                    self._operand(node.test),
                    self._arm("then", node.body),
                    self._arm("else", node.orelse),
                ),
            )
        return Condition(
            operator=OPERATORS[type(node.op)],
            operands=tuple(self._operand(value) for value in node.values),
        )

    def _arm(self, kind, node):
        """An Arm holding node's condition when node is one a choice folds
        into its site, else a plain Arm, once any site inside node is
        noted."""
        at = (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)
        if isinstance(node, FOLDABLE):
            return Arm(kind, self._condition(node), at)
        self.visit(node)
        return Arm(kind, None, at)

    def _operand(self, node):
        """node as a nested Condition when it is an `and`/`or`, else a Leaf,
        once any site inside the leaf is noted too."""
        if isinstance(node, ast.BoolOp):
            return self._condition(node)
        self.visit(node)
        return Leaf(
            node.lineno, node.col_offset, node.end_lineno, node.end_col_offset, _only(node)
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
    """{site: Condition} for each site in source, in source order, each site
    named "path:line:col" of where its condition starts."""
    finder = _SiteFinder(path)
    finder.visit(ast.parse(source))
    return finder.sites

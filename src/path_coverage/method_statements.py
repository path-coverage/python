"""Finds, without running it, the top-level statements of each function in
source, one row each in its method-mode card."""

import ast
from dataclasses import dataclass

from . import site_paths
from .manifest import block_generator, builtin_blocks, sites


@dataclass(frozen=True)
class Statement:
    """One row of a function's card, a top-level statement or a site at its
    top: where it starts; its top, what it is as written, eg = for a write;
    how many paths it has; the name of its site, None when it is no site;
    and its own name, by where it is, eg "k.py:2:4"."""

    line: int
    column: int
    top: str
    paths: int
    site: str | None
    name: str


# The nodes whose bodies run in a context of their own, once per call or
# per item, never once per run of the statement holding them, so they are
# not looked through.
SCOPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)

# The tops of statements with a keyword of their own and no site at their
# top, by their type.
KEYWORDS = {
    ast.For: "for",
    ast.AsyncFor: "for",
    ast.While: "while",
    ast.With: "with",
    ast.AsyncWith: "with",
    ast.Try: "try",
    ast.TryStar: "try",
    ast.FunctionDef: "def",
    ast.AsyncFunctionDef: "def",
    ast.ClassDef: "class",
    ast.Raise: "raise",
    ast.Return: "return",
    ast.Assign: "=",
    ast.AugAssign: "=",
    ast.AnnAssign: "=",
}


def of(source, path):
    """{def site: [Statement, ...]} for each function in source, in source
    order. Example: def f(): x = 1; return x gives = and return rows."""
    return {site: rows for site, (_, rows) in _collect(source, path).items()}


def names(source, path):
    """{def site: its name} for each function in source, eg {"k.py:4:4":
    "ship"}, each its card's title."""
    return {site: node.name for site, (node, _) in _collect(source, path).items()}


def lasts(source, path):
    """{def site: its last line} for each function in source, eg
    {"k.py:4:4": 6}, where its card ends."""
    return {site: node.end_lineno for site, (node, _) in _collect(source, path).items()}


def reaches(source, path):
    """The names of every row that is no site, in every function in source,
    in source order, eg ["k.py:3:4"]: where a call can count the runs of its
    statement, which starts there."""
    return [row.name for rows in of(source, path).values() for row in rows if row.site is None]


def totals(source, path, paths, reached):
    """{def site: [taken, size]} of each function's card in source, its
    rows' taken as taken gives them from paths and reached; a row not known
    counts as not taken, never more than it ran. Example: {"k.py:1:0": [2,
    4]}, 2 of ship's 4 paths taken."""
    return {
        site: [sum(count or 0 for count in taken(rows, paths, reached)), size(rows)]
        for site, rows in of(source, path).items()
    }


def cards(files, paths, reached):
    """{def site: [taken, size]} of every function's card in files,
    {path relative to root: (source, sites)}, as totals gives them.
    Example: {"k.py:1:0": [2, 4], "k.py:9:0": [3, 3]}."""
    return {
        site: card
        for path, (source, _) in files.items()
        for site, card in totals(source, path, paths, reached).items()
    }


def size(rows):
    """The paths a function's tests are to take: its rows' paths added up,
    each row's taken on its own. Example: rows of 1, 2 and 2 paths give 5."""
    return sum(row.paths for row in rows)


def complexity(rows):
    """The paths through a function as a whole: its rows' paths multiplied,
    each path of one row going on to each of the next. Example: rows of 1,
    2 and 2 paths give 4."""
    product = 1
    for row in rows:
        product *= row.paths
    return product


def taken(rows, paths, reached=None):
    """How many paths of each row were taken: for a site's row, its paths
    with a count, paths being as result.paths gives them; for any other
    row, its 1 path when reached has a count for it, 0 when not, None, not
    known, without reached. Example: an if row with only its then taken
    gives 1."""
    return [
        _taken_site(row, paths) if row.site else None if reached is None else int(row.name in reached)
        for row in rows
    ]


def _taken_site(row, paths):
    """How many of a site row's paths have a count in paths."""
    return sum(1 for each in paths[row.site] if each["count"] > 0)


def _collect(source, path):
    """{def site: (def node, rows)} for each function in source, in source
    order."""
    tree = ast.parse(source)
    finder = _Rows(path, sites(source, path), builtin_blocks(tree))
    found = {
        f"{path}:{node.lineno}:{node.col_offset}": (node, finder.rows(node))
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return dict(sorted(found.items(), key=lambda item: (item[1][0].lineno, item[1][0].col_offset)))


def body_of(function):
    """The statements of function's body that run, its docstring left out,
    as Python runs no code for it."""
    body = function.body
    first = body[0]
    docstring = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
    return body[1:] if docstring and isinstance(first.value.value, str) else body


class _Rows:
    """Finds the rows of a function's top-level statements."""

    def __init__(self, path, found, builtins):
        """Names rows after path; found is decision mode's {site:
        Condition}, and builtins the block calls' names the module leaves
        as builtins."""
        self.path = path
        self.found = found
        self.builtins = builtins

    def rows(self, function):
        """The Statement rows of function's body: one per outermost site in
        each statement, or the statement itself when it holds none."""
        return [self._row(top) for statement in body_of(function) for top in self._tops(statement)]

    def _tops(self, statement):
        """The nodes statement's rows are for: the outermost sites in it, in
        the order they run, as what holds them is looked through; statement
        itself when it holds none. Example: x = (1 if a else 2) + (3 if b
        else 4) gives both ternaries."""
        return self._sites_in(statement) or [statement]

    def _sites_in(self, node):
        """[node] when it is a site, else the outermost sites in the parts
        of it looked through, in order; none in a scope of its own."""
        if self._site_of(node):
            return [node]
        if isinstance(node, SCOPES):
            return []
        return [site for child in _looked_through(node) for site in self._sites_in(child)]

    def _site_of(self, node):
        """The name of decision mode's site that node is, eg "k.py:2:4" for
        an if statement there; None when node is no site."""
        if isinstance(node, (ast.BoolOp, ast.IfExp, ast.If, ast.Match)) or (
            isinstance(node, ast.Call) and block_generator(node, self.builtins)
        ):
            name = f"{self.path}:{node.lineno}:{node.col_offset}"
            return name if name in self.found else None
        return None

    def _row(self, node):
        """The Statement row of node, where it starts: a site with as many
        paths as decision mode gives it, anything else with 1."""
        site = self._site_of(node)
        top = self.found[site].operator if site else _top(node)
        paths = len(site_paths.possible(self.found[site])) if site else 1
        name = f"{self.path}:{node.lineno}:{node.col_offset}"
        return Statement(node.lineno, node.col_offset, top, paths, site, name)


def _looked_through(node):
    """The parts of node that run once each time node does: for a loop, its
    header alone, its body running once per item; for a try, all but its
    handlers, which run only when it raises; for anything else, all of
    it."""
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return [node.target, node.iter]
    if isinstance(node, ast.While):
        return [node.test]
    if isinstance(node, (ast.Try, ast.TryStar)):
        return node.body + node.orelse + node.finalbody
    return list(ast.iter_child_nodes(node))


def _top(statement):
    """What a statement that is no site is as written: its keyword's, eg
    for, or = for a write, () for a call, value for anything else."""
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return "()"
    return KEYWORDS.get(type(statement), "value")

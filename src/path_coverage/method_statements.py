"""Finds, without running it, the statements of each function in source, one
row each in its card, and the sites outside every function, each a row of a
top card."""

import ast
from dataclasses import dataclass

from . import site_paths
from . import totals as path_totals
from .manifest import (
    Arm,
    block_generator,
    builtin_blocks,
    if_keywords,
    keyword_before,
    operator_keywords,
    site_at,
    sites,
)


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


# The nodes a statement's sites are never looked for in: a function's body
# runs only when it is called, its sites rows of its own card, and a
# lambda's and a comprehension's parts give rows of their own, after the
# statement holding them.
UNSEEN = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
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


# The tops of the statements that are no site yet are rows: each leaves its
# function, so cuts a path short.
LEAVING = ("return", "raise")


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
    """The names of where runs are counted, in every function in source, in
    source order: each function's entry, by its def's site, so its calls are
    counted, then each of its rows that is no site, where its statement
    starts, eg ["k.py:2:0", "k.py:3:4"]."""
    return [
        name
        for site, rows in of(source, path).items()
        for name in [site, *(row.name for row in rows if row.site is None)]
    ]


def top_rows(source, path):
    """A Statement row for each site in source on no function's card,
    outside every function, for the card of its own lines, in the order
    written: its operator, an elif's elif, and its paths. Example: RATE = 2
    if FAST else 1 gives a ternary row at 1:7."""
    found = sites(source, path)
    carded = {row.site for rows in of(source, path).values() for row in rows}
    lines = source.splitlines()
    rows = [_top_row(lines, name, found[name]) for name in found if name not in carded]
    return sorted(rows, key=lambda row: (row.line, row.column))


def _top_row(lines, name, condition):
    """The Statement row of the site named name, its Condition condition,
    outside every function of the source of lines."""
    line, column = (int(part) for part in name.rsplit(":", 2)[1:])
    top = _top_of_site(lines, line, column, condition)
    paths = len(site_paths.possible(condition))
    return Statement(line, column, top, paths, name, name)


def top_level(source, path, paths):
    """[taken, possible] of the paths of the sites in source on no
    function's card, as top_rows gives them; paths as result.paths gives
    them. Example: RATE = 2 if FAST else 1, its then taken, gives [1, 2]."""
    names = [row.site for row in top_rows(source, path)]
    return path_totals.decisions({name: paths[name] for name in names})


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
    {path relative to root: (source, sites)}, as totals gives them, and each
    file's top level's, as top_level gives it, named for line 0, which no
    function is on. Example: {"k.py:1:0": [2, 4], "k.py:0:0": [1, 2]}."""
    found = {}
    for path, (source, _) in files.items():
        found.update(totals(source, path, paths, reached))
        found[f"{path}:0:0"] = top_level(source, path, paths)
    return found


def label(statement):
    """statement's line:column as its card shows it, the column two digits,
    so a card's columns line up. Example: "3:04"."""
    return f"{statement.line}:{statement.column:02d}"


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
    finder = _Rows(path, source, sites(source, path), tree)
    found = {
        f"{path}:{node.lineno}:{node.col_offset}": (node, finder.rows(node))
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return dict(sorted(found.items(), key=lambda item: (item[1][0].lineno, item[1][0].col_offset)))


def body_of(node):
    """The statements of node's body that run, a function's or a class's,
    its docstring left out, as Python runs no code for it."""
    body = node.body
    first = body[0]
    docstring = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
    return body[1:] if docstring and isinstance(first.value.value, str) else body


def _top_of_site(lines, line, column, condition):
    """The top of the site named at line and column, a UTF-8 byte column,
    in lines, its Condition condition: its operator, but for an if
    statement its keyword, if or elif, then /else when it has an else arm
    that is no elif, eg if/else."""
    if condition.operator != "if":
        return condition.operator
    own = "elif" if _written_at(lines, line, column).startswith(b"elif") else "if"
    arms = [operand for operand in condition.operands if isinstance(operand, Arm) and operand.kind == "else"]
    if arms and not _written_at(lines, *arms[0].extent[:2]).startswith(b"elif"):
        return f"{own}/else"
    return own


def _written_at(lines, line, column):
    """The bytes of line of lines from column, a UTF-8 byte column, on."""
    return lines[line - 1].encode()[column:]


@dataclass(frozen=True)
class _Filter:
    """A comprehension's filter as a node of its own: where its if keyword
    is, which names its site, and its test."""

    lineno: int
    col_offset: int
    test: ast.expr


class _Rows:
    """Finds the rows of a function's statements."""

    def __init__(self, path, source, found, tree):
        """Names rows after path; found is the {site: Condition} of source,
        and tree its parse."""
        self.path = path
        self.found = found
        self.builtins = builtin_blocks(tree)
        self.keywords = if_keywords(source)
        self.operators = operator_keywords(source)
        self.lines = source.splitlines()

    def rows(self, function):
        """The Statement rows of function's body that shape a path, flat, in
        the order written: each site's, and each return's and raise's, as
        each cuts a path short; no row for any other statement, whose one
        path tells the reader nothing."""
        rows = [self._row(node) for node in self._rows_in(body_of(function))]
        return [row for row in rows if row.site or row.top in LEAVING]

    def _rows_in(self, statements):
        """The nodes statements' rows are for, flat, in the order written:
        each statement's tops, each followed by the sites of their own
        inside it, then the rows of its arms' statements; then the rows of
        the statement's bodies. Example: if a: x = 1 gives the if, then the
        write."""
        nodes = []
        for statement in statements:
            for top in self._sites_in(statement) or [statement]:
                named = sorted([top, *self._inner_sites(top)], key=self._at)
                nodes += [*named, *self._rows_in(_arms_of(top))]
            nodes += self._body_rows(statement)
        return nodes

    def _sites_in(self, node):
        """[node] when it is a site, else the outermost sites in its heads,
        in order; none in a node UNSEEN holds. Example: x = (1 if a else 2)
        + (3 if b else 4) gives both ternaries."""
        if self._site_of(node):
            return [node]
        if isinstance(node, UNSEEN):
            return []
        return [site for head in self._heads(node) for site in self._sites_in(head)]

    def _inner_sites(self, site):
        """The sites inside site that are sites of their own, in the order
        written: in its heads, not its arms nor its bodies, which have rows
        of their own. A node named as site is, eg a ternary's then arm when
        it is a call, is site itself, so it is left out. None for a top that
        is no site. Example: valid(a if x else b) and ok gives the
        ternary."""
        if not self._site_of(site):
            return []
        named = {}
        for head in self._heads(site):
            for node in self._sites_within(head):
                named.setdefault(self._name(node), node)
        named.pop(self._name(site), None)
        return list(named.values())

    def _sites_within(self, node):
        """node when it is a site, then each site within its heads, in
        order; none in a node UNSEEN holds."""
        if isinstance(node, UNSEEN):
            return []
        own = [node] if self._site_of(node) else []
        return own + [site for head in self._heads(node) for site in self._sites_within(head)]

    def _body_rows(self, node):
        """The rows of the bodies in node, each as _bodies_in gives it: a
        list of statements' rows, or the site rows of a lambda's or a
        comprehension's parts."""
        rows = []
        for statements, parts in self._bodies_in(node):
            rows += self._rows_in(statements) if parts is None else self._part_rows(parts)
        return rows

    def _bodies_in(self, node):
        """(statements, None) for each body of statements in node, run 0 or
        more times or on a raise: a loop's, a with's, a class's, and a
        try's parts; (None, node) for each lambda and comprehension; none in
        a function, whose rows are its own card's, nor in an arm, whose
        rows follow its site's."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return []
        if isinstance(node, UNSEEN):
            return [(None, node)]
        inner = [body for head in self._heads(node) for body in self._bodies_in(head)]
        own = _statements_of(node)
        return inner + ([(own, None)] if own else [])

    def _part_rows(self, node):
        """The nodes of the rows of node's parts, a lambda's or a
        comprehension's: each site in them, then those of the lambdas and
        comprehensions inside them."""
        heads = self._heads(node)
        sites_in = [site for head in heads for site in self._sites_within(head)]
        return sites_in + [row for head in heads for row in self._body_rows(head)]

    def _heads(self, node):
        """node's children outside its arms and its bodies of statements:
        an if's and a while's test, a match's subject and guards, a for's
        target and items, a with's items, none of a try, a class's
        decorators and bases, a comprehension's target, items and filters;
        all of them for any other node."""
        if isinstance(node, (ast.If, ast.While)):
            return [node.test]
        if isinstance(node, ast.Match):
            return [node.subject, *(case.guard for case in node.cases if case.guard)]
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return [node.target, node.iter]
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return list(node.items)
        if isinstance(node, (ast.Try, ast.TryStar)):
            return []
        if isinstance(node, ast.ClassDef):
            return [*node.decorator_list, *node.bases, *node.keywords]
        if isinstance(node, ast.comprehension):
            return [node.target, node.iter, *(self._filter(test) for test in node.ifs)]
        if isinstance(node, _Filter):
            return [node.test]
        return list(ast.iter_child_nodes(node))

    def _filter(self, test):
        """The _Filter of a comprehension filter's test, at its if
        keyword."""
        line, column = keyword_before(self.keywords, test)
        return _Filter(line, column, test)

    def _site_of(self, node):
        """The name of the site that node is, eg "k.py:2:4" for an if
        statement there; None when node is no site."""
        kinds = (_Filter, ast.BoolOp, ast.IfExp, ast.If, ast.Match)
        if isinstance(node, kinds) or (isinstance(node, ast.Call) and block_generator(node, self.builtins)):
            name = self._name(node)
            return name if name in self.found else None
        return None

    def _name(self, node):
        """The name of where node is, as _at places it, eg "k.py:2:4"."""
        line, column = self._at(node)
        return f"{self.path}:{line}:{column}"

    def _at(self, node):
        """(line, column) of node's row: where its site is named, as
        site_at says, an and or an or at its keyword, a conditional
        expression at its if; where any other node starts."""
        return site_at(self.operators, node) if isinstance(node, (ast.BoolOp, ast.IfExp)) else (
            node.lineno,
            node.col_offset,
        )

    def _row(self, node):
        """The Statement row of node, where it starts: a site with as many
        paths as its Condition has, its top its operator, an elif's elif;
        anything else with 1."""
        site = self._site_of(node)
        name = self._name(node)
        line, column = self._at(node)
        if site is None:
            return Statement(line, column, _top(node), 1, None, name)
        condition = self.found[site]
        top = _top_of_site(self.lines, line, column, condition)
        paths = len(site_paths.possible(condition))
        return Statement(line, column, top, paths, site, name)


def _arms_of(node):
    """The statements of node's arms, in order: an if's then's, then its
    else's, an elif being a statement of it; each of a match's cases' in
    turn; none for any other node."""
    if isinstance(node, ast.If):
        return node.body + node.orelse
    if isinstance(node, ast.Match):
        return [statement for case in node.cases for statement in case.body]
    return []


def _statements_of(node):
    """The statements of node's bodies, in order: a loop's body, then its
    else's; a with's; a class's, its docstring left out; a try's body, each
    handler's, its else's and its finally's; none for any other node."""
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        return node.body + node.orelse
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return node.body
    if isinstance(node, ast.ClassDef):
        return body_of(node)
    if isinstance(node, (ast.Try, ast.TryStar)):
        handled = [statement for handler in node.handlers for statement in handler.body]
        return node.body + handled + node.orelse + node.finalbody
    return []


def _top(statement):
    """What a statement that is no site is as written: its keyword's, eg
    for, or = for a write, () for a call, value for anything else."""
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return "()"
    return KEYWORDS.get(type(statement), "value")

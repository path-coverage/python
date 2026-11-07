"""Generates small Python functions from a grammar of the statements that
decide a function's paths or leave it, each written in a form path_coverage
measures: and, or, not, conditional expressions, walrus, lambda, f-strings,
starred items, chained comparisons, comprehension filters, any and all, if,
elif and else, and match with guards, wildcards, or-patterns and captures.

Each leaf is a spy, a call of a fresh parameter, eg p0(), which the oracle
passes a callable logging its call and giving its value; or a fresh
parameter read as a name, eg p1; or a literal, eg 0, as path_coverage
treats a name and a literal apart from a call. Every statement of run is
preceded by a call of its mark parameter, mark(n, t), which logs that
statement n is about to run with t's value, so the trace of a call is the
path it took. Calling a function on every combination of its parameters'
values takes every path it has. Seeded, so a seed always gives the same
function: the kind of each leaf is drawn from random numbers of its own, so
a seed's statements are those it gave before leaves had kinds."""

import ast
import random
import re
import textwrap

# The statements that leave the function.
LEAVES = ["return t", "raise Stop"]

# The predicates of an if or an elif.
CONDITIONS = {
    "leaf": "<leaf>",
    "and": "<leaf> and <leaf>",
    "or": "<leaf> or <leaf>",
    "not": "not (<leaf> and <leaf>)",
    "walrus": "(w := <leaf>) or <leaf>",
    "ternary": "<leaf> if <leaf> else <leaf>",
}

# The statements that hold no body, for any level.
FLAT = {
    "plain": "t += 1",
    "guarded": "if <leaf>: <leave>",
    "ternary": "t += 1 if <leaf> else 2",
    "values": "t += (<leaf> and 2) or 3",
    "walrus": "t += (w := <leaf>) or <leaf>",
    "lambda": "t += (lambda: <leaf> or <leaf>)()",
    "fstring": 't += len(f"{<leaf> or <leaf>}")',
    "starred": "t += len([*([1] if <leaf> else []), *((<leaf> or ()) and [2])])",
    "chained": "t += (0 < t < 3) or <leaf>",
    "filter": "t += len([u for u in (<leaf>, <leaf>) if u and <leaf>])",
    "any": "t += any(u for u in (<leaf>, <leaf>))",
    "all": "t += all(u or <leaf> for u in (<leaf>,))",
}

# The statements that hold bodies of their own, for the top level only, so a
# function nests at most one deep.
NESTING = {
    "if": "if <cond>:\n    <body>\nelse:\n    <body>",
    "elif": "if <cond>:\n    <body>\nelif <cond>:\n    <body>",
    "guard": "match <leaf>:\n    case True if <leaf>:\n        <body>\n    case False:\n        <body>",
    "wildcard": "match <leaf>:\n    case True:\n        <body>\n    case _:\n        <body>",
    "either": "match <leaf>:\n    case True:\n        <body>\n    case 2 | _:\n        <body>",
    "guarded wildcard": "match <leaf>:\n    case False:\n        <body>\n    case _ if <leaf>:\n        <body>",
    "capture": "match <leaf>:\n    case False:\n        <body>\n    case (s as w):\n        <body>",
}

# A body's one statement: flat, or one that leaves, which ends the body, so
# no code follows it.
BODY = {**FLAT, "leave": "<leave>"}

# The kinds of leaf, a spy twice as often as each other kind.
KINDS = ("spy", "spy", "name", "literal")

# The literals a leaf can be, each a number, so t stays one.
LITERALS = ("True", "False", "0", "1")

# A piece of a template, filled by the method of its name.
PIECE = re.compile(r"<(leaf|leave|cond|body)>")


class FunctionGrammar:
    """The function of one seed. Example: FunctionGrammar(7).source(), the
    function of seed 7. Once its source is made, leaves is how many
    parameters run has before mark, and spies which of them are called."""

    def __init__(self, seed):
        """A grammar drawing from seed's random numbers, with no leaves yet."""
        self.random = random.Random(seed)
        self.kinds = random.Random(f"kinds of {seed}")
        self.leaves = 0
        self.spies = set()

    def source(self):
        """The source of a module holding Stop, the error its raises raise,
        and run, whose parameters are its leaves' then mark: two top-level
        statements between t = 0 and its return of t, each statement
        preceded by its mark."""
        top = {**FLAT, **NESTING}
        return _marked(self.snippet("\n".join(self.statement(top) for _ in range(2))))

    def snippet(self, body):
        """The module whose run's parameters are the leaves so far and mark,
        its body between t = 0 and return t."""
        params = ", ".join([*(f"p{index}" for index in range(self.leaves)), "mark"])
        indented = textwrap.indent(body, "    ")
        return f"class Stop(Exception):\n    pass\n\n\ndef run({params}):\n    t = 0\n{indented}\n    return t\n"

    def statement(self, kinds):
        """One statement, its kind drawn from kinds, its pieces filled left
        to right, so its leaves are numbered in the order written."""
        template = self.random.choice(list(kinds.values()))
        return PIECE.sub(lambda found: getattr(self, f"_{found[1]}")(), template)

    def _leaf(self):
        """A fresh leaf, its kind drawn: a call of the next parameter, the
        next parameter, or a literal."""
        return getattr(self, f"_{self.kinds.choice(KINDS)}")()

    def _spy(self):
        """A call of the next parameter, noted as a spy."""
        self.spies.add(self.leaves)
        return f"{self._name()}()"

    def _name(self):
        """The next parameter."""
        self.leaves += 1
        return f"p{self.leaves - 1}"

    def _literal(self):
        """A literal, drawn."""
        return self.kinds.choice(LITERALS)

    def _leave(self):
        """A statement that leaves the function."""
        return self.random.choice(LEAVES)

    def _cond(self):
        """A predicate of an if or an elif."""
        return self.statement(CONDITIONS)

    def _body(self):
        """The one statement of an arm or a case."""
        return self.statement(BODY)


def _marked(source):
    """source with each statement of run preceded by its mark, numbered in
    the order written: on a line of its own at the statement's indent, or,
    for a statement sharing its line, eg the body of if p0(): return t,
    before it on that line. The first, t = 0, comes before t is set, so its
    mark gives no t."""
    lines = source.splitlines(keepends=True)
    run = ast.parse(source).body[1]
    found = sorted(_statements(run.body, lines), key=lambda each: (each.lineno, each.col_offset))
    for number, statement in reversed(list(enumerate(found))):
        line = lines[statement.lineno - 1]
        indent = len(line) - len(line.lstrip())
        mark = f"mark({number}, t)" if number else "mark(0)"
        if statement.col_offset == indent:
            lines.insert(statement.lineno - 1, f"{' ' * indent}{mark}\n")
        else:
            lines[statement.lineno - 1] = f"{line[: statement.col_offset]}{mark}; {line[statement.col_offset :]}"
    return "".join(lines)


def _statements(body, lines):
    """Each statement in body, and in the bodies of each, at any depth, but
    an elif, which no statement can precede, though its bodies' can."""
    for statement in body:
        if not lines[statement.lineno - 1][statement.col_offset :].startswith("elif"):
            yield statement
        for part in (*getattr(statement, "body", []), *getattr(statement, "orelse", [])):
            yield from _statements([part], lines)
        for case in getattr(statement, "cases", []):
            yield from _statements(case.body, lines)

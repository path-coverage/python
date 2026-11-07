"""Generates small Python functions from a grammar of the statements that
decide a function's paths or leave it, each written in a form path_coverage
rewrites: and, or, not, conditional expressions, walrus, lambda, f-strings,
starred items, chained comparisons, comprehension filters, any and all, if,
elif and else, and match with guards, wildcards, or-patterns and captures.
Each leaf is a fresh boolean parameter, so calling a function on every
combination of its parameters takes every path it has. Seeded, so a seed
always gives the same function."""

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

# A piece of a template, filled by the method of its name.
PIECE = re.compile(r"<(leaf|leave|cond|body)>")


class FunctionGrammar:
    """The function of one seed. Example: FunctionGrammar(7).source(), the
    function of seed 7."""

    def __init__(self, seed):
        """A grammar drawing from seed's random numbers, with no leaves yet."""
        self.random = random.Random(seed)
        self.leaves = 0

    def source(self):
        """The source of a module holding Stop, the error its raises raise,
        and run, whose parameters are its leaves: two top-level statements
        between t = 0 and its return of t."""
        top = {**FLAT, **NESTING}
        return self.snippet("\n".join(self.statement(top) for _ in range(2)))

    def snippet(self, body):
        """The module whose run's parameters are the leaves so far, its
        body between t = 0 and return t."""
        params = ", ".join(f"p{index}" for index in range(self.leaves))
        indented = textwrap.indent(body, "    ")
        return f"class Stop(Exception):\n    pass\n\n\ndef run({params}):\n    t = 0\n{indented}\n    return t\n"

    def statement(self, kinds):
        """One statement, its kind drawn from kinds, its pieces filled left
        to right, so its leaves are numbered in the order written."""
        template = self.random.choice(list(kinds.values()))
        return PIECE.sub(lambda found: getattr(self, f"_{found[1]}")(), template)

    def _leaf(self):
        """A fresh leaf: the next parameter."""
        self.leaves += 1
        return f"p{self.leaves - 1}"

    def _leave(self):
        """A statement that leaves the function."""
        return self.random.choice(LEAVES)

    def _cond(self):
        """A predicate of an if or an elif."""
        return self.statement(CONDITIONS)

    def _body(self):
        """The one statement of an arm or a case."""
        return self.statement(BODY)

"""Wraps the last operand of every and/or, as manifest.wrapped decides, in a
call that counts its outcome and returns it unchanged:

    x = p or q
    # compiles as
    x = p or __path_coverage__(1, q)

No branch tests such an operand when the and/or's value is used, so its
outcome is counted here; every other leaf's comes from sys.monitoring's
branch events, one source per leaf. Each inserted node takes the location of
the operand it wraps, and nothing else in the tree changes."""

import ast
import sys

from .evaluations import Outcome
from .manifest import wrapped

# The name the inserted calls call, bound in each measured module.
NAME = "__path_coverage__"


class Lasts:
    """The outcomes the inserted calls count, logged on evaluations: actions,
    [(actions when false, actions when true), ...], by each call's key."""

    def __init__(self, evaluations):
        """Counts nothing yet, logging on evaluations."""
        self.evaluations = evaluations
        self.actions = []

    def key(self, leaves):
        """The key of a new call counting leaves, [(Shape, leaf index), ...],
        the leaves written where its operand is."""
        self.actions.append(tuple(tuple(Outcome(shape, index, truth) for shape, index in leaves) for truth in (False, True)))
        return len(self.actions) - 1

    def record(self, key, value):
        """Logs the outcome of the leaves of the call keyed key, value's
        truth, from the frame that called it; returns value unchanged."""
        self.evaluations.note(id(sys._getframe(1)), self.actions[key][bool(value)])
        return value


class _Wrapper(ast.NodeTransformer):
    """Wraps each and/or's last operand, inner and/ors first."""

    def __init__(self, source, lasts):
        """Wraps the operands of source, a code_map Source, keying each call
        on lasts."""
        self.source = source
        self.lasts = lasts

    def visit_BoolOp(self, node):
        """node, its operands' own and/ors wrapped first, its last operand
        wrapped when manifest.wrapped says so."""
        self.generic_visit(node)
        last = node.values[-1]
        if wrapped(last, node):
            at = (last.lineno, last.col_offset, last.end_lineno, last.end_col_offset)
            key = ast.Constant(self.lasts.key(self.source.leaves[at]))
            call = ast.Call(func=ast.Name(id=NAME, ctx=ast.Load()), args=[key, last], keywords=[])
            for part in (call, call.func, key):
                ast.copy_location(part, last)
            node.values[-1] = call
        return node


def rewrite(tree, source, lasts):
    """tree, the parse of source, a code_map Source, changed in place and
    returned, each and/or's last operand wrapped in a call keyed on lasts."""
    return _Wrapper(source, lasts).visit(tree)

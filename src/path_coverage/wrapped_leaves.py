"""Wraps each leaf manifest.wrapped names, in a call that counts its outcome
and returns it unchanged:

    x = p or q
    # compiles as
    x = p or __path_coverage__(1, q)

No branch tells such a leaf's outcome: the last operand of an and/or whose
value is used is tested by none, and Python compiles a literal, or a
conditional expression's literal arm, to no test. Every other leaf's
outcome comes from sys.monitoring's branch events, one source per leaf.
Each inserted node takes the location of the leaf it wraps, and nothing
else in the tree changes."""

import ast
import sys

from .evaluations import Outcome
from .manifest import wrapped

# The name the inserted calls call, bound in each measured module.
NAME = "__path_coverage__"


class Leaves:
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
    """Wraps each leaf manifest.wrapped names, the leaves inside it first."""

    def __init__(self, source, leaves):
        """Wraps the leaves of source, a code_map Source, keying each call
        on leaves."""
        self.source = source
        self.leaves = leaves

    def generic_visit(self, node):
        """node, the leaves inside its children wrapped first, then each
        child that is a leaf manifest.wrapped names."""
        super().generic_visit(node)
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                setattr(node, field, [self._wrapped(item, node) for item in value])
            else:
                setattr(node, field, self._wrapped(value, node))
        return node

    def _wrapped(self, child, parent):
        """child, held by parent, in a call counting its outcome when it is
        a leaf manifest.wrapped names; else child unchanged."""
        if not (isinstance(child, ast.expr) and wrapped(child, parent)):
            return child
        at = (child.lineno, child.col_offset, child.end_lineno, child.end_col_offset)
        if at not in self.source.leaves:
            return child
        key = ast.Constant(self.leaves.key(self.source.leaves[at]))
        call = ast.Call(func=ast.Name(id=NAME, ctx=ast.Load()), args=[key, child], keywords=[])
        for part in (call, call.func, key):
            ast.copy_location(part, child)
        return call


def rewrite(tree, source, leaves):
    """tree, the parse of source, a code_map Source, changed in place and
    returned, each leaf manifest.wrapped names wrapped in a call keyed on
    leaves."""
    return _Wrapper(source, leaves).visit(tree)

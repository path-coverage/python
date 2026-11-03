"""Rewrites a module's AST so each leaf operand of every site is passed
through a record call, which returns it unchanged:

    ok(id) and new(id)
    # compiles as
    __condition_coverage_record__("k.py:2:4", 0, ok(id)) and \\
        __condition_coverage_record__("k.py:2:4", 1, new(id))

Each record call takes the leaf's own location, so line numbers in
tracebacks and in line coverage are those of the file as written."""

import ast

RECORD_NAME = "__condition_coverage_record__"


class _Rewriter(ast.NodeTransformer):
    """Wraps the leaves of every site, numbering them as the manifest does."""

    def __init__(self, path):
        """Names sites after path."""
        self.path = path

    def visit_BoolOp(self, node):
        """node with each of its leaves, nested conditions' included, wrapped
        in a record call under this site."""
        site = f"{self.path}:{node.lineno}:{node.col_offset}"
        self._wrap(node, site, [0])
        return node

    def _wrap(self, node, site, counter):
        """Replaces node's operands in place, numbering leaves left to right
        with counter, a one-item list shared across the whole site."""
        node.values = [self._operand(value, site, counter) for value in node.values]

    def _operand(self, value, site, counter):
        """value with its leaves wrapped when it is a nested condition, else
        value (its own sites rewritten first) as the argument of a record."""
        if isinstance(value, ast.BoolOp):
            self._wrap(value, site, counter)
            return value
        value = self.visit(value)
        index = counter[0]
        counter[0] += 1
        call = ast.Call(
            func=ast.Name(id=RECORD_NAME, ctx=ast.Load()),
            args=[ast.Constant(site), ast.Constant(index), value],
            keywords=[],
        )
        for part in (call, call.func, *call.args[:2]):
            ast.copy_location(part, value)
        return call


def rewrite(tree, path):
    """tree, changed in place and returned, with every leaf of every site
    wrapped in a call to RECORD_NAME(site, index, value)."""
    return _Rewriter(path).visit(tree)

"""Rewrites a module's AST so each site's evaluation is entered and left
around it, and each of its leaf operands is passed through a record call,
which returns it unchanged:

    ok(id) and new(id)
    # compiles as
    __path_coverage__.leave(
        __path_coverage__.enter("k.py:2:4", 2),
        __path_coverage__.record("k.py:2:4", 0, ok(id)) and
        __path_coverage__.record("k.py:2:4", 1, new(id)))

Each inserted call takes the location of the code it wraps, so line numbers
in tracebacks and in line coverage are those of the file as written."""

import ast

from .path_manifest import decision_ifs, exits_of

RECORDER_NAME = "__path_coverage__"


def _call(method, args, at):
    """A call of the recorder's method with args, located at node at."""
    func = ast.Attribute(
        value=ast.Name(id=RECORDER_NAME, ctx=ast.Load()), attr=method, ctx=ast.Load()
    )
    call = ast.Call(func=func, args=args, keywords=[])
    for part in (call, func, func.value):
        ast.copy_location(part, at)
    for arg in args:
        if not hasattr(arg, "lineno"):
            ast.copy_location(arg, at)
    return call


PATH_NAME = "__path_coverage_path__"


class _Rewriter(ast.NodeTransformer):
    """Wraps every site, numbering its leaves as the manifest does, and,
    when methods are measured, every decision of each function whose paths
    are counted."""

    def __init__(self, path, methods):
        """Names sites after path; methods says whether functions' paths
        are measured."""
        self.path = path
        self.methods = methods

    def visit_FunctionDef(self, node):
        """node with its own sites rewritten and, when methods are measured
        and it has two or more decisions, each call's path started just
        before its first decision, each decision's predicate in a decide
        call, outside its site's leave."""
        ifs = decision_ifs(node) if self.methods else []
        exits = [exits_of(statement) for statement in ifs]
        self.generic_visit(node)
        if len(ifs) < 2:
            return node
        site = f"{self.path}:{node.lineno}:{node.col_offset}"
        for index, (statement, outcome) in enumerate(zip(ifs, exits)):
            path = ast.Name(id=PATH_NAME, ctx=ast.Load())
            args = [path, ast.Constant(index), statement.test, ast.Constant(outcome)]
            statement.test = _call("decide", args, statement.test)
        # The start takes the location of the first predicate alone: given
        # the whole if statement's, its span would cover the if's arms,
        # and a trace would report an arm's first line as run.
        at = ifs[0].test
        start = ast.Assign(
            targets=[ast.Name(id=PATH_NAME, ctx=ast.Store())],
            value=_call("path", [ast.Constant(site), ast.Constant(len(ifs))], at),
        )
        ast.copy_location(start, at)
        ast.copy_location(start.targets[0], at)
        node.body.insert(node.body.index(ifs[0]), start)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_BoolOp(self, node):
        """node, its leaves (nested conditions' and folded arms' included)
        each wrapped in a record call under this site, as the value of a
        leave call whose first argument enters the site before any leaf
        runs."""
        site = f"{self.path}:{node.lineno}:{node.col_offset}"
        counter = [0]
        self._fold(node, site, counter)
        enter = _call("enter", [ast.Constant(site), ast.Constant(counter[0])], node)
        return _call("leave", [enter, node], node)

    visit_IfExp = visit_BoolOp

    def visit_If(self, node):
        """node with only its predicate entered and left, its leaves
        recorded, since its path is decided there and its arms are
        statements that may return or raise; then its arms, an elif among
        them, rewritten as statements."""
        site = f"{self.path}:{node.lineno}:{node.col_offset}"
        counter = [0]
        test = node.test
        if isinstance(test, ast.BoolOp):
            self._fold(test, site, counter)
        else:
            test = self._operand(test, site, counter)
        enter = _call("enter", [ast.Constant(site), ast.Constant(counter[0])], node.test)
        node.test = _call("leave", [enter, test], node.test)
        node.body = [self.visit(statement) for statement in node.body]
        node.orelse = [self.visit(statement) for statement in node.orelse]
        return node

    def _fold(self, node, site, counter):
        """Wraps node's leaves in place, in the manifest's order: an
        `and`/`or`'s operands left to right; a conditional expression's
        predicate, then its then arm, then its else arm."""
        if isinstance(node, ast.IfExp):
            node.test = self._operand(node.test, site, counter)
            node.body = self._arm(node.body, site, counter)
            node.orelse = self._arm(node.orelse, site, counter)
        else:
            self._wrap(node, site, counter)

    def _arm(self, node, site, counter):
        """An arm folded into the site when it holds a condition, its leaves
        wrapped; any other arm with only its own sites rewritten."""
        if isinstance(node, (ast.BoolOp, ast.IfExp)):
            self._fold(node, site, counter)
            return node
        return self.visit(node)

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
        return _call("record", [ast.Constant(site), ast.Constant(index), value], value)


def rewrite(tree, path, methods=False):
    """tree, changed in place and returned, with every site entered and left
    around it and every leaf of it recorded, and, when methods is true,
    every decision of each function with two or more decided."""
    return _Rewriter(path, methods).visit(tree)

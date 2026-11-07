"""The reference rewrite: path_coverage's rewrite as of 4660fa2, the oracle the
differential property test checks sys.monitoring's measuring against. It
rewrites a module's AST so each decision's evaluation is entered and left
around it, and each of its leaf operands is passed through a record call,
which returns it unchanged:

    ok(id) and new(id)
    # compiles as
    __path_coverage_reference__.leave(
        __path_coverage_reference__.enter("k.py:2:4", 2),
        __path_coverage_reference__.record("k.py:2:4", 0, ok(id)) and
        __path_coverage_reference__.record("k.py:2:4", 1, new(id)))

Each inserted call takes the location of the code it wraps."""

import ast

from path_coverage.columns import Columns
from path_coverage.manifest import (
    block_generator,
    builtin_blocks,
    decision_at,
    if_keywords,
    keyword_before,
    matches_anything,
    operator_keywords,
)
from path_coverage.method_statements import reaches

RECORDER_NAME = "__path_coverage_reference__"

# The statements that define a function, whose calls are counted on entry.
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


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


def _unmatched_case(decision, patterns, at):
    """case _ if unmatched(decision, patterns): pass, located at node at: the
    case a match ends with to note that none of its cases was taken, its
    guard always false, so it is never taken itself."""
    wildcard = ast.MatchAs(pattern=None, name=None)
    body = ast.Pass()
    for part in (wildcard, body):
        ast.copy_location(part, at)
    guard = _call("unmatched", [ast.Constant(decision), ast.Constant(tuple(patterns))], at)
    return ast.match_case(pattern=wildcard, guard=guard, body=[body])


def _reach(name, statement):
    """A reach call of the statement named name, as a statement of its own,
    located at statement's start alone: given statement's whole span, a
    compound statement's, it would cover its body, and a trace would report
    the body's first line as run."""
    at = ast.Pass()
    at.lineno = at.end_lineno = statement.lineno
    at.col_offset = at.end_col_offset = statement.col_offset
    return ast.copy_location(ast.Expr(_call("reach", [ast.Constant(name)], at)), at)


class _Rewriter(ast.NodeTransformer):
    """Wraps every decision, numbering its leaves as the manifest does, and
    precedes each function statement in reaches with a reach call."""

    def __init__(self, path, columns, reaches, keywords, builtins, operators):
        """Names decisions after path, in the source's columns; reaches
        holds the names of the function statements whose runs are counted,
        as method_statements.reaches gives them; keywords are where the
        source's if keywords are, builtins the block calls' names the
        module leaves as builtins, and operators where its and, or and if
        keywords are, as operator_keywords gives them, so decisions are
        named as the manifest names them."""
        self.path = path
        self.columns = columns
        self.reaches = reaches
        self.keywords = keywords
        self.builtins = builtins
        self.operators = operators

    def reach_all(self, tree):
        """tree with each statement in reaches, in any list of statements,
        a body, an else or a finally, preceded by a reach call naming it,
        and each function in reaches entered with one, so its calls are
        counted. Run once every decision is rewritten, as a match's rewrite adds
        a statement before it."""
        for node in list(ast.walk(tree)):
            for field in ("body", "orelse", "finalbody"):
                statements = getattr(node, field, None)
                if isinstance(statements, list):
                    setattr(node, field, [part for statement in statements for part in self._reached(statement)])
            if isinstance(node, FUNCTIONS):
                self._entered(node)
        return tree

    def _reached(self, statement):
        """[statement], preceded by its reach call when it is in reaches;
        a def is counted on entry, not where it is defined."""
        name = self.columns.name(self.path, statement.lineno, statement.col_offset)
        if isinstance(statement, FUNCTIONS) or name not in self.reaches:
            return [statement]
        return [_reach(name, statement), statement]

    def _entered(self, function):
        """function with a reach call naming it, by its def's decision, which
        reaches always holds, first in its body, as the generated functions
        have no docstring. Each call is counted."""
        name = self.columns.name(self.path, function.lineno, function.col_offset)
        function.body = [_reach(name, function.body[0]), *function.body]

    def visit_BoolOp(self, node):
        """node, its leaves (nested conditions' and folded arms' included)
        each wrapped in a record call under this decision, as the value of a
        leave call whose first argument enters the decision before any leaf
        runs. It is named where decision_at says, as the manifest names it."""
        line, col = decision_at(self.operators, node)
        decision = self.columns.name(self.path, line, col)
        counter = [0]
        self._fold(node, decision, counter)
        enter = _call("enter", [ast.Constant(decision), ast.Constant(counter[0])], node)
        return _call("leave", [enter, node], node)

    visit_IfExp = visit_BoolOp

    def visit_If(self, node):
        """node with only its predicate entered and left, its leaves
        recorded, since its path is decided there and its arms are
        statements that may return or raise; then its arms, an elif among
        them, rewritten as statements."""
        node.test = self._predicate(node.test, (node.lineno, node.col_offset))
        node.body = [self.visit(statement) for statement in node.body]
        node.orelse = [self.visit(statement) for statement in node.orelse]
        return node

    def visit_Call(self, node):
        """A block call, eg any(o.late for o in orders), with its
        generator's own decisions rewritten and its element in an answer call,
        as the value of a leave_items call whose first argument enters the
        decision before the builtin runs. Any other call with only its own
        decisions rewritten."""
        generator = block_generator(node, self.builtins)
        if generator is None:
            return self.generic_visit(node)
        decision = self.columns.name(self.path, node.lineno, node.col_offset)
        self.visit(generator)
        args = [ast.Constant(decision), ast.Constant(0), generator.elt]
        generator.elt = _call("answer", args, generator.elt)
        enter = _call("enter", [ast.Constant(decision), ast.Constant(2)], node)
        return _call("leave_items", [enter, ast.Constant(0), node], node)

    def visit_Match(self, node):
        """node, preceded by an enter of its decision, each case's guard (one
        added where there was none) in a matched call noting its pattern
        matched, numbering leaves as the manifest does: each case's
        pattern, then its guard's. Unless the last case matches anything, as
        manifest.matches_anything decides before any guard is added, a case
        is added after it whose guard notes that none matched. The added code
        takes the subject's location. Every case is guarded, as the
        generated functions never hold a case before the last that matches
        anything, which Python refuses."""
        decision = self.columns.name(self.path, node.lineno, node.col_offset)
        node.subject = self.visit(node.subject)
        last = node.cases[-1]
        open_ended = not matches_anything(last)
        counter = [0]
        patterns = []
        for case in node.cases:
            pattern = counter[0]
            counter[0] += 1
            args = [ast.Constant(decision), ast.Constant(pattern), ast.Constant(tuple(patterns))]
            if case.guard is not None:
                args.append(self._leaf(case.guard, decision, counter))
            case.guard = _call("matched", args, case.pattern)
            patterns.append(pattern)
            case.body = [self.visit(statement) for statement in case.body]
        if open_ended:
            node.cases.append(_unmatched_case(decision, patterns, node.subject))
        enter = ast.Expr(_call("enter", [ast.Constant(decision), ast.Constant(counter[0])], node.subject))
        ast.copy_location(enter, node.subject)
        return [enter, node]

    def visit_comprehension(self, node):
        """node with each filter's test entered and left, its leaves
        recorded, under a decision named at the filter's if keyword, as the
        manifest names it."""
        node.target = self.visit(node.target)
        node.iter = self.visit(node.iter)
        node.ifs = [self._predicate(test, keyword_before(self.keywords, test)) for test in node.ifs]
        return node

    def _predicate(self, test, at):
        """test, an if's or a filter's, recorded as one leaf under the decision
        named at at, (line, col), as the value of a leave call whose first
        argument enters the decision before the leaf runs; an `and`/`or` that is
        the whole test is a decision of its own."""
        decision = self.columns.name(self.path, *at)
        counter = [0]
        wrapped = self._leaf(test, decision, counter)
        enter = _call("enter", [ast.Constant(decision), ast.Constant(counter[0])], test)
        return _call("leave", [enter, wrapped], test)

    def _fold(self, node, decision, counter):
        """Wraps node's leaves in place, in the manifest's order: an
        `and`/`or`'s operands left to right; a conditional expression's
        predicate, one leaf, its arms with only their own decisions
        rewritten, as the generated functions fold no `and`/`or` into an
        arm."""
        if isinstance(node, ast.IfExp):
            node.test = self._leaf(node.test, decision, counter)
            node.body = self.visit(node.body)
            node.orelse = self.visit(node.orelse)
        else:
            self._wrap(node, decision, counter)

    def _wrap(self, node, decision, counter):
        """Replaces node's operands in place, numbering leaves left to right
        with counter, a one-item list shared across the whole decision."""
        node.values = [self._operand(value, decision, counter) for value in node.values]

    def _operand(self, value, decision, counter):
        """value with its leaves wrapped when it is a nested condition, else
        value (its own decisions rewritten first) as the argument of a record."""
        if isinstance(value, ast.BoolOp):
            self._wrap(value, decision, counter)
            return value
        return self._leaf(value, decision, counter)

    def _leaf(self, value, decision, counter):
        """value, its own decisions rewritten first, value itself among them, as
        the argument of a record of the next leaf of decision."""
        value = self.visit(value)
        index = counter[0]
        counter[0] += 1
        return _call("record", [ast.Constant(decision), ast.Constant(index), value], value)


def rewrite(tree, path, *, source):
    """tree, changed in place and returned, with every decision entered and
    left around it and every leaf of it recorded, and each run of every
    function statement that is no decision counted. source is tree's
    source, where the if keywords that name filters' decisions are found."""
    reached = set(reaches(source, path))
    operators = operator_keywords(source)
    rewriter = _Rewriter(path, Columns(source), reached, if_keywords(source), builtin_blocks(tree), operators)
    return rewriter.reach_all(rewriter.visit(tree))

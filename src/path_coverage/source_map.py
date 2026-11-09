"""Maps a covered file's source, parsed once, to what measuring it needs,
whichever mode gives its events: its decisions' Shapes, by name; by where
each is written, the leaves whose outcomes count, the block calls, the
matches, the counted statements, the for loops and the whiles' tests; the
loops holding each row; the decisions each while's test repeats; and each
function's entry. Nothing here knows about bytecode: code_map maps code
objects onto these facts, and a rewrite wraps the nodes they name."""

import ast

from . import decision_paths, manifest, method_statements, scopes
from .columns import Columns
from .evaluations import Shape

# The nodes Python compiles to a code object of their own.
SCOPES = method_statements.OWN_FRAMES

# The name Python gives the code object of a scope with no name of its own.
SCOPE_NAMES = {ast.Lambda: "<lambda>", ast.GeneratorExp: "<genexpr>"}


class Source:
    """A covered file, parsed once, with what measuring its code needs: its
    decisions' Shapes, by name, and, by where each is written, the leaves
    whose outcomes count, the block calls, the matches and the statements
    whose runs are counted. loops is {row name: the names of the loops
    holding it, outermost first}, a for's, a while's or an inlined
    comprehension generator's; whiles {span of a while's test: its loop's
    name}; and repeats {decision name: the name of the while whose test
    holds it}, as it runs again with each test."""

    def __init__(self, source, path, kept):
        """source, the text of the file path, as decisions name it, kept
        the line numbers measured, eg scopes.whole(source): a decision on
        no kept line has no shape and no leaf, so none is wrapped."""
        self.kept = kept
        tree, conditions, nodes = manifest.found(source, path)
        conditions = {name: condition for name, condition in conditions.items() if scopes.line(name) in kept}
        columns = Columns(source)
        self.tree = tree
        self.parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        self.spans = {span(node): node for node in ast.walk(tree) if isinstance(node, (ast.expr, ast.stmt, ast.pattern))}
        self.shapes = {name: Shape(name, decision_paths.possible(condition)) for name, condition in conditions.items()}
        self.leaves = {}
        self.blocks = {}
        self.matches = []
        for name, condition in conditions.items():
            self._note(self.shapes[name], condition, nodes[name])
        self._name_rows(source, path, columns)
        self._name_loops(source, path, columns, {name: nodes[name] for name in conditions})

    def _name_rows(self, source, path, columns):
        """Notes, of source, the text of the file path, its columns
        counted by columns: each code object's node, by (name, first
        line); each function's entry's name; and each return or raise
        whose runs are counted, with its name."""
        tree = self.tree
        reaches = set(method_statements.reaches(source, path))
        self.scopes = {(getattr(node, "name", SCOPE_NAMES.get(type(node))), first_line(node)): node for node in ast.walk(tree) if isinstance(node, SCOPES)}
        self.entries = {
            (node.name, first_line(node)): columns.name(path, node.lineno, node.col_offset)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.statements = [
            (node, name)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Return, ast.Raise))
            if (name := columns.name(path, node.lineno, node.col_offset)) in reaches
        ]

    def _name_loops(self, source, path, columns, decisions):
        """Notes, of source, the text of the file path, its columns
        counted by columns, and decisions, {name: node} of its kept ones:
        each for's iterable and each while's test, by where it is written,
        with its loop's name; the loops holding each decision, counted
        statement and loop; and the while whose test holds each decision."""
        kept = self.kept
        self._loop_names = {
            node: columns.name(path, *place) for node, place in manifest.loop_places(source, self.tree).items() if place[0] in kept
        }
        whiles = {node: columns.name(path, node.lineno, node.col_offset) for node in ast.walk(self.tree) if isinstance(node, ast.While)}
        whiles = {node: name for node, name in whiles.items() if node.lineno in kept}
        self.fors = {span(node.iter): name for node, name in self._loop_names.items()}
        self.whiles = {span(node.test): name for node, name in whiles.items()}
        self._loop_names.update(whiles)
        held = [*((node, name) for name, node in decisions.items()), *self.statements, *self._loop_names.items()]
        self.loops = {name: self._holding(node) for node, name in held}
        tested = {name: self._tested_by(node) for name, node in decisions.items()}
        self.repeats = {name: whiles[loop] for name, loop in tested.items() if loop is not None}

    def _note(self, shape, condition, node):
        """Notes the decision of shape, its Condition condition and its node
        node: a block call by its builtin's name; else each of its leaves
        but a match's patterns, which no branch's outcome tells, by where
        it is written."""
        if condition.operator in manifest.BLOCK_CALLS:
            self.blocks[span(node.func)] = shape
            return
        patterns = ()
        if isinstance(node, ast.Match):
            self.matches.append((node, shape, case_leaves(node)))
            patterns = {pattern for pattern, _ in case_leaves(node)}
        for index, leaf in enumerate(condition.leaves()):
            if index not in patterns:
                self.leaves.setdefault((leaf.line, leaf.col, leaf.end_line, leaf.end_col), []).append((shape, index))

    def _holding(self, node):
        """The names of the loops each pass of which runs node again, in
        its own scope, outermost first: a for whose body holds it, not its
        iterable or its else, which run once; a comprehension's generators
        up to the one whose filter or target holds it, or before the one
        whose iterable holds it, or all of them for its element."""
        holding = []
        # A generator runs again as its iterable does.
        child, parent = (node.iter, node) if isinstance(node, ast.comprehension) else (node, self.parents.get(node))
        while parent is not None and not isinstance(parent, SCOPES):
            holding += reversed(self._repeating(child, parent))
            child, parent = parent, self.parents.get(parent)
        return tuple(reversed(holding))

    def _tested_by(self, node):
        """The while, in node's own scope, whose test holds node, so node
        runs again with each test; None when no while's test holds it."""
        child, parent = node, self.parents.get(node)
        while parent is not None and not isinstance(parent, SCOPES):
            if isinstance(parent, ast.While) and child is parent.test:
                return parent
            child, parent = parent, self.parents.get(parent)
        return None

    def _repeating(self, child, parent):
        """The names, outermost first, of the loops of parent each pass of
        which runs child, a node right inside it, again."""
        if isinstance(parent, (ast.For, ast.While)):
            return [self._loop_names[parent]] if parent in self._loop_names and child in parent.body else []
        if isinstance(parent, ast.comprehension) and isinstance(self.parents[parent], manifest.INLINED):
            generators = self.parents[parent].generators
            upto = generators.index(parent) + (child is not parent.iter)
            return [self._loop_names[each] for each in generators[:upto]]
        if isinstance(parent, manifest.INLINED) and not isinstance(child, ast.comprehension):
            return [self._loop_names[each] for each in parent.generators]
        return []

    def scope(self, node):
        """The node whose code object runs node's code: its innermost
        function, class, lambda or generator, else the module's tree."""
        while not isinstance(node, (*SCOPES, ast.Module)):
            node = self.parents[node]
        return node


def case_leaves(match):
    """[(pattern leaf index, guard leaf index or None), ...] of each of
    match's cases, in the manifest's leaf order."""
    found = []
    at = 0
    for case in match.cases:
        guarded = case.guard is not None
        found.append((at, at + 1 if guarded else None))
        at += 1 + guarded
    return found


def first_line(node):
    """The line Python starts node's code object at: its first decorator's,
    else its own."""
    return min([node.lineno, *(decorator.lineno for decorator in getattr(node, "decorator_list", []))])


def span(node):
    """Where node is written, (line, col, end_line, end_col), as ast counts
    them."""
    return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)

"""Each method's machine: its states, built from its AST, each step one
event a call of it sends, as Evaluations.ways records it. Walked as a dry
run, step by step, each step doing what Python does, eg a return ending
the method, it gives every path a call can take, before any is taken."""

import ast
import builtins
from dataclasses import dataclass, replace

from . import decision_paths, manifest, method_statements, stable_names
from .columns import Columns


@dataclass(frozen=True)
class End:
    """The method has ended."""


END = End()

# The nodes whose code runs in a frame of its own, not the method's.
_OWN_FRAMES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


@dataclass(frozen=True)
class Step:
    """A step sending event, a decision's (name, path) or a row's (name,),
    then going on to then."""

    event: tuple
    then: object


@dataclass(frozen=True)
class Fork:
    """Going on to any one of states, sending nothing: where a decision's
    paths part, before the decisions in its leaves step."""

    states: tuple


@dataclass(frozen=True)
class _Exits:
    """Where the ways out of a block go: raised giving the state a raise
    of a class, by its name, goes on to; returned the state a return goes
    on to, each the end of the method unless a try in the method holds the
    block; broke the state a break goes on to, after the innermost loop
    holding the block, and continued the state a continue goes on to, the
    loop's end, each None in no loop, where Python allows neither;
    implicit the state a raise no statement writes, eg a call's, goes on
    to: a fork into each handler of the innermost try with handlers whose
    body holds the block, through the finally of any try between, None in
    no such try's body."""

    raised: object
    returned: object
    broke: object
    continued: object
    implicit: object


def paths(source, path, loops=False):
    """{def decision: [path, ...]} of each function in source, at path:
    every path its machine's dry run gives, each its steps as
    Evaluations.ways has a way's; a loop is no fork, as _Built._loop
    says, unless loops is True."""
    return {decision: _distinct(entry) for decision, (_, entry) in _machines(source, path, loop_forks=loops)[1].items()}


def counts(source, path, loops=False):
    """{def decision: how many paths} of each function in source, at path,
    loops as paths has them: counted over its machine's states, each once,
    so a function of billions of paths is counted without walking them."""
    return {decision: _count(entry, {}) for decision, (_, entry) in _machines(source, path, loop_forks=loops)[1].items()}


def ways(source, path, skipping=frozenset(), loops=False):
    """{def decision: {"possible": paths, "impossible": paths}} of each
    function in source, at path, but those whose decision is in skipping,
    its paths as paths gives them, loops as there: impossible those
    giving a stable name, as stable_names finds it, both outcomes."""
    conditions, machines = _machines(source, path, loop_forks=loops)
    leaves = {name: _spans(condition) for name, condition in conditions.items()}
    never_empty = _never_empty_lines(source)
    found = {}
    for decision, (function, entry) in machines.items():
        if decision in skipping:
            continue
        stable = stable_names.of(function, [span for spans in leaves.values() for span in spans])
        split = {"possible": [], "impossible": []}
        for way in _distinct(entry):
            impossible = _contradicts(way, leaves, stable) or _empties(way, never_empty)
            split["impossible" if impossible else "possible"].append(way)
        found[decision] = split
    return found


def witnessed(way, loops=False):
    """The static paths, as paths gives them, loops as there, that way, a
    call's, as Evaluations.ways has it, witnesses: each made of its
    choices, after the same earlier choices. A loop takes no step: a
    pass's way follows inline, and no pass adds nothing. With loops True
    a loop that made passes is 1+ items, then the way of one of its
    passes, for each way they took; one that made none, 0 items."""
    found = {()}
    for step in way:
        if len(step) < 3:
            found = {each + (step,) for each in found}
        elif not step[2]:
            found = {each + ((step[0], ("0 items",)),) for each in found} if loops else found
        else:
            entered = ((step[0], ("1+ items",)),) if loops else ()
            bodies = {body for taken in step[2] for body in witnessed(taken, loops)}
            found = {each + entered + body for each in found for body in bodies}
    return found


def _machines(source, path, loop_forks=False):
    """(conditions, {def decision: (def node, its machine's entry state)})
    of each function in source, at path, conditions {decision:
    Condition}, its loops forks only when loop_forks is True."""
    tree, conditions, built = _build(source, path, loop_forks)
    columns = Columns(source)
    return conditions, {
        columns.name(path, node.lineno, node.col_offset): (node, built.block(node.body, END, _Exits(_uncaught, END, None, None, None)))
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def top_counter(source, path):
    """A function giving how many ways one run can go through rows, a top
    flow's decision rows in source, at path, counted as a function's are:
    its outermost decisions one after another, each deciding those inside
    it. source is built once, for all its top flows."""
    _, _, built = _build(source, path, False)

    def count(rows):
        """How many ways one run can go through rows, as top_counter says."""
        names = [row.decision for row in rows]
        outermost = [name for name in names if not any(built.holds(other, name) for other in names if other != name)]
        state = END
        for name in reversed(outermost):
            state = built.decision(name, state)
        return _count(state, {})

    return count


def _build(source, path, loop_forks):
    """(tree, conditions, built) of source, at path: its parse, {decision:
    Condition}, and the _Built of its states, its loops forks only when
    loop_forks is True."""
    tree, conditions, nodes, disabled = manifest.found(source, path)
    columns = Columns(source)
    rows = set(method_statements.reaches(source, path))
    loops = {id(node): columns.name(path, *place) for node, place in manifest.loop_places(source, tree).items()}
    built = _Built(
        (conditions, nodes, loops), tree, rows, lambda node: columns.name(path, node.lineno, node.col_offset),
        (loop_forks, disabled),
    )
    return tree, conditions, built


def _spans(condition):
    """The (line, col, end_line, end_col) of each leaf of condition, in
    order."""
    return [(leaf.line, leaf.col, leaf.end_line, leaf.end_col) for leaf in condition.leaves()]


def _span(node):
    """node's (line, col, end_line, end_col), as a leaf's are written."""
    return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)


# The comment on a loop's line declaring it is never given no items.
NEVER_EMPTY = "# path: impossible 0 items"


def _holds(outer, inner):
    """Whether the span outer, (line, col, end_line, end_col), holds the
    span inner."""
    return outer[:2] <= inner[:2] and inner[2:] <= outer[2:]


def _never_empty_lines(source):
    """The line numbers of source whose line carries NEVER_EMPTY."""
    return {number for number, line in enumerate(source.splitlines(), 1) if NEVER_EMPTY in line}


def _empties(way, lines):
    """Whether way gives no items to a loop on one of lines."""
    return any(step[1:] == (("0 items",),) and int(step[0].split(":")[-2]) in lines for step in way)


def _contradicts(way, leaves, stable):
    """Whether way gives a stable name both outcomes, leaves each
    decision's leaf spans, stable as stable_names.of gives it."""
    given = {}
    for step in way:
        for span, outcome in zip(leaves.get(step[0], []), step[1] if len(step) > 1 else ()):
            if span in stable and isinstance(outcome, bool):
                name, flipped = stable[span]
                if given.setdefault(name, outcome != flipped) != (outcome != flipped):
                    return True
    return False


class _Built:
    """The states of a file's methods, built from their statements."""

    def __init__(self, found, tree, rows, named, settings):
        """found ({decision: Condition}, {decision: its node}, {id of a
        comprehension's generator: its loop's name}) in tree, the file's
        parse; rows the names of the rows that are no decision, eg a
        return's, named giving a statement's name, where it starts;
        settings (loop_forks, disabled): whether a loop statement is a
        fork, as _loop says, and the line numbers not analysed, as
        manifest.disabled_lines gives them."""
        self.conditions, self.nodes, self.loops = found
        self.loop_forks, self.disabled = settings
        # A filter's node is its test, which may be a decision too, so
        # filters are found by their test apart from the other decisions.
        self.filters = {id(node): name for name, node in self.nodes.items() if self.conditions[name].operator == "filter"}
        self.names = {id(node): name for name, node in self.nodes.items() if self.conditions[name].operator != "filter"}
        self.spans = {_span(node): node for node in ast.walk(tree) if isinstance(node, ast.expr)}
        self.parents = {id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        self.rows = rows
        self.named = named

    def decision(self, name, then):
        """The state of the decision named name taking one of its paths,
        then going on to then: an expression's as expression runs it, the
        decisions in its arms too; a statement's, eg an if's or a match's,
        or a filter's, as _decided does, its body not run."""
        node = self.nodes[name]
        if isinstance(node, ast.expr) and self.names.get(id(node)) == name:
            return self.expression(node, then)
        return self._decided(name, lambda _each: then)

    def holds(self, outer, inner):
        """Whether the decision named outer holds the one named inner: its
        node's span holds inner's, or, the two the same node, outer is the
        filter whose test inner is."""
        if self.nodes[outer] is self.nodes[inner]:
            return self.filters.get(id(self.nodes[outer])) == outer
        return _holds(_span(self.nodes[outer]), _span(self.nodes[inner]))

    def block(self, statements, then, exits):
        """The state running statements, one after another, then going on
        to then, a raise or return among them going out as exits says,
        and, in a try's body, a raise no statement writes going out before
        any of them that may raise, as _may_raise says."""
        state = then
        for statement in reversed(statements):
            state = self.statement(statement, state, exits)
            if exits.implicit is not None and _may_raise(statement):
                state = Fork((state, exits.implicit))
        return state

    def statement(self, statement, then, exits):
        """The state running statement, then going on to then: an if takes
        its body on a path whose test is true, else its else; a return
        steps where it starts, when it is a row, runs its value's
        decisions, then goes on to exits.returned; a raise likewise, then
        goes on to the state exits.raised gives its class; a with runs its
        items' decisions, then its body. A statement on a line not
        analysed takes no step and goes straight on to then."""
        if statement.lineno in self.disabled or isinstance(statement, manifest.UNMEASURED):
            return then
        if isinstance(statement, ast.If):
            return self._if(statement, then, exits)
        if isinstance(statement, ast.Return):
            return self._reached(statement, self.expression(statement, exits.returned))
        if isinstance(statement, ast.Raise):
            return self._reached(statement, self.expression(statement, exits.raised(_raised_class(statement))))
        if isinstance(statement, (ast.Try, ast.TryStar)):
            return self._try(statement, then, exits)
        if isinstance(statement, ast.Match):
            return self._match(statement, then, exits)
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            return self._in_order(statement.items, self.block(statement.body, then, exits))
        if isinstance(statement, ast.For):
            return self._loop(statement, statement.iter, (then, exits), self.loop_forks)
        if isinstance(statement, ast.AsyncFor):
            return self._loop(statement, statement.iter, (then, exits), False)
        if isinstance(statement, ast.While):
            return self._loop(statement, statement.test, (then, exits), self.loop_forks)
        if isinstance(statement, ast.Break):
            return exits.broke
        if isinstance(statement, ast.Continue):
            return exits.continued
        return self.expression(statement, then)

    def _loop(self, statement, first, onward, forks):
        """The state running the for, async for or while statement, then
        going on as onward, (then, exits), says: the decisions of first, a
        for's iterable or a while's test, as first run, then, when forks,
        a fork, walked without iterating: no pass, its body in no step, or
        at least one, its body walked once, a continue ending the pass.
        Either way, ending without a break, it runs its else. The loop
        steps first, by its keyword; its later tests repeat its fork, so
        take no step. Without forks there is no fork and no step: its body
        is walked once, inline."""
        then, exits = onward
        orelse = self.block(statement.orelse, then, exits)
        body = self.block(statement.body, orelse, replace(exits, broke=then, continued=orelse))
        return self._passes(first, self.named(statement), (orelse, body), forks)

    def _passes(self, first, loop, onward, forks):
        """The state running first, a loop's iterable or test, then the
        fork of the loop named loop, onward being (none, some): going on
        to none, its step 0 items, or to some, its step 1+ items. Without
        forks, no fork and no step: first, then some."""
        none, some = onward
        if not forks:
            return self.expression(first, some)
        return self.expression(first, Fork((Step((loop, ("0 items",)), none), Step((loop, ("1+ items",)), some))))

    def _match(self, statement, then, exits):
        """The state running the match statement, then going on to then:
        each path runs the body of the case it picks, as
        decision_paths.cases_picked gives it, or picking none goes on to
        then."""
        name = self.names[id(statement)]
        bodies = [self.block(case.body, then, exits) for case in statement.cases]
        condition = self.conditions[name]
        picked = dict(zip(map(tuple, decision_paths.possible(condition)), decision_paths.cases_picked(condition)))
        return self._decided(name, lambda each: then if picked[each] is None else bodies[picked[each]])

    def _try(self, statement, then, exits):
        """The state running the try statement, then going on to then: its
        body raises to the first handler catching the raise, a raise no
        statement writes to any handler, and, raising nothing, goes on to
        its else, which its handlers do not guard. Its
        finally runs on each way out of the rest, then goes on out that
        way; a raise or return in the finally itself goes out by exits."""

        def finally_then(onward):
            """The state running the finally, then going on to onward."""
            return self.block(statement.finalbody, onward, exits)

        def through(onward):
            """The state running the finally, then going on to onward, a
            loop's way out or an outer try's handlers; None when onward is,
            in no loop or no try's body."""
            return None if onward is None else finally_then(onward)

        guarded = _Exits(
            lambda raised_class: finally_then(exits.raised(raised_class)),
            finally_then(exits.returned),
            through(exits.broke),
            through(exits.continued),
            through(exits.implicit),
        )
        handlers = [(handler.type, self.block(handler.body, finally_then(then), guarded)) for handler in statement.handlers]
        implicit = Fork(tuple(state for _, state in handlers)) if handlers else guarded.implicit

        def caught(raised_class):
            """The state a raise in the body of the class named raised_class
            goes on to: the first handler catching it, else out by guarded."""
            for named, state in handlers:
                if _catches(named, raised_class):
                    return state
            return guarded.raised(raised_class)

        orelse = self.block(statement.orelse, finally_then(then), guarded)
        return self.block(statement.body, orelse, replace(guarded, raised=caught, implicit=implicit))

    def _reached(self, statement, then):
        """The state of reaching statement, then going on to then: a step
        when statement is a row."""
        name = self.named(statement)
        return Step((name,), then) if name in self.rows else then

    def _if(self, statement, then, exits):
        """The state running the if statement, then going on to then: on a
        path whose test is true its body, else its else, a decision in its
        test decided first, as _decided says."""
        arms = {True: self.block(statement.body, then, exits), False: self.block(statement.orelse, then, exits)}
        return self._decided(self.names[id(statement)], lambda each: arms[each[0]])

    def expression(self, node, then, gives=None):
        """The state running node, then going on to then: a decision takes
        one of its paths, as _decided says, only those whose value is
        gives, unless gives or its value is None; a nested def, class or
        lambda runs in a frame of its own, so takes no step here, as does
        a generator expression, but for its first iterable; a not runs its
        operand, which gives the opposite of what the not gives; any other
        node runs the decisions in its children, one after another."""
        if isinstance(node, _OWN_FRAMES):
            return then
        if isinstance(node, ast.GeneratorExp):
            return self.expression(node.generators[0].iter, then)
        if isinstance(node, manifest.INLINED):
            return self._comprehension(node, node.generators, then)
        name = self.names.get(id(node))
        if name is not None and isinstance(node, ast.IfExp):
            return self._decided(name, lambda each: self._arm(node, self.conditions[name], each[0], then), gives)
        if name is not None:
            return self._decided(name, lambda _each: then, gives)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self.expression(node.operand, then, None if gives is None else not gives)
        return self._in_order(list(ast.iter_child_nodes(node)), then)

    def _arm(self, node, condition, tested, then):
        """The state running the arm of node, a conditional expression of
        condition, its test giving tested, then going on to then: a plain
        arm's decisions, after the expression steps; an arm that is part
        of condition has its decisions among condition's leaves."""
        arm, written = (condition.operands[1], node.body) if tested else (condition.operands[2], node.orelse)
        return self.expression(written, then) if arm.body is None else then

    def _decided(self, name, onward, gives=None):
        """The state of the decision named name taking one of its paths,
        then going on to the state onward gives for that path: first the
        decisions in each leaf the path reaches step, in order, as each is
        decided before the decision is, one that is the whole leaf only on
        its paths giving the leaf the path's outcome; then the decision
        steps. Only its paths whose value is gives, unless gives or that
        value is None."""
        condition = self.conditions[name]
        branches = []
        for each, value in zip(decision_paths.possible(condition), decision_paths.values(condition)):
            if None not in (gives, value) and value != gives:
                continue
            state = Step((name, tuple(each)), onward(tuple(each)))
            for span, outcome in reversed(list(zip(_spans(condition), each))):
                node = self.spans.get(span)
                if outcome is not None and node is not None and not self._elsewhere(node, self.nodes[name]):
                    state = self.expression(node, state, outcome)
            branches.append(state)
        return Fork(tuple(branches))

    def _elsewhere(self, node, decision):
        """Whether node, a leaf of decision's node, runs in a frame of its
        own: inside a generator expression inside decision, as a block
        call's element does, but for its first iterable. No leaf is inside
        a def, class or lambda."""
        child, parent = node, self.parents[id(node)]
        while child is not decision:
            if isinstance(parent, ast.GeneratorExp) and child is not parent.generators[0]:
                return True
            child, parent = parent, self.parents.get(id(parent))
        return False

    def _comprehension(self, node, generators, then):
        """The state running generators, the rest of node's, a list, set or
        dict comprehension's, then going on to then: each a loop, as a for
        statement is, its iterable's decisions, then a fork by its for
        keyword: no pass, or one, its filters stepping in order, a false
        one ending the pass, then the next generator; with none left, the
        element's decisions. Without loop_forks no generator is a fork or
        takes a step: each pass is walked once, inline."""
        if not generators:
            return self._in_order([node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt], then)
        generator = generators[0]
        state = self._comprehension(node, generators[1:], then)
        for test in reversed(generator.ifs):
            state = self._decided(self.filters[id(test)], lambda each, onward=state: onward if each[0] else then)
        return self._passes(generator.iter, self.loops[id(generator)], (then, state), self.loop_forks)

    def _in_order(self, nodes, then):
        """The state running the decisions of each of nodes, one after
        another, then going on to then."""
        state = then
        for node in reversed(nodes):
            state = self.expression(node, state)
        return state


# The statements whose own code runs before the first step of their body,
# by the field holding it: only that code can raise before their body's.
_HEADS = {ast.If: "test", ast.While: "test", ast.For: "iter", ast.AsyncFor: "iter", ast.Match: "subject"}

# The nodes whose running raises nothing: reading or binding a name, a
# constant, a not, and the statements made only of them.
_QUIET = (ast.Name, ast.Constant, ast.Load, ast.Store, ast.Assign, ast.Return, ast.Not)


def _may_raise(statement):
    """Whether statement can raise with no raise written, before its first
    step: false for a raise, its own way out, and a try, whose body's
    statements are asked in turn; else whether its head, or the whole
    statement when it has none, eg a call's, is loud, as _loud says."""
    if isinstance(statement, (ast.Raise, ast.Try, ast.TryStar)):
        return False
    head = _HEADS.get(type(statement))
    return _loud(statement if head is None else getattr(statement, head))


def _loud(node):
    """Whether running node can raise: it is not quiet, or one of its
    children is loud. A not's operator is quiet; any other operator, eg -,
    can call a method."""
    quiet = isinstance(node, _QUIET) or (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not))
    return not quiet or any(_loud(child) for child in ast.iter_child_nodes(node))


def _uncaught(_raised_class):
    """The state a raise no try in the method catches goes on to: the end
    of the method."""
    return END


def _raised_class(statement):
    """The name of the class a raise statement raises, as written, eg
    KeyError for raise KeyError(sku) and yaml.YAMLError for raise
    yaml.YAMLError(text); None for a class it does not name, eg a bare
    raise or raise errors[0]."""
    exc = statement.exc.func if isinstance(statement.exc, ast.Call) else statement.exc
    return _class_name(exc)


def _class_name(node):
    """The dotted name node writes, eg yaml.YAMLError for an attribute of a
    name; None for a node that is no name or attribute of one, eg
    errors[0], or no node, as a bare raise has."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _class_name(node.value)
        return None if owner is None else f"{owner}.{node.attr}"
    return None


def _catches(named, raised_class):
    """Whether a handler of named, its type's node, catches a raise of the
    class named raised_class: always for a bare except, its named None;
    for a tuple, when any of its classes does; never when either class has
    no name; else when it names that class, or both are builtin classes and
    that class is a subclass of the handler's."""
    if named is None:
        return True
    if isinstance(named, ast.Tuple):
        return any(_catches(each, raised_class) for each in named.elts)
    handled_class = _class_name(named)
    if handled_class is None or raised_class is None:
        return False
    handled, raised = getattr(builtins, handled_class, None), getattr(builtins, raised_class, None)
    if isinstance(handled, type) and isinstance(raised, type):
        return issubclass(raised, handled)
    return handled_class == raised_class


def _count(state, known):
    """How many paths go from state, as _walked gives them, known holding
    the count of each state already counted, by its id, as forks share
    the states they go on to."""
    if state is END:
        return 1
    if id(state) not in known:
        onward = (state.then,) if isinstance(state, Step) else state.states
        known[id(state)] = sum(_count(each, known) for each in onward)
    return known[id(state)]


def _distinct(entry):
    """Every path from entry, as _walked gives them, each once, in the
    order first walked: two forks that send nothing, eg a raise no
    statement writes going to a handler before either of two statements
    with no step between them, can end in the same steps."""
    return list(dict.fromkeys(_walked(entry)))


def _walked(state):
    """Every path from state, each a tuple of steps, depth first, a fork's
    states in order."""
    if state is END:
        yield ()
    elif isinstance(state, Step):
        for rest in _walked(state.then):
            yield (state.event, *rest)
    else:
        for each in state.states:
            yield from _walked(each)

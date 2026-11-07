"""The spy-trace oracle of the generated functions. traced calls a function
with spies: each spy leaf a callable that logs ("leaf", i) and gives its
value; mark a callable that logs ("statement", n, t) before statement n
runs. The trace is the path the call took, as the program itself behaved.

Oracle derives from a trace what path_coverage must report: for each
statement the trace says ran, with t as it was, it evaluates that
statement's own expressions afresh from the call's leaf values, a name
leaf's and a spy's from the inputs, a literal's from the source, short
circuiting as Python does, and notes each decision's path, the outcome of
each leaf it evaluated, None for each it skipped, as path_coverage.json
lists paths; and the runs of each statement path_coverage counts, from the
marks."""

import ast
import itertools
from collections import Counter

from path_coverage import manifest, method_statements
from path_coverage.columns import Columns

# How many items a block call was given, as path_coverage.json lists them.
ITEMS = ("0 items", "1 item", "2+ items")

# The block calls, by name, and the answer each stops at.
STOPS = {"any": True, "all": False}

# The method evaluating a call, by the name called; any other is a spy's.
CALLS = {"len": "_len", "any": "_block", "all": "_block"}


def combinations(leaves):
    """Every combination of values of leaves parameters, each True or
    False."""
    return list(itertools.product([True, False], repeat=leaves))


def traced(run, spies, values):
    """[run's value, or "raised" for its module's Stop, the trace] of one
    call of run with values, its parameters' in order: a parameter in
    spies, a set of indexes, passed as a spy giving its value, any other as
    its value; then the mark."""
    trace = []
    args = [_spy(trace, index, value) if index in spies else value for index, value in enumerate(values)]
    try:
        result = run(*args, _marker(trace))
    except run.__globals__["Stop"]:
        result = "raised"
    return [result, trace]


def _spy(trace, index, value):
    """A spy of parameter index: a callable logging its call on trace and
    giving value."""

    def spy():
        """Logs this call, then gives the value."""
        trace.append(("leaf", index))
        return value

    return spy


def _marker(trace):
    """The mark: a callable logging on trace that a statement is about to
    run, with t's value, None before t is set."""

    def mark(number, t=None):
        """Logs that statement number is about to run with t."""
        trace.append(("statement", number, t))

    return mark


class Oracle:
    """What path_coverage must report of the run function of source, the
    file path: counts, {decision: Counter of paths}, and reached, a
    Counter of each counted statement's runs, over every call added."""

    def __init__(self, source, path):
        """Starts with no call added."""
        tree, conditions, nodes = manifest.found(source, path)
        columns = Columns(source)
        reaches = set(method_statements.reaches(source, path))
        run = tree.body[1]
        self.entry = columns.name(path, run.lineno, run.col_offset)
        self.sizes = {name: len(condition.leaves()) for name, condition in conditions.items()}
        roles = {"and": "expressions", "or": "expressions", "ternary": "expressions", "if": "ifs", "match": "matches", "filter": "filters", "any": "blocks", "all": "blocks"}
        for role in set(roles.values()):
            setattr(self, role, {})
        self.leaf_of = {}
        for name, condition in conditions.items():
            getattr(self, roles[condition.operator])[nodes[name]] = name
            patterns = {pattern for pattern, _ in _case_leaves(nodes[name])} if condition.operator == "match" else ()
            for index, leaf in enumerate(condition.leaves()):
                if index not in patterns and condition.operator not in STOPS:
                    self.leaf_of.setdefault((leaf.line, leaf.col, leaf.end_line, leaf.end_col), []).append((name, index))
        self.marked = {
            body[at].value.args[0].value: body[at + 1]
            for body in _bodies(run)
            for at in range(len(body) - 1)
            if _is_mark(body[at])
        }
        self.names = {
            statement: name
            for statement in self.marked.values()
            if (name := columns.name(path, statement.lineno, statement.col_offset)) in reaches
        }
        self.counts = {}
        self.reached = Counter()

    def add(self, values, trace):
        """Adds the paths and statement runs of one call, given values, its
        leaf parameters' in order, which took trace."""
        self.values = values
        self.env = {f"p{index}": value for index, value in enumerate(values)}
        self.open = {name: [] for name in self.sizes}
        self.reached[self.entry] += 1
        for _, number, t in (event for event in trace if event[0] == "statement"):
            self.env["t"] = t
            statement = self.marked[number]
            self.reached.update([self.names[statement]] if statement in self.names else [])
            getattr(self, f"_{type(statement).__name__}")(statement)

    def _Assign(self, statement):
        """Evaluates a write's value."""
        self.ev(statement.value)

    _AugAssign = _Assign

    def _Return(self, statement):
        """Evaluates nothing: a return of t, or a raise of Stop, holds no
        decision."""

    _Raise = _Return

    def _If(self, statement):
        """Evaluates an if's predicate, as its decision, and, when false, an
        elif's, which has no mark of its own."""
        name = self.ifs[statement]
        self._opened(name)
        truth = bool(self.ev(statement.test))
        self._closed(name)
        if not truth and statement.orelse and isinstance(statement.orelse[0], ast.If):
            self._If(statement.orelse[0])

    def _Match(self, statement):
        """Evaluates a match's subject, then tries its cases in order, as
        its decision, each pattern's outcome noted, and a matching case's
        guard evaluated, until a case is taken."""
        name = self.matches[statement]
        subject = self.ev(statement.subject)
        self._opened(name)
        for case, (pattern, guard) in zip(statement.cases, _case_leaves(statement)):
            self.open[name][-1][pattern] = _matches(case.pattern, subject)
            if self.open[name][-1][pattern] and (guard is None or self.ev(case.guard)):
                break
        self._closed(name)

    def ev(self, node):
        """node's value, evaluated as Python evaluates it, noting each
        decision node starts, and the outcome of each leaf node is, on the
        decisions' evaluations under way."""
        name = self.expressions.get(node)
        if name is not None:
            self._opened(name)
        value = getattr(self, f"_{type(node).__name__}_value")(node)
        for decision, index in self.leaf_of.get((node.lineno, node.col_offset, node.end_lineno, node.end_col_offset), ()):
            self.open[decision][-1][index] = bool(value)
        if name is not None:
            self._closed(name)
        return value

    def _opened(self, name):
        """Starts an evaluation of the decision named name, no leaf
        evaluated yet."""
        self.open[name].append([None] * self.sizes[name])

    def _closed(self, name):
        """Counts the path of the latest evaluation of the decision named
        name, as finished."""
        self.counts.setdefault(name, Counter())[tuple(self.open[name].pop())] += 1

    def _Constant_value(self, node):
        """A literal's value."""
        return node.value

    def _Name_value(self, node):
        """A name's value: a parameter's, t's, or one a walrus or a
        comprehension wrote."""
        return self.env[node.id]

    def _Call_value(self, node):
        """A call's value: a lambda's body's; a call of len, any or all;
        else a spy's value, its parameter's."""
        if isinstance(node.func, ast.Lambda):
            return self.ev(node.func.body)
        return getattr(self, CALLS.get(node.func.id, "_spied"))(node)

    def _spied(self, node):
        """A spy's value: the value of the parameter it calls."""
        return self.values[int(node.func.id[1:])]

    def _len(self, node):
        """The length of len's argument."""
        return len(self.ev(node.args[0]))

    def _block(self, node):
        """The value of any or all of a generator, as its decision: each
        item its generator gives answered in turn, until an answer stops
        it; its path is how many items it was given and its last answer."""
        name = self.blocks[node]
        generator = node.args[0]
        stops = STOPS[node.func.id]
        count, last = 0, None
        for item in self.ev(generator.generators[0].iter):
            self.env[generator.generators[0].target.id] = item
            count += 1
            last = bool(self.ev(generator.elt))
            if last == stops:
                break
        self.counts.setdefault(name, Counter())[(ITEMS[min(count, 2)], last)] += 1
        return (last == stops) == stops

    def _BoolOp_value(self, node):
        """An and/or's value: each operand's, left to right, until one
        decides it."""
        for operand in node.values:
            value = self.ev(operand)
            if bool(value) != isinstance(node.op, ast.And):
                return value
        return value

    def _IfExp_value(self, node):
        """A conditional expression's value: its arm's that its predicate
        picks."""
        return self.ev(node.body) if self.ev(node.test) else self.ev(node.orelse)

    def _UnaryOp_value(self, node):
        """A not's value."""
        return not self.ev(node.operand)

    def _NamedExpr_value(self, node):
        """A walrus's value, written to its name."""
        self.env[node.target.id] = self.ev(node.value)
        return self.env[node.target.id]

    def _Compare_value(self, node):
        """A comparison's value, of literals and t."""
        return eval(compile(ast.Expression(node), "<oracle>", "eval"), {}, dict(self.env))  # noqa: S307 - the generated comparison is the point

    def _JoinedStr_value(self, node):
        """An f-string's value."""
        return "".join(str(self.ev(part)) for part in node.values)

    def _FormattedValue_value(self, node):
        """An f-string part's value."""
        return self.ev(node.value)

    def _List_value(self, node):
        """A list display's value, a starred item's items spread."""
        found = []
        for item in node.elts:
            found += list(self.ev(item.value)) if isinstance(item, ast.Starred) else [self.ev(item)]
        return found

    def _Tuple_value(self, node):
        """A tuple display's value."""
        return tuple(self.ev(item) for item in node.elts)

    def _ListComp_value(self, node):
        """A list comprehension's value: its element for each item its
        filters keep, each filter its decision."""
        generator = node.generators[0]
        found = []
        for item in self.ev(generator.iter):
            self.env[generator.target.id] = item
            if self._kept(generator.ifs):
                found.append(self.ev(node.elt))
        return found

    def _kept(self, tests):
        """True when every filter of tests keeps the current item, each
        evaluated as its decision, in order, until one drops it."""
        for test in tests:
            name = self.filters[test]
            self._opened(name)
            kept = bool(self.ev(test))
            self._closed(name)
            if not kept:
                return False
        return True


def _matches(pattern, value):
    """True when pattern, one the grammar writes, matches value, as Python
    matches it."""
    return MATCHERS[type(pattern)](pattern, value)


def _singleton(pattern, value):
    """True when value is the singleton pattern names, eg True."""
    return value is pattern.value


def _value(pattern, value):
    """True when value equals the literal pattern names, eg 2."""
    return value == pattern.value.value


def _as(pattern, value):
    """True for _ or a capture, which match anything; else whether the
    pattern it names, eg (s as w)'s s, matches."""
    return True if pattern.pattern is None else _matches(pattern.pattern, value)


def _or(pattern, value):
    """True when any of an or-pattern's alternatives matches."""
    return True in [_matches(alternative, value) for alternative in pattern.patterns]


# How each kind of pattern the grammar writes matches.
MATCHERS = {ast.MatchSingleton: _singleton, ast.MatchValue: _value, ast.MatchAs: _as, ast.MatchOr: _or}


def _case_leaves(match):
    """[(pattern leaf index, guard leaf index or None), ...] of each of
    match's cases, in the manifest's leaf order."""
    found = []
    at = 0
    for case in match.cases:
        guarded = case.guard is not None
        found.append((at, at + 1 if guarded else None))
        at += 1 + guarded
    return found


def _bodies(run):
    """Every list of statements in run, its own body and each nested one:
    an if's, an else's, a case's."""
    lists = [run.body]
    for node in ast.walk(run):
        lists += [getattr(node, field) for field in ("body", "orelse") if isinstance(getattr(node, field, None), list)]
    return [body for body in lists if body]


def _is_mark(statement):
    """True for a statement that is a call of mark, as every expression
    statement run holds is."""
    return isinstance(statement, ast.Expr)

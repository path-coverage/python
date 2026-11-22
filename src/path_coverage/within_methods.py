"""The JSON report's flows: each function's flow and each top flow, as its
file's page draws it, so a reader, a tool or an AI, finds a flow's gap
without the page."""

import ast

from . import paths_tree, method_machine, method_statements, ways_report
from .source_lines import lines_of

# The most paths a function may have and still be checked, by default.
MAX_PATHS = 4096
# The most max paths may be. Sequential choices multiply a function's paths
# into the billions; analysing each path costs about 2.2 microseconds and
# 110 bytes of JSON per step, so this cap keeps analysing each function's
# paths to about 2 seconds and 120 MB of JSON.
PATHS_CAP = 65536


def of(files, operands, paths, counted, loops=False, max_paths=MAX_PATHS):
    """{flow decision: flow} of every flow in files, {path relative to root:
    (source, decisions)}: each function's, by its def's decision, then each top
    flow's, by its first line, as flow gives them; operands and paths as
    result gives them, counted (reached, ways), each statement's runs, None
    when not known, and each function's ways taken, as Evaluations.ways
    has them, loops and max_paths as function_flows has them. Example: {"k.py:1:0":
    {"name": "ship", "first": 1, "last": 3, "ways": 2, "calls": 1,
    "rows": [...], "taken": [...]}}."""
    listed = {}
    for path, (source, decisions) in files.items():
        listed.update(function_flows(source, (path, decisions), paths, counted, (loops, max_paths)))
        lines = lines_of(source, decisions, operands)
        listed.update(top_flows(source, (path, decisions), lines, paths))
    return listed


def tree(files, operands):
    """{path: {flow "line:col": {row "line:col": place}}} of every flow in
    files, as of lists them, each row placed as paths_tree places it: how
    the rows of each flow nest. operands as result gives them."""
    nested = {}
    for path, (source, decisions) in files.items():
        flows = {decision: rows for decision, rows in paths_tree.of(source, path, decisions).items()}
        lines = lines_of(source, decisions, operands)
        for (first, _), rows in spans(source, path, lines).items():
            flows[f"{path}:{first}:0"] = paths_tree.nested(source, decisions, rows)
        nested[path] = {":".join(decision.split(":")[-2:]): rows for decision, rows in flows.items()}
    return nested


def function_flows(source, at, paths, counted, limits=(False, MAX_PATHS)):
    """The flows of each function in source, at being its (path, decisions), as
    of gives them: each counting its calls, its entry's runs, 0 when never
    called, None when not known, and listing the ways its calls took, as
    ways_report.taken gives them, none when never called. limits is
    (loop_forks, max_paths): its loops forks in its ways only when
    loop_forks is True, as method_machine.ways has it; a function with
    more ways than max_paths lists none of them, covered or gaps."""
    loop_forks, max_paths = limits
    path, decisions = at
    reached, ways = counted
    names = method_statements.names(source, path)
    lasts = method_statements.lasts(source, path)
    loops = method_statements.loops(source, path)
    counts = method_machine.counts(source, path, loops=loop_forks)
    over = {decision for decision, count in counts.items() if count > max_paths}
    listed = method_machine.ways(source, path, skipping=over, loops=loop_forks)
    flows = {}
    for decision, rows in method_statements.of(source, path).items():
        calls = None if reached is None else reached.get(decision, 0)
        count = counts[decision] if decision in over else len(listed[decision]["possible"])
        title = (names[decision], lasts[decision], count, calls)
        flows[decision] = flow(decision, title, rows, method_statements.taken(rows, paths, reached))
        flows[decision]["taken"] = ways_report.taken(ways.get(decision, {}))
        flows[decision]["passes"] = {ways_report.at(loop): ways_report.taken(ways.get(loop, {})) for loop in loops[decision]}
        if decision in over:
            continue
        possible = listed[decision]["possible"]
        seen = {}
        for way, count in ways.get(decision, {}).items():
            for each in method_machine.witnessed(way, loop_forks):
                seen[each] = seen.get(each, 0) + count
        flows[decision]["covered"] = [{"way": ways_report.way(way), "count": seen[way]} for way in possible if way in seen]
        flows[decision]["gaps"] = [ways_report.way(way) for way in possible if way not in seen]
        impossible = listed[decision]["impossible"]
        flows[decision]["impossible"] = [ways_report.way(way) for way in impossible]
        flows[decision]["impossible_taken"] = [ways_report.way(way) for way in impossible if way in seen]
    return flows


def top_flows(source, at, lines, paths):
    """The top flows of source, at being its (path, decisions), its lines as
    source_lines.lines_of gives them: one for each span of lines holding
    decisions outside every function, named for its first line's start, titled
    by its scope, its calls None, as no call runs it."""
    path, decisions = at
    scope = scopes(source)
    ways = method_machine.top_counter(source, path)
    found = {}
    for (first, last), rows in spans(source, path, lines).items():
        decision = f"{path}:{first}:0"
        title = (scope(first), last, ways(rows), None)
        found[decision] = flow(decision, title, rows, method_statements.taken(rows, paths))
    return found


def spans(source, path, lines):
    """{span: its top rows} of source, at path, each top row, as
    method_statements.top_rows gives it, under the span its line is in, as
    lines, from source_lines.lines_of, give it, since a span's lines share
    one button on the page. Example: {(1, 1): [the ternary's row]}."""
    grouped = {}
    for row in method_statements.top_rows(source, path):
        grouped.setdefault(lines[row.line - 1]["span"], []).append(row)
    return grouped


def scopes(source):
    """A function giving the scope of a line of source: the name of the
    innermost class whose lines hold it, a top flow's title as a def is a
    function flow's; file for a line in none. Example: line 2, in class
    Shop on lines 1 to 9, gives Shop."""
    classes = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ClassDef)]

    def scope(line):
        """The scope of line, as scopes says."""
        holding = [node for node in classes if node.lineno <= line <= node.end_lineno]
        return max(holding, key=lambda node: node.lineno).name if holding else "file"

    return scope


def flow(decision, title, rows, taken):
    """The flow at decision, its title (name, last, ways, calls): titled name,
    its first line from decision, ending on line last, ways the ways one call
    can go through it, as method_machine counts them, calls how many times it
    was called, None for a top flow or when not known; and a row for each
    of rows, Statements, with its taken, as method_statements.taken gives
    them."""
    name, last, ways, calls = title
    first = int(decision.split(":")[-2])
    listed = [_row(statement, count) for statement, count in zip(rows, taken)]
    return {"name": name, "first": first, "last": last, "ways": ways, "calls": calls, "rows": listed}


def _row(statement, count):
    """A flow's row: statement's line:column, as its page labels it, its
    top, its paths, count, how many were taken, and its decision, None for a
    statement that is no decision."""
    return {
        "at": method_statements.label(statement),
        "top": statement.top,
        "paths": statement.paths,
        "taken": count,
        "decision": statement.decision,
    }

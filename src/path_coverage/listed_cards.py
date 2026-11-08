"""The JSON report's cards: each function's card and each top card, as its
file's page draws it, so a reader, a tool or an AI, finds a card's gap
without the page."""

import ast

from . import card_tree, card_ways, method_machine, method_statements, ways_report
from .source_lines import lines_of


def of(files, operands, paths, counted):
    """{card decision: card} of every card in files, {path relative to root:
    (source, decisions)}: each function's, by its def's decision, then each top
    card's, by its first line, as card gives them; operands and paths as
    result gives them, counted (reached, ways), each statement's runs, None
    when not known, and each function's ways taken, as Evaluations.ways
    has them. Example: {"k.py:1:0": {"name": "ship", "first": 1, "last": 3,
    "ways": 2, "calls": 1, "rows": [...], "taken": [...]}}."""
    listed = {}
    for path, (source, decisions) in files.items():
        listed.update(function_cards(source, (path, decisions), paths, counted))
        lines = lines_of(source, decisions, operands)
        listed.update(top_cards(source, (path, decisions), lines, paths))
    return listed


def tree(files, operands):
    """{path: {card "line:col": {row "line:col": place}}} of every card in
    files, as of lists them, each row placed as card_tree places it: how
    the rows of each card nest. operands as result gives them."""
    nested = {}
    for path, (source, decisions) in files.items():
        cards = {decision: rows for decision, rows in card_tree.of(source, path, decisions).items()}
        lines = lines_of(source, decisions, operands)
        for (first, _), rows in spans(source, path, lines).items():
            cards[f"{path}:{first}:0"] = card_tree.nested(source, decisions, rows)
        nested[path] = {":".join(decision.split(":")[-2:]): rows for decision, rows in cards.items()}
    return nested


def function_cards(source, at, paths, counted):
    """The cards of each function in source, at being its (path, decisions), as
    of gives them: each counting its calls, its entry's runs, 0 when never
    called, None when not known, and listing the ways its calls took, as
    ways_report.taken gives them, none when never called."""
    path, decisions = at
    reached, ways = counted
    names = method_statements.names(source, path)
    lasts = method_statements.lasts(source, path)
    loops = method_statements.loops(source, path)
    listed = method_machine.ways(source, path)
    cards = {}
    for decision, rows in method_statements.of(source, path).items():
        calls = None if reached is None else reached.get(decision, 0)
        possible = listed[decision]["possible"]
        title = (names[decision], lasts[decision], len(possible), calls)
        cards[decision] = card(decision, title, rows, method_statements.taken(rows, paths, reached))
        cards[decision]["taken"] = ways_report.taken(ways.get(decision, {}))
        cards[decision]["passes"] = {ways_report.at(loop): ways_report.taken(ways.get(loop, {})) for loop in loops[decision]}
        seen = {}
        for way, count in ways.get(decision, {}).items():
            for each in method_machine.witnessed(way):
                seen[each] = seen.get(each, 0) + count
        cards[decision]["covered"] = [{"way": ways_report.way(way), "count": seen[way]} for way in possible if way in seen]
        cards[decision]["gaps"] = [ways_report.way(way) for way in possible if way not in seen]
        cards[decision]["impossible"] = [ways_report.way(way) for way in listed[decision]["impossible"]]
    return cards


def top_cards(source, at, lines, paths):
    """The top cards of source, at being its (path, decisions), its lines as
    source_lines.lines_of gives them: one for each span of lines holding
    decisions outside every function, named for its first line's start, titled
    by its scope, its calls None, as no call runs it."""
    path, decisions = at
    scope = scopes(source)
    found = {}
    for (first, last), rows in spans(source, path, lines).items():
        decision = f"{path}:{first}:0"
        title = (scope(first), last, card_ways.card(source, decisions, rows), None)
        found[decision] = card(decision, title, rows, method_statements.taken(rows, paths))
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
    innermost class whose lines hold it, a top card's title as a def is a
    function card's; file for a line in none. Example: line 2, in class
    Shop on lines 1 to 9, gives Shop."""
    classes = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ClassDef)]

    def scope(line):
        """The scope of line, as scopes says."""
        holding = [node for node in classes if node.lineno <= line <= node.end_lineno]
        return max(holding, key=lambda node: node.lineno).name if holding else "file"

    return scope


def card(decision, title, rows, taken):
    """The card at decision, its title (name, last, ways, calls): titled name,
    its first line from decision, ending on line last, ways the ways one call
    can go through it, as card_ways counts them, calls how many times it
    was called, None for a top card or when not known; and a row for each
    of rows, Statements, with its taken, as method_statements.taken gives
    them."""
    name, last, ways, calls = title
    first = int(decision.split(":")[-2])
    listed = [_row(statement, count) for statement, count in zip(rows, taken)]
    return {"name": name, "first": first, "last": last, "ways": ways, "calls": calls, "rows": listed}


def _row(statement, count):
    """A card's row: statement's line:column, as its page labels it, its
    top, its paths, count, how many were taken, and its decision, None for a
    statement that is no decision."""
    return {
        "at": method_statements.label(statement),
        "top": statement.top,
        "paths": statement.paths,
        "taken": count,
        "decision": statement.decision,
    }

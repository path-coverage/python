"""The JSON report's cards: each function's card and each top card, as its
file's page draws it, so a reader, a tool or an AI, finds a card's gap
without the page."""

import ast

from . import method_statements
from .source_lines import lines_of


def of(files, operands, paths, reached):
    """{card site: card} of every card in files, {path relative to root:
    (source, sites)}: each function's, by its def's site, then each top
    card's, by its first line, as card gives them; operands and paths as
    result gives them, reached each statement's runs, None when not known.
    Example: {"k.py:1:0": {"name": "ship", "first": 1, "last": 3, "rows":
    [...]}}."""
    listed = {}
    for path, (source, sites) in files.items():
        listed.update(_function_cards(source, path, paths, reached))
        lines = lines_of(source, sites, operands)
        listed.update(_top_cards(source, path, lines, paths))
    return listed


def _function_cards(source, path, paths, reached):
    """The cards of each function in source, at path, as of gives them."""
    names = method_statements.names(source, path)
    lasts = method_statements.lasts(source, path)
    return {
        site: card(site, names[site], lasts[site], rows, method_statements.taken(rows, paths, reached))
        for site, rows in method_statements.of(source, path).items()
    }


def _top_cards(source, path, lines, paths):
    """The top cards of source, at path, its lines as source_lines.lines_of
    gives them: one for each span of lines holding sites outside every
    function, named for its first line's start, titled by its scope."""
    scope = scopes(source)
    found = {}
    for (first, last), rows in spans(source, path, lines).items():
        site = f"{path}:{first}:0"
        found[site] = card(site, scope(first), last, rows, method_statements.taken(rows, paths))
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


def card(site, name, last, rows, taken):
    """The card at site, titled name, ending on line last: its first line,
    from site, and a row for each of rows, Statements, with its taken, as
    method_statements.taken gives them."""
    first = int(site.split(":")[-2])
    listed = [_row(statement, count) for statement, count in zip(rows, taken)]
    return {"name": name, "first": first, "last": last, "rows": listed}


def _row(statement, count):
    """A card's row: statement's line:column, as its page labels it, its
    top, its paths, count, how many were taken, and its site, None for a
    statement that is no site."""
    return {
        "at": method_statements.label(statement),
        "top": statement.top,
        "paths": statement.paths,
        "taken": count,
        "site": statement.site,
    }

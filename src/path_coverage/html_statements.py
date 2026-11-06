"""One card of a file's page, hidden until side.js opens it in the rail: a
title row of its function's name, or a top card's scope, its complexity, and
its paths not taken and taken; a row titling the columns; then a row per
statement, as method_statements gives them, a site's with its tree folded
under it."""

from html import escape

from . import html_syntax, method_statements

# The classes of every card.
GRID = "pathgrid statements"

# The tops that name a kind of statement, quoting no code.
KINDS = ("value", "()")

# The class each of a row's cells adds after pcell: none for its top, then
# those colouring not taken and taken.
CELLS = ("", " not-taken", " was-taken")


def card(site, name, rows, taken, last, tree=None):
    """The card of the function named name at site, its rows' taken as
    method_statements.taken gives them, last its def's last line. tree,
    when given, gives a site's tree rows, by its name, folded under its row.
    Example: ship, an if then a value, gives its title row, the column
    titles, then an if row and a value row."""
    first, column = site.split(":")[-2:]
    attrs = (
        f'id="paths-{first}" data-first="{first}" data-col="{column}" data-last="{last}"'
        f' data-status="{status(rows, taken)}" hidden="hidden"'
    )
    head = _title_row(first, name, rows, taken) + _columns_row()
    return f'<div class="{GRID}" {attrs}>{head}{_body(rows, taken, tree)}</div>'


def top_card(site, scope, rows, taken, last, tree=None):
    """The card of the sites outside every function whose lines start at
    site, as card gives it, last its lines' last; titled by scope, eg file
    or its class, as a function's card is by its function, and marked
    top-level, as it is no function's: a class no other part of the page
    has, so no style of another's, eg the header's top line's display,
    shows it when it is hidden. Example: FEE = (1 if a else 0) + (2 if b
    else 0) on line 1 gives a card titled file, a ternary row each."""
    return card(site, scope, rows, taken, last, tree).replace(
        f'class="{GRID}"', f'class="{GRID} top-level"', 1
    )


def status(rows, taken):
    """covered when every row's taken is known and is all of its paths;
    gaps otherwise, as a row not known may have one."""
    return "covered" if all(count == row.paths for row, count in zip(rows, taken)) else "gaps"


def _body(rows, taken, tree):
    """Each statement's row, a site's with the rows tree gives for that
    site folded under it."""
    out = []
    for row, count in zip(rows, taken):
        folded = tree(row.site) if tree and row.site else None
        out.append(_row_of(row, count, folded is not None) + _fold(row, folded))
    return "".join(out)


def _title_row(first, name, rows, taken):
    """The row level with the def: its name, *complexity, then how many of
    its paths were not taken, those of rows not known among them, and how
    many were."""
    seen = sum(count for count in taken if count is not None)
    complexity = method_statements.complexity(rows)
    cells = [f"*{complexity}", str(method_statements.size(rows) - seen), str(seen)]
    return _row(f'class="prow calls" data-line="{first}"', escape(name), cells)


def _columns_row():
    """The row naming the not taken and taken columns."""
    return _row('class="prow columns"', "line:col", ["", "not taken", "taken"])


def _row_of(statement, count, folds):
    """One statement's row: its line:column, the column two digits so they
    line up, its top, how many of its paths were not taken, and how many
    were, ? for both when not known. A site's row is marked as one, so a
    click on it can open its tree; when it folds a tree, its arrow, left of
    its line:column, shows whether the fold is open."""
    counts = ["?", "?"] if count is None else [str(statement.paths - count), str(count)]
    css = "prow site" if statement.site else "prow"
    lead = _arrow(statement) if folds else ""
    attrs = f'class="{css}" data-line="{statement.line}"'
    return _row(attrs, method_statements.label(statement), [_top(statement), *counts], lead)


def _top(statement):
    """statement's top, coloured as the code pane colours the code it
    quotes, eg if, def and return as keywords; but value and (), which name
    kinds of statement and quote no code, escaped and plain. Example: if
    gives <span class="k">if</span>."""
    text = statement.top
    return escape(text) if text in KINDS else html_syntax.fragment(text)


def _arrow(statement):
    """The arrow left of a row's line:column, its glyph, as style.css draws
    it, pointing down while its fold is shut and up while it is open."""
    label = method_statements.label(statement)
    return (
        '<button type="button" class="fold-arrow" aria-expanded="false"'
        f' aria-label="Paths of {label}"></button>'
    )


def _fold(statement, tree):
    """The fold under statement's row, hidden until the row is clicked:
    tree, its site's rows as its tree draws them. Empty for a row with no
    tree."""
    if tree is None:
        return ""
    return (
        f'<div class="fold" data-site="{statement.site}" hidden="hidden">'
        f'<div class="site" data-site="">{tree}</div></div>'
    )


def _none(cell, css):
    """The class marking a not taken cell of 0, no gap, coloured blue as
    taken is; none for any other cell, as a count of paths not taken, or
    one not known, ?, is a gap."""
    return " none" if css == " not-taken" and cell == "0" else ""


def _row(attrs, label, cells, lead=""):
    """A row div with attrs, lead, then its label, then a span per cell."""
    spans = "".join(
        f'<span class="pcell{css}{_none(cell, css)}">{cell}</span>' for cell, css in zip(cells, CELLS)
    )
    return f'<div {attrs}>{lead}<span class="plabel">{label}</span>{spans}</div>'

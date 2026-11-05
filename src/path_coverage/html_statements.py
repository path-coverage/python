"""One function's card in method mode, hidden in its file's page until
side.js moves it into the rail: a title row of the function's name, its
complexity, its size and the paths taken, a row titling the columns, then a
row per statement, as method_statements gives them. A Python name or top
holds no markup, so nothing is escaped."""

from . import method_statements


def card(site, name, rows, taken, last):
    """The card of the function named name at site, its rows' taken as
    method_statements.taken gives them, last its def's last line. Example:
    ship, an if then a return, gives its title row, the column titles, then
    an if row and a return row."""
    first, column = site.split(":")[-2:]
    attrs = (
        f'id="paths-{first}" data-first="{first}" data-col="{column}" data-last="{last}"'
        f' data-status="{status(rows, taken)}" hidden="hidden"'
    )
    body = "".join(_row_of(row, count) for row, count in zip(rows, taken))
    head = _title_row(first, name, rows, taken) + _columns_row()
    return f'<div class="pathgrid statements" {attrs}>{head}{body}</div>'


def status(rows, taken):
    """covered when every row's taken is known and is all of its paths;
    gaps otherwise, as a row not known may have one."""
    return "covered" if all(count == row.paths for row, count in zip(rows, taken)) else "gaps"


def _title_row(first, name, rows, taken):
    """The row level with the def: its name, *complexity, then, above
    paths, its size, and, above taken, the paths taken, those of rows not
    known left out; its title saying so, for the function's bar."""
    size = method_statements.size(rows)
    seen = sum(count for count in taken if count is not None)
    cells = [f"*{method_statements.complexity(rows)}", str(size), str(seen)]
    title = f"{name}: {seen} of {size} paths taken"
    return _row(f'class="prow calls" data-line="{first}" title="{title}"', name, cells)


def _columns_row():
    """The row naming the paths and taken columns."""
    return _row('class="prow columns"', "line:col", ["", "paths", "taken"])


def _row_of(statement, count):
    """One statement's row: its line:column, the column two digits so they
    line up, its top, its paths, and how many were taken, ? when not known.
    A site's row is marked as one, so a click on it can open its tree."""
    cells = [statement.top, str(statement.paths), "?" if count is None else str(count)]
    css = "prow site" if statement.site else "prow"
    label = f"{statement.line}:{statement.column:02d}"
    return _row(f'class="{css}" data-line="{statement.line}"', label, cells)


def _row(attrs, label, cells):
    """A row div with attrs, its label, then a span per cell."""
    spans = "".join(f'<span class="pcell">{cell}</span>' for cell in cells)
    return f'<div {attrs}><span class="plabel">{label}</span>{spans}</div>'

"""The HTML index page: one sortable row per covered file, each linking to
that file's own page, then a Total row; with groups, one such table per
tab."""

from html import escape

from .html_template import asset, page as template_page

# The class and label of each of a total's three columns.
PARTS = (("taken", "taken"), ("of", "/ of"), ("percent", "%"))

# Why a total of no paths shows no percent.
NONE = "no method with two or more decisions"


def page(rows, total, groups=()):
    """The whole index page. rows are summary.files rows and total their
    summary.total. groups are [name, rows, total] for each group, each
    given a tab after All files; with none there is no tab bar, just the
    one table."""
    tables = [["All files", rows, total], *groups]
    names = ["sort.js", *(["tabs.js"] if groups else []), "settings.js", "theme.js"]
    return template_page(
        "index.html",
        script="".join(asset(name) for name in names),
        tabs=_tab_bar([name for name, _, _ in tables]) if groups else "",
        tables="\n".join(
            _table(index, own_rows, own_total) for index, (_, own_rows, own_total) in enumerate(tables)
        ),
        ignored="",
    )


def _tab_bar(names):
    """The tab bar of names, the first tab selected, each tab controlling
    the table of the same index."""
    tabs = "".join(
        f'<button type="button" role="tab" aria-selected="{"true" if index == 0 else "false"}"'
        f' aria-controls="files-{index}">{escape(name)}</button>'
        for index, name in enumerate(names)
    )
    return f'<nav class="tabs" role="tablist" aria-label="Groups">{tabs}</nav>'


def _table(index, rows, total):
    """The index-th tab's table of rows, total as its footer; any but the
    first starts hidden. Only the first, All files, gives its rows ids, as
    the others repeat its rows."""
    hidden = "" if index == 0 else ' hidden="hidden"'
    body = "\n".join(row(each, anchored=index == 0) for each in rows)
    return "\n".join(
        [
            f'<table class="files" id="files-{index}" role="tabpanel"{hidden}>',
            f"<thead>\n{_head()}\n</thead>",
            f"<tbody>\n{body}\n</tbody>",
            f"<tfoot>\n<tr>{_cell('Total', 'Total')}{_counts(total)}</tr>\n</tfoot>",
            "</table>",
        ]
    )


def _head():
    """The heading row: File and Sites, then the taken, / of and % columns
    of each file's total within each method, every column sortable."""
    fixed = [_heading("", 0, "text", "File"), _heading(' class="num"', 1, "number", "Sites")]
    parts = [_heading(f' class="{css}"', 2 + i, "number", label) for i, (css, label) in enumerate(PARTS)]
    return "<tr>\n" + "\n".join(fixed + parts) + "\n</tr>"


def _heading(attrs, column, kind, label):
    """A sortable heading, attrs its th's, sorting the column-th column as
    kind, text or number, its button showing label."""
    button = f'<button type="button" data-column="{column}" data-type="{kind}">{label}</button>'
    return f'<th{attrs} aria-sort="none">{button}</th>'


def row(each, anchored=False):
    """The table row of one summary.files row; each cell has a data-sort
    value for the page's column sorting. An anchored row has the id
    row-<path>, which the file's page links to."""
    path = escape(each["path"])
    link = f'<a href="files/{path}.html">{path}</a>'
    row_id = f' id="row-{path}"' if anchored else ""
    return f"<tr{row_id}>{_cell(path, link)}{_counts(each)}</tr>"


def _counts(each):
    """The cells after the file's: its sites, then its total within each
    method."""
    return _cell(each["sites"], each["sites"]) + "".join(_paths_cells(each["methods"]))


def _paths_cells(pair):
    """Three cells showing [taken, possible] paths, eg 3, / 6 and 50%, each
    sorted by its own number, so they read 3 / 6 50%. With no paths to take,
    as in a group no file is in, the percent shows -, titled with NONE,
    saying why, with an empty sort value, which sort.js keeps last whichever
    way the column is sorted. A percent half way rounds up: 62.5 is 63."""
    taken, possible = pair
    counts = [_cell(taken, taken, css="taken"), _cell(possible, f"/ {possible}", css="of")]
    if possible == 0:
        return [*counts, _cell("", "-", NONE, css="percent")]
    percent = int(100 * taken / possible + 0.5)
    return [*counts, _cell(percent, f"{percent}%", css="percent")]


def _cell(sort_value, content, title=None, css=None):
    """One table cell, sorted by sort_value, showing content, with title as
    its hover text and css as its class, each when there is one."""
    hover = f' title="{title}"' if title else ""
    klass = f' class="{css}"' if css else ""
    return f'<td{klass} data-sort="{sort_value}"{hover}>{content}</td>'

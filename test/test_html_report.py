from path_coverage.html_report import (
    index_page,
    index_row,
    jumps,
    listing,
    method_cards,
)

LINES = [
    {"number": 1, "text": "def can_attest(user, flow):", "status": None, "span": None},
    {"number": 2, "text": "    return user.active and user.admin", "status": "gaps", "span": (2, 2)},
]
TREES = {
    2: [
        {
            "operator": "and",
            "counts": [0, 1, 1],
            "cells": [False, True, False],
            "operands": [
                {"text": "user.active", "cells": [True, True, False]},
                {"text": "user.admin", "cells": [False, True, None]},
            ],
        }
    ]
}


def _cells(*names):
    """The grid cells naming each path's outcome."""
    return "".join(f'<span class="cell" data-cell="">{name}</span>' for name in names)


def test_4f08d204():
    """Example: a = x and (y or z); b = p or q on one line, both covered
    The span's button is collapsed and its tree hidden.
    It shows it holds two sites.
    The nested `or` is a row of its own, with its value on each path.
    Its operands are indented under its branch."""
    lines = [{"number": 7, "text": "    a = x and (y or z); b = p or q", "status": "covered", "span": (7, 7)}]
    trees = {
        7: [
            {
                "operator": "and",
                "counts": [1, 1],
                "cells": [True, False],
                "operands": [
                    {"text": "x", "cells": [True, False]},
                    {
                        "operator": "or",
                        "cells": [True, None],
                        "operands": [{"text": "y", "cells": [True, None]}, {"text": "z", "cells": [None, None]}],
                    },
                ],
            },
            {
                "operator": "or",
                "counts": [1, 1],
                "cells": [True, False],
                "operands": [{"text": "p", "cells": [True, False]}, {"text": "q", "cells": [None, False]}],
            },
        ]
    }
    html = listing(lines, trees)
    assert 'aria-expanded="false"' in html
    assert '<span class="site-count" data-site-count="">2</span>' in html
    assert '<div class="tree" id="tree-7" hidden="hidden">' in html
    assert (
        '<div class="row" data-subtree=""><span class="branch" data-branch="">&#9492;&#9472; </span>'
        f'<span class="operator" data-operator="">or</span>{_cells("T", "")}</div>'
        '<div class="row" data-operand=""><span class="branch" data-branch="">   &#9500;&#9472; </span>'
        '<span class="text" data-text="">y</span>'
    ) in html


def test_4f08d207():
    """Example: if order.big: ... else: ... with one of its two paths taken
    An if's arms are named then and else, as their text is statements.
    A plain arm marks each path that takes it with a tick."""
    lines = [{"number": 2, "text": "    if order.big:", "status": "gaps", "span": (2, 2)}]
    trees = {
        2: [
            {
                "operator": "if",
                "counts": [0, 1],
                "cells": [None, None],
                "operands": [
                    {"text": "order.big", "cells": [False, True]},
                    {"arm": "then", "text": None, "cells": [False, True], "body": None},
                    {"arm": "else", "text": None, "cells": [True, False], "body": None},
                ],
            }
        ]
    }
    html = listing(lines, trees)
    assert (
        '<div class="row" data-arm=""><span class="branch" data-branch="">&#9500;&#9472; </span>'
        '<span class="arm" data-label="">then</span>'
        '<span class="cell" data-cell=""></span><span class="cell" data-cell="">&#10003;</span></div>'
    ) in html


def test_4f08d20c():
    """Example: any(o.late for o in orders) with paths of 0 items, 1 item
    and 2+ items
    The items leaf's cells show 0, 1 and * for 2+."""
    lines = [{"number": 2, "text": "    return any(o.late for o in orders)", "status": "gaps", "span": (2, 2)}]
    trees = {
        2: [
            {
                "operator": "any",
                "counts": [0, 1, 1],
                "cells": [False, True, False],
                "operands": [
                    {"text": "orders", "cells": ["0 items", "1 item", "2+ items"]},
                    {"text": "o.late", "cells": [None, True, False]},
                ],
            }
        ]
    }
    html = listing(lines, trees)
    assert f'<span class="text" data-text="">orders</span>{_cells("0", "1", "*")}' in html


def test_4f08d208():
    """Example: fee, a write, if member and a return, called with member,
    and pack, a call
    Each function's card is hidden in the page until side.js moves it
    into the rail, one after another.
    fee's taken comes from its if's paths and its reaches: 3 of 4.
    pack was never reached, so it has a gap too."""
    source = (
        "def fee(member):\n"
        "    total = 100\n"
        "    if member:\n"
        "        total -= 5\n"
        "    return total\n"
        "\n"
        "def pack(box):\n"
        "    box.close()\n"
    )
    paths = {"k.py:3:4": [{"path": [True], "count": 1}, {"path": [False], "count": 0}]}
    reached = {"k.py:2:4": 1, "k.py:5:4": 1}
    html = method_cards(source, "k.py", paths, reached)
    fee, pack = html.split("\n")
    assert fee.startswith('<div class="pathgrid statements" id="paths-1"')
    assert '<span class="plabel">fee</span><span class="pcell">*2</span>' in fee
    assert '<span class="pcell">4</span><span class="pcell">3</span></div>' in fee
    assert pack.startswith('<div class="pathgrid statements" id="paths-7"')
    assert 'data-status="gaps"' in pack


def test_4f08d201():
    """Example: flow.py with decisions [3, 6] and methods [1, 4]
    Its row links the file to its own page.
    It shows each total in three cells: taken, / possible, percent.
    So they read 3 / 6 50%.
    Each cell has a data-sort value, its own number."""
    row = {"path": "src/model/flow.py", "sites": 2, "decisions": [3, 6], "methods": [1, 4]}
    assert index_row(row) == (
        "<tr>"
        '<td data-sort="src/model/flow.py"><a href="files/src/model/flow.py.html">src/model/flow.py</a></td>'
        '<td data-sort="2">2</td>'
        '<td class="taken" data-sort="3">3</td>'
        '<td class="of" data-sort="6">/ 6</td>'
        '<td class="percent" data-sort="50">50%</td>'
        '<td class="taken" data-sort="1">1</td>'
        '<td class="of" data-sort="4">/ 4</td>'
        '<td class="percent" data-sort="25">25%</td>'
        "</tr>"
    )


def test_4f08d205():
    """Example: a methods total of [0, 0], then of None
    [0, 0]: the file has no method of two or more decisions.
    So the percent shows -, titled with why.
    Its data-sort is empty, which sort.js keeps last either way.
    None: methods are not measured, so the row has no methods cells."""
    row = {"path": "src/kata.py", "sites": 1, "decisions": [1, 2], "methods": [0, 0]}
    title = "no method with two or more decisions"
    assert index_row(row).endswith(
        '<td class="taken" data-sort="0">0</td>'
        '<td class="of" data-sort="0">/ 0</td>'
        f'<td class="percent" data-sort="" title="{title}">-</td></tr>'
    )
    assert index_row({**row, "methods": None}).count("<td") == 5


def test_4f08d20b():
    """Example: groups code and docs, no file in docs
    The docs tab's Total within each decision is [0, 0].
    So its percent shows -, titled no decisions."""
    empty = {"sites": 0, "decisions": [0, 0], "methods": None}
    groups = [["code", [KATA], {**KATA, "path": "Total"}], ["docs", [], empty]]
    page = index_page([KATA], {**KATA, "path": "Total"}, groups)
    assert (
        '<td class="percent" data-sort="" title="no decisions">-</td></tr>\n</tfoot>'
    ) in page


def test_4f08d206():
    """Example: rows for kata.py and fee.py, methods measured
    The table has two heading rows.
    File and Sites span both.
    Each total's name spans its taken, / of and % columns.
    Every column is sortable, the within each method ones included.
    Its footer is the Total row, which sorting leaves last."""
    rows = [
        {"path": "src/kata.py", "sites": 2, "decisions": [3, 6], "methods": [0, 0]},
        {"path": "src/fee.py", "sites": 3, "decisions": [2, 4], "methods": [1, 4]},
    ]
    page = index_page(rows, {"sites": 5, "decisions": [5, 10], "methods": [1, 4]})

    def heading(attrs, column, kind, label):
        """A sortable th, as the page writes it."""
        button = f'<button type="button" data-column="{column}" data-type="{kind}">'
        return f'<th{attrs} aria-sort="none">{button}{label}</button></th>'

    parts = [(' class="taken"', "taken"), (' class="of"', "/ of"), (' class="percent"', "%")]
    top = [
        heading(' rowspan="2"', 0, "text", "File"),
        heading(' class="num" rowspan="2"', 1, "number", "Sites"),
        '<th class="group" colspan="3">Within each decision</th>',
        '<th class="group" colspan="3">Within each method</th>',
    ]
    bottom = [
        heading(attrs, 2 + 3 * group + i, "number", label)
        for group in range(2)
        for i, (attrs, label) in enumerate(parts)
    ]
    head = "\n".join(f"<tr>\n{chr(10).join(row)}\n</tr>" for row in (top, bottom))
    assert f"<thead>\n{head}\n</thead>" in page
    assert (
        '<tfoot>\n<tr><td data-sort="Total">Total</td><td data-sort="5">5</td>'
        '<td class="taken" data-sort="5">5</td><td class="of" data-sort="10">/ 10</td>'
        '<td class="percent" data-sort="50">50%</td>'
        '<td class="taken" data-sort="1">1</td><td class="of" data-sort="4">/ 4</td>'
        '<td class="percent" data-sort="25">25%</td></tr>\n'
        "</tfoot>"
    ) in page
    unmeasured = index_page(rows[:1], {"sites": 2, "decisions": [3, 6], "methods": None})
    assert "Within each method" not in unmeasured


KATA = {"path": "src/kata.py", "sites": 2, "decisions": [3, 6], "methods": None}
KATA_TEST = {"path": "test/test_kata.py", "sites": 1, "decisions": [1, 2], "methods": None}


def test_4f08d209():
    """Example: rows for src/kata.py and test/test_kata.py, groups code and
    test
    A tab bar names All files, then each group, the first selected.
    Each tab controls a table of its own, with its own Total row.
    Every table but the first starts hidden.
    The page's script switches tabs as well as sorting."""
    rows = [KATA, KATA_TEST]
    groups = [
        ["code", [KATA], {"sites": 2, "decisions": [3, 6], "methods": None}],
        ["test", [KATA_TEST], {"sites": 1, "decisions": [1, 2], "methods": None}],
    ]
    page = index_page(rows, {"sites": 3, "decisions": [4, 8], "methods": None}, groups)
    assert (
        '<nav class="tabs" role="tablist" aria-label="Groups">'
        '<button type="button" role="tab" aria-selected="true" aria-controls="files-0">'
        "All files</button>"
        '<button type="button" role="tab" aria-selected="false" aria-controls="files-1">'
        "code</button>"
        '<button type="button" role="tab" aria-selected="false" aria-controls="files-2">'
        "test</button></nav>"
    ) in page
    assert '<table class="files" id="files-0" role="tabpanel">' in page
    assert '<table class="files" id="files-1" role="tabpanel" hidden="hidden">' in page
    assert '<table class="files" id="files-2" role="tabpanel" hidden="hidden">' in page
    assert page.count("<tfoot>") == 3
    assert (
        '<tfoot>\n<tr><td data-sort="Total">Total</td><td data-sort="1">1</td>'
        '<td class="taken" data-sort="1">1</td><td class="of" data-sort="2">/ 2</td>'
        '<td class="percent" data-sort="50">50%</td></tr>\n</tfoot>'
    ) in page
    assert "Switches the index page's tabs" in page


def test_4f08d20a():
    """Example: rows for src/kata.py and test/test_kata.py, no groups
    There is no tab bar, just the one table.
    The page's script only sorts."""
    page = index_page([KATA, KATA_TEST], {"sites": 3, "decisions": [4, 8], "methods": None})
    assert 'role="tablist"' not in page
    assert page.count('<table class="files"') == 1
    assert "Switches the index page's tabs" not in page


def test_4f08d202():
    """The header lists a link to the first line of each span: covered
    spans, then spans with gaps."""
    assert jumps(LINES) == (
        '<nav class="jumps" aria-label="Sites">'
        '<div class="jump-list" data-jumps="covered"><span class="jump-label">Covered</span></div>'
        '<div class="jump-list" data-jumps="gaps"><span class="jump-label">Gaps</span>'
        '<a class="jump" data-status="gaps" href="#L2">2</a></div>'
        "</nav>"
    )


def test_4f08d203():
    """Example: a plain def line, then return user.active and user.admin
    with a path never taken
    A plain line is its nav cell, number and code.
    A span is a button over its numbers, expanded when it has gaps, with
    arrows to the previous and next gap.
    Its tree follows, open when it has gaps: the site's row counts each
    path, never taken first, and each operand row shows T or F per path."""
    nav = '<span class="nav" data-nav="">'
    arrows = (
        '<a data-prev="" href="#L2" aria-label="Previous gap, line 2">&#9650;</a>'
        '<a data-next="" href="#L2" aria-label="Next gap, line 2">&#9660;</a>'
    )
    assert listing(LINES, TREES) == (
        '<div class="code">\n'
        '<div class="line">' + nav + "</span>"
        '<span class="lineno" id="L1" data-line="1">1</span>'
        '<span class="src" data-src="">def can_attest(user, flow):</span></div>\n'
        '<div class="block">' + nav + arrows + "</span>"
        '<button type="button" class="lnum" data-status="gaps" aria-expanded="true" aria-controls="tree-2">'
        '<span class="lineno" id="L2" data-line="2">2</span></button>'
        '<div class="srcs"><span class="src" data-src="">    return user.active and user.admin</span></div></div>'
        '<div class="tree" id="tree-2">'
        '<div class="site" data-site="">'
        '<div class="row"><span class="operator" data-operator="">and</span>'
        '<span class="count never" data-count="">0</span><span class="count" data-count="">1</span>'
        '<span class="count" data-count="">1</span></div>'
        '<div class="row" data-operand=""><span class="branch" data-branch="">&#9500;&#9472; </span>'
        f'<span class="text" data-text="">user.active</span>{_cells("T", "T", "F")}</div>'
        '<div class="row" data-operand=""><span class="branch" data-branch="">&#9492;&#9472; </span>'
        f'<span class="text" data-text="">user.admin</span>{_cells("F", "T", "")}</div>'
        "</div></div>\n"
        "</div>"
    )

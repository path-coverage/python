from path_coverage import html_index, html_syntax, manifest, result
from path_coverage.html_file import Card, jumps, listing, nav_cell
from path_coverage.html_report import file_page, method_cards
from path_coverage.html_tree import site_rows


def _bx(branch):
    """The cell drawing branch, as html_tree writes it."""
    cells = "".join(f'<span class="bx" data-bx="{kind}"></span>' for kind in branch)
    return f'<span class="branch" data-branch="" aria-hidden="true">{cells}</span>'


def _cells(*names):
    """The grid cells naming each path's outcome."""
    return "".join(f'<span class="cell" data-cell="">{name}</span>' for name in names)


def test_4f08d204():
    """Example: a = x and (y or z), two paths taken once each
    The nested or is a row of its own, with its value on each path.
    Its operator is coloured as the keyword it is.
    Its operands are indented under its branch, a tee to y."""
    tree = {
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
    }
    html = "".join(site_rows(tree))
    assert (
        f'<div class="row" data-subtree="">{_bx("lhs")}'
        f'<span class="operator" data-operator=""><span class="k">or</span></span>{_cells("T", "")}</div>'
        f'<div class="row" data-operand="">{_bx("sssths")}<span class="text" data-text="">y</span>'
    ) in html


def test_4f08d207():
    """Example: if order.big: ... else: ... with one of its two paths taken
    An if's arms are named then and else, as their text is statements.
    Its then is marked as a name, no then being written in its code.
    Its else is coloured as the keyword it is.
    A plain arm marks each path that takes it, for CSS to tick."""
    tree = {
        "operator": "if",
        "counts": [0, 1],
        "cells": [None, None],
        "operands": [
            {"text": "order.big", "cells": [False, True]},
            {"arm": "then", "text": None, "cells": [False, True], "body": None},
            {"arm": "else", "text": None, "cells": [True, False], "body": None},
        ],
    }
    html = "".join(site_rows(tree))
    taken = '<span class="cell" data-cell="" data-mark="taken"></span>'
    blank = '<span class="cell" data-cell=""></span>'
    assert (
        f'<div class="row" data-arm="">{_bx("ths")}'
        f'<span class="arm" data-label="" data-named="">then</span>{blank}{taken}</div>'
        f'<div class="row" data-arm="">{_bx("lhs")}'
        f'<span class="arm" data-label=""><span class="k">else</span></span>{taken}{blank}</div>'
    ) in html


def test_4f08d20c():
    """Example: any(o.late for o in orders) with paths of 0 items, 1 item
    and 2+ items
    The items leaf's cells show 0, 1 and * for 2+."""
    tree = {
        "operator": "any",
        "counts": [0, 1, 1],
        "cells": [False, True, False],
        "operands": [
            {"text": "orders", "cells": ["0 items", "1 item", "2+ items"]},
            {"text": "o.late", "cells": [None, True, False]},
        ],
    }
    assert f'<span class="text" data-text="">orders</span>{_cells("0", "1", "*")}' in "".join(site_rows(tree))


def test_4f08d203():
    """Example: user.active and user.admin, a path never taken, then two
    taken, once and 1284 times
    The site's row marks each path 0, never taken, or *, taken.
    How many times shows on hover, its thousands apart.
    Each operand row shows T or F per path, blank where not reached."""
    tree = {
        "operator": "and",
        "counts": [0, 1, 1284],
        "cells": [False, True, False],
        "operands": [
            {"text": "user.active", "cells": [True, True, False]},
            {"text": "user.admin", "cells": [False, True, None]},
        ],
    }
    assert site_rows(tree) == [
        '<div class="row"><span class="operator" data-operator=""><span class="k">and</span></span>'
        '<span class="count never" data-count="" data-hover="0 times">0</span>'
        '<span class="count" data-count="" data-hover="1 time">*</span>'
        '<span class="count" data-count="" data-hover="1,284 times">*</span></div>',
        f'<div class="row" data-operand="">{_bx("ths")}'
        f'<span class="text" data-text="">user.active</span>{_cells("T", "T", "F")}</div>',
        f'<div class="row" data-operand="">{_bx("lhs")}'
        f'<span class="text" data-text="">user.admin</span>{_cells("F", "T", "")}</div>',
    ]


FEE = (
    "def fee(member):\n"
    "    total = 100\n"
    "    if member:\n"
    "        total -= 5\n"
    "    return total\n"
    "\n"
    "def pack(box):\n"
    "    box.close()\n"
)


def test_4f08d208():
    """Example: fee, a write, if member, its then's write and a return,
    called with member, and pack, a call never reached
    Each function has a Card: its lines, its def's column, its status.
    fee's taken comes from its if's paths and its reaches: 4 of 5.
    pack was never reached, so it has a gap too."""
    paths = {"k.py:3:4": [{"path": [True], "count": 1}, {"path": [False], "count": 0}]}
    reached = {"k.py:2:4": 1, "k.py:4:8": 1, "k.py:5:4": 1}
    fee, pack = method_cards(FEE, "k.py", paths, reached)
    assert (fee.first, fee.last, fee.column, fee.status, fee.top) == (1, 5, 0, "gaps", False)
    assert fee.html.startswith('<div class="pathgrid statements" id="paths-1"')
    assert (
        '<span class="plabel">fee</span><span class="pcell">*2</span>'
        '<span class="pcell not-taken">1</span><span class="pcell was-taken">4</span></div>'
    ) in fee.html
    assert (pack.first, pack.status) == (7, "gaps")


def _card(first, last, status, top=False, sites=None):
    """A Card of lines first to last, at column 0, of status, its HTML
    left out."""
    return Card(first, last, 0, status, top, sites, "")


def test_4f08d202():
    """Example: cards with gaps at lines 9 and 2, and one covered at 5
    The header jumps to the first line of each card with gaps, in order.
    With none, its list is marked empty, so the header keeps its height."""
    cards = [_card(9, 9, "gaps"), _card(5, 6, "covered"), _card(2, 3, "gaps")]
    assert jumps(cards) == (
        '<nav class="jumps" aria-label="Cards"><div class="jump-list">'
        '<span class="jump-label">Gaps</span>'
        '<a class="jump" data-status="gaps" href="#L2">2</a>'
        '<a class="jump" data-status="gaps" href="#L9">9</a></div></nav>'
    )
    assert '<div class="jump-list" data-empty="">' in jumps([_card(5, 6, "covered")])


def test_4f08d20d():
    """Example: the same cards, the gutter of line 2's row, then line 4's
    By a card's first line, an arrow to the card of its status before it,
    and one to the one after, wrapping round at either end.
    Any other row's gutter is empty, so the numbers stay aligned."""
    cards = [_card(9, 9, "gaps"), _card(5, 6, "covered"), _card(2, 3, "gaps")]
    assert nav_cell([2], cards) == (
        '<span class="nav" data-nav="">'
        '<a data-prev="" data-status="gaps" href="#L9" aria-label="Previous card with gaps, line 9"></a>'
        '<a data-next="" data-status="gaps" href="#L9" aria-label="Next card with gaps, line 9"></a>'
        "</span>"
    )
    assert nav_cell([4], cards) == '<span class="nav" data-nav=""></span>'


def test_4f08d20e():
    """Example: f, on lines 1 to 2, covered, then x = a or b, outside every
    function, on line 3, its top card with gaps
    f's def number opens its card; its body's line starts folded.
    Its code is marked in f, its def line's with its text's length.
    The loose line is one button, wearing its top card's status, opening
    it."""
    lines = [
        {"number": 1, "text": "def f():", "status": None, "span": None},
        {"number": 2, "text": "    return 1", "status": None, "span": None},
        {"number": 3, "text": "x = a or b", "status": "gaps", "span": (3, 3)},
    ]
    cards = [_card(1, 2, "covered"), _card(3, 3, "gaps", top=True, sites=1)]
    html = listing(lines, cards)
    assert (
        '<span class="lineno mdef" data-status="covered" aria-expanded="false" id="L1" data-line="1">1</span>'
        '<span class="src in-method def-line" data-method-status="covered" style="--def-col: 0; --def-end: 8"'
        ' data-src="">def f():</span>'
    ) in html
    assert '<div class="line method-folded">' in html
    assert 'class="src in-method method-end" data-method-status="covered" style="--def-col: 0"' in html
    assert (
        '<button type="button" class="lnum loose" data-status="gaps" aria-expanded="false"'
        ' aria-controls="paths-3"><span class="lineno" id="L3" data-line="3">3</span></button>'
    ) in html


SHOP = (
    "RATE = 2 if FAST else 1\n"
    "class Shop:\n"
    "    SIZE = 3 if BIG else 1\n"
    "    def fee(self, rush):\n"
    "        if rush:\n"
    "            return 9\n"
    "        elif self.member:\n"
    "            return 5\n"
    "        return 7\n"
)


def _shop_page():
    """SHOP's page, as if it were k.py, no path taken."""
    sites = manifest.sites(SHOP, "k.py")
    paths = result.paths(sites, {})
    return file_page("k.py", SHOP, sites, result.operands(sites, {}), paths, {})


def test_4f08d210():
    """Example: SHOP's page, RATE at the top, SIZE in Shop, fee's if and
    elif in its card
    Each span of sites outside every function has a top card.
    It is titled by its scope: the class holding it, or file.
    A site's row folds its tree; an elif's tree is labelled elif."""
    page = _shop_page()
    assert '<div class="pathgrid statements top-level" id="paths-1"' in page
    assert '<div class="pathgrid statements top-level" id="paths-3"' in page
    assert '<span class="plabel">file</span>' in page
    assert '<span class="plabel">Shop</span>' in page
    assert '<div class="fold" data-site="k.py:7:8" hidden="hidden">' in page
    assert '<span class="operator" data-operator=""><span class="k">elif</span></span>' in page


def test_4f08d211():
    """Example: SHOP's page
    Its code is coloured: keywords, numbers and capitalised names.
    Its scripts open its cards, then keep its settings and its theme."""
    page = _shop_page()
    assert '<span class="k">class</span> <span class="t">Shop</span>:' in page
    assert html_syntax.html("x = 10  # ten", html_syntax.of("x = 10  # ten")[1]) == (
        'x = <span class="n">10</span>  <span class="c"># ten</span>'
    )
    assert page.count("<script>") == 1
    assert "data-theme" in page


def test_4f08d212():
    """Example: a string over lines 1 to 3
    A token over many lines is coloured on each line it reaches."""
    assert html_syntax.of('x = """a\nb\nc"""\n') == {1: [[4, 8, "s"]], 2: [[0, 1, "s"]], 3: [[0, 4, "s"]]}


def test_4f08d201():
    """Example: flow.py with methods [1, 4]
    Its row links the file to its own page, its id its path.
    It shows its total in three cells: taken, / possible, percent.
    So they read 1 / 4 25%.
    Each cell has a data-sort value, its own number."""
    row = {"path": "src/model/flow.py", "sites": 2, "decisions": [3, 6], "methods": [1, 4]}
    assert html_index.row(row, anchored=True) == (
        '<tr id="row-src/model/flow.py">'
        '<td data-sort="src/model/flow.py"><a href="files/src/model/flow.py.html">src/model/flow.py</a></td>'
        '<td data-sort="2">2</td>'
        '<td class="taken" data-sort="1">1</td>'
        '<td class="of" data-sort="4">/ 4</td>'
        '<td class="percent" data-sort="25">25%</td>'
        "</tr>"
    )


def test_4f08d205():
    """Example: a methods total of [0, 0], then of [5, 8]
    [0, 0]: the file has no paths to take.
    So the percent shows -, titled with why.
    Its data-sort is empty, which sort.js keeps last either way.
    5 of 8 is 62.5%, which rounds up to 63%."""
    row = {"path": "src/kata.py", "sites": 1, "decisions": [1, 2], "methods": [0, 0]}
    title = "no method with two or more decisions"
    assert html_index.row(row).endswith(
        '<td class="taken" data-sort="0">0</td>'
        '<td class="of" data-sort="0">/ 0</td>'
        f'<td class="percent" data-sort="" title="{title}">-</td></tr>'
    )
    assert html_index.row({**row, "methods": [5, 8]}).endswith('<td class="percent" data-sort="63">63%</td></tr>')


KATA = {"path": "src/kata.py", "sites": 2, "decisions": [3, 6], "methods": [1, 2]}
KATA_TEST = {"path": "test/test_kata.py", "sites": 1, "decisions": [1, 2], "methods": [1, 2]}


def test_4f08d206():
    """Example: rows for kata.py and test_kata.py
    The table has one heading row: File, Sites, and the total within each
    method's taken, / of and % columns.
    Every column is sortable.
    Its footer is the Total row, which sorting leaves last."""
    page = html_index.page([KATA, KATA_TEST], {"sites": 3, "decisions": [4, 8], "methods": [2, 4]})

    def heading(attrs, column, kind, label):
        """A sortable th, as the page writes it."""
        button = f'<button type="button" data-column="{column}" data-type="{kind}">'
        return f'<th{attrs} aria-sort="none">{button}{label}</button></th>'

    head = [
        heading("", 0, "text", "File"),
        heading(' class="num"', 1, "number", "Sites"),
        heading(' class="taken"', 2, "number", "taken"),
        heading(' class="of"', 3, "number", "/ of"),
        heading(' class="percent"', 4, "number", "%"),
    ]
    assert "<thead>\n<tr>\n" + "\n".join(head) + "\n</tr>\n</thead>" in page
    assert (
        '<tfoot>\n<tr><td data-sort="Total">Total</td><td data-sort="3">3</td>'
        '<td class="taken" data-sort="2">2</td><td class="of" data-sort="4">/ 4</td>'
        '<td class="percent" data-sort="50">50%</td></tr>\n</tfoot>'
    ) in page


def test_4f08d209():
    """Example: rows for src/kata.py and test/test_kata.py, groups code and
    test
    A tab bar names All files, then each group, the first selected.
    Each tab controls a table of its own, with its own Total row.
    Every table but the first starts hidden.
    The page's script switches tabs as well as sorting."""
    total = {"sites": 1, "decisions": [1, 2], "methods": [1, 2]}
    groups = [["code", [KATA], total], ["test", [KATA_TEST], total]]
    page = html_index.page([KATA, KATA_TEST], {"sites": 3, "decisions": [4, 8], "methods": [2, 4]}, groups)
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
    assert page.count("<tfoot>") == 3
    assert "Switches the index page's tabs" in page


def test_4f08d20a():
    """Example: rows for src/kata.py and test/test_kata.py, no groups
    There is no tab bar, just the one table.
    The page's script only sorts, then keeps its settings and theme."""
    page = html_index.page([KATA, KATA_TEST], {"sites": 3, "decisions": [4, 8], "methods": [2, 4]})
    assert 'role="tablist"' not in page
    assert page.count('<table class="files"') == 1
    assert "Switches the index page's tabs" not in page


def test_4f08d20b():
    """Example: groups code and docs, no file in docs
    The docs tab's Total within each method is [0, 0].
    So its percent shows -."""
    empty = {"sites": 0, "decisions": [0, 0], "methods": [0, 0]}
    page = html_index.page([KATA], KATA, [["code", [KATA], KATA], ["docs", [], empty]])
    assert '<td class="percent" data-sort="" title="no method with two or more decisions">-</td></tr>\n</tfoot>' in page

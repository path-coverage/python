import re

from path_coverage import method_statements
from path_coverage.html_statements import card, top_card


def _cells(html):
    """The texts of each row of html's card: its label, then each of its
    cells, a coloured top's text included."""
    rows = re.findall(r'<div class="prow[^"]*"[^>]*>(.*?)</div>', html)
    return [re.findall(r"<span[^>]*>([^<]*)</span>", row) for row in rows]


SHIP = (
    "def ship(order):\n"
    "    if order.paid:\n"
    "        order.pack()\n"
    "    return order\n"
)


def test_c81d5f01():
    """Example: ship, an if with only its then taken, its then's call and
    a return, neither known
    Its card is hidden, level with its def, line 1, to its last line, 4.
    Its title row has its name and its complexity.
    Above not taken it has how many of its paths were not taken, the
    rows not known among them, and above taken how many were.
    Its next row titles its columns.
    A row's column is two digits, eg 2:04, so they line up.
    Each row after has its line:column, top, paths not taken and taken.
    A row not known is ? for both.
    It has a gap, as its if's else was never taken.
    A site's row is marked as one, to open its tree when clicked."""
    site = "k.py:1:0"
    rows = method_statements.of(SHIP, "k.py")[site]
    html = card(site, "ship", rows, [1, None, None], 4)
    assert 'id="paths-1" data-first="1"' in html
    assert 'data-col="0" data-last="4"' in html
    assert 'data-status="gaps" hidden="hidden"' in html
    assert '<div class="prow site" data-line="2">' in html
    assert '<div class="prow" data-line="4">' in html
    assert _cells(html) == [
        ["ship", "*2", "3", "1"],
        ["line:col", "", "not taken", "taken"],
        ["2:04", "if", "1", "1"],
        ["3:08", "()", "?", "?"],
        ["4:04", "return", "?", "?"],
    ]


def test_c81d5f02():
    """Example: is_member, returning one and, all 3 of its paths taken
    Its one row is a site with every path taken, so it is covered.
    Its not taken is 0, no gap, so it is marked none, coloured as taken."""
    source = (
        "def is_member(user):\n"
        "    return user.member and not user.banned\n"
    )
    site = "k.py:1:0"
    rows = method_statements.of(source, "k.py")[site]
    html = card(site, "is_member", rows, [3], 2)
    assert 'data-status="covered"' in html
    assert '<span class="pcell not-taken none">0</span><span class="pcell was-taken">3</span>' in html


def test_c81d5f03():
    """Example: ship's card, its if's tree given
    A top that quotes code is coloured as the code is: if a keyword.
    A top naming a kind of statement, eg (), is plain.
    A site's row folding a tree has an arrow before its line:column.
    Its fold follows it, hidden, holding the tree's rows."""
    site = "k.py:1:0"
    rows = method_statements.of(SHIP, "k.py")[site]
    html = card(site, "ship", rows, [1, 1, 1], 4, lambda name: f"<i>{name}</i>")
    assert (
        '<div class="prow site" data-line="2">'
        '<button type="button" class="fold-arrow" aria-expanded="false" aria-label="Paths of 2:04"></button>'
        '<span class="plabel">2:04</span><span class="pcell"><span class="k">if</span></span>'
    ) in html
    assert '<span class="pcell">()</span>' in html
    assert (
        '<div class="fold" data-site="k.py:2:4" hidden="hidden">'
        '<div class="site" data-site=""><i>k.py:2:4</i></div></div>'
    ) in html


def test_c81d5f04():
    """Example: RATE = 2 if FAST else 1, outside every function, its then
    taken
    Its card is a top card, titled by its scope, file.
    It is marked top-level, as it is no function's."""
    source = "RATE = 2 if FAST else 1\n"
    rows = method_statements.top_rows(source, "k.py")
    html = top_card("k.py:1:0", "file", rows, [1], 1)
    assert html.startswith('<div class="pathgrid statements top-level" id="paths-1"')
    assert _cells(html)[0] == ["file", "*2", "1", "1"]

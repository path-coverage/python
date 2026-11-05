import re

from path_coverage import method_statements
from path_coverage.html_statements import card


def _cells(html):
    """The texts of each row of html's card: its label, then each of its
    cells."""
    rows = re.findall(r'<div class="prow[^"]*"[^>]*>(.*?)</div>', html)
    return [re.findall(r"<span[^>]*>([^<]*)</span>", row) for row in rows]


def test_c81d5f01():
    """Example: ship, an if with only its then taken, then a return
    Its card is hidden, level with its def, line 1, to its last line, 4.
    Its title row has its name and its complexity.
    Its title says how many paths were taken, for its bar to show.
    Above paths it has its size, the sum of its rows' paths.
    Above taken it has how many of those were taken.
    Its next row titles its columns.
    A row's column is two digits, eg 2:04, so they line up.
    Each row after has its line:column, top, paths and taken.
    A taken not known is ?.
    It has a gap, as its if's else was never taken.
    A site's row is marked as one, to open its tree when clicked."""
    source = (
        "def ship(order):\n"
        "    if order.paid:\n"
        "        order.pack()\n"
        "    return order\n"
    )
    site = "k.py:1:0"
    rows = method_statements.of(source, "k.py")[site]
    html = card(site, "ship", rows, [1, None], 4)
    assert 'id="paths-1" data-first="1"' in html
    assert 'data-col="0" data-last="4"' in html
    assert 'data-status="gaps" hidden="hidden"' in html
    assert 'title="ship: 1 of 3 paths taken"' in html
    assert '<div class="prow site" data-line="2">' in html
    assert '<div class="prow" data-line="4">' in html
    assert _cells(html) == [
        ["ship", "*2", "3", "1"],
        ["line:col", "", "paths", "taken"],
        ["2:04", "if", "2", "1"],
        ["4:04", "return", "1", "?"],
    ]


def test_c81d5f02():
    """Example: is_member, returning one and, all 3 of its paths taken
    Its one row is a site with every path taken, so it is covered."""
    source = (
        "def is_member(user):\n"
        "    return user.member and not user.banned\n"
    )
    site = "k.py:1:0"
    rows = method_statements.of(source, "k.py")[site]
    assert 'data-status="covered"' in card(site, "is_member", rows, [3], 2)

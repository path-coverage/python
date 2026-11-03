from condition_coverage.html_report import index_row, jumps, listing

LINES = [
    {"number": 1, "text": "def can_attest(user, flow):", "status": None, "span": None},
    {"number": 2, "text": "    return user.active and user.admin", "status": "gaps", "span": (2, 2)},
]
TREES = {
    2: [
        {
            "operator": "and",
            "operands": [
                {"text": "user.active", "truthy": 1, "falsy": 1, "gap": None},
                {"text": "user.admin", "truthy": 1, "falsy": 0, "gap": "never false"},
            ],
        }
    ]
}


def test_4f08d204():
    """A covered span's button is collapsed and its tree hidden; a span
    holding two or more sites shows how many; a nested condition is a row
    of its own, its operands indented under its branch."""
    lines = [{"number": 7, "text": "    ok = a and (b or c); d or e", "status": "covered", "span": (7, 7)}]
    covered = {"truthy": 1, "falsy": 1, "gap": None}
    trees = {
        7: [
            {
                "operator": "and",
                "operands": [
                    {"text": "a", **covered},
                    {"operator": "or", "operands": [{"text": "b", **covered}, {"text": "c", **covered}]},
                ],
            },
            {"operator": "or", "operands": [{"text": "d", **covered}, {"text": "e", **covered}]},
        ]
    }
    html = listing(lines, trees)
    assert 'aria-expanded="false"' in html
    assert '<span class="site-count" data-site-count="">2</span>' in html
    assert '<div class="tree" id="tree-7" hidden="hidden">' in html
    assert (
        '<div class="row" data-subtree=""><span class="branch" data-branch="">&#9492;&#9472; </span>'
        '<span class="operator" data-operator="">or</span></div>'
        '<div class="row" data-operand=""><span class="branch" data-branch="">   &#9500;&#9472; </span>'
        '<span class="text" data-text="">b</span>'
    ) in html


def test_4f08d201():
    """An index row links the file to its page and gives each cell a
    data-sort value for the page's column sorting."""
    row = {"path": "src/model/flow.py", "sites": 2, "seen": 5, "outcomes": 9, "percent": 56, "missing": 4}
    assert index_row(row) == (
        "<tr>"
        '<td data-sort="src/model/flow.py"><a href="files/src/model/flow.py.html">src/model/flow.py</a></td>'
        '<td data-sort="2">2</td>'
        '<td data-sort="56">5 / 9 &middot; 56%</td>'
        '<td data-sort="4">4</td>'
        "</tr>"
    )


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
    """A plain line is its nav cell, number and code; a span is a button
    over its numbers (expanded when it has gaps, with arrows to the previous
    and next gap) followed by its tree, open when it has gaps, the operands
    branching from their operator."""
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
        '<div class="row headings" data-heading=""><span>condition</span><span>true</span><span>false</span><span>gap</span></div>'
        '<div class="site" data-site="">'
        '<div class="row"><span class="operator" data-operator="">and</span></div>'
        '<div class="row" data-operand=""><span class="branch" data-branch="">&#9500;&#9472; </span>'
        '<span class="text" data-text="">user.active</span><span class="truthy" data-truthy="">1</span>'
        '<span class="falsy" data-falsy="">1</span><span class="gap" data-gap=""></span></div>'
        '<div class="row" data-operand=""><span class="branch" data-branch="">&#9492;&#9472; </span>'
        '<span class="text" data-text="">user.admin</span><span class="truthy" data-truthy="">1</span>'
        '<span class="falsy" data-falsy="">0</span><span class="gap" data-gap="">never false</span></div>'
        "</div></div>\n"
        "</div>"
    )

from path_coverage.gaps import code, lines, operand_gap

SITE = "src/model/flow.py:2:11"
TEXTS = {SITE: ["user.active", "user.admin", "flow.public"]}


def test_d40e6a01():
    """Example: user.active and (user.admin or flow.public), with two of
    its four paths taken
    One line per path never taken, in possible-path order.
    Each names the outcome of every leaf the path reaches, by its text.
    A leaf the path never reaches is left out."""
    operands = {SITE: [{"truthy": 2, "falsy": 1}, {"truthy": 0, "falsy": 2}, {"truthy": 2, "falsy": 0}]}
    paths = {
        SITE: [
            {"path": [True, True, None], "count": 0},
            {"path": [True, False, True], "count": 2},
            {"path": [True, False, False], "count": 0},
            {"path": [False, None, None], "count": 1},
        ]
    }
    assert lines(operands, paths, TEXTS) == [
        f"{SITE} path never taken: `user.active` true, `user.admin` true",
        f"{SITE} path never taken: `user.active` true, `user.admin` false, `flow.public` false",
    ]


def test_d40e6a02():
    """Example: a site none of whose leaves ever ran
    It gets one line, `never reached`, not a line per path."""
    operands = {SITE: [{"truthy": 0, "falsy": 0}] * 3}
    paths = {SITE: [{"path": [True, True, None], "count": 0}]}
    assert lines(operands, paths, TEXTS) == [f"{SITE} never reached"]


def test_d40e6a04():
    """Example: tags or [], its tags once truthy and once falsy, so its []
    evaluated once
    [] can only be falsy, so having run it has no gap, though it was never
    true; tags, taken both ways, has none either."""
    counts = [{"truthy": 1, "falsy": 1}, {"truthy": 0, "falsy": 1, "only": "falsy"}]
    assert [operand_gap(each) for each in counts] == [[], []]


def test_d40e6a03():
    """Example: leaf texts holding backticks, or spread over lines
    Each is quoted as a Markdown code span on one line.
    Its fence is one backtick longer than any run inside it."""
    assert code("tags\n    or []") == "`tags or []`"
    assert code("x == '`'") == "``x == '`'``"
    assert code("`x`") == "`` `x` ``"

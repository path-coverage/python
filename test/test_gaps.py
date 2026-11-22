from path_coverage.gaps import code, lines, operand_gap
from tallies import untested

DECISION = "src/model/flow.py:2:11"
TEXTS = {DECISION: ["user.active", "user.admin", "flow.public"]}


def test_d40e6a01():
    """Example: user.active and (user.admin or flow.public), with two of
    its four paths taken
    One line per path never taken, in possible-path order.
    Each names the outcome of every leaf the path reaches, by its text.
    A leaf the path never reaches is left out."""
    operands = {DECISION: [{"truthy": untested(2), "falsy": untested(1)}, {"truthy": untested(0), "falsy": untested(2)}, {"truthy": untested(2), "falsy": untested(0)}]}
    paths = {
        DECISION: [
            {"path": [True, True, None], "tests": untested(0)},
            {"path": [True, False, True], "tests": untested(2)},
            {"path": [True, False, False], "tests": untested(0)},
            {"path": [False, None, None], "tests": untested(1)},
        ]
    }
    assert lines(operands, paths, TEXTS) == [
        f"{DECISION} path never taken: `user.active` true, `user.admin` true",
        f"{DECISION} path never taken: `user.active` true, `user.admin` false, `flow.public` false",
    ]


def test_d40e6a02():
    """Example: a decision none of whose leaves ever ran
    It gets one line, `never reached`, not a line per path."""
    operands = {DECISION: [{"truthy": untested(0), "falsy": untested(0)}] * 3}
    paths = {DECISION: [{"path": [True, True, None], "tests": untested(0)}]}
    assert lines(operands, paths, TEXTS) == [f"{DECISION} never reached"]


def test_d40e6a04():
    """Example: tags or [], its tags once truthy and once falsy, so its []
    evaluated once
    [] can only be falsy, so having run it has no gap, though it was never
    true; tags, taken both ways, has none either."""
    counts = [{"truthy": untested(1), "falsy": untested(1)}, {"truthy": untested(0), "falsy": untested(1), "only": "falsy"}]
    assert [operand_gap(each) for each in counts] == [[], []]


def test_d40e6a03():
    """Example: leaf texts holding backticks, or spread over lines
    Each is quoted as a Markdown code span on one line.
    Its fence is one backtick longer than any run inside it."""
    assert code("tags\n    or []") == "`tags or []`"
    assert code("x == '`'") == "``x == '`'``"

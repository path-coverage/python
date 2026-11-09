from path_coverage.manifest import decisions
from path_coverage.source_lines import lines_of

SOURCE = (
    "def can_attest(user, flow):\n"
    "    if user.active and user.admin:\n"
    "        return True\n"
    "    assert (\n"
    "        flow.public\n"
    "        or flow.owner == user\n"
    "    )\n"
)


def test_0d9b5501():
    """Each line has its number and text; a line a decision spans has the
    decision's status and its span, from the line the decision's code starts on to
    the line its last operand ends on, so a multi-line condition is one
    span, even an or named at its keyword on its second line."""
    operands = {
        "src/model/flow.py:2:4": [{"truthy": 1, "falsy": 1}],
        "src/model/flow.py:2:19": [{"truthy": 1, "falsy": 1}, {"truthy": 1, "falsy": 1}],
        "src/model/flow.py:6:8": [{"truthy": 2, "falsy": 0}, {"truthy": 0, "falsy": 0}],
    }
    found = decisions(SOURCE, "src/model/flow.py")
    assert lines_of(SOURCE, found, operands) == [
        {"number": 1, "text": "def can_attest(user, flow):", "status": None, "span": None},
        {"number": 2, "text": "    if user.active and user.admin:", "status": "covered", "span": (2, 2)},
        {"number": 3, "text": "        return True", "status": None, "span": None},
        {"number": 4, "text": "    assert (", "status": None, "span": None},
        {"number": 5, "text": "        flow.public", "status": "gaps", "span": (5, 6)},
        {"number": 6, "text": "        or flow.owner == user", "status": "gaps", "span": (5, 6)},
        {"number": 7, "text": "    )", "status": None, "span": None},
    ]


def test_0d9b5502():
    """Decisions whose spans overlap share one merged span, which has gaps when
    any of them has, so a covered decision never hides another's gaps."""
    source = (
        "def visible(flows, user):\n"
        "    return [f for f in flows if f.public or f.owner == user] or (\n"
        "        user.admin and flows\n"
        "    )\n"
    )
    operands = {
        "src/model/flow.py:2:61": [{"truthy": 3, "falsy": 1}, {"truthy": 1, "falsy": 1}, {"truthy": 1, "falsy": 1}],
        "src/model/flow.py:2:29": [{"truthy": 4, "falsy": 2}],
        "src/model/flow.py:2:41": [{"truthy": 4, "falsy": 2}, {"truthy": 0, "falsy": 2}],
    }
    found = decisions(source, "src/model/flow.py")
    assert [(line["status"], line["span"]) for line in lines_of(source, found, operands)] == [
        (None, None),
        ("gaps", (2, 3)),
        ("gaps", (2, 3)),
        (None, None),
    ]

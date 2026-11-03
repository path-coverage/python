from condition_coverage.manifest import sites
from condition_coverage.source_lines import lines_of

SOURCE = (
    "def can_attest(user, flow):\n"
    "    if user.active and user.admin:\n"
    "        return True\n"
    "    return (\n"
    "        flow.public\n"
    "        or flow.owner == user\n"
    "    )\n"
)


def test_0d9b5501():
    """Each line has its number and text; a line a site spans has the
    site's status and its span, from the line the site starts on to the
    line its last operand ends on, so a multi-line condition is one span."""
    operands = {
        "src/model/flow.py:2:7": [{"truthy": 1, "falsy": 1}, {"truthy": 1, "falsy": 1}],
        "src/model/flow.py:5:8": [{"truthy": 2, "falsy": 0}, {"truthy": 0, "falsy": 0}],
    }
    found = sites(SOURCE, "src/model/flow.py")
    assert lines_of(SOURCE, found, operands) == [
        {"number": 1, "text": "def can_attest(user, flow):", "status": None, "span": None},
        {"number": 2, "text": "    if user.active and user.admin:", "status": "covered", "span": (2, 2)},
        {"number": 3, "text": "        return True", "status": None, "span": None},
        {"number": 4, "text": "    return (", "status": None, "span": None},
        {"number": 5, "text": "        flow.public", "status": "gaps", "span": (5, 6)},
        {"number": 6, "text": "        or flow.owner == user", "status": "gaps", "span": (5, 6)},
        {"number": 7, "text": "    )", "status": None, "span": None},
    ]


def test_0d9b5502():
    """Sites whose spans overlap share one merged span, which has gaps when
    any of them has, so a covered site never hides another's gaps."""
    source = (
        "def visible(flows, user):\n"
        "    return [f for f in flows if f.public or f.owner == user] or (\n"
        "        user.admin and flows\n"
        "    )\n"
    )
    operands = {
        "src/model/flow.py:2:11": [{"truthy": 3, "falsy": 1}, {"truthy": 1, "falsy": 1}, {"truthy": 1, "falsy": 1}],
        "src/model/flow.py:2:32": [{"truthy": 4, "falsy": 2}, {"truthy": 0, "falsy": 2}],
    }
    found = sites(source, "src/model/flow.py")
    assert [(line["status"], line["span"]) for line in lines_of(source, found, operands)] == [
        (None, None),
        ("gaps", (2, 3)),
        ("gaps", (2, 3)),
        (None, None),
    ]

from condition_coverage.gaps import lines


def test_d40e6a01():
    """One line per missing outcome in manifest order, one `never reached`
    line for a site none of whose operands ran, nothing for a site seen
    both ways."""
    operands = {
        "src/model/flow.py:2:11": [
            {"truthy": 3, "falsy": 1},
            {"truthy": 0, "falsy": 2},
            {"truthy": 0, "falsy": 0},
        ],
        "src/model/flow.py:5:11": [
            {"truthy": 0, "falsy": 0},
            {"truthy": 0, "falsy": 0},
        ],
        "src/model/trail.py:9:15": [
            {"truthy": 4, "falsy": 1},
            {"truthy": 2, "falsy": 2},
        ],
        "src/model/trail.py:12:8": [
            {"truthy": 1, "falsy": 1},
            {"truthy": 5, "falsy": 0},
        ],
    }
    assert lines(operands) == [
        "src/model/flow.py:2:11 operand 1 never true",
        "src/model/flow.py:2:11 operand 2 never evaluated",
        "src/model/flow.py:5:11 never reached",
        "src/model/trail.py:12:8 operand 1 never false",
    ]


def test_d40e6a02():
    """A leaf with one possible outcome needs only to be evaluated."""
    operands = {
        "src/model/tags.py:1:7": [
            {"truthy": 2, "falsy": 1},
            {"truthy": 0, "falsy": 1, "only": "falsy"},
        ],
        "src/model/tags.py:2:7": [
            {"truthy": 3, "falsy": 1},
            {"truthy": 0, "falsy": 0, "only": "truthy"},
        ],
    }
    assert lines(operands) == ["src/model/tags.py:2:7 operand 1 never evaluated"]

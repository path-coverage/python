from condition_coverage.summary import files


def test_b7e21901():
    """One row per file in path order: its sites, the outcomes seen out of
    those possible (a fixed leaf has one possible outcome), the rounded
    percent, and how many are missing."""
    operands = {
        "src/model/trail.py:12:8": [
            {"truthy": 1, "falsy": 1},
            {"truthy": 5, "falsy": 0},
        ],
        "src/model/flow.py:2:11": [
            {"truthy": 3, "falsy": 1},
            {"truthy": 0, "falsy": 2},
            {"truthy": 0, "falsy": 0},
        ],
        "src/model/flow.py:9:7": [
            {"truthy": 2, "falsy": 0},
            {"truthy": 0, "falsy": 1, "only": "falsy"},
        ],
    }
    assert files(operands) == [
        {"path": "src/model/flow.py", "sites": 2, "seen": 5, "outcomes": 9, "percent": 56, "missing": 4},
        {"path": "src/model/trail.py", "sites": 1, "seen": 3, "outcomes": 4, "percent": 75, "missing": 1},
    ]

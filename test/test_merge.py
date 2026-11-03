from condition_coverage.merge import merge


def test_f2c67d01():
    """Runs' operands are merged by adding their counts, operand by operand,
    keeping only, so a gap shows only when every run left it."""
    worker_0 = {
        "src/model/tags.py:1:7": [
            {"truthy": 2, "falsy": 0},
            {"truthy": 0, "falsy": 0, "only": "falsy"},
        ],
        "src/model/flow.py:2:11": [
            {"truthy": 1, "falsy": 1},
            {"truthy": 1, "falsy": 0},
        ],
    }
    worker_1 = {
        "src/model/tags.py:1:7": [
            {"truthy": 3, "falsy": 1},
            {"truthy": 0, "falsy": 1, "only": "falsy"},
        ],
        "src/model/flow.py:2:11": [
            {"truthy": 1, "falsy": 1},
            {"truthy": 1, "falsy": 0},
        ],
    }
    assert merge([worker_0, worker_1]) == {
        "src/model/tags.py:1:7": [
            {"truthy": 5, "falsy": 1},
            {"truthy": 0, "falsy": 1, "only": "falsy"},
        ],
        "src/model/flow.py:2:11": [
            {"truthy": 2, "falsy": 2},
            {"truthy": 2, "falsy": 0},
        ],
    }

from path_coverage.merge import merge, merge_paths


def test_f2c67d02():
    """Example: two workers' paths for flow.py's and, one taking
    [True, True] once, the other twice and [False, None] once
    Each path's counts are added across the runs.
    A path in one run only keeps its count."""
    decision = "src/model/flow.py:2:11"
    worker_0 = {decision: [{"path": [True, True], "count": 1}, {"path": [False, None], "count": 0}]}
    worker_1 = {decision: [{"path": [True, True], "count": 2}, {"path": [False, None], "count": 1}]}
    assert merge_paths([worker_0, worker_1]) == {
        decision: [{"path": [True, True], "count": 3}, {"path": [False, None], "count": 1}]
    }


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

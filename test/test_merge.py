from path_coverage.merge import merge, merge_paths, merge_ways
from path_coverage.tally import Tally
from tallies import untested

PROMPT = "test/test_orders.py::test_prompt_order_ships"
LATE = "test/test_orders.py::test_late_order_waits"


def test_f2c67d03():
    """Example: two xdist workers, one running test_prompt_order_ships,
    the other test_late_order_waits, each taking flow.py's and's
    [True, True] path, and calling ship the same way
    Counts add test by test, so the merged run still tells which test
    took which path, and which way."""
    decision = "src/model/flow.py:2:23"
    worker_0 = {decision: [{"path": [True, True], "tests": Tally({PROMPT: 2})}]}
    worker_1 = {decision: [{"path": [True, True], "tests": Tally({LATE: 1})}]}
    assert merge_paths([worker_0, worker_1]) == {
        decision: [{"path": [True, True], "tests": Tally({PROMPT: 2, LATE: 1})}]
    }
    way = (("src/model/flow.py:2:23", (True, True)),)
    ways_0 = {"src/model/flow.py:1:0": {way: Tally({PROMPT: 2})}}
    ways_1 = {"src/model/flow.py:1:0": {way: Tally({LATE: 1})}}
    assert merge_ways([ways_0, ways_1]) == {"src/model/flow.py:1:0": {way: Tally({PROMPT: 2, LATE: 1})}}


def test_f2c67d02():
    """Example: two workers' paths for flow.py's and, one taking
    [True, True] once, the other twice and [False, None] once
    Each path's counts are added across the runs.
    A path in one run only keeps its count."""
    decision = "src/model/flow.py:2:11"
    worker_0 = {decision: [{"path": [True, True], "tests": untested(1)}, {"path": [False, None], "tests": untested(0)}]}
    worker_1 = {decision: [{"path": [True, True], "tests": untested(2)}, {"path": [False, None], "tests": untested(1)}]}
    assert merge_paths([worker_0, worker_1]) == {
        decision: [{"path": [True, True], "tests": untested(3)}, {"path": [False, None], "tests": untested(1)}]
    }


def test_f2c67d01():
    """Runs' operands are merged by adding their counts, operand by operand,
    keeping only, so a gap shows only when every run left it."""
    worker_0 = {
        "src/model/tags.py:1:7": [
            {"truthy": untested(2), "falsy": untested(0)},
            {"truthy": untested(0), "falsy": untested(0), "only": "falsy"},
        ],
        "src/model/flow.py:2:11": [
            {"truthy": untested(1), "falsy": untested(1)},
            {"truthy": untested(1), "falsy": untested(0)},
        ],
    }
    worker_1 = {
        "src/model/tags.py:1:7": [
            {"truthy": untested(3), "falsy": untested(1)},
            {"truthy": untested(0), "falsy": untested(1), "only": "falsy"},
        ],
        "src/model/flow.py:2:11": [
            {"truthy": untested(1), "falsy": untested(1)},
            {"truthy": untested(1), "falsy": untested(0)},
        ],
    }
    assert merge([worker_0, worker_1]) == {
        "src/model/tags.py:1:7": [
            {"truthy": untested(5), "falsy": untested(1)},
            {"truthy": untested(0), "falsy": untested(1), "only": "falsy"},
        ],
        "src/model/flow.py:2:11": [
            {"truthy": untested(2), "falsy": untested(2)},
            {"truthy": untested(2), "falsy": untested(0)},
        ],
    }

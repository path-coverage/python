from path_coverage.manifest import decisions
from path_coverage.result import operands, paths

SOURCE = (
    "def can_attest(user, flow):\n"
    "    return user.active and (user.admin or flow.public)\n"
    "\n"
    "def is_new(trail_id, trails):\n"
    "    return trail_id in trails and trails[trail_id].is_new\n"
)


def test_c3b8f401():
    """Every decision of the manifest is listed in order with each leaf's counts,
    nested leaves included, and zeros for operands that never ran."""
    decision = "src/model/flow.py:2:23"
    counts = {
        (decision, 0): {"truthy": 3, "falsy": 1},
        (decision, 2): {"truthy": 1, "falsy": 0},
    }
    assert operands(decisions(SOURCE, "src/model/flow.py"), counts) == {
        decision: [
            {"truthy": 3, "falsy": 1},
            {"truthy": 0, "falsy": 0},
            {"truthy": 1, "falsy": 0},
        ],
        "src/model/flow.py:5:30": [
            {"truthy": 0, "falsy": 0},
            {"truthy": 0, "falsy": 0},
        ],
    }


def test_c3b8f402():
    """A leaf that can have one outcome only carries it as only."""
    source = "tags = record.get('tags') or []\n"
    decision = "src/model/tags.py:1:26"
    counts = {(decision, 0): {"truthy": 2, "falsy": 1}, (decision, 1): {"truthy": 0, "falsy": 1}}
    assert operands(decisions(source, "src/model/tags.py"), counts) == {
        decision: [
            {"truthy": 2, "falsy": 1},
            {"truthy": 0, "falsy": 1, "only": "falsy"},
        ],
    }


def test_c3b8f403():
    """Example: can_attest's and/or taken twice one way and once another,
    and is_new's and never evaluated
    Every decision lists each possible path with its count.
    A path never taken has count 0.
    So is_new's decision lists its paths too, every count 0."""
    decision = "src/model/flow.py:2:23"
    decision_paths = {decision: {(True, False, True): 2, (False, None, None): 1}}
    assert paths(decisions(SOURCE, "src/model/flow.py"), decision_paths) == {
        decision: [
            {"path": [True, True, None], "count": 0},
            {"path": [True, False, True], "count": 2},
            {"path": [True, False, False], "count": 0},
            {"path": [False, None, None], "count": 1},
        ],
        "src/model/flow.py:5:30": [
            {"path": [True, True], "count": 0},
            {"path": [True, False], "count": 0},
            {"path": [False, None], "count": 0},
        ],
    }

from path_coverage.manifest import decisions
from path_coverage.result import operands, paths
from tallies import untested

SOURCE = (
    "def can_attest(user, flow):\n"
    "    while user.active and (user.admin or flow.public): break\n"
    "\n"
    "def is_new(trail_id, trails):\n"
    "    while trail_id in trails and trails[trail_id].is_new: break\n"
)


def test_c3b8f401():
    """Every decision of the manifest is listed in order with each leaf's counts,
    nested leaves included, and zeros for operands that never ran."""
    decision = "src/model/flow.py:2:22"
    counts = {
        (decision, 0): {"truthy": untested(3), "falsy": untested(1)},
        (decision, 2): {"truthy": untested(1), "falsy": untested(0)},
    }
    assert operands(decisions(SOURCE, "src/model/flow.py"), counts) == {
        decision: [
            {"truthy": untested(3), "falsy": untested(1)},
            {"truthy": untested(0), "falsy": untested(0)},
            {"truthy": untested(1), "falsy": untested(0)},
        ],
        "src/model/flow.py:5:29": [
            {"truthy": untested(0), "falsy": untested(0)},
            {"truthy": untested(0), "falsy": untested(0)},
        ],
    }


def test_c3b8f402():
    """A leaf that can have one outcome only carries it as only."""
    source = "while record.get('tags') or []: break\n"
    decision = "src/model/tags.py:1:25"
    counts = {(decision, 0): {"truthy": untested(2), "falsy": untested(1)}, (decision, 1): {"truthy": untested(0), "falsy": untested(1)}}
    assert operands(decisions(source, "src/model/tags.py"), counts) == {
        decision: [
            {"truthy": untested(2), "falsy": untested(1)},
            {"truthy": untested(0), "falsy": untested(1), "only": "falsy"},
        ],
    }


def test_c3b8f403():
    """Example: can_attest's and/or taken twice one way and once another,
    and is_new's and never evaluated
    Every decision lists each possible path with its count.
    A path never taken has count 0.
    So is_new's decision lists its paths too, every count 0."""
    decision = "src/model/flow.py:2:22"
    decision_paths = {decision: {(True, False, True): untested(2), (False, None, None): untested(1)}}
    assert paths(decisions(SOURCE, "src/model/flow.py"), decision_paths) == {
        decision: [
            {"path": [True, True, None], "tests": untested(0)},
            {"path": [True, False, True], "tests": untested(2)},
            {"path": [True, False, False], "tests": untested(0)},
            {"path": [False, None, None], "tests": untested(1)},
        ],
        "src/model/flow.py:5:29": [
            {"path": [True, True], "tests": untested(0)},
            {"path": [True, False], "tests": untested(0)},
            {"path": [False, None], "tests": untested(0)},
        ],
    }

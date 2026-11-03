from condition_coverage.manifest import sites
from condition_coverage.result import operands

SOURCE = (
    "def can_attest(user, flow):\n"
    "    return user.active and (user.admin or flow.public)\n"
    "\n"
    "def is_new(trail_id, trails):\n"
    "    return trail_id in trails and trails[trail_id].is_new\n"
)


def test_c3b8f401():
    """Every site of the manifest is listed in order with each leaf's counts,
    nested leaves included, and zeros for operands that never ran."""
    site = "src/model/flow.py:2:11"
    counts = {
        (site, 0): {"truthy": 3, "falsy": 1},
        (site, 2): {"truthy": 1, "falsy": 0},
    }
    assert operands(sites(SOURCE, "src/model/flow.py"), counts) == {
        site: [
            {"truthy": 3, "falsy": 1},
            {"truthy": 0, "falsy": 0},
            {"truthy": 1, "falsy": 0},
        ],
        "src/model/flow.py:5:11": [
            {"truthy": 0, "falsy": 0},
            {"truthy": 0, "falsy": 0},
        ],
    }


def test_c3b8f402():
    """A leaf that can have one outcome only carries it as only."""
    source = "tags = record.get('tags') or []\n"
    site = "src/model/tags.py:1:7"
    counts = {(site, 0): {"truthy": 2, "falsy": 1}, (site, 1): {"truthy": 0, "falsy": 1}}
    assert operands(sites(source, "src/model/tags.py"), counts) == {
        site: [
            {"truthy": 2, "falsy": 1},
            {"truthy": 0, "falsy": 1, "only": "falsy"},
        ],
    }

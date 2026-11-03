from condition_coverage.manifest import sites
from condition_coverage.site_tree import tree_of


def test_1a6c3e01():
    """A site's tree nests as its condition does; each leaf has its text cut
    from the source (byte columns, so non-ASCII text before it is counted
    right), its counts, and its gap in the gaps report's words."""
    source = (
        "def can_attest(user, flow):\n"
        "    return user.name != 'J\N{LATIN SMALL LETTER O WITH STROKE}rgen'"
        " and (user.admin or flow.public)\n"
    )
    [condition] = sites(source, "src/model/flow.py").values()
    counts = [
        {"truthy": 3, "falsy": 1},
        {"truthy": 0, "falsy": 3},
        {"truthy": 2, "falsy": 1},
    ]
    assert tree_of(source, condition, counts) == {
        "operator": "and",
        "operands": [
            {
                "text": "user.name != 'J\N{LATIN SMALL LETTER O WITH STROKE}rgen'",
                "truthy": 3,
                "falsy": 1,
                "gap": None,
            },
            {
                "operator": "or",
                "operands": [
                    {"text": "user.admin", "truthy": 0, "falsy": 3, "gap": "never true"},
                    {"text": "flow.public", "truthy": 2, "falsy": 1, "gap": None},
                ],
            },
        ],
    }


def test_1a6c3e02():
    """A leaf written over several lines keeps all of its text."""
    source = (
        "def is_compliant(trail):\n"
        "    return trail.done and all(\n"
        "        a.ok for a in trail.attestations\n"
        "    )\n"
    )
    [condition] = sites(source, "src/model/trail.py").values()
    counts = [{"truthy": 2, "falsy": 1}, {"truthy": 1, "falsy": 1}]
    assert tree_of(source, condition, counts)["operands"][1]["text"] == (
        "all(\n        a.ok for a in trail.attestations\n    )"
    )

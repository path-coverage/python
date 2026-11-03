from condition_coverage.manifest import Condition, Leaf, sites


def test_5c1e9a01():
    """A single `and` is one site, named path:line:col where it starts
    (col 0-based, as ast and Prism both count it), with its two operands
    as leaves, left to right."""
    source = (
        "def is_new(trail_id, trails):\n"
        "    return trail_id in trails and trails[trail_id].is_new\n"
    )
    assert sites(source, "src/model/trail.py") == {
        "src/model/trail.py:2:11": Condition(
            operator="and",
            operands=(Leaf(2, 11, 2, 29), Leaf(2, 34, 2, 57)),
        ),
    }


def test_5c1e9a02():
    """An `or` inside an `and` (parenthesised or not) nests as a Condition
    within the one site, and a chain of one operator stays flat."""
    source = (
        "def can_attest(user, flow):\n"
        "    return user.active and (user.admin or flow.public or flow.owner == user)\n"
    )
    assert sites(source, "src/model/flow.py") == {
        "src/model/flow.py:2:11": Condition(
            operator="and",
            operands=(
                Leaf(2, 11, 2, 22),
                Condition(
                    operator="or",
                    operands=(
                        Leaf(2, 28, 2, 38),
                        Leaf(2, 42, 2, 53),
                        Leaf(2, 57, 2, 75),
                    ),
                ),
            ),
        ),
    }


def test_5c1e9a04():
    """A leaf whose form allows one outcome only is marked with it: falsy
    for None, False, zero, an empty string or an empty display; truthy for
    any other literal, a non-empty display, a lambda or an f-string holding
    literal text. Anything that may unpack to empty, or call anything, is
    left open."""
    source = (
        "name = (payload.get('name') or '').strip()\n"
        "tags = record.get('tags') or []\n"
        "versions = versions or [None]\n"
        "label = label or f'v{n}'\n"
        "key = key or (lambda d: d.name)\n"
        "merged = extra or {**defaults}\n"
        "config = stored or NotificationConfig()\n"
        "limit = limit or 0\n"
        "ids = ids or [*mine, *theirs]\n"
    )
    found = sites(source, "src/model/defaults.py")
    assert [leaf.only for condition in found.values() for leaf in condition.leaves()] == [
        None, "falsy",
        None, "falsy",
        None, "truthy",
        None, "truthy",
        None, "truthy",
        None, None,
        None, None,
        None, "falsy",
        None, None,
    ]


def test_5c1e9a03():
    """A condition inside a leaf operand is a site of its own, following
    the site whose leaf holds it."""
    source = (
        "def all_compliant(trails, strict):\n"
        "    return any(t.done and t.ok for t in trails) or not strict\n"
    )
    assert sites(source, "src/model/trail.py") == {
        "src/model/trail.py:2:11": Condition(
            operator="or",
            operands=(Leaf(2, 11, 2, 47), Leaf(2, 51, 2, 61)),
        ),
        "src/model/trail.py:2:15": Condition(
            operator="and",
            operands=(Leaf(2, 15, 2, 21), Leaf(2, 26, 2, 30)),
        ),
    }

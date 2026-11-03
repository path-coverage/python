from path_coverage.manifest import Arm, Condition, Leaf, sites


def test_5c1e9a07():
    """Example: if order.big and order.new: ... else: ...
    An if statement is a site, named at its keyword, col 4.
    Its predicate's `and` nests in it, as no site of its own.
    Its then and else arms are plain, as they are statements."""
    source = (
        "def fee(order):\n"
        "    if order.big and order.new:\n"
        "        return 5\n"
        "    else:\n"
        "        return 7\n"
    )
    both = Condition(operator="and", operands=(Leaf(2, 7, 2, 16), Leaf(2, 21, 2, 30)))
    assert sites(source, "k.py") == {
        "k.py:2:4": Condition(operator="if", operands=(both, Arm("then"), Arm("else"))),
    }


def test_5c1e9a08():
    """Example: if order.big: ... elif order.new: ...
    The elif is a site of its own, named at its keyword.
    The if's else arm is the whole elif.
    The elif has no else, so it has a then arm only."""
    source = (
        "def fee(order):\n"
        "    if order.big:\n"
        "        return 5\n"
        "    elif order.new:\n"
        "        return 6\n"
        "    return 7\n"
    )
    assert sites(source, "k.py") == {
        "k.py:2:4": Condition(
            operator="if", operands=(Leaf(2, 7, 2, 16), Arm("then"), Arm("else"))
        ),
        "k.py:4:4": Condition(operator="if", operands=(Leaf(4, 9, 4, 18), Arm("then"))),
    }


def test_5c1e9a05():
    """Example: "admin" if user.admin else "guest"
    A conditional expression is a site, even with a one-leaf predicate.
    It is named where it starts, at "admin", col 11.
    Its operands are its predicate, then its then and else arms.
    Both arms are plain values, so neither holds a condition."""
    source = (
        "def role(user):\n"
        '    return "admin" if user.admin else "guest"\n'
    )
    assert sites(source, "src/model/user.py") == {
        "src/model/user.py:2:11": Condition(
            operator="ternary",
            operands=(Leaf(2, 22, 2, 32), Arm("then", None), Arm("else", None)),
        ),
    }


def test_5c1e9a06():
    """Example: user.admin or flow.public if user.active else False
    The then arm holds an `or`.
    It is part of the conditional expression's site, not a site of its own.
    Its leaves are numbered after the predicate's."""
    source = (
        "def can_see(user, flow):\n"
        "    return user.admin or flow.public if user.active else False\n"
    )
    either = Condition(operator="or", operands=(Leaf(2, 11, 2, 21), Leaf(2, 25, 2, 36)))
    condition = Condition(
        operator="ternary",
        operands=(Leaf(2, 40, 2, 51), Arm("then", either), Arm("else", None)),
    )
    assert sites(source, "src/model/flow.py") == {"src/model/flow.py:2:11": condition}
    assert condition.leaves() == [Leaf(2, 40, 2, 51), Leaf(2, 11, 2, 21), Leaf(2, 25, 2, 36)]


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

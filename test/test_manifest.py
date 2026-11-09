from path_coverage.manifest import Arm, Condition, Leaf, decisions


def test_5c1e9a09():
    """Example: [u for u in users if u.active]
    A comprehension's filter is a decision, named at its if keyword.
    Its test is its predicate.
    Its then arm keeps the item, its else arm drops it."""
    source = "def active(users):\n    return [u for u in users if u.active]\n"
    assert decisions(source, "k.py") == {
        "k.py:2:29": Condition(
            operator="filter", operands=(Leaf(2, 32, 2, 40), Arm("then"), Arm("else"))
        ),
    }


def test_5c1e9a0a():
    """Example: a filter (u.active and u.admin) on a line of its own, after
    a comment, then a second filter u.new
    The filter is named at its if keyword, not at its test.
    Its predicate, the whole `and`, is one leaf of it, and the `and` is a
    decision of its own.
    Each filter is a decision of its own."""
    source = (
        "def admins(users):\n"
        "    return [\n"
        "        u for u in users\n"
        "        if  # only some\n"
        "        (u.active and u.admin)\n"
        "        if u.new\n"
        "    ]\n"
    )
    both = Condition(operator="and", operands=(Leaf(5, 9, 5, 17), Leaf(5, 22, 5, 29)))
    arms = (Arm("then"), Arm("else"))
    assert decisions(source, "k.py") == {
        "k.py:4:8": Condition(operator="filter", operands=(Leaf(5, 9, 5, 29), *arms)),
        "k.py:5:18": both,
        "k.py:6:8": Condition(operator="filter", operands=(Leaf(6, 11, 6, 16), *arms)),
    }


def test_5c1e9a0b():
    """Example: match order.kind: case "gold" if order.big: ... case
    "silver": ...
    A match statement is a decision, named at its keyword.
    Each case's pattern is a leaf, true when it matches.
    A guarded case is a `case` of its pattern and its guard, as both must
    hold.
    The cases chain as an `or` does, stopping at the first that holds."""
    source = (
        "def fee(order):\n"
        "    match order.kind:\n"
        '        case "gold" if order.big:\n'
        "            return 1\n"
        '        case "silver":\n'
        "            return 2\n"
    )
    gold = Condition(operator="case", operands=(Leaf(3, 13, 3, 19), Leaf(3, 23, 3, 32)))
    assert decisions(source, "k.py") == {
        "k.py:2:4": Condition(operator="match", operands=(gold, Leaf(5, 13, 5, 21))),
    }


def test_5c1e9a0c():
    """Example: match code: case 200: ... case _: ...
    The _ pattern matches anything.
    So its leaf can only be true."""
    source = (
        "def label(code):\n"
        "    match code:\n"
        "        case 200:\n"
        '            return "ok"\n'
        "        case _:\n"
        '            return "other"\n'
    )
    always = Leaf(5, 13, 5, 14, "truthy")
    assert decisions(source, "k.py") == {
        "k.py:2:4": Condition(operator="match", operands=(Leaf(3, 13, 3, 16), always)),
    }


def test_5c1e9a0d():
    """Example: any(o.late for o in orders)
    An any() of a generator is a decision, named where the call starts.
    Its first leaf is the items it was given: orders.
    Its second is the generator's answer for an item: o.late."""
    source = "def late(orders):\n    return any(o.late for o in orders)\n"
    assert decisions(source, "k.py") == {
        "k.py:2:11": Condition(operator="any", operands=(Leaf(2, 31, 2, 37), Leaf(2, 15, 2, 21))),
    }


def test_5c1e9a0e():
    """Example: any(o.late for o in orders) or all(o.paid for o in orders),
    in a module that imports its own any
    That any may not be the builtin, so its call is a leaf only.
    The all is the builtin, so its call is a decision of its own.
    The or is named at its keyword, col 39."""
    source = (
        "from flags import any\n"
        "\n"
        "def late(orders):\n"
        "    assert any(o.late for o in orders) or all(o.paid for o in orders)\n"
    )
    assert decisions(source, "k.py") == {
        "k.py:4:39": Condition(operator="or", operands=(Leaf(4, 11, 4, 38), Leaf(4, 42, 4, 69))),
        "k.py:4:42": Condition(operator="all", operands=(Leaf(4, 62, 4, 68), Leaf(4, 46, 4, 52))),
    }


def test_5c1e9a10():
    """Example: any(o.late for o in orders) in modules that bind any by
    def, class, assignment, parameter, except as, match captures, import
    as and star import
    Each binding may hide the builtin.
    So in each module the call is no decision, though a match binding it is."""
    call = "any(o.late for o in orders)"
    bindings = [
        "def any(xs):\n    return xs\n",
        "class any:\n    pass\n",
        "any = None\n",
        "def k(any):\n    return any\n",
        "try:\n    pass\nexcept ValueError as any:\n    pass\n",
        "match 1:\n    case any:\n        pass\n",
        "match []:\n    case [*any]:\n        pass\n",
        "match {}:\n    case {**any}:\n        pass\n",
        "import flags as any\n",
        "from flags import *\n",
    ]
    for binding in bindings:
        source = f"{binding}\ndef late(orders):\n    return {call}\n"
        operators = [condition.operator for condition in decisions(source, "k.py").values()]
        assert operators == (["match"] if binding.startswith("match") else []), binding


def test_5c1e9a0f():
    """Example: any(flags)
    Its argument is no generator, so there is no answer to note.
    So the call is no decision."""
    assert decisions("def k(flags):\n    return any(flags)\n", "k.py") == {}


def test_5c1e9a13():
    """Example: a match whose last case is case 2 | _:, case _ as size:,
    case (n as size): or case [n]:
    An or-pattern with an irrefutable alternative, and an as-pattern of an
    irrefutable pattern, match anything, as Python itself decides, so each
    such case's pattern leaf can only be true; [n] can fail to match."""

    def last_pattern(case):
        """The only of the last case's pattern leaf of a match whose last
        case is case."""
        source = f"def size_of(order):\n    match order:\n        case 1:\n            return 1\n        {case}\n            return 2\n"
        return decisions(source, "k.py")["k.py:2:4"].operands[-1].only

    cases = ["case 2 | _:", "case _ as size:", "case (n as size):", "case [n]:"]
    assert [last_pattern(case) for case in cases] == ["truthy", "truthy", "truthy", None]


def test_5c1e9a07():
    """Example: if order.big and order.new: ... else: ...
    An if statement is a decision, named at its keyword, col 4.
    Its predicate, the whole `and`, is one leaf of it, and the `and` is a
    decision of its own, named at its keyword, so each row of a card is one
    decision.
    Its then and else arms are plain, as they are statements, and each
    leaves the function by return."""
    source = (
        "def fee(order):\n"
        "    if order.big and order.new:\n"
        "        return 5\n"
        "    else:\n"
        "        return 7\n"
    )
    both = Condition(operator="and", operands=(Leaf(2, 7, 2, 16), Leaf(2, 21, 2, 30)))
    predicate = Leaf(2, 7, 2, 30)
    arms = (Arm("then", leaving="return"), Arm("else", leaving="return"))
    assert decisions(source, "k.py") == {
        "k.py:2:4": Condition(operator="if", operands=(predicate, *arms)),
        "k.py:2:17": both,
    }


def test_5c1e9a08():
    """Example: if order.big: ... elif order.new: ...
    The elif is a decision of its own, named at its keyword.
    The if's else arm is the whole elif.
    The elif has no else, so it has a then arm only.
    Each then arm leaves by return; the if's else arm, the elif, leaves
    only when its predicate holds, so does not leave."""
    source = (
        "def fee(order):\n"
        "    if order.big:\n"
        "        return 5\n"
        "    elif order.new:\n"
        "        return 6\n"
        "    return 7\n"
    )
    returns = Arm("then", leaving="return")
    assert decisions(source, "k.py") == {
        "k.py:2:4": Condition(operator="if", operands=(Leaf(2, 7, 2, 16), returns, Arm("else"))),
        "k.py:4:4": Condition(operator="if", operands=(Leaf(4, 9, 4, 18), returns)),
    }


def test_5c1e9a05():
    """Example: "admin" if user.admin else "guest"
    A conditional expression is a decision, even with a one-leaf predicate.
    It is named at its if keyword, col 19, so it never shares a name with a
    decision starting where it does, eg a call in its then arm.
    Its operands are its predicate, then its then and else arms.
    Both arms are plain values, so neither holds a condition."""
    source = (
        "def role(user):\n"
        '    return "admin" if user.admin else "guest"\n'
    )
    assert decisions(source, "src/model/user.py") == {
        "src/model/user.py:2:19": Condition(
            operator="ternary",
            operands=(Leaf(2, 22, 2, 32), Arm("then", None), Arm("else", None)),
        ),
    }


def test_5c1e9a06():
    """Example: user.admin or flow.public if user.active else False
    The then arm holds an `or`.
    It is part of the conditional expression's decision, not a decision of its own.
    Its leaves are numbered after the predicate's."""
    source = (
        "def can_see(user, flow):\n"
        "    assert user.admin or flow.public if user.active else False\n"
    )
    either = Condition(operator="or", operands=(Leaf(2, 11, 2, 21), Leaf(2, 25, 2, 36)))
    condition = Condition(
        operator="ternary",
        operands=(Leaf(2, 40, 2, 51), Arm("then", either), Arm("else", None)),
    )
    assert decisions(source, "src/model/flow.py") == {"src/model/flow.py:2:37": condition}
    assert condition.leaves() == [Leaf(2, 40, 2, 51), Leaf(2, 11, 2, 21), Leaf(2, 25, 2, 36)]


def test_5c1e9a01():
    """A single `and` is one decision, named path:line:col of its keyword (col
    0-based, as ast counts it), with its two operands as leaves, left to
    right."""
    source = (
        "def is_new(trail_id, trails):\n"
        "    assert trail_id in trails and trails[trail_id].is_new\n"
    )
    assert decisions(source, "src/model/trail.py") == {
        "src/model/trail.py:2:30": Condition(
            operator="and",
            operands=(Leaf(2, 11, 2, 29), Leaf(2, 34, 2, 57)),
        ),
    }


def test_5c1e9a02():
    """An `or` inside an `and` (parenthesised or not) nests as a Condition
    within the one decision, and a chain of one operator stays flat."""
    source = (
        "def can_attest(user, flow):\n"
        "    assert user.active and (user.admin or flow.public or flow.owner == user)\n"
    )
    assert decisions(source, "src/model/flow.py") == {
        "src/model/flow.py:2:23": Condition(
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
        "assert payload.get('name') or ''\n"
        "assert record.get('tags') or []\n"
        "assert versions or [None]\n"
        "assert label or f'v{n}'\n"
        "assert key or (lambda d: d.name)\n"
        "assert extra or {**defaults}\n"
        "assert stored or NotificationConfig()\n"
        "assert limit or 0\n"
        "assert ids or [*mine, *theirs]\n"
    )
    found = decisions(source, "src/model/defaults.py")
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


def test_5c1e9a11():
    """Example: name or f'', name or f'x', name or f'{n}', name or
    f'{a}{b}', name or f'{n} items'
    An f-string with literal text anywhere is truthy, whatever its
    expressions give. One that is only expressions may be either, and so
    may an empty one, as nothing is known of its parts."""
    source = (
        "assert name or f''\n"
        "assert name or f'x'\n"
        "assert name or f'{n}'\n"
        "assert name or f'{a}{b}'\n"
        "assert name or f'{n} items'\n"
    )
    onlys = [condition.leaves()[1].only for condition in decisions(source, "k.py").values()]
    assert onlys == [None, "truthy", None, None, "truthy"]


def test_5c1e9a14():
    """Example: ship, a or b written, walrused into an if's test, under a
    not, as a conditional expression's test, as a while's test, as an
    assert's message, as a comprehension's iterable and its filter, as a
    guard, as any's element and sum's; then conditional expressions in an
    or and in another's arm
    An or's last operand is a leaf only when a branch forks on the or's
    truth: as, or through a walrus, a not or an arm, the test of an if,
    a conditional expression, a while, a filter, a guard or a block
    call's element. Where its value is only used, it is evaluated or
    not, and no leaf."""
    source = (
        "def ship(a, b, xs, m):\n"
        "    x = a or b\n"
        "    if (y := a or b):\n"
        "        pass\n"
        "    z = not (a or b)\n"
        "    w = 1 if a or b else 2\n"
        "    while a or b:\n"
        "        break\n"
        "    assert m, a or b\n"
        "    u = [x for x in a or b if a or b]\n"
        "    match m:\n"
        "        case 1 if a or b:\n"
        "            pass\n"
        "    t = any(a or b for x in xs)\n"
        "    s = sum(a or b for x in xs)\n"
        "    q = (1 if a else 2) or b\n"
        "    v = 1 if m else (2 if a else 3)\n"
    )
    ors = [len(condition.leaves()) for condition in decisions(source, "k.py").values() if condition.operator == "or"]
    assert ors == [1, 2, 1, 2, 2, 1, 1, 2, 2, 2, 1, 1]


def test_5c1e9a12():
    """Example: match n: case 0 as zero: ... case _: ...
    A case binding a name to a pattern matches only what its pattern does,
    so its leaf may be either; only a bare _ or name matches anything."""
    source = (
        "def size(n):\n"
        "    match n:\n"
        "        case 0 as zero:\n"
        "            return zero\n"
        "        case _:\n"
        "            return n\n"
    )
    [match] = decisions(source, "k.py").values()
    assert [leaf.only for leaf in match.leaves()] == [None, "truthy"]


def test_5c1e9a03():
    """A condition inside a leaf operand is a decision of its own: the any
    that is the or's first leaf, and the and in the any's generator. The
    any starts where the or's code does, but the or is named at its
    keyword, so each keeps a name of its own."""
    source = (
        "def all_compliant(trails, strict):\n"
        "    assert any(t.done and t.ok for t in trails) or not strict\n"
    )
    assert decisions(source, "src/model/trail.py") == {
        "src/model/trail.py:2:48": Condition(
            operator="or",
            operands=(Leaf(2, 11, 2, 47), Leaf(2, 51, 2, 61)),
        ),
        "src/model/trail.py:2:11": Condition(
            operator="any",
            operands=(Leaf(2, 40, 2, 46), Leaf(2, 15, 2, 30)),
        ),
        "src/model/trail.py:2:22": Condition(
            operator="and",
            operands=(Leaf(2, 15, 2, 21), Leaf(2, 26, 2, 30)),
        ),
    }

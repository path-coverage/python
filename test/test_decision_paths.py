from path_coverage.manifest import decisions
from path_coverage.decision_paths import possible


def _only_decision(source):
    """The Condition of the one decision in source."""
    [condition] = decisions(source, "k.py").values()
    return condition


def test_7b3d9101():
    """Example: ok(id) and new(id)
    An `and` goes on to its next leaf only when a leaf is true.
    So its paths are [True, True], [True, False] and [False, None].
    None marks a leaf the path never reaches."""
    condition = _only_decision("def k(id):\n    return ok(id) and new(id)\n")
    assert possible(condition) == [[True, True], [True, False], [False, None]]


def test_7b3d9102():
    """Example: cached(id) or fetch(id)
    An `or` goes on to its next leaf only when a leaf is false.
    So its paths are [True, None], [False, True] and [False, False]."""
    condition = _only_decision("def k(id):\n    return cached(id) or fetch(id)\n")
    assert possible(condition) == [[True, None], [False, True], [False, False]]


def test_7b3d9103():
    """Example: ok(id) and (new(id) or len(id) == 6)
    The nested `or` is walked inside the `and`.
    Its leaves follow ok(id), numbered left to right."""
    source = "def k(id):\n    return ok(id) and (new(id) or len(id) == 6)\n"
    assert possible(_only_decision(source)) == [
        [True, True, None],
        [True, False, True],
        [True, False, False],
        [False, None, None],
    ]


def test_7b3d9105():
    """Example: "admin" if user.admin else "guest"
    Both arms are plain values.
    So the paths are just the predicate's: [True] and [False]."""
    source = 'def k(user):\n    return "admin" if user.admin else "guest"\n'
    assert possible(_only_decision(source)) == [[True], [False]]


def test_7b3d9106():
    """Example: user.admin or flow.public if user.active else False
    A true predicate picks the then arm, whose `or` is walked next.
    A false predicate picks the plain else arm, so ends the path."""
    source = (
        "def k(user, flow):\n"
        "    return user.admin or flow.public if user.active else False\n"
    )
    assert possible(_only_decision(source)) == [
        [True, True, None],
        [True, False, True],
        [True, False, False],
        [False, None, None],
    ]


def test_7b3d9107():
    """Example: if order.big and order.new: return 5, with no else
    An if's arms are statements, so they add no paths of their own.
    Its paths are its predicate's, one leaf, as the and is a decision of its
    own: true and false.
    It has no else arm, yet still has a false path."""
    source = "def fee(order):\n    if order.big and order.new:\n        return 5\n    return 7\n"
    assert possible(decisions(source, "k.py")["k.py:2:4"]) == [[True], [False]]


def test_7b3d9108():
    """Example: [u for u in users if u.active and u.admin]
    The filter keeps an item on true and drops it on false.
    Its arms hold no condition, so its paths are its predicate's, one leaf,
    as the and is a decision of its own."""
    source = "def admins(users):\n    return [u for u in users if u.active and u.admin]\n"
    assert possible(decisions(source, "k.py")["k.py:2:29"]) == [[True], [False]]


def test_7b3d9109():
    """Example: match order.kind: case "gold" if order.big: ... case
    "silver": ..., then the same with case _ in place of "silver"
    A guard is reached only when its pattern matches.
    A later case is reached only when no earlier one held.
    With no case holding, nothing matched, a path of its own.
    The _ pattern always matches, so no path has nothing matched."""
    source = (
        "def fee(order):\n"
        "    match order.kind:\n"
        '        case "gold" if order.big:\n'
        "            return 1\n"
        '        case "silver":\n'
        "            return 2\n"
    )
    assert possible(_only_decision(source)) == [
        [True, True, None],
        [True, False, True],
        [True, False, False],
        [False, None, True],
        [False, None, False],
    ]
    wildcard = source.replace('case "silver"', "case _")
    assert possible(_only_decision(wildcard)) == [
        [True, True, None],
        [True, False, True],
        [False, None, True],
    ]


def test_7b3d910a():
    """Example: any(o.late for o in orders)
    Its items leaf is how many items the generator gave: 0, 1 or 2+.
    Its answer leaf is the last answer, where any stopped.
    With 0 items there is no answer.
    all has the same paths, as it too stops at the answer deciding it."""
    late = "def late(orders):\n    return any(o.late for o in orders)\n"
    paths = [
        ["0 items", None],
        ["1 item", True],
        ["1 item", False],
        ["2+ items", True],
        ["2+ items", False],
    ]
    assert possible(_only_decision(late)) == paths
    assert possible(_only_decision(late.replace("any(", "all("))) == paths


def test_7b3d9104():
    """Example: options.get("tags") or []
    [] can only be falsy, so a path needing it true is impossible.
    The paths are [True, None] and [False, False]."""
    source = 'def k(options):\n    return options.get("tags") or []\n'
    assert possible(_only_decision(source)) == [[True, None], [False, False]]

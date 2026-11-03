from path_coverage.manifest import sites
from path_coverage.site_paths import possible


def _only_site(source):
    """The Condition of the one site in source."""
    [condition] = sites(source, "k.py").values()
    return condition


def test_7b3d9101():
    """Example: ok(id) and new(id)
    An `and` goes on to its next leaf only when a leaf is true.
    So its paths are [True, True], [True, False] and [False, None].
    None marks a leaf the path never reaches."""
    condition = _only_site("def k(id):\n    return ok(id) and new(id)\n")
    assert possible(condition) == [[True, True], [True, False], [False, None]]


def test_7b3d9102():
    """Example: cached(id) or fetch(id)
    An `or` goes on to its next leaf only when a leaf is false.
    So its paths are [True, None], [False, True] and [False, False]."""
    condition = _only_site("def k(id):\n    return cached(id) or fetch(id)\n")
    assert possible(condition) == [[True, None], [False, True], [False, False]]


def test_7b3d9103():
    """Example: ok(id) and (new(id) or len(id) == 6)
    The nested `or` is walked inside the `and`.
    Its leaves follow ok(id), numbered left to right."""
    source = "def k(id):\n    return ok(id) and (new(id) or len(id) == 6)\n"
    assert possible(_only_site(source)) == [
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
    assert possible(_only_site(source)) == [[True], [False]]


def test_7b3d9106():
    """Example: user.admin or flow.public if user.active else False
    A true predicate picks the then arm, whose `or` is walked next.
    A false predicate picks the plain else arm, so ends the path."""
    source = (
        "def k(user, flow):\n"
        "    return user.admin or flow.public if user.active else False\n"
    )
    assert possible(_only_site(source)) == [
        [True, True, None],
        [True, False, True],
        [True, False, False],
        [False, None, None],
    ]


def test_7b3d9107():
    """Example: if order.big and order.new: return 5, with no else
    An if's arms are statements, so they add no paths of their own.
    Its paths are its predicate's.
    It has no else arm, yet still has a false path."""
    source = "def fee(order):\n    if order.big and order.new:\n        return 5\n    return 7\n"
    assert possible(_only_site(source)) == [[True, True], [True, False], [False, None]]


def test_7b3d9104():
    """Example: options.get("tags") or []
    [] can only be falsy, so a path needing it true is impossible.
    The paths are [True, None] and [False, False]."""
    source = 'def k(options):\n    return options.get("tags") or []\n'
    assert possible(_only_site(source)) == [[True, None], [False, False]]

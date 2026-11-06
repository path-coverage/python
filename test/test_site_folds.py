from path_coverage import manifest, site_paths, source_report


def test_7d61a401():
    """Example: size, a match whose second case is guarded, case count if
    count > 10, no path taken
    The guarded case is a condition nested in the match, its pattern then
    its guard, so its fold row is placed at its code, from its pattern to
    its guard's end, as every other row of a fold is."""
    source = (
        "def size(n):\n"
        "    match n:\n"
        "        case 0:\n"
        '            return "none"\n'
        "        case count if count > 10:\n"
        '            return "many"\n'
    )
    rows = _fold(source, "k.py:2:4", "match")
    [case] = [row for row in rows if row["kind"] == "subtree"]
    assert [case["label"]["text"], case["at"]] == ["case", [5, 13, 5, 32]]


def test_7d61a403():
    """Example: pick, an if whose else returns
    The if's fold names where its else keyword is, line 4, columns 4 to 8,
    so hovering that else can open the fold, as hovering its if does; its
    else arm returns, so it has a return row, placed at that return."""
    source = (
        "def pick(a):\n"
        "    if a:\n"
        "        a = 2\n"
        "    else:\n"
        "        return 2\n"
    )
    rows = _fold(source, "k.py:2:4", "if/else")
    [leaves] = [row for row in rows if row["kind"] == "leaves"]
    assert [rows[0]["else"], leaves["at"]] == [[4, 4, 4, 8], [5, 8, 5, 16]]


def test_7d61a404():
    """Example: size, an if whose else is an elif, and tidy, an if whose
    else keyword has a comment after it
    An elif is a site of its own, so the if names no else; nor does an if
    whose else is followed by a comment, as its arm's code does not follow
    the keyword."""
    source = (
        "def size(a):\n"
        "    if a > 9:\n"
        "        return 2\n"
        "    elif a > 1:\n"
        "        return 1\n"
        "def tidy(a):\n"
        "    if a:\n"
        "        return 1\n"
        "    else:  # the rest\n"
        "        return 2\n"
    )
    elses = [_fold(source, site, "if")[0]["else"] for site in ("k.py:2:4", "k.py:7:4")]
    assert elses == [None, None]


def test_7d61a405():
    """Example: 1 if a else (b or c), its else arm an or
    Each row is placed at its code: the predicate, each arm, and the or's
    operands, under the else arm whose row stands for the or."""
    source = "def pick(a, b, c):\n    return 1 if a else (b or c)\n"
    rows = _fold(source, "k.py:2:13", "ternary")
    placed = [(row["kind"], row["label"]["text"], row["at"]) for row in rows[1:]]
    assert placed == [
        ("operand", "a", [2, 16, 2, 17]),
        ("arm", "? 1", [2, 11, 2, 12]),
        ("arm", ": or", [2, 24, 2, 30]),
        ("operand", "b", [2, 24, 2, 25]),
        ("operand", "c", [2, 29, 2, 30]),
    ]


def test_7d61a406():
    """Example: [u for u in users if u.active], its filter
    The filter's arms, keep and drop, have no code, so are placed nowhere;
    its fold is its predicate, placed at its code."""
    source = "def active(users):\n    return [u for u in users if u.active]\n"
    rows = _fold(source, "k.py:2:29", "filter")
    assert [(row["kind"], row["at"]) for row in rows] == [("site", [2, 29, 2, 40]), ("operand", [2, 32, 2, 40])]


def test_7d61a407():
    """Example: guard, an if with no else, returning early
    An if with no else arm has no else keyword to name."""
    source = "def guard(a):\n    if a:\n        return 0\n    return 1\n"
    assert _fold(source, "k.py:2:4", "if")[0]["else"] is None


def _fold(source, site, top):
    """The rows of the fold of site in source, as if it were k.py, as the
    source report has them, headed by top, a column for each of its
    possible paths."""
    sites = manifest.sites(source, "k.py")
    paths = [{"path": path, "count": 0} for path in site_paths.possible(sites[site])]
    return source_report.site(source, sites, site, paths, top)["fold"]

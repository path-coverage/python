from pathlib import Path

from path_coverage import card_tree, manifest, site_paths

TOP = (None, None, None, None, None)


def _places(source):
    """(parent, in, on, leaf, gives) of each row of source's one card, its
    def on line 1, as if source were k.py."""
    rows = card_tree.of(source, "k.py")["k.py:1:0"]
    keys = ("parent", "in", "on", "leaf", "gives")
    return {key: tuple(place[name] for name in keys) for key, place in rows.items()}


def test_5be7c001():
    """Example: pick, an if of a and b holding an if of b, each arm of
    which returns.
    Each row names its parent, the site whose arm it is in, that arm, and
    on, the parent's possible paths it runs on, by index: the inner if runs
    only on the outer's one path that takes its then arm. A row at the top
    of the function has none of these. The and, the outer if's predicate,
    is a row in that if's one leaf, giving it true only where a and b
    are."""
    source = (
        "def pick(a, b):\n"
        "    if a and b:\n"
        "        if b:\n"
        "            return 1\n"
        "        else:\n"
        "            return 2\n"
    )
    assert _places(source) == {
        "2:4": TOP,
        "2:9": ("2:4", None, [0, 1], 0, [True, False, False]),
        "3:8": ("2:4", "then", [0], None, None),
        "4:12": ("3:8", "then", [0], None, None),
        "6:12": ("3:8", "else", [1], None, None),
    }


def test_5be7c002():
    """Example: odd, an if of a whose then arm passes, a conditional
    expression returned in its else.
    The pass is no row; the conditional expression runs in the else, on the
    if's false path."""
    source = (
        "def odd(a, b):\n"
        "    if a:\n"
        "        pass\n"
        "    else:\n"
        "        return 1 if b else 2\n"
    )
    assert _places(source) == {
        "2:4": TOP,
        "5:17": ("2:4", "else", [1], None, None),
    }


def test_5be7c003():
    """Example: kept, an and of a and an any of a generator.
    A row inside a leaf of its parent is in no arm, names that leaf by its
    index, and runs on each of its parent's paths that evaluate the leaf:
    the any runs where a was true, not where it was false.
    The any is the whole of that leaf, so it also names what each of its
    own possible paths gives the leaf: its value, False with 0 items, else
    its last answer."""
    source = "def kept(a, xs):\n    return a and any(x > 1 for x in xs)\n"
    gives = [False, True, False, True, False]
    assert _places(source) == {
        "2:13": TOP,
        "2:17": ("2:13", None, [0, 1], 1, gives),
    }


def test_5be7c004():
    """Example: each_if, an and of a and a conditional expression of b
    whose else arm is an any.
    A row inside an arm of a site runs only on that site's paths that take
    the arm: the any runs where b was false. The conditional expression
    itself is a row, the whole of the and's second leaf, giving it a value
    not known on each of its paths, as neither arm's truthiness is noted;
    the any is in an arm, in no leaf, so gives nothing."""
    source = "def each_if(a, b, xs):\n    return a and (3 if b else any(x for x in xs))\n"
    assert _places(source) == {
        "2:13": TOP,
        "2:20": ("2:13", None, [0, 1], 1, [None, None]),
        "2:30": ("2:20", "else", [1], None, None),
    }


def test_5be7c006():
    """Example: size, a conditional expression whose else arm is another.
    The inner conditional expression is a site of its own, not part of the
    outer one's, so it is a row of its own, placed in the outer's else arm,
    on its false path."""
    source = 'def size(n, big):\n    return "big" if big else ("some" if n > 1 else "none")\n'
    assert _places(source) == {
        "2:17": TOP,
        "2:37": ("2:17", "else", [1], None, None),
    }


def test_5be7c007():
    """Example: pick, a conditional expression whose else arm is an or of b
    and an any
    The any is in the else arm and in the or's second leaf, the
    expression's third, so it runs only on the paths that take the else
    arm and evaluate that leaf: where a and b were both false. It is the
    whole of its leaf, so gives the leaf its value."""
    source = "def pick(a, b, xs):\n    return 1 if a else (b or any(x for x in xs))\n"
    assert _places(source) == {
        "2:13": TOP,
        "2:29": ("2:13", "else", [2, 3], 2, [False, True, False, True, False]),
    }


def test_5be7c005():
    """Example: every Python file of the package's src and test.
    Every row placed in a parent is placed in a row of its own card, on
    some of that parent's possible paths and on none it does not have: no
    row hangs from nothing, or runs on no path. And no row is its own
    ancestor: following parents from any row reaches the top."""
    root = Path(__file__).resolve().parent.parent
    files = sorted([*root.glob("src/path_coverage/**/*.py"), *root.glob("test/*.py")])
    misplaced = {str(path.relative_to(root)): _misplaced(path.read_text()) for path in files}
    assert misplaced == {name: [] for name in misplaced}


def _misplaced(source):
    """Each misfit of every card of source, as if it were k.py: a parent
    that is no row of its card, a row on no path, a path its parent does
    not have, and a row that is its own ancestor."""
    sites = manifest.sites(source, "k.py")
    found = []
    for rows in card_tree.of(source, "k.py").values():
        inner = [place for place in rows.values() if place["parent"]]
        for place in inner:
            parent = place["parent"]
            possible = range(len(site_paths.possible(sites[f"k.py:{parent}"])))
            found += sorted({parent} - set(rows))
            found += ["no path"] * (place["on"] == [])
            found += sorted(set(place["on"]) - set(possible))
        found += _looped(rows)
    return found


def _looped(rows):
    """The key each row of rows, a card's places, reaches after as many
    steps up its parents as rows has rows: none, unless a row is its own
    ancestor, as every other walk reaches the top."""
    reached = []
    for key in rows:
        at = key
        for _ in rows:
            at = rows.get(at, {}).get("parent")
        reached.append(at)
    return list(filter(None, reached))

from path_coverage import listed_cards, manifest, result

SHOP = (
    "RATE = 2 if FAST else 1\n"
    "def ship(order):\n"
    "    return order.paid and order.packed\n"
    "class Shop:\n"
    "    SIZE = 3 if BIG else 1\n"
)


def _then_taken(count):
    """A ternary's paths, its then taken count times, its else never."""
    return [{"path": [True], "count": count}, {"path": [False], "count": 0}]


PATHS = {
    "k.py:1:9": _then_taken(1),
    "k.py:3:22": [
        {"path": [True, True], "count": 1},
        {"path": [True, False], "count": 0},
        {"path": [False, None], "count": 0},
    ],
    "k.py:5:13": _then_taken(0),
}


def _listed(source, paths, reached):
    """The listed cards of source, as if it were k.py, from paths and
    reached, its operands all zero, with no ways taken."""
    decisions = manifest.decisions(source, "k.py")
    files = {"k.py": (source, decisions)}
    return listed_cards.of(files, result.operands(decisions, {}), paths, (reached, {}))


def test_d3c9a101():
    """Example: SHOP, RATE's then taken, SIZE's never, ship's and once
    Each card is listed as its page draws it: its name, its first and
    last lines, the ways one call can go through it, how many times it was
    called, never here, none for a top card, and a row per statement.
    A row has its line:col, its top, its paths, how many were taken,
    and its decision.
    A top card is named for its first line, its name the class holding
    it, or file when none does."""
    assert _listed(SHOP, PATHS, {}) == {
        "k.py:2:0": {
            "name": "ship",
            "first": 2,
            "last": 3,
            "ways": 3,
            "calls": 0,
            "rows": [{"at": "3:22", "top": "and", "paths": 3, "taken": 1, "decision": "k.py:3:22"}],
            "taken": [],
            "passes": {},
            "covered": [],
            "gaps": [
                [{"at": "3:22", "path": [True, True]}],
                [{"at": "3:22", "path": [True, False]}],
                [{"at": "3:22", "path": [False, None]}],
            ],
            "impossible": [],
        },
        "k.py:1:0": {
            "name": "file",
            "first": 1,
            "last": 1,
            "ways": 2,
            "calls": None,
            "rows": [{"at": "1:09", "top": "ternary", "paths": 2, "taken": 1, "decision": "k.py:1:9"}],
        },
        "k.py:5:0": {
            "name": "Shop",
            "first": 5,
            "last": 5,
            "ways": 2,
            "calls": None,
            "rows": [{"at": "5:13", "top": "ternary", "paths": 2, "taken": 0, "decision": "k.py:5:13"}],
        },
    }


def test_d3c9a103():
    """Example: SHOP's tree
    How each card's rows nest is listed for ship's card and for each top
    card, RATE's and Shop's, each by its line:col; each row here at the
    top, inside no other decision."""
    top = {"parent": None, "in": None, "on": None, "leaf": None, "gives": None}
    decisions = manifest.decisions(SHOP, "k.py")
    tree = listed_cards.tree({"k.py": (SHOP, decisions)}, result.operands(decisions, {}))
    assert tree == {"k.py": {"2:0": {"3:22": top}, "1:0": {"1:9": top}, "5:0": {"5:13": top}}}


def test_d3c9a102():
    """Example: ship, a write then a return, the return reached
    The write is no row. The return is a row that has no decision, and its
    taken is 1 when reached. Without reached, its taken is None, not
    known."""
    source = (
        "def ship(order):\n"
        "    box = order.pack()\n"
        "    return box\n"
    )
    rows = [
        [row["taken"] for row in _listed(source, {}, reached)["k.py:1:0"]["rows"]]
        for reached in ({"k.py:3:4": 1}, None)
    ]
    assert rows == [[1], [None]]
    assert [row["decision"] for row in _listed(source, {}, {})["k.py:1:0"]["rows"]] == [None]


def test_d3c9a104():
    """Example: save, an if on dry_run whose arm returns, a for loop, an
    if on not dry_run, a return; called twice, dry_run false, 2+ records.
    A function card lists the possible paths of its machine some call
    witnessed, covered, each with how many calls did; its gaps, those no
    call witnessed; and its impossible paths, each giving the stable
    dry_run both outcomes, neither with a count. The for is a fork, 0 or
    1+ items; the calls' 2+ passes witness its 1+ items path. Its ways
    are its possible paths."""
    source = (
        "def save(records, dry_run, db):\n"
        "    if dry_run:\n"
        "        return 0\n"
        "    for record in records:\n"
        "        db.append(record)\n"
        "    if not dry_run:\n"
        "        db.append('done')\n"
        "    return len(db)\n"
    )
    decisions = manifest.decisions(source, "k.py")
    taken = (("k.py:2:4", (False,)), ("k.py:4:4", ("2+ items",), frozenset({()})), ("k.py:6:4", (True,)), ("k.py:8:4",))
    counted = ({"k.py:1:0": 2}, {"k.py:1:0": {taken: 2}})
    paths = {
        "k.py:2:4": [{"path": [True], "count": 0}, {"path": [False], "count": 2}],
        "k.py:6:4": [{"path": [True], "count": 2}, {"path": [False], "count": 0}],
    }
    files = {"k.py": (source, decisions)}
    card = listed_cards.of(files, result.operands(decisions, {}), paths, counted)["k.py:1:0"]
    on = {"at": "2:04", "path": [False]}
    none, some = {"at": "4:04", "path": ["0 items"]}, {"at": "4:04", "path": ["1+ items"]}
    assert (card["ways"], card["covered"], card["gaps"], card["impossible"]) == (
        3,
        [{"way": [on, some, {"at": "6:04", "path": [True]}, {"at": "8:04"}], "count": 2}],
        [[{"at": "2:04", "path": [True]}, {"at": "3:08"}], [on, none, {"at": "6:04", "path": [True]}, {"at": "8:04"}]],
        [[on, loop, {"at": "6:04", "path": [False]}, {"at": "8:04"}] for loop in (none, some)],
    )


def test_d3c9a105():
    """Example: half, an if whose condition is an or, then a return;
    called once, with a child.
    A call steps the or, decided first, before the if holding it, though
    the card's tree lists the if first; the machine steps in that order
    too, so a taken way matches its possible path, and each gap lists its
    steps as a call would take them."""
    source = (
        "def half(age, price):\n"
        "    if age < 16 or age >= 65:\n"
        "        price //= 2\n"
        "    return price\n"
    )
    decisions = manifest.decisions(source, "k.py")
    taken = (("k.py:2:16", (True, None)), ("k.py:2:4", (True,)), ("k.py:4:4",))
    counted = ({"k.py:1:0": 1}, {"k.py:1:0": {taken: 1}})
    paths = {
        "k.py:2:4": [{"path": [True], "count": 1}, {"path": [False], "count": 0}],
        "k.py:2:16": [
            {"path": [True, None], "count": 1},
            {"path": [False, True], "count": 0},
            {"path": [False, False], "count": 0},
        ],
    }
    files = {"k.py": (source, decisions)}
    card = listed_cards.of(files, result.operands(decisions, {}), paths, counted)["k.py:1:0"]
    assert card["gaps"] == [
        [{"at": "2:16", "path": [False, True]}, {"at": "2:04", "path": [True]}, {"at": "4:04"}],
        [{"at": "2:16", "path": [False, False]}, {"at": "2:04", "path": [False]}, {"at": "4:04"}],
    ]

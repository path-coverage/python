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

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
    "k.py:1:7": _then_taken(1),
    "k.py:3:11": [
        {"path": [True, True], "count": 1},
        {"path": [True, False], "count": 0},
        {"path": [False, None], "count": 0},
    ],
    "k.py:5:11": _then_taken(0),
}


def _listed(source, paths, reached):
    """The listed cards of source, as if it were k.py, from paths and
    reached, its operands all zero."""
    sites = manifest.sites(source, "k.py")
    files = {"k.py": (source, sites)}
    return listed_cards.of(files, result.operands(sites, {}), paths, reached)


def test_d3c9a101():
    """Example: SHOP, RATE's then taken, SIZE's never, ship's and once
    Each card is listed as its page draws it: its name, its first and
    last lines, and a row per statement.
    A row has its line:col, its top, its paths, how many were taken,
    and its site.
    A top card is named for its first line, its name the class holding
    it, or file when none does."""
    assert _listed(SHOP, PATHS, {}) == {
        "k.py:2:0": {
            "name": "ship",
            "first": 2,
            "last": 3,
            "rows": [{"at": "3:11", "top": "and", "paths": 3, "taken": 1, "site": "k.py:3:11"}],
        },
        "k.py:1:0": {
            "name": "file",
            "first": 1,
            "last": 1,
            "rows": [{"at": "1:07", "top": "ternary", "paths": 2, "taken": 1, "site": "k.py:1:7"}],
        },
        "k.py:5:0": {
            "name": "Shop",
            "first": 5,
            "last": 5,
            "rows": [{"at": "5:11", "top": "ternary", "paths": 2, "taken": 0, "site": "k.py:5:11"}],
        },
    }


def test_d3c9a102():
    """Example: ship, a write then a return, the write reached
    A row that is no site has no site, and its taken is 1 when reached.
    Without reached, its taken is None, not known."""
    source = (
        "def ship(order):\n"
        "    box = order.pack()\n"
        "    return box\n"
    )
    rows = [
        [row["taken"] for row in _listed(source, {}, reached)["k.py:1:0"]["rows"]]
        for reached in ({"k.py:2:4": 1}, None)
    ]
    assert rows == [[1, 0], [None, None]]
    assert [row["site"] for row in _listed(source, {}, {})["k.py:1:0"]["rows"]] == [None, None]

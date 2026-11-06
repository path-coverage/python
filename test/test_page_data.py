from path_coverage import page_data


def test_e2b45f01():
    """Example: shop.py, 1 of its 8 method paths taken, and a group
    holding no file
    The index's data has a table per tab, each row's percent rounded half
    up, and none, None, when no path is possible, so the page shows -
    rather than dividing by zero."""
    row = {"path": "src/shop.py", "sites": 2, "decisions": [2, 4], "methods": [1, 8]}
    none = {"sites": 0, "decisions": [0, 0], "methods": [0, 0]}
    data = page_data.index([["All files", [row], row], ["Admin", [], none]], [])
    assert data == {
        "schema": 1,
        "page": "index",
        "tables": [
            {
                "name": "All files",
                "rows": [{"path": "src/shop.py", "sites": 2, "methods": [1, 8], "percent": 13}],
                "total": {"sites": 2, "methods": [1, 8], "percent": 13},
            },
            {"name": "Admin", "rows": [], "total": {"sites": 0, "methods": [0, 0], "percent": None}},
        ],
        "ignored": [],
    }


def test_e2b45f02():
    """Example: ship, an if/else at 3:4 taken one way of two, then a
    return at 7:4 reached
    A card's data has its title's numbers worked out: the paths not taken,
    and taken, over its rows. A site's row has its fold; a return row, no
    site, has none, and its fold is never asked for."""
    listed = {
        "name": "ship",
        "first": 2,
        "last": 7,
        "ways": 3,
        "calls": 2,
        "rows": [
            {"at": "3:04", "top": "if/else", "paths": 2, "taken": 1, "site": "k.py:3:4"},
            {"at": "7:04", "top": "return", "paths": 1, "taken": 1, "site": None},
        ],
    }
    place = {"first": 2, "last": 7, "column": 0, "status": "gaps", "top": False, "sites": None}
    asked = []

    def fold(site, top):
        """A fold of one site row, noting what it was asked for."""
        asked.append((site, top))
        return [{"kind": "site"}]

    data = page_data.card(listed, place, fold)
    assert asked == [("k.py:3:4", "if/else")]
    assert data["title"] == {"name": "ship", "calls": 2, "ways": 3, "notTaken": 1, "taken": 2}
    assert [row["fold"] for row in data["rows"]] == [[{"kind": "site"}], None]
    assert data["rows"][0]["top"] == {"text": "if/else", "tokens": [[0, 2, "k"], [3, 7, "k"]]}


def test_e2b45f03():
    """Example: __init__, no rows, called once, then never; ship, its if
    taken one way of two, then every way; pick, both its rows taken every
    way, then its return never reached
    A card is covered only when every row took all its paths and its
    function was called: never called, a function ran none of its code,
    so it has a gap; and one row's gap is the card's."""
    def init(calls):
        """__init__'s card, called calls times."""
        return {"calls": calls, "rows": []}

    def ship(taken):
        """ship's card, its if taken taken ways of 2."""
        return {"calls": 3, "rows": [{"paths": 2, "taken": taken}]}

    def pick(returned):
        """pick's card, its if taken every way, its return reached
        returned times."""
        return {"calls": 2, "rows": [{"paths": 2, "taken": 2}, {"paths": 1, "taken": returned}]}

    cards = (init(1), init(0), ship(1), ship(2), pick(1), pick(0))
    assert [page_data.status(card) for card in cards] == ["covered", "gaps", "gaps", "covered", "covered", "gaps"]


def test_e2b45f04():
    """Example: line 3 of shop.py, if order.gift and, in a span of sites
    over lines 3 to 4, and line 5, blank
    A file page's data has each line's text and tokens, and the status and
    span of the sites it is in, None for a line in none."""
    lines = [
        {"number": 3, "text": "    if order.gift and", "status": "gaps", "span": (3, 4), "tokens": [[4, 6, "k"]]},
        {"number": 5, "text": "", "status": None, "span": None, "tokens": []},
    ]
    assert page_data.file("src/shop.py", lines, []) == {
        "schema": 1,
        "page": "file",
        "path": "src/shop.py",
        "lines": [
            {"text": "    if order.gift and", "tokens": [[4, 6, "k"]], "status": "gaps", "span": [3, 4]},
            {"text": "", "tokens": [], "status": None, "span": None},
        ],
        "cards": [],
    }

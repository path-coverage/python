from path_coverage.summary import files, groups, total


def _paths(*counts):
    """A site's paths, one per count given, as result.paths gives them."""
    return [{"path": [index], "count": count} for index, count in enumerate(counts)]


def test_1a6f0c01():
    """Example: kata.py with two sites, team.py with one
    Each covered file gets one row for the index page.
    Its sites, eg 2 for kata.py.
    Its decisions total as [taken, possible] paths, eg [3, 6].
    Its methods total, its cards added up, eg [2, 3]."""
    paths = {
        "src/kata.py:3:11": _paths(2, 0, 1),
        "src/kata.py:4:11": _paths(1, 0, 0),
        "src/team.py:2:11": _paths(1, 1, 4),
    }
    cards = {"src/kata.py:1:0": [2, 3], "src/team.py:0:0": [3, 3]}
    assert files(paths, cards) == [
        {"path": "src/kata.py", "sites": 2, "decisions": [3, 6], "methods": [2, 3]},
        {"path": "src/team.py", "sites": 1, "decisions": [3, 3], "methods": [3, 3]},
    ]


def test_1a6f0c02():
    """Example: fee.py's cards, fee's 3 of 6 paths taken and tax's 2 of
    3, and kata.py with no function
    fee.py's methods total is its cards added up, [5, 9].
    kata.py's is [0, 0], as it has no card."""
    paths = {
        "src/fee.py:7:4": _paths(1, 0),
        "src/fee.py:9:4": _paths(0, 1),
        "src/kata.py:3:11": _paths(1, 1),
    }
    cards = {"src/fee.py:4:0": [3, 6], "src/fee.py:12:0": [2, 3]}
    rows = files(paths, cards)
    assert {row["path"]: row["methods"] for row in rows} == {
        "src/fee.py": [5, 9],
        "src/kata.py": [0, 0],
    }


def test_1a6f0c03():
    """Example: rows for kata.py and fee.py
    The total row adds up each column over every file.
    Sites 2 + 3 = 5, decisions [3, 6] + [2, 4] = [5, 10], and methods
    [0, 0] + [1, 4] = [1, 4]."""
    rows = [
        {"path": "src/kata.py", "sites": 2, "decisions": [3, 6], "methods": [0, 0]},
        {"path": "src/fee.py", "sites": 3, "decisions": [2, 4], "methods": [1, 4]},
    ]
    assert total(rows) == {"sites": 5, "decisions": [5, 10], "methods": [1, 4]}


KATA = {"path": "src/model/kata.py", "sites": 2, "decisions": [3, 6], "methods": [4, 7]}
FEE = {"path": "src/model/fee.py", "sites": 3, "decisions": [2, 4], "methods": [3, 5]}
ROUTES = {"path": "src/app/routes.py", "sites": 1, "decisions": [1, 2], "methods": [1, 2]}
SETUP = {"path": "setup.py", "sites": 1, "decisions": [0, 2], "methods": [0, 2]}


def test_1a6f0c04():
    """Example: groups models (src/model/**/*.py) and kata (**/kata.py)
    Each group is [name, its rows, their total], in the order given.
    A file is in every group a glob of which it matches, so kata.py is in
    both.
    Ungrouped comes last, holding the rows no group matches."""
    rows = [ROUTES, FEE, KATA, SETUP]
    named = {"models": ["src/model/**/*.py"], "kata": ["**/kata.py"]}
    assert groups(rows, named) == [
        ["models", [FEE, KATA], {"sites": 5, "decisions": [5, 10], "methods": [7, 12]}],
        ["kata", [KATA], {"sites": 2, "decisions": [3, 6], "methods": [4, 7]}],
        ["Ungrouped", [ROUTES, SETUP], {"sites": 2, "decisions": [1, 4], "methods": [1, 4]}],
    ]


def test_1a6f0c05():
    """Example: groups code (src/**/*.py) and setup (setup.py)
    Every row is in a group.
    So there is no Ungrouped group."""
    rows = [ROUTES, KATA, SETUP]
    named = {"code": ["src/**/*.py"], "setup": ["setup.py"]}
    assert [name for name, _, _ in groups(rows, named)] == ["code", "setup"]


def test_1a6f0c06():
    """Example: a group lib (lib/**/*.py) that no file matches
    Its total has no sites and 0 / 0 paths.
    So its tab's Total row shows - rather than failing."""
    assert groups([KATA], {"lib": ["lib/**/*.py"]})[0] == [
        "lib",
        [],
        {"sites": 0, "decisions": [0, 0], "methods": [0, 0]},
    ]

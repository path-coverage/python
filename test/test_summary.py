from path_coverage.path_manifest import Decision, PathMethod
from path_coverage.summary import files, total


def _paths(*counts):
    """A site's paths, one per count given, as result.paths gives them."""
    return [{"path": [index], "count": count} for index, count in enumerate(counts)]


def test_1a6f0c01():
    """Example: kata.py with two sites, team.py with one
    Each covered file gets one row for the index page.
    Its sites, eg 2 for kata.py.
    Its decisions total as [taken, possible] paths, eg [3, 6].
    Its methods total is None, as methods are not measured."""
    paths = {
        "src/kata.py:3:11": _paths(2, 0, 1),
        "src/kata.py:4:11": _paths(1, 0, 0),
        "src/team.py:2:11": _paths(1, 1, 4),
    }
    assert files(paths) == [
        {"path": "src/kata.py", "sites": 2, "decisions": [3, 6], "methods": None},
        {"path": "src/team.py", "sites": 1, "decisions": [3, 3], "methods": None},
    ]


def test_1a6f0c02():
    """Example: fee.py's fee with two decisions, called with True then
    False only, and kata.py with no function of two decisions
    Methods are measured, so each row has a methods total.
    fee.py's is [1, 4], one of fee's four paths.
    kata.py's is [0, 0], as it has no function's paths."""
    paths = {
        "src/fee.py:7:4": _paths(1, 0),
        "src/fee.py:9:4": _paths(0, 1),
        "src/kata.py:3:11": _paths(1, 1),
    }
    fee = PathMethod(name="fee", decisions=(Decision(line=7), Decision(line=9)))
    methods = {"src/fee.py:4:0": fee}
    taken = {"src/fee.py:4:0": {(True, False): 1}}
    rows = files(paths, methods, taken)
    assert {row["path"]: row["methods"] for row in rows} == {
        "src/fee.py": [1, 4],
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

from path_coverage.console_summary import group_totals, grouped_lines, lines

GROUPS = {"code": ["src/**/*.py"], "test": ["test/**/*.py"]}


def test_7c3d9101():
    """Example: src/kata.py's site taking 2 of its 3 paths, no groups
    The summary is one line of the paths taken within decisions.
    Methods are not measured, so there is no methods line."""
    paths = {
        "src/kata.py:3:11": [
            {"path": [True, True], "count": 2},
            {"path": [True, False], "count": 1},
            {"path": [False, None], "count": 0},
        ]
    }
    assert lines(paths) == ["Path coverage within decisions: 2 / 3 (66.67%)"]


def test_7c3d9102():
    """Example: src/kata.py's site taking 2 of its 3 paths, and
    test/test_kata.py's taking 1 of its 2, with groups code and test
    Each group is a heading, its own totals indented under it.
    There is no total over every group."""
    paths = {
        "src/kata.py:3:11": [
            {"path": [True, True], "count": 2},
            {"path": [True, False], "count": 1},
            {"path": [False, None], "count": 0},
        ],
        "test/test_kata.py:9:11": [
            {"path": [True], "count": 4},
            {"path": [False], "count": 0},
        ],
    }
    assert lines(paths, groups=GROUPS) == [
        "code:",
        "  Path coverage within decisions: 2 / 3 (66.67%)",
        "test:",
        "  Path coverage within decisions: 1 / 2 (50.00%)",
    ]


def test_7c3d9103():
    """Example: fee's card in src/fee.py, 1 of its 4 paths taken, and
    groups code and test
    Each group has a methods line too: code has fee's 1 / 4.
    test, with no function, has 0 / 0, shown as -."""
    cards = {"src/fee.py:1:0": [1, 4]}
    assert lines({}, cards, GROUPS) == [
        "code:",
        "  Path coverage within decisions: 0 / 0 (-)",
        "  Path coverage within methods: 1 / 4 (25.00%)",
        "test:",
        "  Path coverage within decisions: 0 / 0 (-)",
        "  Path coverage within methods: 0 / 0 (-)",
    ]


def test_7c3d9104():
    """Example: two sites, both in src/, with groups code and test
    code totals both sites' paths; test totals none."""
    taken_once = {"path": [True], "count": 1}
    paths = {"src/a.py:1:0": [taken_once], "src/b.py:1:0": [taken_once]}
    assert group_totals(paths, None, GROUPS) == {
        "code": {"decisions": [2, 2]},
        "test": {"decisions": [0, 0]},
    }


def test_7c3d9105():
    """Example: a JSON report's totals.groups for code and test
    Each group is a heading, its totals indented under it, as the
    summary reporter prints them."""
    assert grouped_lines(
        {
            "code": {"decisions": [260, 325], "methods": [32, 62]},
            "test": {"decisions": [7, 8], "methods": [0, 0]},
        }
    ) == [
        "code:",
        "  Path coverage within decisions: 260 / 325 (80.00%)",
        "  Path coverage within methods: 32 / 62 (51.61%)",
        "test:",
        "  Path coverage within decisions: 7 / 8 (87.50%)",
        "  Path coverage within methods: 0 / 0 (-)",
    ]

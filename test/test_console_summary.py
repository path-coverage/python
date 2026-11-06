from path_coverage.console_summary import group_totals, grouped_lines, lines

GROUPS = {"code": ["src/**/*.py"], "test": ["test/**/*.py"]}


def test_7c3d9101():
    """Example: src/kata.py's decision taking 2 of its 3 paths, no groups
    The summary is one line of the paths taken alone.
    Methods are not measured, so there is no combined line."""
    paths = {
        "src/kata.py:3:11": [
            {"path": [True, True], "count": 2},
            {"path": [True, False], "count": 1},
            {"path": [False, None], "count": 0},
        ]
    }
    assert lines(paths) == ["Paths alone: 2 / 3 (66.67%)"]


def test_7c3d9102():
    """Example: src/kata.py's decision taking 2 of its 3 paths, and
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
        "  Paths alone: 2 / 3 (66.67%)",
        "test:",
        "  Paths alone: 1 / 2 (50.00%)",
    ]


def test_7c3d9103():
    """Example: fee's card in src/fee.py, 1 of its 4 paths taken, and
    groups code and test
    Each group has a combined line too: code has fee's 1 / 4.
    test, with no function, has 0 / 0, shown as -."""
    cards = {"src/fee.py:1:0": [1, 4]}
    assert lines({}, cards, GROUPS) == [
        "code:",
        "  Paths alone: 0 / 0 (-)",
        "  Paths combined: 1 / 4 (25.00%)",
        "test:",
        "  Paths alone: 0 / 0 (-)",
        "  Paths combined: 0 / 0 (-)",
    ]


def test_7c3d9104():
    """Example: two decisions, both in src/, with groups code and test
    code totals both decisions' paths; test totals none."""
    taken_once = {"path": [True], "count": 1}
    paths = {"src/a.py:1:0": [taken_once], "src/b.py:1:0": [taken_once]}
    assert group_totals(paths, None, GROUPS) == {
        "code": {"alone": [2, 2]},
        "test": {"alone": [0, 0]},
    }


def test_7c3d9105():
    """Example: a JSON report's totals.groups for code and test
    Each group is a heading, its totals indented under it, as the
    summary reporter prints them."""
    assert grouped_lines(
        {
            "code": {"alone": [260, 325], "combined": [32, 62]},
            "test": {"alone": [7, 8], "combined": [0, 0]},
        }
    ) == [
        "code:",
        "  Paths alone: 260 / 325 (80.00%)",
        "  Paths combined: 32 / 62 (51.61%)",
        "test:",
        "  Paths alone: 7 / 8 (87.50%)",
        "  Paths combined: 0 / 0 (-)",
    ]

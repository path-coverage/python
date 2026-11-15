from path_coverage.card_gaps import lines

CARD = "source/fee.py:5:0"
ROWS = [
    {"at": "8:04", "top": "if", "paths": 2, "taken": 2, "decision": "source/fee.py:8:4"},
    {"at": "8:19", "top": "and", "paths": 3, "taken": 2, "decision": "source/fee.py:8:19"},
    {"at": "10:04", "top": "if", "paths": 2, "taken": 2, "decision": "source/fee.py:10:4"},
    {"at": "12:04", "top": "return", "paths": 1, "taken": 1, "decision": None},
]
TEXTS = {
    "source/fee.py:8:4": ["user.member and order.paid"],
    "source/fee.py:8:19": ["user.member", "order.paid"],
    "source/fee.py:10:4": ["order.big"],
}
PARENTS = {"source/fee.py:8:19": "source/fee.py:8:4"}


def test_a3c95e01():
    """Example: fee, an if on an and, then an if on order.big, its card
    with 4 of its 6 paths untested
    One heading for the function, then each untested path as a numbered
    line of its choices, in order, each leaf by its text. An if whose
    test is an and repeats the and's choice, so only the and is named;
    a step with no choice, eg a return, is left out."""
    gaps = [
        [{"at": "8:19", "path": [True, True]}, {"at": "8:04", "path": [True]}, {"at": "10:04", "path": [False]}, {"at": "12:04"}],
        [{"at": "8:19", "path": [True, False]}, {"at": "8:04", "path": [False]}, {"at": "10:04", "path": [True]}, {"at": "12:04"}],
        [{"at": "8:19", "path": [True, False]}, {"at": "8:04", "path": [False]}, {"at": "10:04", "path": [False]}, {"at": "12:04"}],
        [{"at": "8:19", "path": [False, None]}, {"at": "8:04", "path": [False]}, {"at": "10:04", "path": [True]}, {"at": "12:04"}],
    ]
    cards = {CARD: {"name": "fee", "rows": ROWS, "gaps": gaps}}
    assert lines(cards, TEXTS, PARENTS) == [
        "source/fee.py:5 fee has 4 untested paths.",
        "Add tests that take each of these paths:",
        "  1. line 8 `user.member` true, `order.paid` true, then line 10 `order.big` false",
        "  2. line 8 `user.member` true, `order.paid` false, then line 10 `order.big` true",
        "  3. line 8 `user.member` true, `order.paid` false, then line 10 `order.big` false",
        "  4. line 8 `user.member` false, then line 10 `order.big` true",
    ]


def test_a3c95e02():
    """Example: fee with every path tested, beside a card with one gap
    A function with no untested path gets no lines at all; one with a
    single untested path says path, not paths."""
    tested = {"name": "fee", "rows": ROWS, "gaps": []}
    untested = {
        "name": "fee",
        "rows": ROWS,
        "gaps": [[{"at": "8:19", "path": [False, None]}, {"at": "8:04", "path": [False]}, {"at": "10:04", "path": [True]}, {"at": "12:04"}]],
    }
    cards = {CARD: tested, "source/fee_copy.py:5:0": untested}
    assert lines(cards, TEXTS, PARENTS) == [
        "source/fee_copy.py:5 fee has 1 untested path.",
        "Add tests that take each of these paths:",
        "  1. line 8 `user.member` false, then line 10 `order.big` true",
    ]


def test_a3c95e03():
    """Example: left_in, a list comprehension whose loop ran no items
    A loop has no row, so its step is named by its line, and how many
    items it ran."""
    rows = [{"at": "6:04", "top": "return", "paths": 1, "taken": 1, "decision": None}]
    cards = {
        "src/nested.py:4:0": {
            "name": "left_in",
            "rows": rows,
            "gaps": [[{"at": "6:04"}, {"at": "6:14", "path": ["0 items"]}]],
        }
    }
    assert lines(cards, {}, {}) == [
        "src/nested.py:4 left_in has 1 untested path.",
        "Add tests that take each of these paths:",
        "  1. line 6 loop: 0 items",
    ]

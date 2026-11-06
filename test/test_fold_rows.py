from path_coverage import fold_rows


def _shown(row):
    """What a fold row shows: its label's text, then each cell's mark, eg
    taken, or else its text."""
    return [row["label"]["text"], *([mark or text for text, mark, _ in row.get("cells", [])])]


def _of_kind(rows, kind):
    """The rows of rows of kind, eg operand."""
    return [row for row in rows if row["kind"] == kind]


def test_a91f2b01():
    """Example: user.active and user.admin, a path never taken, then two
    taken, once and 1284 times
    The decision's row has each path's count, how many times it was taken.
    Each operand row shows T or F per path, blank where not reached, each
    branching from the and: a tee, then an ell to the last."""
    tree = {
        "operator": "and",
        "counts": [0, 1, 1284],
        "cells": [False, True, False],
        "operands": [
            {"text": "user.active", "cells": [True, True, False]},
            {"text": "user.admin", "cells": [False, True, None]},
        ],
    }
    rows = fold_rows.rows(tree)
    assert [rows[0]["kind"], rows[0]["label"], rows[0]["counts"]] == [
        "decision",
        {"text": "and", "tokens": [[0, 3, "k"]]},
        [0, 1, 1284],
    ]
    assert [[row["branch"], *_shown(row)] for row in rows[1:]] == [
        ["ths", "user.active", "T", "T", "F"],
        ["lhs", "user.admin", "F", "T", ""],
    ]


def test_a91f2b02():
    """Example: x and (y or z), two paths taken once each
    The nested or is a row of its own, with its value on each path, its
    operator coloured as the keyword it is.
    Its operands are indented under its branch: a tee to y, an ell to z."""
    tree = {
        "operator": "and",
        "counts": [1, 1],
        "cells": [True, False],
        "operands": [
            {"text": "x", "cells": [True, False]},
            {
                "operator": "or",
                "cells": [True, None],
                "operands": [{"text": "y", "cells": [True, None]}, {"text": "z", "cells": [None, None]}],
            },
        ],
    }
    rows = fold_rows.rows(tree)
    assert [(row["kind"], row["branch"], *_shown(row)) for row in rows[1:]] == [
        ("operand", "ths", "x", "T", "F"),
        ("subtree", "lhs", "or", "T", ""),
        ("operand", "sssths", "y", "T", ""),
        ("operand", "ssslhs", "z", "", ""),
    ]


def test_a91f2b03():
    """Example: if order.big: ... else: ..., one of its two paths taken
    An if's fold has no row for its arms: which arm a path takes follows
    from its predicate, and the code in an arm is a card row of its own."""
    tree = {
        "operator": "if",
        "counts": [0, 1],
        "cells": [None, None],
        "operands": [
            {"text": "order.big", "cells": [False, True]},
            {"arm": "then", "text": "pack(order)", "cells": [False, True], "body": None},
            {"arm": "else", "text": "drop(order)", "cells": [True, False], "body": None},
        ],
    }
    rows = fold_rows.rows(tree)
    assert _of_kind(rows, "arm") == []
    assert [_shown(row) for row in _of_kind(rows, "operand")] == [["order.big", "F", "T"]]


def test_a91f2b04():
    """Example: if order.free: return 0, on line 5, its then taken once
    Its arm returns, so its fold has a row for it, return, placed at its
    code, so hovering return in the code opens the fold and lights that
    row, marking each path that leaves the function there."""
    tree = {
        "operator": "if",
        "counts": [1, 1],
        "cells": [None, None],
        "operands": [
            {"text": "order.free", "cells": [True, False], "at": [5, 7, 5, 17]},
            {"arm": "then", "text": "return 0", "cells": [True, False], "body": None, "at": [6, 8, 6, 16]},
        ],
    }
    [leaves] = _of_kind(fold_rows.rows(tree), "leaves")
    assert [_shown(leaves), leaves["at"], leaves["branch"]] == [["return", "leaves", ""], [6, 8, 6, 16], "lhs"]


def test_a91f2b07():
    """Example: the filter of [u for u in users if u.active], each way once
    A filter's arms, keep and drop, have no code of their own, so its fold
    shows its predicate alone: no arm row, and no return or raise row."""
    tree = {
        "operator": "filter",
        "counts": [1, 1],
        "cells": [None, None],
        "operands": [
            {"text": "u.active", "cells": [True, False]},
            {"arm": "then", "text": None, "cells": [True, False], "body": None},
            {"arm": "else", "text": None, "cells": [False, True], "body": None},
        ],
    }
    assert [(row["kind"], *_shown(row)) for row in fold_rows.rows(tree)[1:]] == [
        ("operand", "u.active", "T", "F"),
    ]


def test_a91f2b05():
    """Example: "big" if order.big else "small", its else taken
    A ternary's fold keeps a row for each arm, ? and :, as its arms are
    part of its one expression, each marking the paths that took it."""
    tree = {
        "operator": "ternary",
        "counts": [0, 1],
        "cells": [None, None],
        "operands": [
            {"text": "order.big", "cells": [True, False]},
            {"arm": "then", "text": '"big"', "cells": [True, False], "body": None},
            {"arm": "else", "text": '"small"', "cells": [False, True], "body": None},
        ],
    }
    assert [_shown(row) for row in _of_kind(fold_rows.rows(tree), "arm")] == [
        ['? "big"', "taken", ""],
        [': "small"', "", "taken"],
    ]


def test_a91f2b06():
    """Example: any(o.late for o in orders) with paths of 0 items, 1 item
    and 2+ items, and a leaf written over two lines
    The items leaf's cells show 0, 1 and * for 2+.
    A leaf written over two lines reads as one, its line break and indent
    one space."""
    tree = {
        "operator": "any",
        "counts": [0, 1, 1],
        "cells": [False, True, False],
        "operands": [
            {"text": "orders", "cells": ["0 items", "1 item", "2+ items"]},
            {"text": "o.late and\n        o.paid", "cells": [None, True, False]},
        ],
    }
    assert [_shown(row) for row in _of_kind(fold_rows.rows(tree), "operand")] == [
        ["orders", "0", "1", "*"],
        ["o.late and o.paid", "", "T", "F"],
    ]

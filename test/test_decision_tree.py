from path_coverage.manifest import decisions
from path_coverage.decision_paths import possible
from path_coverage.decision_tree import tree_of


def _tree(source, counts, decision=None):
    """The tree of the decision named decision in source, or of its one decision when
    none is named, its possible paths taken counts times each, in possible
    order."""
    found = decisions(source, "k.py")
    [condition] = [found[decision]] if decision else found.values()
    paths = [{"path": path, "count": count} for path, count in zip(possible(condition), counts)]
    return tree_of(source, condition, paths)


def test_1a6c3e04():
    """Example: any(o.late for o in orders), its 1 item true and 2+ items
    true paths never taken
    The items leaf shows how many items each path's generator gave.
    The answer leaf shows the last answer, None with no items.
    The value follows from both: any of no items is False."""
    source = "def late(orders):\n    return any(o.late for o in orders)\n"
    assert _tree(source, [1, 0, 1, 0, 1]) == {
        "operator": "any",
        "counts": [0, 0, 1, 1, 1],
        "cells": [True, True, False, False, False],
        "operands": [
            {"text": "orders", "cells": ["1 item", "2+ items", "0 items", "1 item", "2+ items"]},
            {"text": "o.late", "cells": [True, True, None, False, False]},
        ],
    }


def test_1a6c3e01():
    """Example: ok(id) and id.startswith('N'), taken once each way but
    true then false
    The tree names its operator, with one column per path.
    Paths never taken (count 0) come first, each with its count.
    Each leaf has its source text and its outcome on each path, None
    where unreached; the decision has its value on each path."""
    source = "def kata(id):\n    return ok(id) and id.startswith('N')\n"
    assert _tree(source, [1, 0, 1]) == {
        "operator": "and",
        "counts": [0, 1, 1],
        "cells": [False, True, False],
        "operands": [
            {"text": "ok(id)", "cells": [True, True, False]},
            {"text": "id.startswith('N')", "cells": [False, True, None]},
        ],
    }


def test_1a6c3e02():
    """Example: new(id) or len(id) == 6 if ok(id) else "no"
    The predicate ok(id) decides which arm each path took.
    The then arm holds an `or`, so it has its tree; the else arm ("no")
    is plain, so its tree is None.
    The ternary's value on a path is its taken arm's, None for a plain
    arm."""
    source = 'def kata(id):\n    return new(id) or len(id) == 6 if ok(id) else "no"\n'
    tree = _tree(source, [1, 0, 2, 3])
    assert tree["counts"] == [0, 1, 2, 3]
    assert tree["cells"] == [True, True, False, None]
    predicate, then_arm, else_arm = tree["operands"]
    assert predicate == {"text": "ok(id)", "cells": [True, True, True, False]}
    assert then_arm["arm"] == "then"
    assert then_arm["text"] == "new(id) or len(id) == 6"
    assert then_arm["cells"] == [True, True, True, False]
    assert then_arm["body"]["operator"] == "or"
    assert else_arm == {"arm": "else", "text": '"no"', "cells": [False, False, False, True], "body": None}


def test_1a6c3e03():
    """Example: if order.big and order.new: ... else: ..., taken once each
    way
    An if's tree is a ternary's, its arms plain, its predicate one leaf.
    So the if's value on every path is None."""
    source = (
        "def fee(order):\n"
        "    if order.big and order.new:\n"
        "        return 5\n"
        "    else:\n"
        "        return 7\n"
    )
    tree = _tree(source, [1, 1], "k.py:2:4")
    assert tree["operator"] == "if"
    assert tree["cells"] == [None, None]
    _, then_arm, else_arm = tree["operands"]
    assert then_arm["cells"] == [True, False]
    assert else_arm["cells"] == [False, True]

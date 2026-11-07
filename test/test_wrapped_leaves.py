import ast
import sys

from path_coverage import code_map, scopes, wrapped_leaves
from path_coverage.evaluations import Evaluations, Outcome

SOURCE = (
    "def f(a, b, c, p, q):\n"
    "    if a and (b or c):\n"
    "        x = p or q\n"
    "        return x\n"
)


def _rewritten(source):
    """(the rewritten tree, the Leaves it records into, the Source) of
    source, the file k.py."""
    found = code_map.Source(source, "k.py", scopes.whole(source))
    leaves = wrapped_leaves.Leaves(Evaluations())
    return wrapped_leaves.rewrite(ast.parse(source), found, leaves), leaves, found


def test_4a8c2e01():
    """Example: if a and (b or c): x = p or q
    The last operand of each and/or that is no and/or itself, c and q, is
    passed through a call that counts its outcome, keyed by the order it
    is met, inner and/ors first; b or c, the and's last operand, is an
    and/or, so it is not, and nothing else changes."""
    tree, leaves, found = _rewritten(SOURCE)
    assert ast.unparse(tree) == (
        "def f(a, b, c, p, q):\n"
        "    if a and (b or __path_coverage__(0, c)):\n"
        "        x = p or __path_coverage__(1, q)\n"
        "        return x"
    )
    inner, outer = found.shapes["k.py:2:9"], found.shapes["k.py:3:14"]
    assert leaves.actions == [
        ((Outcome(inner, 2, False),), (Outcome(inner, 2, True),)),
        ((Outcome(outer, 1, False),), (Outcome(outer, 1, True),)),
    ]


def test_4a8c2e02():
    """Example: q's call, given "" then "yes", from this frame
    Each returns the value it is given, unchanged, and logs its leaf's
    outcome by its truth, from the frame that called it."""
    _, leaves, found = _rewritten(SOURCE)
    outer = found.shapes["k.py:3:14"]
    assert [leaves.record(1, ""), leaves.record(1, "yes")] == ["", "yes"]
    here = id(sys._getframe())
    assert leaves.evaluations.log == [
        (here, (Outcome(outer, 1, False),)),
        (here, (Outcome(outer, 1, True),)),
    ]


def test_4a8c2e03():
    """Example: if a if b else True, then return (0 and a) or b
    A leaf whose form fixes its outcome, 0, and a leaf that is a
    conditional expression, the if's predicate, are wrapped too, as
    Python compiles a literal, or a literal arm, to no test; a literal
    that is no leaf, eg the arm True or the 1 returned, is not."""
    tree, leaves, found = _rewritten("def f(a, b):\n    if a if b else True:\n        return 1\n    return (0 and a) or b\n")
    assert ast.unparse(tree) == (
        "def f(a, b):\n"
        "    if __path_coverage__(0, a if b else True):\n"
        "        return 1\n"
        "    return __path_coverage__(1, 0) and __path_coverage__(2, a) or __path_coverage__(3, b)"
    )
    predicate, values = found.shapes["k.py:2:4"], found.shapes["k.py:4:21"]
    assert [actions[1] for actions in leaves.actions] == [
        (Outcome(predicate, 0, True),),
        (Outcome(values, 0, True),),
        (Outcome(values, 1, True),),
        (Outcome(values, 2, True),),
    ]

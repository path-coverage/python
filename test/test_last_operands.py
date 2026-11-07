import ast
import sys

from path_coverage import code_map, last_operands
from path_coverage.evaluations import Evaluations, Outcome

SOURCE = (
    "def f(a, b, c, p, q):\n"
    "    if a and (b or c):\n"
    "        x = p or q\n"
    "        return x\n"
)


def _rewritten(source):
    """(the rewritten tree, the Lasts it records into, the Source) of
    source, the file k.py."""
    found = code_map.Source(source, "k.py")
    lasts = last_operands.Lasts(Evaluations())
    return last_operands.rewrite(ast.parse(source), found, lasts), lasts, found


def test_4a8c2e01():
    """Example: if a and (b or c): x = p or q
    The last operand of each and/or that is no and/or itself, c and q, is
    passed through a call that counts its outcome, keyed by the order it
    is met, inner and/ors first; b or c, the and's last operand, is an
    and/or, so it is not, and nothing else changes."""
    tree, lasts, found = _rewritten(SOURCE)
    assert ast.unparse(tree) == (
        "def f(a, b, c, p, q):\n"
        "    if a and (b or __path_coverage__(0, c)):\n"
        "        x = p or __path_coverage__(1, q)\n"
        "        return x"
    )
    inner, outer = found.shapes["k.py:2:9"], found.shapes["k.py:3:14"]
    assert lasts.actions == [
        ((Outcome(inner, 2, False),), (Outcome(inner, 2, True),)),
        ((Outcome(outer, 1, False),), (Outcome(outer, 1, True),)),
    ]


def test_4a8c2e02():
    """Example: q's call, given "" then "yes", from this frame
    Each returns the value it is given, unchanged, and logs its leaf's
    outcome by its truth, from the frame that called it."""
    _, lasts, found = _rewritten(SOURCE)
    outer = found.shapes["k.py:3:14"]
    assert [lasts.record(1, ""), lasts.record(1, "yes")] == ["", "yes"]
    here = id(sys._getframe())
    assert lasts.evaluations.log == [
        (here, (Outcome(outer, 1, False),)),
        (here, (Outcome(outer, 1, True),)),
    ]

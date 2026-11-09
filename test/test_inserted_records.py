import ast
import sys
from types import SimpleNamespace

from path_coverage import inserted_records, method_machine, scopes, source_map
from path_coverage.evaluations import (
    Answer,
    Begin,
    End,
    Enter,
    Evaluations,
    Exhausted,
    Item,
    Matched,
    Opened,
    Outcome,
    Pass,
    Reach,
    Unmatched,
)
from path_coverage.inserted_records import BlockAnswer, BlockItems, Items, Leaf, Mark

SOURCE = (
    "def f(a, b, c, p, q):\n"
    "    if a and (b or c):\n"
    "        if (x := p or q):\n"
    "            return x\n"
)

FEE = (
    "def fee(user, orders):\n"
    '    """The fee for user\'s orders."""\n'
    "    for order in orders:\n"
    "        if user.member and order.paid:\n"
    "            return 5\n"
    "    return 10\n"
)


def _rewritten(source, mode="monitoring"):
    """(the rewritten tree, the Recorder it records into, the Source) of
    source, the file k.py, with the records mode inserts."""
    found = source_map.Source(source, "k.py", scopes.whole(source))
    recorder = inserted_records.Recorder(Evaluations())
    return inserted_records.rewrite(ast.parse(source), found, recorder, mode), recorder, found


def _here():
    """The key of the frame calling this, as an inserted call logs it."""
    frame = sys._getframe(1)
    return (id(frame), id(frame.f_code))


def test_4a8c2e01():
    """Example: if a and (b or c): if (x := p or q), in monitoring mode
    The last operand of each and/or that is no and/or itself, c and q, is
    passed through a call that counts its outcome, keyed by the order it
    is met, inner and/ors first; b or c, the and's last operand, is an
    and/or, so it is not, and nothing else changes. c's truth is all the
    if tests, so its call gives back its truth; q's value is x's too, so
    its call gives back q itself."""
    tree, recorder, found = _rewritten(SOURCE)
    assert ast.unparse(tree) == (
        "def f(a, b, c, p, q):\n"
        "    if a and (b or __path_coverage__(0, c)):\n"
        "        if (x := (p or __path_coverage__(1, q))):\n"
        "            return x"
    )
    inner, outer = found.shapes["k.py:2:9"], found.shapes["k.py:3:19"]
    assert recorder.records == [
        Leaf((Outcome(inner, 2, False),), (Outcome(inner, 2, True),), True),
        Leaf((Outcome(outer, 1, False),), (Outcome(outer, 1, True),), False),
    ]


def test_4a8c2e02():
    """Example: q's call, given "" then "yes", from this frame
    Each returns the value it is given, unchanged, and logs its leaf's
    outcome by its truth, from the frame that called it, by that frame's
    id and its code's."""
    _, recorder, found = _rewritten(SOURCE)
    outer = found.shapes["k.py:3:19"]
    assert [recorder.record(1, ""), recorder.record(1, "yes")] == ["", "yes"]
    assert recorder.evaluations.log == [
        (_here(), (Outcome(outer, 1, False),)),
        (_here(), (Outcome(outer, 1, True),)),
    ]


def test_4a8c2e03():
    """Example: if a if b else True, then return (0 and a) or b
    A leaf whose form fixes its outcome, 0, and a leaf that is a
    conditional expression, the if's predicate, are wrapped too, as
    Python compiles a literal, or a literal arm, to no test; a literal
    that is no leaf, eg the arm True or the 1 returned, is not."""
    tree, recorder, found = _rewritten("def f(a, b):\n    if a if b else True:\n        return 1\n    assert (0 and a) or b\n")
    assert ast.unparse(tree) == (
        "def f(a, b):\n"
        "    if __path_coverage__(0, a if b else True):\n"
        "        return 1\n"
        "    assert __path_coverage__(1, 0) and __path_coverage__(2, a) or __path_coverage__(3, b)"
    )
    predicate, values = found.shapes["k.py:2:4"], found.shapes["k.py:4:21"]
    assert [record.truthy for record in recorder.records] == [
        (Outcome(predicate, 0, True),),
        (Outcome(values, 0, True),),
        (Outcome(values, 1, True),),
        (Outcome(values, 2, True),),
    ]


class _Flag:
    """A truthy value counting each test of its truth."""

    def __init__(self):
        """Not yet tested."""
        self.tests = 0

    def __bool__(self):
        """True, counted."""
        self.tests += 1
        return True


def test_4a8c2e04():
    """Example: if a and (b or c), its c a value counting truth tests, run
    with the leaves wrapped
    A leaf whose truth is all that is tested is tested once, as plain
    Python tests it: its call tests it, and gives back the truth for the
    if to test."""
    tree, recorder, _ = _rewritten(SOURCE)
    namespace = {inserted_records.NAME: recorder.record}
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running the rewrite is the point
    c = _Flag()
    namespace["f"](True, False, c, 1, 2)
    assert c.tests == 1


def test_4a8c2e05():
    """Example: fee, a docstring, a for, an if of an and, two returns, in
    rewrite mode
    Every leaf is wrapped; the for's iterable is wrapped, so it can give
    each pass; and a record statement goes first in the body, after the
    docstring, giving the call's entry, and before each return, giving
    its reach. The and is the if's leaf, so its call is around theirs.
    Calls are keyed innermost first. Nothing else changes."""
    tree, recorder, found = _rewritten(FEE, "rewrite")
    assert ast.unparse(tree) == (
        "def fee(user, orders):\n"
        '    """The fee for user\'s orders."""\n'
        "    __path_coverage__(6)\n"
        "    for order in __path_coverage__(4, orders):\n"
        "        if __path_coverage__(2, __path_coverage__(0, user.member) and __path_coverage__(1, order.paid)):\n"
        "            __path_coverage__(3)\n"
        "            return 5\n"
        "    __path_coverage__(5)\n"
        "    return 10"
    )
    both, predicate = found.shapes["k.py:4:23"], found.shapes["k.py:4:8"]
    assert recorder.records == [
        Leaf((Outcome(both, 0, False),), (Outcome(both, 0, True),), True),
        Leaf((Outcome(both, 1, False),), (Outcome(both, 1, True),), True),
        Leaf((Outcome(predicate, 0, False),), (Outcome(predicate, 0, True),), True),
        Mark((Reach("k.py:5:12"),)),
        Items((Pass("k.py:3:4"),), (Exhausted("k.py:3:4"),)),
        Mark((Reach("k.py:6:4"),)),
        Mark((Enter("k.py:1:0"),)),
    ]


def test_4a8c2e06():
    """Example: fee's iterable's call given two orders, then iterated, from
    this frame
    It gives each item in turn, logging a pass before each and the loop's
    end once they are all given, by the key of the frame that called it,
    where the loop runs."""
    _, recorder, _ = _rewritten(FEE, "rewrite")
    assert list(recorder.record(4, ["o1", "o2"])) == ["o1", "o2"]
    passed, exhausted = (Pass("k.py:3:4"),), (Exhausted("k.py:3:4"),)
    assert recorder.evaluations.log == [(_here(), passed), (_here(), passed), (_here(), exhausted)]


SIZE = (
    "def size(n, big):\n"
    "    match n:\n"
    "        case 0:\n"
    "            return 'none'\n"
    "        case 1 if big:\n"
    "            return 'one'\n"
    "    return 'many'\n"
)


def test_4a8c2e08():
    """Example: size's match, a case with no guard, one with a guard, and
    no case matching anything, in rewrite mode
    The subject is wrapped, so the match is opened as it starts trying
    its cases; a record statement first in a case's body says its pattern
    matched; a guard's record says so before its outcome, as the guard
    runs only once its pattern matched; and a record statement after the
    match says no case was taken, when it is reached that way."""
    tree, recorder, found = _rewritten(SIZE, "rewrite")
    assert ast.unparse(tree) == (
        "def size(n, big):\n"
        "    __path_coverage__(7)\n"
        "    match __path_coverage__(4, n):\n"
        "        case 0:\n"
        "            __path_coverage__(1)\n"
        "            __path_coverage__(0)\n"
        "            return 'none'\n"
        "        case 1 if __path_coverage__(2, big):\n"
        "            __path_coverage__(3)\n"
        "            return 'one'\n"
        "    __path_coverage__(5)\n"
        "    __path_coverage__(6)\n"
        "    return 'many'"
    )
    shape = found.shapes["k.py:2:4"]
    matched = Matched(shape, 1, (0,))
    assert recorder.records[1:3] + recorder.records[4:6] == [
        Mark((Matched(shape, 0, ()),)),
        Leaf((matched, Outcome(shape, 2, False)), (matched, Outcome(shape, 2, True)), True),
        Mark((Opened(shape),)),
        Mark((Unmatched(shape, (0, 1)),)),
    ]


def test_4a8c2e09():
    """Example: the subject's record given 3, from this frame
    It gives back the subject unchanged, having opened the match."""
    _, recorder, found = _rewritten(SIZE, "rewrite")
    assert recorder.record(4, 3) == 3
    assert recorder.evaluations.log == [(_here(), (Opened(found.shapes["k.py:2:4"]),))]


LATE = "def late(orders):\n    return any(o.late for o in orders)\n"


def test_4a8c2e0a():
    """Example: return any(o.late for o in orders), in rewrite mode
    The call is wrapped, ending the block call once it gives its answer;
    its first iterable, run in the caller's frame, is wrapped so it begins
    the block call and gives each item; and its element is wrapped, giving
    each answer."""
    tree, recorder, found = _rewritten(LATE, "rewrite")
    assert ast.unparse(tree) == (
        "def late(orders):\n"
        "    __path_coverage__(3)\n"
        "    return __path_coverage__(2, any((__path_coverage__(1, o.late) for o in __path_coverage__(0, orders))))"
    )
    shape = found.shapes["k.py:2:11"]
    assert recorder.records[:3] == [BlockItems(shape), BlockAnswer(shape), Mark((End(shape),))]


def test_4a8c2e0b():
    """Example: late's records run from this frame as its rewrite runs
    them, on two orders, the first late: its generator is resumed from
    here once, as any(...) would, giving its answer, which stops it
    Every action is logged by the caller's frame: the begin and each item
    by the iterable's, made there; each answer by the frame that resumed
    the generator; and the end by the call's."""
    _, recorder, found = _rewritten(LATE, "rewrite")
    items = recorder.record(0, [SimpleNamespace(late=True), SimpleNamespace(late=False)])
    answers = (recorder.record(1, order.late) for order in items)
    assert recorder.record(2, next(answers)) is True
    shape = found.shapes["k.py:2:11"]
    assert recorder.evaluations.log == [
        (_here(), (Begin(shape),)),
        (_here(), (Item(shape),)),
        (_here(), (Answer(shape, True),)),
        (_here(), (End(shape),)),
    ]


def test_4a8c2e0c():
    """Example: paid, then first_paid, in rewrite mode, measuring only paid
    Code on no kept line gets no record: first_paid runs as plain Python,
    no entry, no reach and no pass of its loop recorded."""
    source = (
        "def paid(order):\n"
        "    return order.paid and not order.refunded\n"
        "\n"
        "def first_paid(orders):\n"
        "    for order in orders:\n"
        "        if paid(order):\n"
        "            return order\n"
        "    return None\n"
    )
    found = source_map.Source(source, "k.py", scopes.lines(source, "paid"))
    recorder = inserted_records.Recorder(Evaluations())
    tree = inserted_records.rewrite(ast.parse(source), found, recorder, "rewrite")
    assert ast.unparse(tree).split("\n\n")[1] == ast.unparse(ast.parse(source)).split("\n\n")[1]


def test_4a8c2e0d():
    """Example: a stub, ship, its body ..., and pending, which makes a
    generator expression for later and one for tuple(...), in rewrite mode
    An entry's record statement goes first in a body that starts with no
    docstring; a generator expression in no block call takes no block's
    records."""
    source = (
        "def ship(order):\n"
        "    ...\n"
        "\n"
        "def pending(orders):\n"
        "    later = (o for o in orders)\n"
        "    return tuple(o.id for o in later)\n"
    )
    tree, recorder, _ = _rewritten(source, "rewrite")
    assert ast.unparse(tree) == (
        "def ship(order):\n"
        "    __path_coverage__(0)\n"
        "    ...\n"
        "\n"
        "def pending(orders):\n"
        "    __path_coverage__(2)\n"
        "    later = (o for o in orders)\n"
        "    __path_coverage__(1)\n"
        "    return tuple((o.id for o in later))"
    )
    assert recorder.records == [Mark((Enter("k.py:1:0"),)), Mark((Reach("k.py:6:4"),)), Mark((Enter("k.py:4:0"),))]


def _raised_at(tree, recorder):
    """The line of fee's frame in the traceback of fee(None, [order]),
    compiled from tree, its records calling recorder: it raises, as a
    None user has no member."""
    namespace = {inserted_records.NAME: recorder.record}
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running the rewrite is the point
    try:
        namespace["fee"](None, [SimpleNamespace(paid=True)])
    except AttributeError as error:
        return error.__traceback__.tb_next.tb_lineno


def test_4a8c2e0e():
    """Example: fee, in rewrite mode, called with no user, so its if
    raises
    Each inserted node takes the location of the node it wraps or is
    placed by, so the traceback names the line plain Python names."""
    tree, recorder, _ = _rewritten(FEE, "rewrite")
    plain = ast.parse(FEE)
    assert _raised_at(tree, recorder) == _raised_at(plain, recorder) == 4


DRAIN = (
    "def drain(queue, limit):\n"
    "    taken = 0\n"
    "    while queue and taken < limit:\n"
    "        if queue.pop():\n"
    "            taken += 1\n"
    "    return taken\n"
)


def test_4a8c2e0f():
    """Example: drain, a while, in rewrite mode, run on a queue of two
    truthy items, then on an empty one
    A while's test is wrapped so each run of it starts a pass or ends the
    loop; each way a call takes is one the method machine lists as
    possible."""
    tree, recorder, _ = _rewritten(DRAIN, "rewrite")
    assert ast.unparse(tree) == (
        "def drain(queue, limit):\n"
        "    __path_coverage__(5)\n"
        "    taken = 0\n"
        "    while __path_coverage__(3, __path_coverage__(0, queue) and __path_coverage__(1, taken < limit)):\n"
        "        if __path_coverage__(2, queue.pop()):\n"
        "            taken += 1\n"
        "    __path_coverage__(4)\n"
        "    return taken"
    )
    namespace = {inserted_records.NAME: recorder.record}
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running the rewrite is the point
    evaluations = recorder.evaluations
    evaluations.loops.update(source_map.Source(DRAIN, "k.py", scopes.whole(DRAIN)).loops)
    evaluations.repeats.update(source_map.Source(DRAIN, "k.py", scopes.whole(DRAIN)).repeats)
    assert [namespace["drain"]([1, 2], 5), namespace["drain"]([], 5)] == [2, 0]
    evaluations.flush()
    evaluations.close()
    possible = method_machine.ways(DRAIN, "k.py")["k.py:1:0"]["possible"]
    taken = [witnessed for way in evaluations.ways["k.py:1:0"] for witnessed in method_machine.witnessed(way)]
    assert sorted(taken) == [
        (("k.py:3:16", (False, None)), ("k.py:3:4", ("0 items",)), ("k.py:6:4",)),
        (("k.py:3:16", (True, True)), ("k.py:3:4", ("1+ items",)), ("k.py:4:8", (True,)), ("k.py:6:4",)),
    ]
    assert set(taken) <= set(possible)


def test_4a8c2e07():
    """Example: fee's entry's record statement, called from this frame
    It logs the entry by this frame's key and gives back nothing."""
    _, recorder, _ = _rewritten(FEE, "rewrite")
    assert recorder.record(6) is None
    assert recorder.evaluations.log == [(_here(), (Enter("k.py:1:0"),))]


def test_4a8c2e10():
    """Example: assert (a or b) if c else d, in rewrite mode
    A leaf in a conditional expression's arm is tested as that expression
    is: the assert tests only its truth, so a's and b's calls give back
    their truth, as c's does, c being the expression's own test."""
    _, recorder, _ = _rewritten("def f(a, b, c, d):\n    assert (a or b) if c else d\n", "rewrite")
    leaves = [record for record in recorder.records if isinstance(record, Leaf)]
    assert [leaf.tested for leaf in leaves] == [True, True, True]

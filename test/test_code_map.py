import ast
import dataclasses
import dis

from path_coverage import code_map, last_operands
from path_coverage.evaluations import Evaluations, Shape


def _said(action):
    """action as a tuple of its type's name then its fields, a Shape by its
    decision's name, so a test can read it."""
    fields = [getattr(action, field.name) for field in dataclasses.fields(action)]
    return (type(action).__name__, *[field.name if isinstance(field, Shape) else field for field in fields])


def _module(source):
    """source, the file k.py, compiled as path_coverage compiles it, each
    and/or's last operand wrapped."""
    found = code_map.Source(source, "k.py")
    tree = last_operands.rewrite(ast.parse(source), found, last_operands.Lasts(Evaluations()))
    return compile(tree, "k.py", "exec")


def _tables(source):
    """{code name: Table} for each code object compiled from source, a file
    k.py, as code_map maps them."""
    module = _module(source)
    return {code.co_name: table for code, table in code_map.tables(module, code_map.Source(source, "k.py")).items()}


def _branches(table):
    """table's branches in offset order, each (its left actions, its right
    actions), each action as _said gives it."""
    return [
        ([_said(a) for a in table.left[offset]], [_said(a) for a in table.right[offset][1]])
        for offset in sorted(table.left)
    ]


def _marks(table):
    """table's instruction marks in offset order, each its actions as _said
    gives them."""
    return [[_said(a) for a in actions] for _, actions in sorted(table.marks.items())]


FEE = (
    "def fee(user, order):\n"
    "    total = 100\n"
    "    if user.member and order.paid:\n"
    "        total -= 5\n"
    "    if order.big:\n"
    "        total -= 10\n"
    "    return total\n"
)


def test_7b20d401():
    """Example: fee, an if of an and, an if, and a return
    Each branch gives its leaf's outcome, and the if's predicate's when it
    decides it; the and's last leaf, order.paid, is counted by the call
    around it, so its branch gives the if's predicate's alone. The return
    is reached, and fee's entry counted."""
    fee = _tables(FEE)["fee"]
    assert _branches(fee) == [
        ([("Outcome", "k.py:3:19", 0, True)], [("Outcome", "k.py:3:19", 0, False), ("Outcome", "k.py:3:4", 0, False)]),
        ([("Outcome", "k.py:3:4", 0, True)], [("Outcome", "k.py:3:4", 0, False)]),
        ([("Outcome", "k.py:5:4", 0, True)], [("Outcome", "k.py:5:4", 0, False)]),
    ]
    assert _marks(fee) == [[("Reach", "k.py:7:4")]]
    assert fee.entry == "k.py:1:0"


def test_7b20d402():
    """Example: fee's first branch
    A right branch counts only when it goes where its jump goes, as
    Python 3.14 also reports a right branch from a loop's end it did not
    take."""
    module = _module(FEE)
    fee = module.co_consts[0]
    tables = code_map.tables(module, code_map.Source(FEE, "k.py"))
    jump = next(ins for ins in dis.get_instructions(fee) if ins.opname.startswith("POP_JUMP"))
    assert tables[fee].right[jump.offset][0] == jump.argval


CHECK = (
    "def check(items, x, w, t):\n"
    "    if not items:\n"
    "        return 1\n"
    "    if x is None:\n"
    "        return 2\n"
    "    if 0 < t < 3 or (w := x):\n"
    "        return 3\n"
    "    t = (0 < t < 3) or w\n"
    "    return t\n"
)


def test_7b20d403():
    """Example: if not items, if x is None, if 0 < t < 3 or (w := x), and
    t = (0 < t < 3) or w
    A not flips the outcome its branch tests; is None is tested as its own
    jump. A chained comparison tested as a jump tells from its first jump
    only when false, from its last both ways; one whose value is tested
    later, as an and/or's operand whose value is used, tells nothing from
    its first jump, as its value's own test tells the outcome once."""
    check = _tables(CHECK)["check"]
    assert _branches(check) == [
        ([("Outcome", "k.py:2:4", 0, True)], [("Outcome", "k.py:2:4", 0, False)]),
        ([("Outcome", "k.py:4:4", 0, True)], [("Outcome", "k.py:4:4", 0, False)]),
        ([], [("Outcome", "k.py:6:17", 0, False)]),
        ([("Outcome", "k.py:6:17", 0, False)], [("Outcome", "k.py:6:17", 0, True), ("Outcome", "k.py:6:4", 0, True)]),
        ([("Outcome", "k.py:6:4", 0, True)], [("Outcome", "k.py:6:4", 0, False)]),
        ([("Outcome", "k.py:8:20", 0, False)], [("Outcome", "k.py:8:20", 0, True)]),
    ]


MEMBER = (
    "def member(member, vip):\n"
    "    ok = member and vip\n"
    "    either = member or vip\n"
    "    return 5 if either and not ok else 7\n"
)


def test_7b20d404():
    """Example: ok = member and vip, either = member or vip, and return 5
    if either and not ok else 7
    Each and/or's first leaf is tested by a branch; its last, vip and not
    ok, counted by the call around it, so the branch testing not ok gives
    the ternary's predicate's outcome alone."""
    member = _tables(MEMBER)["member"]
    assert _branches(member) == [
        ([("Outcome", "k.py:2:16", 0, True)], [("Outcome", "k.py:2:16", 0, False)]),
        ([("Outcome", "k.py:3:20", 0, False)], [("Outcome", "k.py:3:20", 0, True)]),
        ([("Outcome", "k.py:4:23", 0, True)], [("Outcome", "k.py:4:23", 0, False), ("Outcome", "k.py:4:13", 0, False)]),
        ([("Outcome", "k.py:4:13", 0, True)], [("Outcome", "k.py:4:13", 0, False)]),
    ]
    assert _marks(member) == []


def test_7b20d406():
    """Example: if True and a, then, after a return, if a and b
    Python tests True with no branch, so it is fixed true; a, the last
    operand, is counted by the call around it, so is never fixed. Code
    after a return is never compiled, so no branch tests its a either,
    but its form fixes no outcome, so it is not fixed."""
    text = "def f(a, b):\n    if True and a:\n        return 1\n    return 2\n    if a and b:\n        return 3\n"
    source = code_map.Source(text, "k.py")
    code_map.tables(_module(text), source)
    assert [source.shapes["k.py:2:12"].fixed, source.shapes["k.py:5:9"].fixed] == [{0: True}, {}]


SIZE = (
    "def size(order):\n"
    "    match len(order['items']):\n"
    "        case 0:\n"
    "            return 'empty'\n"
    "        case 1 | 2:\n"
    "            return 'small'\n"
    "        case count if count > 10:\n"
    "            return 'large'\n"
    "        case _:\n"
    "            return 'medium'\n"
)


def test_7b20d407():
    """Example: size's match, its last case matching anything
    Its first pattern's start opens an evaluation; reaching a case's
    guard, or its body when it has none, matches its pattern; its guard's
    branch gives the guard's outcome; no pattern's own branch gives
    anything."""
    size = _tables(SIZE)["size"]
    assert _branches(size) == [([("Outcome", "k.py:2:4", 3, True)], [("Outcome", "k.py:2:4", 3, False)])]
    assert _marks(size) == [
        [("Opened", "k.py:2:4")],
        [("Matched", "k.py:2:4", 0, ()), ("Reach", "k.py:4:12")],
        [("Matched", "k.py:2:4", 1, (0,)), ("Reach", "k.py:6:12")],
        [("Matched", "k.py:2:4", 2, (0, 1))],
        [("Reach", "k.py:8:12")],
        [("Matched", "k.py:2:4", 4, (0, 1, 2)), ("Reach", "k.py:10:12")],
    ]


KIND = (
    "def label(order):\n"
    "    match order.kind:\n"
    "        case 'gold' if order.big:\n"
    "            return 1\n"
    "        case 'silver':\n"
    "            return 2\n"
    "    return 3\n"
)


def test_7b20d408():
    """Example: label's match, no case of which matches anything
    Leaving the last case's pattern unmatched leaves the match with no
    case taken, there where the code after the match starts."""
    label = _tables(KIND)["label"]
    assert _marks(label) == [
        [("Opened", "k.py:2:4")],
        [("Matched", "k.py:2:4", 0, ())],
        [("Reach", "k.py:4:12")],
        [("Matched", "k.py:2:4", 2, (0,)), ("Reach", "k.py:6:12")],
        [("Unmatched", "k.py:2:4", (0, 2)), ("Reach", "k.py:7:4")],
    ]


LATE = "def any_late(orders):\n    return any(o.late for o in orders)\n"


def test_7b20d409():
    """Example: return any(o.late for o in orders)
    Python runs any of a generator in the caller: a check that any is the
    builtin begins it, its loop's each item and its end, and its test of
    each answer, which ends it when it decides."""
    tables = _tables(LATE)
    assert _branches(tables["any_late"]) == [
        ([("Begin", "k.py:2:11")], []),
        ([("Item", "k.py:2:11")], [("End", "k.py:2:11")]),
        ([("Answer", "k.py:2:11", False)], [("Answer", "k.py:2:11", True), ("End", "k.py:2:11")]),
    ]
    assert _branches(tables["<genexpr>"]) == []


def test_7b20d40b():
    """Example: return any(o.late for o in orders)
    While its instructions are monitored too, Python 3.14 reports a left
    branch from the NOT_TAKEN after its jump, and a loop's end from the
    POP_ITER after its END_FOR, so each is found there as well."""
    module = compile(LATE, "k.py", "exec")
    late = module.co_consts[0]
    table = code_map.tables(module, code_map.Source(LATE, "k.py"))[late]
    listed = list(dis.get_instructions(late))
    after = {ins.offset: listed[at + 1] for at, ins in enumerate(listed[:-1])}
    jumps = [offset for offset in sorted(table.left) if after[offset].opname == "NOT_TAKEN"]
    loop = next(ins for ins in listed if ins.opname == "FOR_ITER")
    assert table.left_aliases == {after[offset].offset: offset for offset in jumps}
    assert table.right_aliases == {after[loop.argval].offset: loop.offset}
    assert after[loop.argval].opname == "POP_ITER"
    assert len(jumps) == 2


SHAPES = (
    "def shapes(items, kind, t, x, w, a, b):\n"
    "    total = sum(1 for item in items if item)\n"
    "    pairs = [item and kind for item in items]\n"
    "    match kind:\n"
    "        case int():\n"
    "            total += 1\n"
    "    if (x if t else w):\n"
    "        total += 2\n"
    "    items[0], kind.size = total, 3\n"
    "    known = [item for item in items if item is not None]\n"
    "    first = items; pair = first and kind\n"
    "    return (w := a and b)\n"
)


def test_7b20d40c():
    """Example: a filter testing the item it was just given, an and over
    each item, a class pattern, an if of a ternary, a write to no name, a
    filter testing the item is not None, an and reading a name written
    just before it on its line, and an and in a returned walrus
    Python fuses a name's write and its next read into one instruction
    placed at the write, so the read is found by its name: in a
    comprehension, in what reads first after the write, its filters, then
    its element; else inside what the next instruction reads. A pattern's
    test of None gives nothing; a ternary's arm gives the if its
    outcome."""
    tables = _tables(SHAPES)
    assert _branches(tables["<genexpr>"]) == [([("Outcome", "k.py:2:36", 0, False)], [("Outcome", "k.py:2:36", 0, True)])]
    assert _branches(tables["shapes"]) == [
        ([("Outcome", "k.py:3:18", 0, True)], [("Outcome", "k.py:3:18", 0, False)]),
        ([("Outcome", "k.py:7:10", 0, True)], [("Outcome", "k.py:7:10", 0, False)]),
        ([("Outcome", "k.py:7:4", 0, True)], [("Outcome", "k.py:7:4", 0, False)]),
        ([("Outcome", "k.py:7:4", 0, True)], [("Outcome", "k.py:7:4", 0, False)]),
        ([("Outcome", "k.py:10:36", 0, False)], [("Outcome", "k.py:10:36", 0, True)]),
        ([("Outcome", "k.py:11:32", 0, True)], [("Outcome", "k.py:11:32", 0, False)]),
        ([("Outcome", "k.py:12:19", 0, True)], [("Outcome", "k.py:12:19", 0, False)]),
    ]


READY = (
    "def ready(kata, started):\n"
    "    match kata:\n"
    "        case _ if started:\n"
    "            return 'ready'\n"
    "    return 'waiting'\n"
)


def test_7b20d40d():
    """Example: match kata: case _ if started, then a return after it
    Its one case matches anything but for its guard, whose outcome ends
    every evaluation, so no mark is needed where no case is taken."""
    ready = _tables(READY)["ready"]
    assert _branches(ready) == [([("Outcome", "k.py:2:4", 1, True)], [("Outcome", "k.py:2:4", 1, False)])]
    assert _marks(ready) == [
        [("Opened", "k.py:2:4")],
        [("Matched", "k.py:2:4", 0, ())],
        [("Reach", "k.py:4:12")],
        [("Reach", "k.py:5:4")],
    ]


COPIED = (
    "def run(p0, p1, t):\n"
    "    match p0:\n"
    "        case True:\n"
    "            if p1: raise ValueError\n"
    "        case 2 | _:\n"
    "            raise ValueError\n"
    "    return t\n"
)


def test_7b20d40e():
    """Example: a match whose last case, 2 | _, only raises, after a case
    whose body is an if that raises
    Python copies the raise to each of the last pattern's alternatives, so
    the case is reached, and its raise run, at each copy; the first case's
    body is reached once, though its if's false branch lands back inside
    it."""
    marks = [action for actions in _marks(_tables(COPIED)["run"]) for action in actions]
    assert [marks.count(action) for action in (
        ("Matched", "k.py:2:4", 0, ()),
        ("Matched", "k.py:2:4", 1, (0,)),
        ("Reach", "k.py:4:19"),
        ("Reach", "k.py:6:12"),
        ("Reach", "k.py:7:4"),
    )] == [1, 2, 1, 2, 1]


def test_7b20d40a():
    """Example: a decorated function, f, and a lambda
    A function's entry is counted by its def's decision, decorators or
    not; a lambda's is not counted, as it has no card."""
    tables = _tables("import functools\n\n@functools.cache\ndef f(a):\n    return lambda: a\n")
    assert tables["f"].entry == "k.py:4:0"
    assert tables["<lambda>"].entry is None

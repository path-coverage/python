import dataclasses
import dis

from path_coverage import code_map
from path_coverage.evaluations import Shape


def _said(action):
    """action as a tuple of its type's name then its fields, a Shape by its
    decision's name, so a test can read it."""
    fields = [getattr(action, field.name) for field in dataclasses.fields(action)]
    return (type(action).__name__, *[field.name if isinstance(field, Shape) else field for field in fields])


def _tables(source):
    """{code name: Table} for each code object compiled from source, a file
    k.py, as code_map maps them."""
    module = compile(source, "k.py", "exec")
    return {code.co_name: table for code, table in code_map.tables(module, code_map.Source(source, "k.py")).items()}


def _branches(table):
    """table's branches in offset order, each (its left actions, its right
    actions), each action as _said gives it."""
    return [
        ([_said(a) for a in table.left[offset]], [_said(a) for a in table.right[offset][1]])
        for offset in sorted(table.left)
    ]


def _marks(table):
    """table's instruction marks in offset order, each (its actions as
    _said gives them, the name whose stored value it reads)."""
    return [([_said(a) for a in actions], name) for _, (actions, name) in sorted(table.marks.items())]


def _values(table):
    """table's returned or yielded values' actions in offset order, as
    _said gives them."""
    return [[_said(a) for a in actions] for _, actions in sorted(table.values.items())]


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
    Each branch gives its leaf's outcome; the and's last leaf, and its
    first when false, give the if's predicate's too. The return is
    reached, and fee's entry counted."""
    fee = _tables(FEE)["fee"]
    assert _branches(fee) == [
        ([("Outcome", "k.py:3:19", 0, True)], [("Outcome", "k.py:3:19", 0, False), ("Outcome", "k.py:3:4", 0, False)]),
        (
            [("Outcome", "k.py:3:19", 1, True), ("Outcome", "k.py:3:4", 0, True)],
            [("Outcome", "k.py:3:19", 1, False), ("Outcome", "k.py:3:4", 0, False)],
        ),
        ([("Outcome", "k.py:5:4", 0, True)], [("Outcome", "k.py:5:4", 0, False)]),
    ]
    assert _marks(fee) == [([("Reach", "k.py:7:4")], None)]
    assert _values(fee) == []
    assert fee.entry == "k.py:1:0"


def test_7b20d402():
    """Example: fee's first branch
    A right branch counts only when it goes where its jump goes, as
    Python 3.14 also reports a right branch from a loop's end it did not
    take."""
    module = compile(FEE, "k.py", "exec")
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
    "    if (w := x) or 0 < t < 3:\n"
    "        return 3\n"
    "    return 4\n"
)


def test_7b20d403():
    """Example: if not items, if x is None, and if (w := x) or 0 < t < 3
    A not flips the outcome its branch tests; is None is tested as its own
    jump; a walrus's outcome is its value's; a chained comparison's first
    jump tells only when it is false."""
    check = _tables(CHECK)["check"]
    assert _branches(check) == [
        ([("Outcome", "k.py:2:4", 0, True)], [("Outcome", "k.py:2:4", 0, False)]),
        ([("Outcome", "k.py:4:4", 0, True)], [("Outcome", "k.py:4:4", 0, False)]),
        ([("Outcome", "k.py:6:16", 0, False)], [("Outcome", "k.py:6:16", 0, True), ("Outcome", "k.py:6:4", 0, True)]),
        ([], [("Outcome", "k.py:6:16", 1, False), ("Outcome", "k.py:6:4", 0, False)]),
        (
            [("Outcome", "k.py:6:16", 1, True), ("Outcome", "k.py:6:4", 0, True)],
            [("Outcome", "k.py:6:16", 1, False), ("Outcome", "k.py:6:4", 0, False)],
        ),
    ]


MEMBER = (
    "def member(member, vip):\n"
    "    ok = member and vip\n"
    "    either = member or vip\n"
    "    return 5 if either and not ok else 7\n"
    "\n"
    "def is_member(user):\n"
    '    return user.get("member") and not user.get("banned")\n'
)


def test_7b20d404():
    """Example: ok = member and vip, either = member or vip, and return 5
    if either and not ok else 7
    vip is tested by no branch, so each write's value, read once it is
    written, tells its outcome; the ternary's leaves are all tested, so
    its returned value tells nothing."""
    member = _tables(MEMBER)["member"]
    assert _branches(member) == [
        ([("Outcome", "k.py:2:16", 0, True)], [("Outcome", "k.py:2:16", 0, False)]),
        ([("Outcome", "k.py:3:20", 0, False)], [("Outcome", "k.py:3:20", 0, True)]),
        ([("Outcome", "k.py:4:23", 0, True)], [("Outcome", "k.py:4:23", 0, False), ("Outcome", "k.py:4:13", 0, False)]),
        (
            [("Outcome", "k.py:4:23", 1, True), ("Outcome", "k.py:4:13", 0, True)],
            [("Outcome", "k.py:4:23", 1, False), ("Outcome", "k.py:4:13", 0, False)],
        ),
    ]
    assert _marks(member) == [([("Value", "k.py:2:16", False)], "ok"), ([("Value", "k.py:3:20", False)], "either")]
    assert _values(member) == []


def test_7b20d405():
    """Example: return user.get("member") and not user.get("banned")
    The not is tested by no branch, so the value returned tells its
    outcome."""
    is_member = _tables(MEMBER)["is_member"]
    assert _values(is_member) == [[("Value", "k.py:7:30", False)]]


def test_7b20d406():
    """Example: return a and True
    Python tests True with no branch, so it is fixed true, and the
    returned value is not needed."""
    source = code_map.Source("def f(a):\n    return a and True\n", "k.py")
    tables = code_map.tables(compile("def f(a):\n    return a and True\n", "k.py", "exec"), source)
    assert source.shapes["k.py:2:13"].fixed == {1: True}
    assert [_values(table) for table in tables.values()] == [[], []]


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
        ([("Opened", "k.py:2:4")], None),
        ([("Matched", "k.py:2:4", 0, ()), ("Reach", "k.py:4:12")], None),
        ([("Matched", "k.py:2:4", 1, (0,)), ("Reach", "k.py:6:12")], None),
        ([("Matched", "k.py:2:4", 2, (0, 1))], None),
        ([("Reach", "k.py:8:12")], None),
        ([("Matched", "k.py:2:4", 4, (0, 1, 2)), ("Reach", "k.py:10:12")], None),
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
        ([("Opened", "k.py:2:4")], None),
        ([("Matched", "k.py:2:4", 0, ())], None),
        ([("Reach", "k.py:4:12")], None),
        ([("Matched", "k.py:2:4", 2, (0,)), ("Reach", "k.py:6:12")], None),
        ([("Unmatched", "k.py:2:4", (0, 2)), ("Reach", "k.py:7:4")], None),
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
    just before it on its line, and a walrus returned
    Python fuses a name's write and its next read into one instruction
    placed at the write, so the read is found by its name: in a
    comprehension, in what reads first after the write, its filters, then
    its element; else inside what the next instruction reads. A pattern's
    test of None gives nothing; a ternary's arm gives the if its outcome;
    a returned walrus's value is its and's."""
    tables = _tables(SHAPES)
    assert _branches(tables["<genexpr>"]) == [([("Outcome", "k.py:2:36", 0, False)], [("Outcome", "k.py:2:36", 0, True)])]
    shapes = tables["shapes"]
    assert _branches(shapes) == [
        ([("Outcome", "k.py:3:18", 0, True)], [("Outcome", "k.py:3:18", 0, False)]),
        ([("Outcome", "k.py:7:10", 0, True)], [("Outcome", "k.py:7:10", 0, False)]),
        ([("Outcome", "k.py:7:4", 0, True)], [("Outcome", "k.py:7:4", 0, False)]),
        ([("Outcome", "k.py:7:4", 0, True)], [("Outcome", "k.py:7:4", 0, False)]),
        ([("Outcome", "k.py:10:36", 0, False)], [("Outcome", "k.py:10:36", 0, True)]),
        ([("Outcome", "k.py:11:32", 0, True)], [("Outcome", "k.py:11:32", 0, False)]),
        ([("Outcome", "k.py:12:19", 0, True)], [("Outcome", "k.py:12:19", 0, False)]),
    ]
    assert _values(shapes) == [[("Value", "k.py:12:19", False)]]


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
        ([("Opened", "k.py:2:4")], None),
        ([("Matched", "k.py:2:4", 0, ())], None),
        ([("Reach", "k.py:4:12")], None),
        ([("Reach", "k.py:5:4")], None),
    ]


def test_7b20d40a():
    """Example: a decorated function, f, and a lambda
    A function's entry is counted by its def's decision, decorators or
    not; a lambda's is not counted, as it has no card."""
    tables = _tables("import functools\n\n@functools.cache\ndef f(a):\n    return lambda: a\n")
    assert tables["f"].entry == "k.py:4:0"
    assert tables["<lambda>"].entry is None

from pathlib import Path

from path_coverage import manifest, method_statements


def _statements(source):
    """{def decision: its statements' rows} for source, as if it were k.py."""
    return method_statements.of(source, "k.py")


def _placed(source, decision="k.py:1:0"):
    """The (line, column, top) of each row of the def at decision in source."""
    return [(row.line, row.column, row.top) for row in _statements(source)[decision]]


SHIP = (
    "def ship(order):\n"
    '    """Packs order, sealing a fragile one."""\n'
    "    box = order.pack()\n"
    "    box.seal() if order.fragile else None\n"
    "    return box\n"
)


def test_b47e3a02():
    """Example: refuse, logging then raising, and first, returning
    A raise is a row, raise, as it leaves the function; the log call is
    none, its one path telling the reader nothing.
    A return is a row, return."""
    source = (
        "def refuse(order):\n"
        "    order.log('refused')\n"
        "    raise ValueError('refused')\n"
        "\n"
        "def first(items):\n"
        "    return items[0]\n"
    )
    tops = {decision: [row.top for row in rows] for decision, rows in _statements(source).items()}
    assert tops == {"k.py:1:0": ["raise"], "k.py:5:0": ["return"]}


def test_b47e3a03():
    """Example: a class whose __init__ is a docstring alone
    __init__ has no statement that runs, so no rows."""
    source = (
        "class Feed:\n"
        "    def __init__(self):\n"
        '        """Starts empty."""\n'
    )
    assert _statements(source) == {"k.py:2:4": []}


def test_b47e3a04():
    """Example: ship, an if statement then a return
    The if is a decision, so its row is named by its operator, if.
    It is at the if keyword, as decision mode names it.
    Its then's statement, a call, is no row."""
    source = (
        "def ship(order):\n"
        "    if order.paid:\n"
        "        order.pack()\n"
        "    return order\n"
    )
    assert _placed(source) == [(2, 4, "if"), (4, 4, "return")]


def test_b47e3a05():
    """Example: label, writing a conditional expression's value
    A write is looked through, so its row is the ternary's.
    It is at the ternary's if, where decision mode names it."""
    source = (
        "def label(items):\n"
        "    text = 'some' if items else 'none'\n"
        "    return text\n"
    )
    assert _placed(source) == [(2, 18, "ternary"), (3, 4, "return")]


def test_b47e3a06():
    """Example: discount, adding two ternaries' values
    + imposes no flow, so it is looked through, as is the write.
    Each ternary is a row, in the order they run."""
    source = (
        "def discount(big, member):\n"
        "    total = (10 if big else 0) + (5 if member else 0)\n"
        "    return total\n"
    )
    assert _placed(source) == [(2, 16, "ternary"), (2, 36, "ternary"), (3, 4, "return")]


def test_b47e3a07():
    """Example: price, returning 0 if free, else its cost
    A return is looked through, so its row is the ternary's."""
    source = (
        "def price(item):\n"
        "    return 0 if item.free else item.cost\n"
    )
    assert _placed(source) == [(2, 13, "ternary")]


def test_b47e3a08():
    """Example: ship, writing an and, an if, then a return
    A decision's row has as many paths as decision mode gives it.
    An and of two operands whose value is written, not tested, has 2, as
    its last operand's truth decides nothing; an if 2.
    A return has 1."""
    source = (
        "def ship(order):\n"
        "    ready = order.paid and order.packed\n"
        "    if ready:\n"
        "        order.send_off()\n"
        "    return order\n"
    )
    rows = _statements(source)["k.py:1:0"]
    assert [(row.top, row.paths) for row in rows] == [("and", 2), ("if", 2), ("return", 1)]


def test_b47e3a09():
    """Example: fee, a write, four ifs, then a return
    Its rows are the four ifs and the return.
    Its size is the sum of its rows' paths, 2+2+2+2+1 = 9.
    Its complexity is their product, 2*2*2*2*1 = 16.
    Each path of one row goes on to each of the next."""
    source = (
        "def fee(user, order):\n"
        "    total = order.total\n"
        "    if user.member:\n"
        "        total -= 5\n"
        "    if order.big:\n"
        "        total -= 10\n"
        "    if order.express:\n"
        "        total += 3\n"
        "    if order.gift:\n"
        "        total += 1\n"
        "    return total\n"
    )
    rows = _statements(source)["k.py:1:0"]
    assert [method_statements.size(rows), method_statements.complexity(rows)] == [9, 16]


def test_b47e3a10():
    """Example: ship, an if then a return, its then taken twice
    A decision's row names its decision.
    Its taken is how many of the decision's paths were taken: 1 of 2.
    The return names no decision.
    Its taken is None, not known, without reaches."""
    source = (
        "def ship(order):\n"
        "    if order.paid:\n"
        "        order.pack()\n"
        "    return order\n"
    )
    rows = _statements(source)["k.py:1:0"]
    paths = {"k.py:2:4": [{"path": [True], "count": 2}, {"path": [False], "count": 0}]}
    assert [row.decision for row in rows] == ["k.py:2:4", None]
    assert method_statements.taken(rows, paths) == [1, None]


def test_b47e3a11():
    """Example: labels, a comprehension, and tally, a for loop
    A comprehension's element runs once for each item.
    The ternary in it is a row, though the write holding it is none.
    A for loop's body runs once for each item too.
    So tally's for is no row, but each decision in its body is one."""
    source = (
        "def labels(items):\n"
        "    names = ['sale' if i.sale else 'full' for i in items]\n"
        "    return names\n"
        "\n"
        "def tally(items):\n"
        "    for item in items:\n"
        "        if item.sale:\n"
        "            item.count()\n"
    )
    assert _placed(source) == [(2, 20, "ternary"), (3, 4, "return")]
    assert _placed(source, "k.py:5:0") == [(7, 8, "if")]


def test_b47e3a12():
    """Example: load, reading a file in a try, rescuing a missing one
    The try is no row, nor is its write, but a decision in any of its parts
    is one: its handler's too, as a raise runs them."""
    source = (
        "def load(path, fallback):\n"
        "    try:\n"
        "        text = read(path)\n"
        "    except OSError:\n"
        "        text = fallback if fallback else ''\n"
        "    return text\n"
    )
    assert _placed(source) == [(5, 24, "ternary"), (6, 4, "return")]


def test_b47e3a14():
    """Example: a class with __init__ and an async ship
    Each def's name, by its decision, for its card's title."""
    source = (
        "class Shop:\n"
        "    def __init__(self):\n"
        "        self.orders = []\n"
        "\n"
        "    async def ship(self, order):\n"
        "        await order.pack()\n"
    )
    assert method_statements.names(source, "k.py") == {
        "k.py:2:4": "__init__",
        "k.py:5:4": "ship",
    }


def test_b47e3a15():
    """Example: ship, a write, a ternary, then a return
    ship's entry is reached, named by its def's decision, so its calls are
    counted. Each row that is no decision, the return, is reached where its
    statement starts. The write is no row, so not reached; the ternary is
    a decision, its paths already counted."""
    assert method_statements.reaches(SHIP, "k.py") == ["k.py:1:0", "k.py:5:4"]


def test_b47e3a16():
    """Example: outer, defining inner, then returning it
    A nested def is no row of outer's, nor is it looked through, as its
    body runs when it is called.
    inner has its own card, its rows its own."""
    source = (
        "def outer(rate):\n"
        "    def inner(x):\n"
        "        return x * rate if rate else x\n"
        "    return inner\n"
    )
    assert _placed(source) == [(4, 4, "return")]
    assert _placed(source, "k.py:2:4") == [(3, 24, "ternary")]


def test_b47e3a17():
    """Example: ship, a write, a ternary, then a return, the return
    reached twice, the ternary's then taken
    Each row is named by where it is.
    A row that is no decision is taken when its statement was reached.
    So the ternary's taken is 1, of 2, and the return's 1; never reached,
    the return's is 0."""
    rows = _statements(SHIP)["k.py:1:0"]
    paths = {"k.py:4:15": [{"path": [True], "count": 2}, {"path": [False], "count": 0}]}
    assert [row.name for row in rows] == ["k.py:4:15", "k.py:5:4"]
    taken = [method_statements.taken(rows, paths, reached) for reached in ({"k.py:5:4": 2}, {})]
    assert taken == [[1, 1], [1, 0]]


def test_b47e3a18():
    """Example: ship, the ternary's then taken, the return reached
    Its card's total is [taken, size]: [2, 3].
    Without reaches, the return is not known.
    It counts as not taken: [1, 3], never more than it ran."""
    paths = {"k.py:4:15": [{"path": [True], "count": 2}, {"path": [False], "count": 0}]}
    totals = [
        method_statements.totals(SHIP, "k.py", paths, reached)
        for reached in ({"k.py:5:4": 1}, None)
    ]
    assert totals == [{"k.py:1:0": [2, 3]}, {"k.py:1:0": [1, 3]}]


def test_b47e3a20():
    """Example: a class with __init__, on two lines, and ship, on four
    Each def's last line, by its decision, where its card ends."""
    source = (
        "class Shop:\n"
        "    def __init__(self):\n"
        "        self.orders = []\n"
        "\n"
        "    def ship(self, order):\n"
        "        order.pack()\n"
        "        self.orders.append(order)\n"
        "        return order\n"
    )
    assert method_statements.lasts(source, "k.py") == {"k.py:2:4": 3, "k.py:5:4": 8}


def test_b47e3a21():
    """Example: drain, a while, a with, a match, an any, a class and
    a lambda
    A while's test is looked through, so its row is the and.
    A with, a class and a pass are no rows, but each decision in a body is one.
    A match is a decision, its row at its keyword.
    Each body, and each case's, gives rows after its statement.
    A lambda's body gives a row for each decision in it, after its return."""
    source = (
        "def drain(queue, path):\n"
        "    while queue.size and queue.open:\n"
        "        queue.pop() if queue.size else None\n"
        "    with open(path) as file:\n"
        "        late = any(line.late for line in file)\n"
        "    match late:\n"
        "        case True:\n"
        "            pass\n"
        "    class Box:\n"
        "        size = 1 if late else 2\n"
        "    return lambda: 1 if late else 2\n"
    )
    assert _placed(source) == [
        (2, 21, "and"),
        (3, 20, "ternary"),
        (5, 15, "any"),
        (6, 4, "match"),
        (10, 17, "ternary"),
        (11, 4, "return"),
        (11, 21, "ternary"),
    ]


def test_b47e3a23():
    """Example: fee, an if, an elif and an else, then a return
    An elif is a row of the else before it, its top elif. The if's else is
    that elif, so the if is labelled if; the elif has an else of its own,
    so it is labelled elif/else. The writes in their arms are no rows."""
    source = (
        "def fee(user):\n"
        "    if user.member:\n"
        "        rate = 5\n"
        "    elif user.trial:\n"
        "        rate = 2\n"
        "    else:\n"
        "        rate = 9\n"
        "    return rate\n"
    )
    assert _placed(source) == [(2, 4, "if"), (4, 4, "elif/else"), (8, 4, "return")]


def test_b47e3a24():
    """Example: size, a match of two cases
    Each case's statements are rows after the match, case by case."""
    source = (
        "def size(box):\n"
        "    match box.kind:\n"
        '        case "big":\n'
        "            return 3\n"
        "        case _:\n"
        "            return 1 if box.full else 0\n"
    )
    assert _placed(source) == [(2, 4, "match"), (4, 12, "return"), (6, 21, "ternary")]


def test_b47e3a25():
    """Example: ready, an and holding a ternary, and ship, an if whose
    predicate holds one
    A decision inside a decision's leaf is a decision of its own.
    So it is a row too. Rows on one line are in the order they are named:
    the ternary, at its if, before the and, at its keyword."""
    source = (
        "def ready(order):\n"
        "    return valid(order.code if order.code else None) and order.paid\n"
        "\n"
        "def ship(order):\n"
        "    if send(order.fast if order.paid else None):\n"
        "        order.done()\n"
    )
    assert _placed(source) == [(2, 28, "ternary"), (2, 53, "and")]
    assert _placed(source, "k.py:4:0") == [(5, 4, "if"), (5, 23, "ternary")]


def test_b47e3a26():
    """Example: ship, an if returning a paid order packed, then a return
    A row in an arm that is no decision, the first return, is reached where it
    starts too, after ship's entry."""
    source = (
        "def ship(order):\n"
        "    if order.paid:\n"
        "        return order.pack()\n"
        "    return order\n"
    )
    assert method_statements.reaches(source, "k.py") == ["k.py:1:0", "k.py:3:8", "k.py:4:4"]


SHOP = (
    "RATE = 2 if FAST else 1\n"
    "def ship(order):\n"
    "    assert order.paid and order.packed\n"
    "class Shop:\n"
    "    SIZE = 3 if BIG else 1\n"
)


def test_b47e3a27():
    """Example: a ternary at the top, ship, and one in class Shop
    A decision outside every function is on no function's card.
    Each is a top row, for the card of its own lines, in order.
    ship's and is on its card, so it is no top row."""
    rows = method_statements.top_rows(SHOP, "k.py")
    assert [(row.line, row.column, row.top, row.paths) for row in rows] == [
        (1, 9, "ternary", 2),
        (5, 13, "ternary", 2),
    ]
    assert [row.decision for row in rows] == ["k.py:1:9", "k.py:5:13"]


def _then_taken(count):
    """A ternary's paths, its then taken count times, its else never."""
    return [{"path": [True], "count": count}, {"path": [False], "count": 0}]


SHOP_PATHS = {
    "k.py:1:9": _then_taken(1),
    "k.py:3:22": [
        {"path": [True, True], "count": 1},
        {"path": [True, False], "count": 0},
        {"path": [False, None], "count": 0},
    ],
    "k.py:5:13": _then_taken(0),
}


def test_b47e3a28():
    """Example: SHOP, RATE's then taken, SIZE's never, ship's and once
    The top level's total is [taken, possible] of its top rows' paths.
    ship's and is on its own card, so it is not in it: [1, 4]."""
    assert method_statements.top_level(SHOP, "k.py", SHOP_PATHS) == [1, 4]


def test_b47e3a29():
    """Example: SHOP's cards
    Each file's top level has a total too, named for line 0.
    No function is on line 0, so every decision is in some total."""
    files = {"k.py": (SHOP, manifest.decisions(SHOP, "k.py"))}
    cards = method_statements.cards(files, SHOP_PATHS, None)
    assert cards == {"k.py:2:0": [1, 3], "k.py:0:0": [1, 4]}


def test_b47e3a30():
    """Example: every file of this repo's src and test
    Each decision is a row of a function's card, or a top row."""
    root = Path(__file__).parent.parent
    missed = {}
    for file in sorted([*root.glob("src/**/*.py"), *root.glob("test/**/*.py")]):
        source = file.read_text()
        path = file.relative_to(root).as_posix()
        carded = {row.decision for rows in method_statements.of(source, path).values() for row in rows}
        tops = {row.decision for row in method_statements.top_rows(source, path)}
        missed[path] = sorted(set(manifest.decisions(source, path)) - carded - tops)
    assert missed == {path: [] for path in missed}


def test_b47e3a33():
    """Example: note, whose first statement is a call holding a ternary,
    log(1 if a else 2)
    A first statement that is an expression but no string is no
    docstring, so it runs, and its ternary is a row."""
    source = "def note(a):\n    log(1 if a else 2)\n"
    assert _placed(source) == [(2, 10, "ternary")]


def test_b47e3a31():
    """Example: ship, a write, a for over its items, a call, an if with an
    else, a return, and a raise in the else
    A row that is no decision and has one path tells the reader nothing, so a
    card has no row for it: the write, the for and the call are dropped,
    though the for's body still gives rows. A return or a raise stays, as it
    cuts a path short. An if with an else is labelled if/else."""
    source = (
        "def ship(order):\n"
        "    box = order.pack()\n"
        "    for item in order.items:\n"
        "        item.check()\n"
        "        if item.big:\n"
        "            return box\n"
        "        else:\n"
        "            raise ValueError(item)\n"
    )
    assert _placed(source) == [(5, 8, "if/else"), (6, 12, "return"), (8, 12, "raise")]


def test_b47e3a32():
    """Example: ship, a write then an if returning early, and RATE outside
    every function
    Each row that is no decision, a return here, is reached where it starts,
    and so is each function's entry, named by its def's decision, where its
    body starts, so its calls can be counted."""
    source = (
        "RATE = 2\n"
        "def ship(order):\n"
        '    """Ships order."""\n'
        "    box = order.pack()\n"
        "    if box.empty:\n"
        "        return None\n"
        "    return box\n"
    )
    assert method_statements.reaches(source, "k.py") == ["k.py:2:0", "k.py:6:8", "k.py:7:4"]

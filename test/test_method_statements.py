from pathlib import Path

from path_coverage import manifest, method_statements


def _statements(source):
    """{def site: its statements' rows} for source, as if it were k.py."""
    return method_statements.of(source, "k.py")


def _placed(source, site="k.py:1:0"):
    """The (line, column, top) of each row of the def at site in source."""
    return [(row.line, row.column, row.top) for row in _statements(source)[site]]


SHIP = (
    "def ship(order):\n"
    '    """Packs order, sealing a fragile one."""\n'
    "    box = order.pack()\n"
    "    box.seal() if order.fragile else None\n"
    "    return box\n"
)


def test_b47e3a01():
    """Example: total, a write, a call and a value
    Each top-level statement is a row: its line, column and top.
    A write is =, a call is (), and a name read is a value.
    The docstring is no row, as Python runs no code for it."""
    source = (
        "def total(order):\n"
        '    """The order\'s subtotal, its first item saved."""\n'
        "    amount = order.subtotal\n"
        "    order.items[0].save()\n"
        "    amount\n"
    )
    assert _placed(source) == [(3, 4, "="), (4, 4, "()"), (5, 4, "value")]


def test_b47e3a02():
    """Example: refuse, logging then raising, and first, returning
    A raise is raise, as it leaves the function.
    A return is return."""
    source = (
        "def refuse(order):\n"
        "    order.log('refused')\n"
        "    raise ValueError('refused')\n"
        "\n"
        "def first(items):\n"
        "    return items[0]\n"
    )
    tops = {site: [row.top for row in rows] for site, rows in _statements(source).items()}
    assert tops == {"k.py:1:0": ["()", "raise"], "k.py:5:0": ["return"]}


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
    The if is a site, so its row is named by its operator, if.
    It is at the if keyword, as decision mode names it.
    Its then's statement is a row after it."""
    source = (
        "def ship(order):\n"
        "    if order.paid:\n"
        "        order.pack()\n"
        "    return order\n"
    )
    assert _placed(source) == [(2, 4, "if"), (3, 8, "()"), (4, 4, "return")]


def test_b47e3a05():
    """Example: label, writing a conditional expression's value
    A write is looked through, so its row is the ternary's.
    It is at the ternary's column, as decision mode names it."""
    source = (
        "def label(items):\n"
        "    text = 'some' if items else 'none'\n"
        "    return text\n"
    )
    assert _placed(source) == [(2, 11, "ternary"), (3, 4, "return")]


def test_b47e3a06():
    """Example: discount, adding two ternaries' values
    + imposes no flow, so it is looked through, as is the write.
    Each ternary is a row, in the order they run."""
    source = (
        "def discount(big, member):\n"
        "    total = (10 if big else 0) + (5 if member else 0)\n"
        "    return total\n"
    )
    assert _placed(source) == [(2, 13, "ternary"), (2, 34, "ternary"), (3, 4, "return")]


def test_b47e3a07():
    """Example: price, returning 0 if free, else its cost
    A return is looked through, so its row is the ternary's."""
    source = (
        "def price(item):\n"
        "    return 0 if item.free else item.cost\n"
    )
    assert _placed(source) == [(2, 11, "ternary")]


def test_b47e3a08():
    """Example: ship, writing an and, an if, then a return
    A site's row has as many paths as decision mode gives it.
    An and of two operands has 3, an if 2.
    Any other row has 1."""
    source = (
        "def ship(order):\n"
        "    ready = order.paid and order.packed\n"
        "    if ready:\n"
        "        order.send_off()\n"
        "    return order\n"
    )
    rows = _statements(source)["k.py:1:0"]
    assert [(row.top, row.paths) for row in rows] == [("and", 3), ("if", 2), ("()", 1), ("return", 1)]


def test_b47e3a09():
    """Example: fee, a write, four ifs, then a return
    Each if's then is a row of 1 path after it.
    Its size is the sum of its rows' paths, 1+2+1+2+1+2+1+2+1+1 = 14.
    Its complexity is their product, 1*2*1*2*1*2*1*2*1*1 = 16.
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
    assert [method_statements.size(rows), method_statements.complexity(rows)] == [14, 16]


def test_b47e3a10():
    """Example: ship, an if then a return, its then taken twice
    A site's row names its site.
    Its taken is how many of the site's paths were taken: 1 of 2.
    Any other row names no site.
    Its taken is None, not known, without reaches."""
    source = (
        "def ship(order):\n"
        "    if order.paid:\n"
        "        order.pack()\n"
        "    return order\n"
    )
    rows = _statements(source)["k.py:1:0"]
    paths = {"k.py:2:4": [{"path": [True], "count": 2}, {"path": [False], "count": 0}]}
    assert [row.site for row in rows] == ["k.py:2:4", None, None]
    assert method_statements.taken(rows, paths) == [1, None, None]


def test_b47e3a11():
    """Example: labels, a comprehension, and tally, a for loop
    A comprehension's element runs once for each item.
    So labels' write is a row, and the ternary in it is a row after it.
    A for loop's body runs once for each item too.
    So tally's for is a row, then a row for each statement of its body."""
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
    assert _placed(source) == [(2, 4, "="), (2, 13, "ternary"), (3, 4, "return")]
    assert _placed(source, "k.py:5:0") == [(6, 4, "for"), (7, 8, "if"), (8, 12, "()")]


def test_b47e3a12():
    """Example: load, reading a file in a try, rescuing a missing one
    The try is a row, then a row for each statement of its parts.
    Its handler's are rows too, as a raise runs them."""
    source = (
        "def load(path, fallback):\n"
        "    try:\n"
        "        text = read(path)\n"
        "    except OSError:\n"
        "        text = fallback if fallback else ''\n"
        "    return text\n"
    )
    assert _placed(source) == [(2, 4, "try"), (3, 8, "="), (5, 15, "ternary"), (6, 4, "return")]


def test_b47e3a13():
    """Example: record, writing an index, an attribute, an op-write
    and an annotated name
    Each write is =."""
    source = (
        "def record(event, index):\n"
        "    event['index'] = index\n"
        "    event.time = now()\n"
        "    index += 1\n"
        "    count: int = index\n"
    )
    rows = _statements(source)["k.py:1:0"]
    assert [(row.top, row.paths) for row in rows] == [("=", 1)] * 4


def test_b47e3a14():
    """Example: a class with __init__ and an async ship
    Each def's name, by its site, for its card's title."""
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
    Each row that is no site is reached where its statement starts.
    It is named by that place, so a call there can count its runs.
    The ternary is a site, its paths already counted."""
    assert method_statements.reaches(SHIP, "k.py") == ["k.py:3:4", "k.py:5:4"]


def test_b47e3a16():
    """Example: outer, defining inner, then returning it
    A nested def is a row of its own: def, with 1 path.
    It is not looked through, as its body runs when it is called.
    inner has its own rows."""
    source = (
        "def outer(rate):\n"
        "    def inner(x):\n"
        "        return x * rate if rate else x\n"
        "    return inner\n"
    )
    assert _placed(source) == [(2, 4, "def"), (4, 4, "return")]
    assert _placed(source, "k.py:2:4") == [(3, 15, "ternary")]


def test_b47e3a17():
    """Example: ship, a write, a ternary, then a return, the write
    reached twice, the return never, the ternary's then taken
    Each row is named by where it is.
    A row that is no site is taken when its statement was reached.
    So the write's taken is 1 and the return's 0."""
    rows = _statements(SHIP)["k.py:1:0"]
    paths = {"k.py:4:4": [{"path": [True], "count": 2}, {"path": [False], "count": 0}]}
    assert [row.name for row in rows] == ["k.py:3:4", "k.py:4:4", "k.py:5:4"]
    reached = {"k.py:3:4": 2}
    assert method_statements.taken(rows, paths, reached) == [1, 1, 0]


def test_b47e3a18():
    """Example: ship, the write reached, the ternary's then taken,
    the return never reached
    Its card's total is [taken, size]: [2, 4].
    Without reaches, the write and return are not known.
    They count as not taken: [1, 4], never more than it ran."""
    paths = {"k.py:4:4": [{"path": [True], "count": 2}, {"path": [False], "count": 0}]}
    totals = [
        method_statements.totals(SHIP, "k.py", paths, reached)
        for reached in ({"k.py:3:4": 1}, None)
    ]
    assert totals == [{"k.py:1:0": [2, 4]}, {"k.py:1:0": [1, 4]}]


def test_b47e3a19():
    """Example: ship, logging with a call of a plain name, then a
    pass
    A call of a name is a call: ().
    Any statement with no top of its own, eg pass, is a value."""
    source = (
        "def ship(order):\n"
        "    log('shipped')\n"
        "    pass\n"
    )
    assert [row.top for row in _statements(source)["k.py:1:0"]] == ["()", "value"]


def test_b47e3a20():
    """Example: a class with __init__, on two lines, and ship, on four
    Each def's last line, by its site, where its card ends."""
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
    A with's items are looked through; it holds none, so it is with.
    A match is a site, its row at its keyword.
    Each body, and each case's, gives rows after its statement.
    A lambda's body gives a row for each site in it."""
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
        (2, 10, "and"),
        (3, 8, "ternary"),
        (4, 4, "with"),
        (5, 15, "any"),
        (6, 4, "match"),
        (8, 12, "value"),
        (9, 4, "class"),
        (10, 15, "ternary"),
        (11, 4, "return"),
        (11, 19, "ternary"),
    ]


def test_b47e3a22():
    """Example: a stub whose body is ... alone
    A constant other than a string is no docstring.
    So it is a row of its own, a value."""
    source = (
        "def stub(order):\n"
        "    ...\n"
    )
    assert _placed(source) == [(2, 4, "value")]


def test_b47e3a23():
    """Example: fee, an if, an elif and an else, then a return
    Each arm's statements are rows after its if, in the order written.
    An elif is a row of the else before it, its top elif."""
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
    assert _placed(source) == [
        (2, 4, "if"),
        (3, 8, "="),
        (4, 4, "elif"),
        (5, 8, "="),
        (7, 8, "="),
        (8, 4, "return"),
    ]


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
    assert _placed(source) == [(2, 4, "match"), (4, 12, "return"), (6, 19, "ternary")]


def test_b47e3a25():
    """Example: ready, an and holding a ternary, and ship, an if whose
    predicate holds one
    A site inside a site's leaf is a site of its own.
    So it is a row too, after the site holding it."""
    source = (
        "def ready(order):\n"
        "    return valid(order.code if order.code else None) and order.paid\n"
        "\n"
        "def ship(order):\n"
        "    if send(order.fast if order.paid else None):\n"
        "        order.done()\n"
    )
    assert _placed(source) == [(2, 11, "and"), (2, 17, "ternary")]
    assert _placed(source, "k.py:4:0") == [(5, 4, "if"), (5, 12, "ternary"), (6, 8, "()")]


def test_b47e3a26():
    """Example: ship, an if packing a paid order, then a return
    A row in an arm that is no site is reached where it starts too."""
    source = (
        "def ship(order):\n"
        "    if order.paid:\n"
        "        order.pack()\n"
        "    return order\n"
    )
    assert method_statements.reaches(source, "k.py") == ["k.py:3:8", "k.py:4:4"]


SHOP = (
    "RATE = 2 if FAST else 1\n"
    "def ship(order):\n"
    "    return order.paid and order.packed\n"
    "class Shop:\n"
    "    SIZE = 3 if BIG else 1\n"
)


def test_b47e3a27():
    """Example: a ternary at the top, ship, and one in class Shop
    A site outside every function is on no function's card.
    Each is a top row, for the card of its own lines, in order.
    ship's and is on its card, so it is no top row."""
    rows = method_statements.top_rows(SHOP, "k.py")
    assert [(row.line, row.column, row.top, row.paths) for row in rows] == [
        (1, 7, "ternary", 2),
        (5, 11, "ternary", 2),
    ]
    assert [row.site for row in rows] == ["k.py:1:7", "k.py:5:11"]


def _then_taken(count):
    """A ternary's paths, its then taken count times, its else never."""
    return [{"path": [True], "count": count}, {"path": [False], "count": 0}]


SHOP_PATHS = {
    "k.py:1:7": _then_taken(1),
    "k.py:3:11": [
        {"path": [True, True], "count": 1},
        {"path": [True, False], "count": 0},
        {"path": [False, None], "count": 0},
    ],
    "k.py:5:11": _then_taken(0),
}


def test_b47e3a28():
    """Example: SHOP, RATE's then taken, SIZE's never, ship's and once
    The top level's total is [taken, possible] of its top rows' paths.
    ship's and is on its own card, so it is not in it: [1, 4]."""
    assert method_statements.top_level(SHOP, "k.py", SHOP_PATHS) == [1, 4]


def test_b47e3a29():
    """Example: SHOP's cards
    Each file's top level has a total too, named for line 0.
    No function is on line 0, so every site is in some total."""
    files = {"k.py": (SHOP, manifest.sites(SHOP, "k.py"))}
    cards = method_statements.cards(files, SHOP_PATHS, None)
    assert cards == {"k.py:2:0": [1, 3], "k.py:0:0": [1, 4]}


def test_b47e3a30():
    """Example: every file of this repo's src and test
    Each site is a row of a function's card, or a top row."""
    root = Path(__file__).parent.parent
    missed = {}
    for file in sorted([*root.glob("src/**/*.py"), *root.glob("test/**/*.py")]):
        source = file.read_text()
        path = file.relative_to(root).as_posix()
        carded = {row.site for rows in method_statements.of(source, path).values() for row in rows}
        tops = {row.site for row in method_statements.top_rows(source, path)}
        lost = set(manifest.sites(source, path)) - carded - tops
        if lost:
            missed[path] = sorted(lost)
    assert missed == {}

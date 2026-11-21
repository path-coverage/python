import signal

from path_coverage import listed_cards, manifest, result

SHOP = (
    "RATE = 2 if FAST else 1\n"
    "def ship(order):\n"
    "    while order.paid and order.packed: break\n"
    "class Shop:\n"
    "    SIZE = 3 if BIG else 1\n"
)


def _then_taken(count):
    """A ternary's paths, its then taken count times, its else never."""
    return [{"path": [True], "count": count}, {"path": [False], "count": 0}]


PATHS = {
    "k.py:1:9": _then_taken(1),
    "k.py:3:21": [
        {"path": [True, True], "count": 1},
        {"path": [True, False], "count": 0},
        {"path": [False, None], "count": 0},
    ],
    "k.py:5:13": _then_taken(0),
}


def _listed(source, paths, reached):
    """The listed cards of source, as if it were k.py, from paths and
    reached, its operands all zero, with no ways taken."""
    decisions = manifest.decisions(source, "k.py")
    files = {"k.py": (source, decisions)}
    return listed_cards.of(files, result.operands(decisions, {}), paths, (reached, {}))


def test_d3c9a101():
    """Example: SHOP, RATE's then taken, SIZE's never, ship's and once
    Each card is listed as its page draws it: its name, its first and
    last lines, the ways one call can go through it, how many times it was
    called, never here, none for a top card, and a row per statement.
    A row has its line:col, its top, its paths, how many were taken,
    and its decision.
    A top card is named for its first line, its name the class holding
    it, or file when none does."""
    assert _listed(SHOP, PATHS, {}) == {
        "k.py:2:0": {
            "name": "ship",
            "first": 2,
            "last": 3,
            "ways": 3,
            "calls": 0,
            "rows": [{"at": "3:21", "top": "and", "paths": 3, "taken": 1, "decision": "k.py:3:21"}],
            "taken": [],
            "passes": {},
            "covered": [],
            "gaps": [
                [{"at": "3:21", "path": [True, True]}],
                [{"at": "3:21", "path": [True, False]}],
                [{"at": "3:21", "path": [False, None]}],
            ],
            "impossible": [],
            "impossible_taken": [],
        },
        "k.py:1:0": {
            "name": "file",
            "first": 1,
            "last": 1,
            "ways": 2,
            "calls": None,
            "rows": [{"at": "1:09", "top": "ternary", "paths": 2, "taken": 1, "decision": "k.py:1:9"}],
        },
        "k.py:5:0": {
            "name": "Shop",
            "first": 5,
            "last": 5,
            "ways": 2,
            "calls": None,
            "rows": [{"at": "5:13", "top": "ternary", "paths": 2, "taken": 0, "decision": "k.py:5:13"}],
        },
    }


def test_d3c9a103():
    """Example: SHOP's tree
    How each card's rows nest is listed for ship's card and for each top
    card, RATE's and Shop's, each by its line:col; each row here at the
    top, inside no other decision."""
    top = {"parent": None, "in": None, "on": None, "leaf": None, "gives": None}
    decisions = manifest.decisions(SHOP, "k.py")
    tree = listed_cards.tree({"k.py": (SHOP, decisions)}, result.operands(decisions, {}))
    assert tree == {"k.py": {"2:0": {"3:21": top}, "1:0": {"1:9": top}, "5:0": {"5:13": top}}}


def test_d3c9a102():
    """Example: ship, a write then a return, the return reached
    The write is no row. The return is a row that has no decision, and its
    taken is 1 when reached. Without reached, its taken is None, not
    known."""
    source = (
        "def ship(order):\n"
        "    box = order.pack()\n"
        "    return box\n"
    )
    rows = [
        [row["taken"] for row in _listed(source, {}, reached)["k.py:1:0"]["rows"]]
        for reached in ({"k.py:3:4": 1}, None)
    ]
    assert rows == [[1], [None]]
    assert [row["decision"] for row in _listed(source, {}, {})["k.py:1:0"]["rows"]] == [None]


def test_d3c9a104():
    """Example: save, an if on dry_run whose arm returns, a for loop, an
    if on not dry_run, a return; called twice, dry_run false, 2+ records.
    A function card lists the possible paths of its machine some call
    witnessed, covered, each with how many calls did; its gaps, those no
    call witnessed; and its impossible paths, each giving the stable
    dry_run both outcomes, neither with a count. The for is a fork, 0 or
    1+ items; the calls' 2+ passes witness its 1+ items path. Its ways
    are its possible paths."""
    source = (
        "def save(records, dry_run, db):\n"
        "    if dry_run:\n"
        "        return 0\n"
        "    for record in records:\n"
        "        db.append(record)\n"
        "    if not dry_run:\n"
        "        db.append('done')\n"
        "    return len(db)\n"
    )
    decisions = manifest.decisions(source, "k.py")
    taken = (("k.py:2:4", (False,)), ("k.py:4:4", ("2+ items",), frozenset({()})), ("k.py:6:4", (True,)), ("k.py:8:4",))
    counted = ({"k.py:1:0": 2}, {"k.py:1:0": {taken: 2}})
    paths = {
        "k.py:2:4": [{"path": [True], "count": 0}, {"path": [False], "count": 2}],
        "k.py:6:4": [{"path": [True], "count": 2}, {"path": [False], "count": 0}],
    }
    files = {"k.py": (source, decisions)}
    card = listed_cards.of(files, result.operands(decisions, {}), paths, counted, loops=True)["k.py:1:0"]
    on = {"at": "2:04", "path": [False]}
    none, some = {"at": "4:04", "path": ["0 items"]}, {"at": "4:04", "path": ["1+ items"]}
    assert (card["ways"], card["covered"], card["gaps"], card["impossible"]) == (
        3,
        [{"way": [on, some, {"at": "6:04", "path": [True]}, {"at": "8:04"}], "count": 2}],
        [[{"at": "2:04", "path": [True]}, {"at": "3:08"}], [on, none, {"at": "6:04", "path": [True]}, {"at": "8:04"}]],
        [[on, loop, {"at": "6:04", "path": [False]}, {"at": "8:04"}] for loop in (none, some)],
    )


def test_d3c9a105():
    """Example: half, an if whose condition is an or, then a return;
    called once, with a child.
    A call steps the or, decided first, before the if holding it, though
    the card's tree lists the if first; the machine steps in that order
    too, so a taken way matches its possible path, and each gap lists its
    steps as a call would take them."""
    source = (
        "def half(age, price):\n"
        "    if age < 16 or age >= 65:\n"
        "        price //= 2\n"
        "    return price\n"
    )
    decisions = manifest.decisions(source, "k.py")
    taken = (("k.py:2:16", (True, None)), ("k.py:2:4", (True,)), ("k.py:4:4",))
    counted = ({"k.py:1:0": 1}, {"k.py:1:0": {taken: 1}})
    paths = {
        "k.py:2:4": [{"path": [True], "count": 1}, {"path": [False], "count": 0}],
        "k.py:2:16": [
            {"path": [True, None], "count": 1},
            {"path": [False, True], "count": 0},
            {"path": [False, False], "count": 0},
        ],
    }
    files = {"k.py": (source, decisions)}
    card = listed_cards.of(files, result.operands(decisions, {}), paths, counted)["k.py:1:0"]
    assert card["gaps"] == [
        [{"at": "2:16", "path": [False, True]}, {"at": "2:04", "path": [True]}, {"at": "4:04"}],
        [{"at": "2:16", "path": [False, False]}, {"at": "2:04", "path": [False]}, {"at": "4:04"}],
    ]


# A small function beside one with 2**40 ways: forty ternaries in a row.
HUGE = (
    "def ok(a):\n"
    "    return 1 if a else 0\n"
    "def huge(c):\n" + "".join(f"    v{i} = 1 if c[{i}] else 0\n" for i in range(40))
)


def test_d3c9a110():
    """A file holding a function with 2**40 ways is listed within 5 seconds,
    that function's card counting its ways."""
    # A listing still running at the alarm is interrupted, not left to hang.
    previous = signal.signal(signal.SIGALRM, signal.default_int_handler)
    signal.alarm(5)
    try:
        never = {decision: _then_taken(0) for decision in manifest.decisions(HUGE, "k.py")}
        cards = _listed(HUGE, never, {})
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    assert cards["k.py:3:0"]["ways"] == 2**40


def test_d3c9a120():
    """Example: retry, a for loop over BACKOFFS whose line says
    # path: impossible 0 items, called once with BACKOFFS empty.
    The call takes the 0 items way the comment declared impossible, so
    the card lists that way as an impossible way taken."""
    source = (
        "BACKOFFS = ()\n"
        "def retry(call):\n"
        "    for backoff in BACKOFFS:  # path: impossible 0 items\n"
        "        call(backoff)\n"
        "    return call\n"
    )
    decisions = manifest.decisions(source, "k.py")
    taken = (("k.py:3:4", ("0 items",)), ("k.py:5:4",))
    counted = ({"k.py:2:0": 1}, {"k.py:2:0": {taken: 1}})
    files = {"k.py": (source, decisions)}
    card = listed_cards.of(files, result.operands(decisions, {}), {}, counted, loops=True)["k.py:2:0"]
    assert card["impossible_taken"] == [[{"at": "3:04", "path": ["0 items"]}, {"at": "5:04"}]]


def test_d3c9a121():
    """Example: save, an if on dry_run whose arm returns, a for loop, an
    if on not dry_run, a return; called twice, dry_run false, 2+ records,
    listed with loops as they are by default, off.
    With loops off the for is no fork: no way, covered, gap or impossible,
    steps at it, and the card has one way fewer than with it a fork."""
    source = (
        "def save(records, dry_run, db):\n"
        "    if dry_run:\n"
        "        return 0\n"
        "    for record in records:\n"
        "        db.append(record)\n"
        "    if not dry_run:\n"
        "        db.append('done')\n"
        "    return len(db)\n"
    )
    decisions = manifest.decisions(source, "k.py")
    taken = (("k.py:2:4", (False,)), ("k.py:4:4", ("2+ items",), frozenset({()})), ("k.py:6:4", (True,)), ("k.py:8:4",))
    counted = ({"k.py:1:0": 2}, {"k.py:1:0": {taken: 2}})
    paths = {
        "k.py:2:4": [{"path": [True], "count": 0}, {"path": [False], "count": 2}],
        "k.py:6:4": [{"path": [True], "count": 2}, {"path": [False], "count": 0}],
    }
    files = {"k.py": (source, decisions)}
    card = listed_cards.of(files, result.operands(decisions, {}), paths, counted)["k.py:1:0"]
    on = {"at": "2:04", "path": [False]}
    assert (card["ways"], card["covered"], card["gaps"], card["impossible"]) == (
        2,
        [{"way": [on, {"at": "6:04", "path": [True]}, {"at": "8:04"}], "count": 2}],
        [[{"at": "2:04", "path": [True]}, {"at": "3:08"}]],
        [[on, {"at": "6:04", "path": [False]}, {"at": "8:04"}]],
    )


def test_d3c9a122():
    """Example: save, an if on dry_run whose arm returns, a for loop, an
    if on not dry_run, a return; called twice, listed with max_paths 1
    A function with more paths than max_paths is not checked: its card
    lists no covered and no gaps, so the worklist names it as too many
    to check."""
    source = (
        "def save(records, dry_run, db):\n"
        "    if dry_run:\n"
        "        return 0\n"
        "    for record in records:\n"
        "        db.append(record)\n"
        "    if not dry_run:\n"
        "        db.append('done')\n"
        "    return len(db)\n"
    )
    decisions = manifest.decisions(source, "k.py")
    taken = (("k.py:2:4", (False,)), ("k.py:4:4", ("2+ items",), frozenset({()})), ("k.py:6:4", (True,)), ("k.py:8:4",))
    counted = ({"k.py:1:0": 2}, {"k.py:1:0": {taken: 2}})
    paths = {
        "k.py:2:4": [{"path": [True], "count": 0}, {"path": [False], "count": 2}],
        "k.py:6:4": [{"path": [True], "count": 2}, {"path": [False], "count": 0}],
    }
    files = {"k.py": (source, decisions)}
    card = listed_cards.of(files, result.operands(decisions, {}), paths, counted, max_paths=1)["k.py:1:0"]
    assert ("covered" in card, "gaps" in card) == (False, False)


def test_d3c9a123():
    """Example: restock, a for loop whose body breaks on a sold-out item,
    else reorders a low one, then a return; never called, listed with
    max_paths 3.
    Whether a function has more paths than max_paths is told by counting
    the very paths it lists: a break ends its pass, so restock has 3, not
    over 3, and its card lists them, each a gap."""
    source = (
        "def restock(items, low):\n"
        "    for item in items:\n"
        "        if item.sold_out:\n"
        "            break\n"
        "        if item.count < low:\n"
        "            item.reorder()\n"
        "    return items\n"
    )
    decisions = manifest.decisions(source, "k.py")
    files = {"k.py": (source, decisions)}
    counted = ({"k.py:1:0": 0}, {})
    never = [{"path": [True], "count": 0}, {"path": [False], "count": 0}]
    paths = {"k.py:3:8": never, "k.py:5:8": never}
    card = listed_cards.of(files, result.operands(decisions, {}), paths, counted, max_paths=3)["k.py:1:0"]
    assert (card["ways"], len(card["gaps"])) == (3, 3)


def test_d3c9a124():
    """Example: READY, outside every function, an any over ORDERS whose
    generator's element is an and; never run.
    A top card's ways are counted as a function's are: the and runs in
    the generator's frame, so adds no way; READY's ways are its any's 5,
    0 items, 1 or 2+ giving true or false."""
    source = "READY = any(o.paid and o.packed for o in ORDERS)\n"
    decisions = manifest.decisions(source, "k.py")
    never = [{"path": [True], "count": 0}, {"path": [False], "count": 0}]
    paths = {decision: never for decision in decisions}
    card = _listed(source, paths, None)["k.py:1:0"]
    assert card["ways"] == 5


def test_d3c9a125():
    """Example: PAID, outside every function, a list comprehension over
    ORDERS whose filter is an and; never run.
    A filter whose test is a decision decides on it: the filter keeps the
    item on the and's 1 path giving true, drops it on its 2 giving false,
    so PAID's ways are 3."""
    source = "PAID = [o for o in ORDERS if o.paid and o.sent]\n"
    decisions = manifest.decisions(source, "k.py")
    never = [{"path": [True], "count": 0}, {"path": [False], "count": 0}]
    paths = {decision: never for decision in decisions}
    card = _listed(source, paths, None)["k.py:1:0"]
    assert card["ways"] == 3


def test_d3c9a126():
    """Example: FEE, outside every function, a conditional expression on
    PAID or FREE whose then is a conditional expression on VIP; never run.
    A top card's decisions inside another are decided by it, not after
    it: the or's 2 true paths each take the inner one's 2, its false path
    the else, so FEE's ways are 5, not 3 times 2 times 2."""
    source = "FEE = (5 if VIP else 10) if PAID or FREE else 0\n"
    decisions = manifest.decisions(source, "k.py")
    never = [{"path": [True], "count": 0}, {"path": [False], "count": 0}]
    paths = {decision: never for decision in decisions}
    card = _listed(source, paths, None)["k.py:1:0"]
    assert (card["ways"], len(card["rows"])) == (5, 3)

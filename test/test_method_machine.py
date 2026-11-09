from path_coverage import method_machine


def test_5b1f3c01():
    """Example: label, an if whose arm returns a conditional expression,
    then a return.
    A method's machine is walked step by step, each step doing what
    Python does: the return in the if's arm ends the method, after the
    conditional expression in its value, so no path goes on to the last
    return. Each path is its steps, as Evaluations.ways has a way."""
    source = (
        "def label(token, upper):\n"
        "    if token.keyword:\n"
        "        return 'k' if upper else 'kw'\n"
        "    return 'name'\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4", (True,)), ("k.py:3:19", (True,))),
            (("k.py:2:4", (True,)), ("k.py:3:19", (False,))),
            (("k.py:2:4", (False,)), ("k.py:4:4",)),
        ]
    }


def test_5b1f3c02():
    """Example: fare, an assignment of a conditional expression, then an
    if whose test is an or, its arm returning, then a return.
    A decision in any statement is a step. A decision in an if's test is
    decided first, so steps before the if, and the if then takes only the
    arm its value gives: true for the or's first two paths, false for its
    last."""
    source = (
        "def fare(age, peak):\n"
        "    price = 1200 if peak else 800\n"
        "    if age < 16 or age >= 65:\n"
        "        return price // 2\n"
        "    return price\n"
    )
    ways = [
        (
            ("k.py:2:17", (peak,)),
            ("k.py:3:16", either),
            ("k.py:3:4", (taken,)),
            ("k.py:4:8",) if taken else ("k.py:5:4",),
        )
        for peak in (True, False)
        for either, taken in (((True, None), True), ((False, True), True), ((False, False), False))
    ]
    assert method_machine.paths(source, "k.py") == {"k.py:1:0": ways}


def test_5b1f3c03():
    """Example: parse, a try whose body raises ValueError when text is
    empty, its handler of ValueError raising again when strict, then a
    return.
    A raise in a try's body goes on to the handler catching it; a raise
    no try in the method catches, as the handler's own is outside the
    try's body, ends the method."""
    source = (
        "def parse(text, strict):\n"
        "    try:\n"
        "        if not text:\n"
        "            raise ValueError('empty')\n"
        "        value = int(text)\n"
        "    except ValueError:\n"
        "        if strict:\n"
        "            raise\n"
        "        value = 0\n"
        "    return value\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:8", (True,)), ("k.py:4:12",), ("k.py:7:8", (True,)), ("k.py:8:12",)),
            (("k.py:3:8", (True,)), ("k.py:4:12",), ("k.py:7:8", (False,)), ("k.py:10:4",)),
            (("k.py:3:8", (False,)), ("k.py:10:4",)),
        ]
    }


def test_5b1f3c04():
    """Example: find, a try raising KeyError when sku is not in stock, else
    ShopError when strict, else returning, its handlers of ValueError and
    of LookupError each returning.
    A raise goes on to the first handler naming its class, or a builtin
    class it is a subclass of: KeyError is a LookupError, not a
    ValueError. A class that is no builtin, ShopError, is caught by no
    handler naming another, so ends the method."""
    source = (
        "def find(stock, sku, strict):\n"
        "    try:\n"
        "        if sku not in stock:\n"
        "            raise KeyError(sku)\n"
        "        if strict:\n"
        "            raise ShopError(sku)\n"
        "        return stock[sku]\n"
        "    except ValueError:\n"
        "        return -1\n"
        "    except LookupError:\n"
        "        return 0\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:8", (True,)), ("k.py:4:12",), ("k.py:11:8",)),
            (("k.py:3:8", (False,)), ("k.py:5:8", (True,)), ("k.py:6:12",)),
            (("k.py:3:8", (False,)), ("k.py:5:8", (False,)), ("k.py:7:8",)),
        ]
    }


def test_5b1f3c05():
    """Example: load, a try raising ShopError when strict, else returning,
    its handler a bare except, returning.
    A bare except catches every raise, of any class."""
    source = (
        "def load(path, strict):\n"
        "    try:\n"
        "        if strict:\n"
        "            raise ShopError(path)\n"
        "        return 1\n"
        "    except:\n"
        "        return 0\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:8", (True,)), ("k.py:4:12",), ("k.py:7:8",)),
            (("k.py:3:8", (False,)), ("k.py:5:8",)),
        ]
    }


def test_5b1f3c06():
    """Example: price, a try raising KeyError when strict, else returning,
    its handler of ValueError or LookupError, returning.
    A handler of a tuple of classes catches a raise any one of them
    catches: KeyError is a LookupError."""
    source = (
        "def price(order, strict):\n"
        "    try:\n"
        "        if strict:\n"
        "            raise KeyError(order)\n"
        "        return 1\n"
        "    except (ValueError, LookupError):\n"
        "        return 0\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:8", (True,)), ("k.py:4:12",), ("k.py:7:8",)),
            (("k.py:3:8", (False,)), ("k.py:5:8",)),
        ]
    }


def test_5b1f3c07():
    """Example: stock, a try raising KeyError when strict, its handler of
    LookupError returning, its else returning 9 for a count over 9, then
    a return.
    A try's else runs after its body, only when the body raised nothing."""
    source = (
        "def stock(shelf, sku, strict):\n"
        "    try:\n"
        "        if strict:\n"
        "            raise KeyError(sku)\n"
        "        count = shelf[sku]\n"
        "    except LookupError:\n"
        "        return 0\n"
        "    else:\n"
        "        if count > 9:\n"
        "            return 9\n"
        "    return count\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:8", (True,)), ("k.py:4:12",), ("k.py:7:8",)),
            (("k.py:3:8", (False,)), ("k.py:9:8", (True,)), ("k.py:10:12",)),
            (("k.py:3:8", (False,)), ("k.py:9:8", (False,)), ("k.py:11:4",)),
        ]
    }


def test_5b1f3c08():
    """Example: save, a try raising KeyError when strict, else returning
    when there is a record, its finally flushing a dirty db, then a
    return.
    A try's finally runs on each way out of its body, then goes on out
    that way: after the raise, ending the method, as nothing catches it;
    after the return, ending it; else on to the last return."""
    source = (
        "def save(db, record, strict):\n"
        "    try:\n"
        "        if strict:\n"
        "            raise KeyError(record)\n"
        "        if record:\n"
        "            return db.add(record)\n"
        "    finally:\n"
        "        if db.dirty:\n"
        "            db.flush()\n"
        "    return 0\n"
    )
    flushed = [("k.py:8:8", (True,)), ("k.py:8:8", (False,))]
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            *[(("k.py:3:8", (True,)), ("k.py:4:12",), each) for each in flushed],
            *[(("k.py:3:8", (False,)), ("k.py:5:8", (True,)), ("k.py:6:12",), each) for each in flushed],
            *[(("k.py:3:8", (False,)), ("k.py:5:8", (False,)), each, ("k.py:10:4",)) for each in flushed],
        ]
    }


def test_5b1f3c09():
    """Example: size, a match of three cases, each returning, the last
    guarded, then a return.
    A case's body runs on the paths that pick it: those whose last leaf
    reached, its pattern's or its guard's, is the case's and true. A path
    picking no case, its guard false, goes on after the match."""
    source = (
        "def size(order):\n"
        "    match len(order['items']):\n"
        "        case 0:\n"
        "            return 'empty'\n"
        "        case 1 | 2:\n"
        "            return 'small'\n"
        "        case count if count > 10:\n"
        "            return 'large'\n"
        "    return 'medium'\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4", (True, None, None, None)), ("k.py:4:12",)),
            (("k.py:2:4", (False, True, None, None)), ("k.py:6:12",)),
            (("k.py:2:4", (False, False, True, True)), ("k.py:8:12",)),
            (("k.py:2:4", (False, False, True, False)), ("k.py:9:4",)),
        ]
    }


def test_5b1f3c0a():
    """Example: read, a with whose body raises when strict, then a return
    of a conditional expression.
    A with's body runs as any block does: its raise ends the method."""
    source = (
        "def read(path, strict):\n"
        "    with open(path) as file:\n"
        "        if strict:\n"
        "            raise ValueError(path)\n"
        "        text = file.read()\n"
        "    return text if text else None\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:8", (True,)), ("k.py:4:12",)),
            (("k.py:3:8", (False,)), ("k.py:6:16", (True,))),
            (("k.py:3:8", (False,)), ("k.py:6:16", (False,))),
        ]
    }


def test_5b1f3c0b():
    """Example: pricer, defining a function, a class and a lambda, each
    holding a conditional expression, then returning one of its own.
    A nested def, class or lambda runs in a frame of its own, so its
    decisions are no steps of the method defining it; a nested def has a
    machine of its own."""
    source = (
        "def pricer(rate, member):\n"
        "    def apply(total):\n"
        "        return total * rate if member else total\n"
        "    class Plan:\n"
        "        LEVEL = 2 if member else 1\n"
        "    discount = lambda total: total - 1 if total else 0\n"
        "    return apply if rate else discount\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [(("k.py:7:17", (True,)),), (("k.py:7:17", (False,)),)],
        "k.py:2:4": [(("k.py:3:28", (True,)),), (("k.py:3:28", (False,)),)],
    }


def test_5b1f3c0c():
    """Example: save, an if on dry_run whose arm returns, then an if on
    not dry_run, then a return.
    The dry run knows what each step has given a stable name, a
    parameter used only as a leaf, as stable_names finds it: a path giving
    one both outcomes is impossible, listed apart from the possible ones.
    dry_run is false at 2:4, so not dry_run cannot be false at 6:4."""
    source = (
        "def save(record, dry_run, db, audit):\n"
        "    if dry_run:\n"
        "        print('would save', record)\n"
        "        return None\n"
        "    db.append(record)\n"
        "    if not dry_run:\n"
        "        audit.append(record)\n"
        "    return len(db)\n"
    )
    assert method_machine.ways(source, "k.py") == {
        "k.py:1:0": {
            "possible": [
                (("k.py:2:4", (True,)), ("k.py:4:8",)),
                (("k.py:2:4", (False,)), ("k.py:6:4", (True,)), ("k.py:8:4",)),
            ],
            "impossible": [
                (("k.py:2:4", (False,)), ("k.py:6:4", (False,)), ("k.py:8:4",)),
            ],
        }
    }


def test_5b1f3c0d():
    """Example: ship, an if on quick or dry_run or order.held whose arm
    returns, then an if on not dry_run, then a return.
    order.held reads no stable name, so gives nothing; a path not reaching
    a leaf, dry_run when quick, gives its name nothing either. Only the
    or's last path, dry_run false, then not dry_run false, is
    impossible."""
    source = (
        "def ship(order, dry_run, quick):\n"
        "    if quick or dry_run or order.held:\n"
        "        return None\n"
        "    if not dry_run:\n"
        "        order.send()\n"
        "    return order\n"
    )
    taking = ((True, None, None), (False, True, None), (False, False, True))
    left = [(("k.py:2:13", each), ("k.py:2:4", (True,)), ("k.py:3:8",)) for each in taking]
    on = (("k.py:2:13", (False, False, False)), ("k.py:2:4", (False,)))
    assert method_machine.ways(source, "k.py") == {
        "k.py:1:0": {
            "possible": [*left, (*on, ("k.py:4:4", (True,)), ("k.py:6:4",))],
            "impossible": [(*on, ("k.py:4:4", (False,)), ("k.py:6:4",))],
        }
    }


def test_5b1f3c10():
    """Example: paid, returning the sum over a generator expression whose
    iterable is an or, its filter order.paid.
    A statement that is a row steps where it starts, before the decisions
    in it. A generator expression runs in a frame of its own, but for its
    first iterable, run where it is written: the or is a step of the
    method, the filter is not. The or's value is iterated, its truth
    tested by no branch, so fallback is no leaf of it."""
    source = (
        "def paid(orders, fallback):\n"
        "    return sum(1 for order in (orders or fallback) if order.paid)\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4",), ("k.py:2:38", (True,))),
            (("k.py:2:4",), ("k.py:2:38", (False,))),
        ]
    }


def test_5b1f3c11():
    """Example: one, a conditional expression whose test is an or; two, an
    and whose last operand is a conditional expression; three, a
    conditional expression whose else is an and; four, an or whose first
    operand calls f on a conditional expression.
    A decision inside a leaf of another is decided first, so steps
    before it, on each path of the other reaching that leaf; one that is
    the whole leaf only on its paths whose value the leaf's outcome
    allows, any when its value is not known, as for two's arms. An and in
    a conditional expression's arm is part of its decision, so no step of
    its own."""
    source = (
        "def one(truth, a, b):\n"
        "    assert truth if a or b else None\n"
        "def two(a, b):\n"
        "    assert a and (1 if b else 2)\n"
        "def three(x, c, a, b):\n"
        "    assert x if c else (a and b)\n"
        "def four(f, x, c, y, z):\n"
        "    assert f(x if c else y) or z\n"
    )
    either = ((True,), (False,))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:22", (True, None)), ("k.py:2:17", (True,))),
            (("k.py:2:22", (False, True)), ("k.py:2:17", (True,))),
            (("k.py:2:22", (False, False)), ("k.py:2:17", (False,))),
        ],
        "k.py:3:0": [
            *[(("k.py:4:20", arm), ("k.py:4:13", path)) for path in ((True, True), (True, False)) for arm in either],
            (("k.py:4:13", (False, None)),),
        ],
        "k.py:5:0": [
            (("k.py:6:13", path),) for path in ((True, None, None), (False, True, True), (False, True, False), (False, False, None))
        ],
        "k.py:7:0": [
            (("k.py:8:15", arm), ("k.py:8:28", path)) for path in ((True, None), (False, True), (False, False)) for arm in either
        ],
    }


def test_5b1f3c12():
    """Example: led, an or of an any, whose generator's element is an and,
    and of not xs.
    The any is the or's first leaf, so steps first, on the or's true path
    only its paths giving true, on each false path only those giving
    false. Its element is one of its leaves, but runs in the generator
    expression's frame, so its and takes no step here."""
    source = (
        "def led(xs):\n"
        "    assert any(x % 2 and x > 1 for x in xs) or not xs\n"
    )
    falsy = (("0 items", None), ("1 item", False), ("2+ items", False))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            *[(("k.py:2:11", path), ("k.py:2:44", (True, None))) for path in (("1 item", True), ("2+ items", True))],
            *[(("k.py:2:11", path), ("k.py:2:44", (False, True))) for path in falsy],
            *[(("k.py:2:11", path), ("k.py:2:44", (False, False))) for path in falsy],
        ]
    }


def test_5b1f3c13():
    """Example: keep, returning a list comprehension with a filter.
    A comprehension's generator is a loop, a fork by its for keyword, as
    a for statement is: its filter steps only on its 1+ items path. A
    filter's decision is its test, which is also its one leaf: the
    decision is not inside its own leaf, so steps once there."""
    source = (
        "def keep(xs):\n"
        "    return [x for x in xs if x]\n"
    )
    passes = ("k.py:2:14", ("1+ items",))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4",), ("k.py:2:14", ("0 items",))),
            (("k.py:2:4",), passes, ("k.py:2:26", (True,))),
            (("k.py:2:4",), passes, ("k.py:2:26", (False,))),
        ]
    }


def test_5b1f3c14():
    """Example: total, a for loop whose body holds an if, then a return.
    A loop is a fork, walked without iterating: on one path it runs no
    pass, its body in no step; on the other at least one, its body walked
    once, each of its body's ways a path of its own. The loop steps first,
    by its for keyword, with 0 items or 1+ items."""
    source = (
        "def total(orders):\n"
        "    amount = 0\n"
        "    for order in orders:\n"
        "        if order['paid']:\n"
        "            amount += order['amount']\n"
        "    return amount\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:4", ("0 items",)), ("k.py:6:4",)),
            (("k.py:3:4", ("1+ items",)), ("k.py:4:8", (True,)), ("k.py:6:4",)),
            (("k.py:3:4", ("1+ items",)), ("k.py:4:8", (False,)), ("k.py:6:4",)),
        ]
    }


def test_5b1f3c15():
    """Example: first_late, a for loop whose body breaks on a late order,
    else returns on a lost one, then a return.
    A break ends the loop: the rest of the body is skipped, and the path
    goes on after the loop."""
    source = (
        "def first_late(orders):\n"
        "    found = None\n"
        "    for order in orders:\n"
        "        if order['late']:\n"
        "            found = order\n"
        "            break\n"
        "        if order['lost']:\n"
        "            return 'lost'\n"
        "    return found\n"
    )
    passes = ("k.py:3:4", ("1+ items",))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:4", ("0 items",)), ("k.py:9:4",)),
            (passes, ("k.py:4:8", (True,)), ("k.py:9:4",)),
            (passes, ("k.py:4:8", (False,)), ("k.py:7:8", (True,)), ("k.py:8:12",)),
            (passes, ("k.py:4:8", (False,)), ("k.py:7:8", (False,)), ("k.py:9:4",)),
        ]
    }


def test_5b1f3c16():
    """Example: find, a for loop whose body continues past another sku,
    else breaks on an open order, its else returning None, then a return.
    A loop's else runs when it ends without a break: after no pass, or
    after its body. A continue ends the pass, walked once, so goes on to
    the else; a break skips it."""
    source = (
        "def find(orders, sku):\n"
        "    for order in orders:\n"
        "        if order['sku'] != sku:\n"
        "            continue\n"
        "        if order['open']:\n"
        "            break\n"
        "    else:\n"
        "        return None\n"
        "    return order\n"
    )
    passes = ("k.py:2:4", ("1+ items",))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4", ("0 items",)), ("k.py:8:8",)),
            (passes, ("k.py:3:8", (True,)), ("k.py:8:8",)),
            (passes, ("k.py:3:8", (False,)), ("k.py:5:8", (True,)), ("k.py:9:4",)),
            (passes, ("k.py:3:8", (False,)), ("k.py:5:8", (False,)), ("k.py:8:8",)),
        ]
    }


def test_5b1f3c17():
    """Example: drain, a for loop whose body is a try breaking on a done
    job, its finally writing to a log when there is one, then a return.
    A break out of a try runs its finally first, as a return or a raise
    does."""
    source = (
        "def drain(queue, log):\n"
        "    for job in queue:\n"
        "        try:\n"
        "            if job.done:\n"
        "                break\n"
        "        finally:\n"
        "            if log:\n"
        "                log.write(job)\n"
        "    return queue\n"
    )
    passes = ("k.py:2:4", ("1+ items",))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4", ("0 items",)), ("k.py:9:4",)),
            *[
                (passes, ("k.py:4:12", (done,)), ("k.py:7:12", (logged,)), ("k.py:9:4",))
                for done in (True, False)
                for logged in (True, False)
            ],
        ]
    }


def test_5b1f3c18():
    """Example: drain, a while loop on queue whose body holds an if, then
    a return.
    A while loop is a fork as a for loop is, by its while keyword: entered
    or not. Its later tests, another pass or leaving, repeat that fork, so
    are no steps."""
    source = (
        "def drain(queue):\n"
        "    while queue:\n"
        "        if queue.pop():\n"
        "            queue.log()\n"
        "    return queue\n"
    )
    passes = ("k.py:2:4", ("1+ items",))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4", ("0 items",)), ("k.py:5:4",)),
            (passes, ("k.py:3:8", (True,)), ("k.py:5:4",)),
            (passes, ("k.py:3:8", (False,)), ("k.py:5:4",)),
        ]
    }


def test_5b1f3c19():
    """Example: prices, returning a dict comprehension whose value is a
    conditional expression.
    A dict comprehension's key and value run on its 1+ items path, after
    its generators, so their decisions step there."""
    source = (
        "def prices(items, member):\n"
        "    return {item: (5 if member else 10) for item in items}\n"
    )
    passes = ("k.py:2:40", ("1+ items",))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4",), ("k.py:2:40", ("0 items",))),
            (("k.py:2:4",), passes, ("k.py:2:21", (True,))),
            (("k.py:2:4",), passes, ("k.py:2:21", (False,))),
        ]
    }


def test_5b1f3c1a():
    """Example: total's ways, as calls take them: on paid, unpaid and paid
    orders, its for made 2+ passes, taking the if true and false; on none,
    0.
    A call witnesses each static path whose every choice it made, after
    the same earlier choices: its loop, made 1+ items, followed by each
    way a pass took, then the rest of the call's way."""
    paid, unpaid = (("k.py:4:8", (True,)),), (("k.py:4:8", (False,)),)
    passes = ("k.py:3:4", ("1+ items",))
    three = (("k.py:3:4", ("2+ items",), frozenset({paid, unpaid})), ("k.py:6:4",))
    none = (("k.py:3:4", ("0 items",), frozenset()), ("k.py:6:4",))
    assert [method_machine.witnessed(way) for way in (three, none)] == [
        {(passes, *paid, ("k.py:6:4",)), (passes, *unpaid, ("k.py:6:4",))},
        {(("k.py:3:4", ("0 items",)), ("k.py:6:4",))},
    ]


def test_5b1f3c1b():
    """Example: keep, returning a list comprehension whose filter is an
    and.
    A filter and the and that is its test are two decisions of one node:
    the and is the filter's whole leaf, so steps first, on each of the
    filter's paths only its paths giving that outcome."""
    source = (
        "def keep(xs, strict):\n"
        "    return [x for x in xs if x and strict]\n"
    )
    entered = (("k.py:2:4",), ("k.py:2:14", ("1+ items",)))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:4",), ("k.py:2:14", ("0 items",))),
            (*entered, ("k.py:2:31", (True, True)), ("k.py:2:26", (True,))),
            (*entered, ("k.py:2:31", (True, False)), ("k.py:2:26", (False,))),
            (*entered, ("k.py:2:31", (False, None)), ("k.py:2:26", (False,))),
        ]
    }


def test_5b1f3c1c():
    """Example: kept, a conditional expression whose then is a list
    comprehension with a filter, its else a name.
    A conditional expression steps when its test is decided, then runs
    the arm it takes: the decisions in that arm step after it."""
    source = (
        "def kept(items, strict):\n"
        "    return [item for item in items if item] if strict else items\n"
    )
    taken = (("k.py:2:44", (True,)), ("k.py:2:17", ("1+ items",)))
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:2:44", (True,)), ("k.py:2:17", ("0 items",))),
            (*taken, ("k.py:2:35", (True,))),
            (*taken, ("k.py:2:35", (False,))),
            (("k.py:2:44", (False,)),),
        ]
    }


def test_5b1f3c1d():
    """Example: report, VERBOSE read by an if, then refresh called, then
    VERBOSE read by a conditional expression.
    Only a parameter can be stable: VERBOSE is a global, which a call
    between the reads can rebind, so no path is impossible."""
    source = (
        "def report(rows):\n"
        "    if VERBOSE:\n"
        "        print(len(rows))\n"
        "    refresh()\n"
        "    return 'long' if VERBOSE else 'short'\n"
    )
    either = ((True,), (False,))
    assert method_machine.ways(source, "k.py") == {
        "k.py:1:0": {
            "possible": [(("k.py:2:4", first), ("k.py:5:18", second)) for first in either for second in either],
            "impossible": [],
        }
    }


def test_5b1f3c1e():
    """Example: sign, an if on delta whose arm returns, then a conditional
    expression on -delta.
    Only the name, or not the name, reads a stable name: -delta is a use
    of delta that is no such leaf, so delta is not stable, and no path is
    impossible, though -delta read as not delta would make one so."""
    source = (
        "def sign(delta):\n"
        "    if delta:\n"
        "        return 'moved'\n"
        "    return 'back' if -delta else 'still'\n"
    )
    assert method_machine.ways(source, "k.py") == {
        "k.py:1:0": {
            "possible": [
                (("k.py:2:4", (True,)), ("k.py:3:8",)),
                (("k.py:2:4", (False,)), ("k.py:4:18", (True,))),
                (("k.py:2:4", (False,)), ("k.py:4:18", (False,))),
            ],
            "impossible": [],
        }
    }


def test_5b1f3c0e():
    """Example: reprice, a try raising KeyError when strict, its handlers
    of TypeError alone, of no class, of TypeError or ValueError, then of
    LookupError alone.
    A tuple catches a raise when one of its classes does: a tuple of one
    class not catching it, an empty tuple, and a tuple of two neither
    catching it each pass it on, to the last handler."""
    source = (
        "def reprice(order, strict):\n"
        "    try:\n"
        "        if strict:\n"
        "            raise KeyError(order)\n"
        "        return 1\n"
        "    except (TypeError,):\n"
        "        return 2\n"
        "    except ():\n"
        "        return 3\n"
        "    except (TypeError, ValueError):\n"
        "        return 4\n"
        "    except (LookupError,):\n"
        "        return 5\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:8", (True,)), ("k.py:4:12",), ("k.py:13:8",)),
            (("k.py:3:8", (False,)), ("k.py:5:8",)),
        ]
    }


def test_5b1f3c0f():
    """Example: book, a try raising ShopError when strict, its handler of
    ShopError returning.
    A handler naming a class that is no builtin catches a raise of the
    class it names."""
    source = (
        "def book(order, strict):\n"
        "    try:\n"
        "        if strict:\n"
        "            raise ShopError(order)\n"
        "        return 1\n"
        "    except ShopError:\n"
        "        return 0\n"
    )
    assert method_machine.paths(source, "k.py") == {
        "k.py:1:0": [
            (("k.py:3:8", (True,)), ("k.py:4:12",), ("k.py:7:8",)),
            (("k.py:3:8", (False,)), ("k.py:5:8",)),
        ]
    }

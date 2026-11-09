from path_coverage import scopes, source_map


def test_c4e81d01():
    """Example: first_ok, its for's iterable an or, its body an if and a
    return, its else a raise
    Only a row in a for's body is held by it, as only the body runs again
    on each pass: its iterable and its else run once."""
    source = (
        "def first_ok(orders, fallback):\n"
        "    for order in (orders or fallback):\n"
        "        if order.ok:\n"
        "            return order\n"
        "    else:\n"
        "        raise LookupError('no order is ok')\n"
    )
    assert source_map.Source(source, "k.py", scopes.whole(source)).loops == {
        "k.py:2:25": (),
        "k.py:3:8": ("k.py:2:4",),
        "k.py:4:12": ("k.py:2:4",),
        "k.py:6:8": (),
        "k.py:2:4": (),
    }


def test_c4e81d02():
    """Example: paid, then first_paid, its for on lines not kept, as
    measuring only paid
    A for on no kept line is no loop: nothing is held by it, nor named by
    it."""
    source = (
        "def paid(order):\n"
        "    return order.paid and not order.refunded\n"
        "\n"
        "def first_paid(orders):\n"
        "    for order in orders:\n"
        "        if paid(order):\n"
        "            return order\n"
    )
    assert source_map.Source(source, "k.py", scopes.lines(source, "paid")).loops == {
        "k.py:2:22": (),
        "k.py:7:12": (),
    }


DRAIN = (
    "def drain(queue, limit):\n"
    "    taken = 0\n"
    "    while queue and taken < limit:\n"
    "        if queue.pop():\n"
    "            taken += 1\n"
    "    return taken\n"
)


def test_c4e81d04():
    """Example: drain, a while whose test is an and, its body an if
    A while is a loop, named by its keyword: a row in its body is held by
    it, as each pass runs it again; its test is where its passes are
    told; and each decision in its test repeats with each pass, its first
    run, before any pass, held by no loop."""
    found = source_map.Source(DRAIN, "k.py", scopes.whole(DRAIN))
    assert [found.loops, found.whiles, found.repeats, found.fors] == [
        {"k.py:3:16": (), "k.py:4:8": ("k.py:3:4",), "k.py:6:4": (), "k.py:3:4": ()},
        {(3, 10, 3, 33): "k.py:3:4"},
        {"k.py:3:16": "k.py:3:4"},
        {},
    ]


def test_c4e81d05():
    """Example: paid, then drain_paid, its while on lines not kept, as
    measuring only paid
    A while on no kept line is no loop: its test is not told, and no
    decision repeats with it."""
    source = (
        "def paid(order):\n"
        "    return order.paid and not order.refunded\n"
        "\n"
        "def drain_paid(orders):\n"
        "    while orders and paid(orders[-1]):\n"
        "        orders.pop()\n"
    )
    found = source_map.Source(source, "k.py", scopes.lines(source, "paid"))
    assert [found.whiles, found.repeats, found.loops] == [{}, {}, {"k.py:2:22": ()}]


def test_c4e81d03():
    """Example: late_refunds, a list comprehension of two generators, each
    with a filter
    Each generator of a comprehension run in its function's frame is a
    loop, named by its for keyword: its filter is held by it and every
    generator before it, its iterable by those before it only, as each
    runs once per item of the one before."""
    source = (
        "def late_refunds(orders, refunds):\n"
        "    return [r for o in orders if o.late for r in refunds if r.big]\n"
    )
    found = source_map.Source(source, "k.py", scopes.whole(source))
    assert [found.loops, found.fors] == [
        {
            "k.py:2:30": ("k.py:2:14",),
            "k.py:2:57": ("k.py:2:14", "k.py:2:40"),
            "k.py:2:4": (),
            "k.py:2:14": (),
            "k.py:2:40": ("k.py:2:14",),
        },
        {(2, 23, 2, 29): "k.py:2:14", (2, 49, 2, 56): "k.py:2:40"},
    ]

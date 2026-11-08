from path_coverage import decision_paths, manifest
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
    Shape,
    Unmatched,
    Unwalked,
)


def _shape(source, decision):
    """The Shape of the decision named decision in source, a file k.py, its
    possible paths as the manifest gives them."""
    condition = manifest.decisions(source, "k.py")[decision]
    return Shape(decision, decision_paths.possible(condition))


def _run(evaluations, *events):
    """Logs each of events, (frame, actions), on evaluations, then
    rebuilds them; returns evaluations."""
    evaluations.log.extend(events)
    evaluations.flush()
    return evaluations


TRAILS = "def is_new(trail_id, trails):\n    return ok(trail_id) and new(trail_id)\n"


def test_3c9e5101():
    """Example: ok(id) and new(id), evaluated twice in one frame: true then
    false, then false
    Each evaluation's path is counted once it is complete, and each leaf's
    outcomes are counted as they happen."""
    shape = _shape(TRAILS, "k.py:2:24")
    ran = _run(
        Evaluations(),
        (7, (Outcome(shape, 0, True),)),
        (7, (Outcome(shape, 1, False),)),
        (7, (Outcome(shape, 0, False),)),
    )
    assert ran.decision_paths == {"k.py:2:24": {(True, False): 1, (False, None): 1}}
    assert ran.counts == {
        ("k.py:2:24", 0): {"truthy": 1, "falsy": 1},
        ("k.py:2:24", 1): {"truthy": 0, "falsy": 1},
    }


def test_3c9e5102():
    """Example: ok(id) and new(id), its new calling is_new again, so a
    second frame evaluates the same decision inside the first's evaluation
    Each frame's evaluation is its own, so the paths do not mix."""
    shape = _shape(TRAILS, "k.py:2:24")
    ran = _run(
        Evaluations(),
        (1, (Outcome(shape, 0, True),)),
        (2, (Outcome(shape, 0, True),)),
        (2, (Outcome(shape, 1, True),)),
        (1, (Outcome(shape, 1, False),)),
    )
    assert ran.decision_paths == {"k.py:2:24": {(True, True): 1, (True, False): 1}}


def test_3c9e5103():
    """Example: ok(id) true, then new(id) raises; then, in the same frame,
    ok(id) false
    The evaluation that raised never completes, so its path is not
    counted, though ok's outcome is."""
    shape = _shape(TRAILS, "k.py:2:24")
    ran = _run(
        Evaluations(),
        (3, (Outcome(shape, 0, True),)),
        (3, (Outcome(shape, 0, False),)),
    )
    assert ran.decision_paths == {"k.py:2:24": {(False, None): 1}}
    assert ran.counts == {("k.py:2:24", 0): {"truthy": 1, "falsy": 1}}


def test_3c9e5104():
    """Example: return member and vip, member true, vip false as the call
    around it counts it; then member false
    The last operand's outcome, from its call, completes the evaluation
    its branch began."""
    shape = _shape("def f(member, vip):\n    return member and vip\n", "k.py:2:18")
    ran = _run(
        Evaluations(),
        (5, (Outcome(shape, 0, True),)),
        (5, (Outcome(shape, 1, False),)),
        (5, (Outcome(shape, 0, False),)),
    )
    assert ran.decision_paths == {"k.py:2:18": {(True, False): 1, (False, None): 1}}
    assert ran.counts[("k.py:2:18", 1)] == {"truthy": 0, "falsy": 1}


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


def test_3c9e5107():
    """Example: size's match, given 5 items: case count reached, its guard
    false, then case _
    Reaching a case's guard or body matches its pattern, and every earlier
    pattern not yet matched did not match."""
    shape = _shape(SIZE, "k.py:2:4")
    ran = _run(
        Evaluations(),
        (8, (Matched(shape, 2, (0, 1)),)),
        (8, (Outcome(shape, 3, False),)),
        (8, (Matched(shape, 4, (0, 1, 2)),)),
        (8, (Matched(shape, 0, ()),)),
    )
    assert ran.decision_paths == {
        "k.py:2:4": {(False, False, True, False, True): 1, (True, None, None, None, None): 1}
    }
    assert ran.counts[("k.py:2:4", 2)] == {"truthy": 1, "falsy": 0}
    assert ran.counts[("k.py:2:4", 1)] == {"truthy": 0, "falsy": 1}


KIND = (
    "def label(order):\n"
    "    match order.kind:\n"
    "        case 'gold' if order.big:\n"
    "            return 1\n"
    "        case 'silver':\n"
    "            return 2\n"
    "    return 3\n"
)


def test_3c9e5108():
    """Example: label's match, no case of which matches anything: a plain
    order, then a small gold one, then a silver one, whose body done, the
    code after the match is reached
    When no case matches, every pattern not yet matched did not, whether
    or not an earlier one matched with its guard false. The code after the
    match is reached as well when a case was taken, its evaluation
    complete, so it opens none."""
    shape = _shape(KIND, "k.py:2:4")
    ran = _run(
        Evaluations(),
        (9, (Opened(shape),)),
        (9, (Unmatched(shape, (0, 2)),)),
        (9, (Opened(shape),)),
        (9, (Matched(shape, 0, ()),)),
        (9, (Outcome(shape, 1, False),)),
        (9, (Unmatched(shape, (0, 2)),)),
        (9, (Opened(shape),)),
        (9, (Matched(shape, 2, (0,)),)),
        (9, (Unmatched(shape, (0, 2)),)),
    )
    assert ran.decision_paths == {
        "k.py:2:4": {(False, None, False): 1, (True, False, False): 1, (False, None, True): 1}
    }


LATE = "def any_late(orders):\n    return any(o.late for o in orders)\n"


def test_3c9e5109():
    """Example: any(o.late for o in orders), given a prompt order then a
    late one, and given none
    The items are counted, 0, 1 or 2+, and the last answer is the path's,
    each answer and whether there were items counted as a leaf's outcomes."""
    shape = _shape(LATE, "k.py:2:11")
    ran = _run(
        Evaluations(),
        (4, (Begin(shape),)),
        (4, (Item(shape),)),
        (4, (Answer(shape, False),)),
        (4, (Item(shape),)),
        (4, (Answer(shape, True), End(shape))),
        (4, (Begin(shape),)),
        (4, (End(shape),)),
    )
    assert ran.decision_paths == {"k.py:2:11": {("2+ items", True): 1, ("0 items", None): 1}}
    assert ran.counts == {
        ("k.py:2:11", 0): {"truthy": 1, "falsy": 1},
        ("k.py:2:11", 1): {"truthy": 1, "falsy": 1},
    }


def test_3c9e510a():
    """Example: ship's return reached twice
    reached holds each statement's runs; one never reached has none."""
    ran = _run(Evaluations(), (2, (Reach("k.py:3:4"),)), (2, (Reach("k.py:3:4"),)))
    assert ran.reached == {"k.py:3:4": 2}


def test_3c9e510c():
    """Example: ok(id) and new(id), new's outcome seen in a frame whose ok
    was never seen, as when measuring started inside the evaluation
    No possible path agrees, so the evaluation is dropped, though new's
    outcome is counted."""
    shape = _shape(TRAILS, "k.py:2:24")
    ran = _run(Evaluations(), (6, (Outcome(shape, 1, True),)))
    assert ran.decision_paths == {}
    assert ran.counts == {("k.py:2:24", 1): {"truthy": 1, "falsy": 0}}


def test_3c9e510b():
    """Example: Evaluations(limit=2), noting two events
    The log is rebuilt as soon as it holds limit events, so a long run
    never holds every event it saw."""
    shape = _shape(TRAILS, "k.py:2:24")
    evaluations = Evaluations(limit=2)
    evaluations.note(1, (Outcome(shape, 0, True),))
    assert evaluations.log == [(1, (Outcome(shape, 0, True),))]
    evaluations.note(1, (Outcome(shape, 1, True),))
    assert evaluations.log == []
    assert evaluations.decision_paths == {"k.py:2:24": {(True, True): 1}}


TOTAL = (
    "def total(orders):\n"
    "    amount = 0\n"
    "    for order in orders:\n"
    "        if order.paid:\n"
    "            amount += order.amount\n"
    "    return amount\n"
)

# Where each of TOTAL's rows runs: the loops holding it, outermost first.
TOTAL_LOOPS = {"k.py:3:4": (), "k.py:4:8": ("k.py:3:4",), "k.py:6:4": ()}


def _paid(shape, *paid):
    """The events of one pass of total's for per order, paid or not."""
    return [event for each in paid for event in ((1, (Pass("k.py:3:4"),)), (1, (Outcome(shape, 0, each),)))]


def test_3c9e510d():
    """Example: total called on 3 orders, paid, unpaid, paid; then on 1
    paid order; then on none
    A call's way holds its loop once, as 0, 1 or 2+ items, however many
    passes it made, with the set of ways its passes took, so a call
    witnesses each of them; each pass's own way is counted on the loop.
    The ways kept never grow with the passes made, only with the body's
    distinct ways."""
    shape = _shape(TOTAL, "k.py:4:8")
    evaluations = Evaluations()
    evaluations.loops.update(TOTAL_LOOPS)
    for orders in ((True, False, True), (True,), ()):
        evaluations.log.append((1, (Enter("k.py:1:0"),)))
        evaluations.log.extend(_paid(shape, *orders))
        evaluations.log += [(1, (Exhausted("k.py:3:4"),)), (1, (Reach("k.py:6:4"),))]
    evaluations.flush()
    evaluations.close()
    paid, unpaid = (("k.py:4:8", (True,)),), (("k.py:4:8", (False,)),)
    assert evaluations.ways == {
        "k.py:1:0": {
            (("k.py:3:4", ("2+ items",), frozenset({paid, unpaid})), ("k.py:6:4",)): 1,
            (("k.py:3:4", ("1 item",), frozenset({paid})), ("k.py:6:4",)): 1,
            (("k.py:3:4", ("0 items",), frozenset()), ("k.py:6:4",)): 1,
        },
        "k.py:3:4": {(("k.py:4:8", (True,)),): 3, (("k.py:4:8", (False,)),): 1},
    }


FIRST_LATE = (
    "def first_late(orders):\n"
    "    for order in orders:\n"
    "        if order.late:\n"
    "            return order\n"
    "    return None\n"
)

# Where each of FIRST_LATE's rows runs: the loops holding it, outermost
# first.
FIRST_LATE_LOOPS = {"k.py:2:4": (), "k.py:3:8": ("k.py:2:4",), "k.py:4:12": ("k.py:2:4",), "k.py:5:4": ()}


def test_3c9e510e():
    """Example: first_late of a prompt order then a late one, its return
    inside the for; then first_late of 1 prompt order
    A loop left by a return, no Exhausted seen, ends with its call: its
    last pass is counted, and the call's way holds it."""
    shape = _shape(FIRST_LATE, "k.py:3:8")
    evaluations = Evaluations()
    evaluations.loops.update(FIRST_LATE_LOOPS)
    _run(
        evaluations,
        (2, (Enter("k.py:1:0"),)),
        (2, (Pass("k.py:2:4"),)),
        (2, (Outcome(shape, 0, False),)),
        (2, (Pass("k.py:2:4"),)),
        (2, (Outcome(shape, 0, True),)),
        (2, (Reach("k.py:4:12"),)),
        (2, (Enter("k.py:1:0"),)),
        (2, (Pass("k.py:2:4"),)),
        (2, (Outcome(shape, 0, False),)),
        (2, (Exhausted("k.py:2:4"),)),
        (2, (Reach("k.py:5:4"),)),
    )
    evaluations.close()
    prompt, late = (("k.py:3:8", (False,)),), (("k.py:3:8", (True,)), ("k.py:4:12",))
    assert evaluations.ways == {
        "k.py:1:0": {
            (("k.py:2:4", ("2+ items",), frozenset({prompt, late})),): 1,
            (("k.py:2:4", ("1 item",), frozenset({prompt})), ("k.py:5:4",)): 1,
        },
        "k.py:2:4": {
            (("k.py:3:8", (False,)),): 2,
            (("k.py:3:8", (True,)), ("k.py:4:12",)): 1,
        },
    }


AUDIT = (
    "def audit(orders, refunds):\n"
    "    for order in orders:\n"
    "        if order.late:\n"
    "            break\n"
    "    for refund in refunds:\n"
    "        if refund.big:\n"
    "            return refund\n"
)


def test_3c9e5110():
    """Example: audit of a late order, its first for left by a break, then
    of a small refund
    A pass of a loop after it closes the loop before it, though no row
    outside both ran between them: each holds its own pass's way."""
    late, big = _shape(AUDIT, "k.py:3:8"), _shape(AUDIT, "k.py:6:8")
    evaluations = Evaluations()
    evaluations.loops.update({"k.py:2:4": (), "k.py:3:8": ("k.py:2:4",), "k.py:5:4": (), "k.py:6:8": ("k.py:5:4",)})
    _run(
        evaluations,
        (4, (Enter("k.py:1:0"),)),
        (4, (Pass("k.py:2:4"),)),
        (4, (Outcome(late, 0, True),)),
        (4, (Pass("k.py:5:4"),)),
        (4, (Outcome(big, 0, False),)),
        (4, (Exhausted("k.py:5:4"),)),
    )
    evaluations.close()
    assert evaluations.ways == {
        "k.py:1:0": {
            (
                ("k.py:2:4", ("1 item",), frozenset({(("k.py:3:8", (True,)),)})),
                ("k.py:5:4", ("1 item",), frozenset({(("k.py:6:8", (False,)),)})),
            ): 1
        },
        "k.py:2:4": {(("k.py:3:8", (True,)),): 1},
        "k.py:5:4": {(("k.py:6:8", (False,)),): 1},
    }


SPANS = (
    "def within(inner, outer):\n"
    "    return outer[0] <= inner[0] and inner[1] <= outer[1]\n"
    "\n"
    "def span(parts):\n"
    "    return tuple(-1 if part is None else part for part in parts)\n"
)


def test_3c9e5111():
    """Example: within called, then span's generator expression run in a
    frame of the id within's frame had, as CPython reuses a finished
    frame's id
    The start of code that has no card, eg a generator expression, ends
    the way under way in its frame, and starts none: within's way holds
    only its own steps."""
    within, part = _shape(SPANS, "k.py:2:32"), _shape(SPANS, "k.py:5:20")
    evaluations = Evaluations()
    evaluations.loops.update({"k.py:2:32": (), "k.py:5:20": ()})
    _run(
        evaluations,
        (6, (Enter("k.py:1:0"),)),
        (6, (Outcome(within, 0, False),)),
        (6, (Unwalked(),)),
        (6, (Outcome(part, 0, True),)),
        (6, (Outcome(part, 0, False),)),
    )
    evaluations.close()
    assert evaluations.ways == {"k.py:1:0": {(("k.py:2:32", (False, None)),): 1}}


def test_3c9e510f():
    """Example: a loop like first_late's, its if's body a break, so its
    return None follows, given one late order
    A loop left by a break, no Exhausted seen, ends at the next row
    outside it, which follows it on the call's way."""
    shape = _shape(FIRST_LATE, "k.py:3:8")
    evaluations = Evaluations()
    evaluations.loops.update(FIRST_LATE_LOOPS)
    _run(
        evaluations,
        (3, (Enter("k.py:1:0"),)),
        (3, (Pass("k.py:2:4"),)),
        (3, (Outcome(shape, 0, True),)),
        (3, (Reach("k.py:5:4"),)),
    )
    evaluations.close()
    assert evaluations.ways == {
        "k.py:1:0": {(("k.py:2:4", ("1 item",), frozenset({(("k.py:3:8", (True,)),)})), ("k.py:5:4",)): 1},
        "k.py:2:4": {(("k.py:3:8", (True,)),): 1},
    }

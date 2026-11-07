from path_coverage import decision_paths, manifest
from path_coverage.evaluations import (
    Answer,
    Begin,
    End,
    Evaluations,
    Item,
    Matched,
    Opened,
    Outcome,
    Reach,
    Shape,
    Unmatched,
    Value,
)


def _shape(source, decision):
    """The Shape of the decision named decision in source, a file k.py, its
    possible paths as the manifest gives them."""
    condition = manifest.decisions(source, "k.py")[decision]
    return Shape(decision, decision_paths.possible(condition))


def _run(evaluations, *events):
    """Logs each of events, (frame, actions, truth), on evaluations, then
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
        (7, (Outcome(shape, 0, True),), None),
        (7, (Outcome(shape, 1, False),), None),
        (7, (Outcome(shape, 0, False),), None),
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
        (1, (Outcome(shape, 0, True),), None),
        (2, (Outcome(shape, 0, True),), None),
        (2, (Outcome(shape, 1, True),), None),
        (1, (Outcome(shape, 1, False),), None),
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
        (3, (Outcome(shape, 0, True),), None),
        (3, (Outcome(shape, 0, False),), None),
    )
    assert ran.decision_paths == {"k.py:2:24": {(False, None): 1}}
    assert ran.counts == {("k.py:2:24", 0): {"truthy": 1, "falsy": 1}}


def test_3c9e5104():
    """Example: return member and vip, member true, then the function
    returns a falsy value; then member false, and a return
    vip is tested by no branch, so the returned value gives its outcome; a
    value with no evaluation waiting for it is ignored."""
    shape = _shape("def f(member, vip):\n    return member and vip\n", "k.py:2:18")
    ran = _run(
        Evaluations(),
        (5, (Outcome(shape, 0, True),), None),
        (5, (Value(shape, False),), False),
        (5, (Outcome(shape, 0, False),), None),
        (5, (Value(shape, False),), False),
    )
    assert ran.decision_paths == {"k.py:2:18": {(True, False): 1, (False, None): 1}}
    assert ran.counts[("k.py:2:18", 1)] == {"truthy": 0, "falsy": 1}


def test_3c9e5105():
    """Example: return not (a and b), a true, and the function returns
    False
    The value returned is the decision's flipped, so b was true."""
    shape = _shape("def f(a, b):\n    return not (a and b)\n", "k.py:2:18")
    ran = _run(
        Evaluations(),
        (5, (Outcome(shape, 0, True),), None),
        (5, (Value(shape, True),), False),
    )
    assert ran.decision_paths == {"k.py:2:18": {(True, True): 1}}


def test_3c9e5106():
    """Example: return a and True, a true; and return True and a, a false
    A leaf whose form fixes its outcome, and that no branch tests, takes
    that outcome when it is reached, first or last."""
    last = _shape("def f(a):\n    return a and True\n", "k.py:2:13")
    last.fixed = {1: True}
    first = _shape("def g(a):\n    return True and a\n", "k.py:2:16")
    first.fixed = {0: True}
    ran = _run(
        Evaluations(),
        (5, (Outcome(last, 0, True),), None),
        (6, (Outcome(first, 1, False),), None),
    )
    assert ran.decision_paths == {
        "k.py:2:13": {(True, True): 1},
        "k.py:2:16": {(True, False): 1},
    }
    assert ran.counts[("k.py:2:13", 1)] == {"truthy": 1, "falsy": 0}
    assert ran.counts[("k.py:2:16", 0)] == {"truthy": 1, "falsy": 0}


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
        (8, (Matched(shape, 2, (0, 1)),), None),
        (8, (Outcome(shape, 3, False),), None),
        (8, (Matched(shape, 4, (0, 1, 2)),), None),
        (8, (Matched(shape, 0, ()),), None),
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
        (9, (Opened(shape),), None),
        (9, (Unmatched(shape, (0, 2)),), None),
        (9, (Opened(shape),), None),
        (9, (Matched(shape, 0, ()),), None),
        (9, (Outcome(shape, 1, False),), None),
        (9, (Unmatched(shape, (0, 2)),), None),
        (9, (Opened(shape),), None),
        (9, (Matched(shape, 2, (0,)),), None),
        (9, (Unmatched(shape, (0, 2)),), None),
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
        (4, (Begin(shape),), None),
        (4, (Item(shape),), None),
        (4, (Answer(shape, False),), None),
        (4, (Item(shape),), None),
        (4, (Answer(shape, True), End(shape)), None),
        (4, (Begin(shape),), None),
        (4, (End(shape),), None),
    )
    assert ran.decision_paths == {"k.py:2:11": {("2+ items", True): 1, ("0 items", None): 1}}
    assert ran.counts == {
        ("k.py:2:11", 0): {"truthy": 1, "falsy": 1},
        ("k.py:2:11", 1): {"truthy": 1, "falsy": 1},
    }


def test_3c9e510a():
    """Example: ship's return reached twice
    reached holds each statement's runs; one never reached has none."""
    ran = _run(Evaluations(), (2, (Reach("k.py:3:4"),), None), (2, (Reach("k.py:3:4"),), None))
    assert ran.reached == {"k.py:3:4": 2}


def test_3c9e510c():
    """Example: ok(id) and new(id), new's outcome seen in a frame whose ok
    was never seen, as when measuring started inside the evaluation
    No possible path agrees, so the evaluation is dropped, though new's
    outcome is counted."""
    shape = _shape(TRAILS, "k.py:2:24")
    ran = _run(Evaluations(), (6, (Outcome(shape, 1, True),), None))
    assert ran.decision_paths == {}
    assert ran.counts == {("k.py:2:24", 1): {"truthy": 1, "falsy": 0}}


def test_3c9e510b():
    """Example: Evaluations(limit=2), noting two events
    The log is rebuilt as soon as it holds limit events, so a long run
    never holds every event it saw."""
    shape = _shape(TRAILS, "k.py:2:24")
    evaluations = Evaluations(limit=2)
    evaluations.note(1, (Outcome(shape, 0, True),), None)
    assert evaluations.log == [(1, (Outcome(shape, 0, True),), None)]
    evaluations.note(1, (Outcome(shape, 1, True),), None)
    assert evaluations.log == []
    assert evaluations.decision_paths == {"k.py:2:24": {(True, True): 1}}

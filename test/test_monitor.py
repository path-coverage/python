import sys
import threading
from types import SimpleNamespace

from path_coverage import code_map, monitor, wrapped_leaves
from path_coverage.evaluations import Evaluations

DISABLE = sys.monitoring.DISABLE


def _measured(source, name, path="k.py"):
    """(the function named name, the Evaluations measuring it) once source,
    the file path, is instrumented and has run as a module."""
    evaluations = Evaluations()
    code, record = monitor.instrument(source, path, path, evaluations, monitor.compiled)
    namespace = {wrapped_leaves.NAME: record}
    exec(code, namespace)  # noqa: S102 - running the measured code is the point
    return namespace[name], evaluations


def _rebuilt(evaluations):
    """evaluations, every event logged so far rebuilt."""
    evaluations.flush()
    return evaluations


CAN_ATTEST = "def can_attest(user, flow):\n    return user.active and (user.admin or flow.public)\n"


def test_d86a1f01():
    """Example: user.active and (user.admin or flow.public), with active,
    not admin, and a public flow
    Each leaf a branch tests gives its outcome; flow.public, the last
    operand, which none tests, the call around it. The value is
    unchanged."""
    can_attest, evaluations = _measured(CAN_ATTEST, "can_attest", "src/model/flow.py")
    assert can_attest(SimpleNamespace(active=True, admin=False), SimpleNamespace(public="yes")) == "yes"
    assert _rebuilt(evaluations).decision_paths == {"src/model/flow.py:2:23": {(True, False, True): 1}}


def test_d86a1f02():
    """Example: the same condition with an inactive user
    The condition short-circuits after its first leaf, so the leaves it
    skips are never counted, and stay None on its path."""
    can_attest, evaluations = _measured(CAN_ATTEST, "can_attest", "src/model/flow.py")
    assert can_attest(SimpleNamespace(active=False, admin=True), None) is False
    assert _rebuilt(evaluations).decision_paths == {"src/model/flow.py:2:23": {(False, None, None): 1}}
    assert list(evaluations.counts) == [("src/model/flow.py:2:23", 0)]


def test_d86a1f03():
    """Example: user.admin or flow.public if user.active else False, called
    twice
    The conditional expression is one decision: its predicate leaf 0, the
    then arm's `or` leaves 1 and 2. The values it returns are unchanged."""
    source = "def can_see(user, flow):\n    return user.admin or flow.public if user.active else False\n"
    can_see, evaluations = _measured(source, "can_see", "src/model/flow.py")
    flow = SimpleNamespace(public="yes")
    assert can_see(SimpleNamespace(active=True, admin=False), flow) == "yes"
    assert can_see(SimpleNamespace(active=False, admin=True), flow) is False
    assert _rebuilt(evaluations).decision_paths == {
        "src/model/flow.py:2:37": {(True, False, True): 1, (False, None, None): 1},
    }


def test_d86a1f04():
    """Example: if order.big and order.new: return 5 / elif order.vip:
    return 6 / return 7, called three ways
    The if's predicate, the whole and, is one leaf, and the and is a
    decision of its own. The elif is a decision of its own. An arm that
    returns still has its path counted."""
    source = (
        "def fee(order):\n"
        "    if order.big and order.new:\n"
        "        return 5\n"
        "    elif order.vip:\n"
        "        return 6\n"
        "    return 7\n"
    )
    fee, evaluations = _measured(source, "fee")
    orders = [(True, True, False), (False, False, True), (True, False, False)]
    assert [fee(SimpleNamespace(big=b, new=n, vip=v)) for b, n, v in orders] == [5, 6, 7]
    assert _rebuilt(evaluations).decision_paths == {
        "k.py:2:4": {(True,): 1, (False,): 2},
        "k.py:2:17": {(True, True): 1, (False, None): 1, (True, False): 1},
        "k.py:4:4": {(True,): 1, (False,): 1},
    }


def test_d86a1f05():
    """Example: [u.name for u in users if u.active and u.admin], over an
    admin, an inactive user and an active non-admin
    Each item's path is counted under the filter's if keyword, its test
    one leaf, the and a decision of its own. The names it keeps are
    unchanged."""
    source = "def admins(users):\n    return [u.name for u in users if u.active and u.admin]\n"
    admins, evaluations = _measured(source, "admins")
    users = [
        SimpleNamespace(name="ann", active=True, admin=True),
        SimpleNamespace(name="bob", active=False, admin=True),
        SimpleNamespace(name="cat", active=True, admin=False),
    ]
    assert admins(users) == ["ann"]
    assert _rebuilt(evaluations).decision_paths == {
        "k.py:2:34": {(True,): 1, (False,): 2},
        "k.py:2:46": {(True, True): 1, (False, None): 1, (True, False): 1},
    }


MATCH = (
    "def fee(order):\n"
    "    match order.kind:\n"
    '        case "gold" if order.big:\n'
    "            return 1\n"
    '        case "silver":\n'
    "            return 2\n"
)


def test_d86a1f06():
    """Example: match order.kind: case "gold" if order.big: return 1 /
    case "silver": return 2, for a big gold, a small gold, a silver and a
    bronze order
    A small gold order matches gold, fails its guard, then matches nothing;
    a bronze order matches nothing at all. The fees are unchanged."""
    fee, evaluations = _measured(MATCH, "fee")
    orders = [("gold", True), ("gold", False), ("silver", False), ("bronze", True)]
    assert [fee(SimpleNamespace(kind=kind, big=big)) for kind, big in orders] == [1, None, 2, None]
    assert _rebuilt(evaluations).decision_paths == {
        "k.py:2:4": {
            (True, True, None): 1,
            (True, False, False): 1,
            (False, None, True): 1,
            (False, None, False): 1,
        }
    }


def test_d86a1f07():
    """Example: the same match with case _ in place of case "silver", for a
    small gold order
    It is taken, so the path ends with its pattern matched."""
    fee, evaluations = _measured(MATCH.replace('case "silver"', "case _"), "fee")
    assert fee(SimpleNamespace(kind="gold", big=False)) == 2
    assert _rebuilt(evaluations).decision_paths == {"k.py:2:4": {(True, False, True): 1}}


def test_d86a1f08():
    """Example: the same match with case "silver" as kind in place of case
    "silver", for a bronze order
    A last case that names its match still matches only silver, so the
    bronze order's path, no case taken, is counted."""
    fee, evaluations = _measured(MATCH.replace('case "silver"', 'case "silver" as kind'), "fee")
    assert fee(SimpleNamespace(kind="bronze", big=True)) is None
    assert _rebuilt(evaluations).decision_paths == {"k.py:2:4": {(False, None, False): 1}}


def test_d86a1f09():
    """Example: a generator suspended inside an and, at its yield, then
    resumed in another thread
    The evaluation is kept by the generator's frame, wherever it resumes,
    so its path is counted: a true, and the value written to got, 5, true.
    The generator gives what it would unmeasured."""
    source = 'def ask(a):\n    got = a and (yield "asked")\n    yield got\n'
    ask, evaluations = _measured(source, "ask")
    asking = ask(True)
    assert next(asking) == "asked"
    answers = []
    thread = threading.Thread(target=lambda: answers.append(asking.send(5)))
    thread.start()
    thread.join(5)
    assert answers == [5]
    assert _rebuilt(evaluations).decision_paths == {"k.py:2:12": {(True, True): 1}}


LATE = "def late(orders):\n    return any(o.late for o in orders)\n"


def test_d86a1f0a():
    """Example: any(o.late for o in orders), for no orders, two on time,
    then one late
    Its items are counted, and each answer noted, the last one where any
    stopped. The values it returns are unchanged."""
    late, evaluations = _measured(LATE, "late")
    on_time, overdue = SimpleNamespace(late=False), SimpleNamespace(late=True)
    assert [late([]), late([on_time, on_time]), late([overdue])] == [False, False, True]
    assert _rebuilt(evaluations).decision_paths == {
        "k.py:2:11": {("0 items", None): 1, ("2+ items", False): 1, ("1 item", True): 1},
    }


def test_d86a1f0b():
    """Example: any(o.late for o in orders) in a module defining its own
    any, which counts late orders
    That any is not the builtin, so its call is no decision; only its own
    filter's paths are counted. It returns the module's own answer."""
    source = (
        "def any(answers):\n"
        "    return sum(1 for answer in answers if answer)\n"
        "\n"
        "def late(orders):\n"
        "    return any(o.late for o in orders)\n"
    )
    late, evaluations = _measured(source, "late")
    assert late([SimpleNamespace(late=True), SimpleNamespace(late=True)]) == 2
    assert list(_rebuilt(evaluations).decision_paths) == ["k.py:2:39"]


def test_d86a1f0c():
    """Example: fee with a docstring, then if not rates: return 0, a
    write, if member: total -= 5 and a return, called three ways
    fee's entry is reached on each call, by its def's decision, and each
    return, a row that is no decision, by its name, an arm's too; the writes
    are no rows, so not reached. The early return skips the last return."""
    source = (
        "def fee(rates, member):\n"
        '    """The fee."""\n'
        "    if not rates:\n"
        "        return 0\n"
        "    total = 100\n"
        "    if member:\n"
        "        total -= 5\n"
        "    return total\n"
    )
    fee, evaluations = _measured(source, "fee")
    assert [fee([], True), fee([1], True), fee([1], False)] == [0, 95, 100]
    assert _rebuilt(evaluations).reached == {"k.py:1:0": 3, "k.py:4:8": 1, "k.py:8:4": 2}
    assert evaluations.decision_paths["k.py:6:4"] == {(True,): 1, (False,): 1}


def test_d86a1f0d():
    """Example: depth(1), whose and's second leaf calls depth(0), whose
    first leaf raises, caught back in the outer leaf
    The inner evaluation raised, so is never counted; the outer one, kept
    by its own frame, completes with the value depth returns, so its path
    is. The if in check is counted both ways."""
    source = (
        "def check(n):\n"
        "    if n == 0:\n"
        "        raise ValueError(n)\n"
        "    return True\n"
        "def attempt(call):\n"
        "    try:\n"
        "        return call()\n"
        "    except ValueError:\n"
        "        return False\n"
        "def depth(n):\n"
        "    return check(n) and attempt(lambda: depth(n - 1))\n"
    )
    depth, evaluations = _measured(source, "depth")
    assert depth(1) is False
    assert _rebuilt(evaluations).decision_paths == {
        "k.py:2:4": {(False,): 1, (True,): 1},
        "k.py:11:20": {(True, False): 1},
    }


def test_d86a1f0e():
    """Example: describe, a function whose body is its docstring alone,
    called once, and stub, whose body is ... alone
    Each call is counted at the function's entry."""
    source = 'def describe():\n    """Describes nothing."""\ndef stub():\n    ...\n'
    describe, evaluations = _measured(source, "describe")
    describe()
    describe.__globals__["stub"]()
    assert _rebuilt(evaluations).reached == {"k.py:1:0": 1, "k.py:3:0": 1}


def test_d86a1f0f():
    """Example: 1 if a and b else (2 if c else 3), called with a and b
    true, then with a false and c true
    The and that is the outer conditional expression's whole predicate is
    a decision of its own, as is the conditional expression in its else
    arm, each as the manifest names it."""
    source = "def pick(a, b, c):\n    return 1 if a and b else (2 if c else 3)\n"
    pick, evaluations = _measured(source, "pick")
    assert [pick(True, True, False), pick(False, True, True)] == [1, 2]
    assert _rebuilt(evaluations).decision_paths == {
        "k.py:2:13": {(True,): 1, (False,): 1},
        "k.py:2:18": {(True, True): 1, (False, None): 1},
        "k.py:2:32": {(True,): 1},
    }


def test_d86a1f10():
    """Example: FLAG = a and b, FLAG declared global, called with a true
    and b true
    b, the last operand, is tested by no branch, so the call around it
    counts its outcome."""
    source = "FLAG = None\n\ndef flag(a, b):\n    global FLAG\n    FLAG = a and b\n"
    flag, evaluations = _measured(source, "flag")
    flag(True, "yes")
    assert _rebuilt(evaluations).decision_paths == {"k.py:5:13": {(True, True): 1}}


def test_d86a1f15():
    """Example: t += len(f"{a or b}") and t += (0 < t < 3) or b, called
    twice
    An and/or's last operand, inside an f-string or a write, is counted by
    the call around it; a chained comparison whose value is an and/or's
    operand is counted once, by that and/or's test of it."""
    source = "def run(a, b, t):\n    t += len(f\"{a or b}\")\n    t += (0 < t < 3) or b\n    return t\n"
    run, evaluations = _measured(source, "run")
    assert [run(False, True, 0), run(True, False, 1)] == [5, 5]
    assert _rebuilt(evaluations).decision_paths == {
        "k.py:2:18": {(False, True): 1, (True, None): 1},
        "k.py:3:21": {(False, True): 1, (False, False): 1},
    }
    assert evaluations.reached == {"k.py:1:0": 2, "k.py:4:4": 2}


def test_d86a1f16():
    """Example: a match whose last case, 2 | _, only raises, after a case
    whose body is an if that raises, then a return; called with True, 5
    and 2
    Python copies the last case's raise to each of its alternatives, so it
    is counted at each, as is the case's match; the first case is counted
    once, its if's false branch landing back inside it."""
    source = (
        "def run(p0, p1, t):\n"
        "    match p0:\n"
        "        case True:\n"
        "            if p1: raise ValueError\n"
        "        case 2 | _:\n"
        "            raise ValueError\n"
        "    return t\n"
    )
    run, evaluations = _measured(source, "run")
    returned = []
    for p0 in (True, 5, 2):
        try:
            returned.append(run(p0, False, 1))
        except ValueError:
            returned.append("raised")
    assert returned == [1, "raised", "raised"]
    assert _rebuilt(evaluations).decision_paths == {"k.py:2:4": {(True, None): 1, (False, True): 2}, "k.py:4:12": {(False,): 1}}
    assert evaluations.reached == {"k.py:1:0": 3, "k.py:6:12": 2, "k.py:7:4": 1}


MEMBER = (
    "def member(member, vip):\n"
    "    ok = member and vip\n"
    "    return ok\n"
    "\n"
    "def fee(total):\n"
    "    return total\n"
)


def _codes(source):
    """(module code, {name: code of each function}) of source, the file
    k.py, once measured, logging on the Evaluations returned third."""
    module = compile(source, "k.py", "exec")
    evaluations = Evaluations()
    monitor.measure(module, code_map.Source(source, "k.py"), evaluations)
    functions = {const.co_name: const for const in module.co_consts if hasattr(const, "co_code")}
    return module, functions, evaluations


def test_d86a1f11():
    """Example: member and fee measured, then each branch and mark
    callback called as sys.monitoring calls it, from this frame
    An event that means something is logged by this frame's id; one that
    means nothing is disabled where it happens; a right branch that goes
    where its jump does not is ignored."""
    _, functions, evaluations = _codes(MEMBER)
    member, fee = functions["member"], functions["fee"]
    tables = code_map.tables(compile(MEMBER, "k.py", "exec"), code_map.Source(MEMBER, "k.py"))
    member_table, fee_table = (table for code, table in tables.items() if code.co_name in functions)
    jump = min(member_table.left)
    goes_to, _ = member_table.right[jump]
    assert [
        monitor._branched_left(member, jump, 0),
        monitor._branched_right(member, jump, goes_to),
        monitor._branched_right(member, jump, goes_to + 2),
        monitor._instruction(fee, min(fee_table.marks)),
        monitor._branched_left(member, 0, 0),
        monitor._branched_right(member, 0, 0),
        monitor._instruction(member, 0),
    ] == [None] * 4 + [DISABLE] * 3
    here = id(sys._getframe())
    assert [frame for frame, _ in evaluations.log] == [here, here, here]
    assert _rebuilt(evaluations).decision_paths == {"k.py:2:16": {(False, None): 1}}
    assert evaluations.reached == {"k.py:6:4": 1}


def test_d86a1f14():
    """Example: the line callback, called for a line of member's code at an
    instruction a mark is on, and at one none is on
    The line event is kept where a mark is, as Python 3.14 drops an
    instruction event at the start of a line once another tool, eg
    coverage.py, disables its own line event there; it is disabled
    anywhere else."""
    _, functions, _ = _codes(MEMBER)
    fee = functions["fee"]
    tables = code_map.tables(compile(MEMBER, "k.py", "exec"), code_map.Source(MEMBER, "k.py"))
    mark = min(next(table for code, table in tables.items() if code.co_name == "fee").marks)
    assert [monitor._kept(fee, mark), monitor._kept(fee, 0), monitor._line_started(fee, 6)] == [None, DISABLE, DISABLE]


def test_d86a1f13():
    """Example: the start callback, for member's code, and for the
    module's
    member's start counts its entry; the module's, no function's, is
    disabled, never seen again."""
    module, functions, evaluations = _codes(MEMBER)
    assert [monitor._started(functions["member"], 0), monitor._started(module, 0)] == [None, DISABLE]
    assert evaluations.reached == {"k.py:1:0": 1}

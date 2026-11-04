import ast
import sys
from types import SimpleNamespace

from path_coverage.recorder import Recorder
from path_coverage.rewriter import RECORDER_NAME, rewrite

SOURCE = (
    "def can_attest(user, flow):\n"
    "    return user.active and (user.admin or flow.public)\n"
)
SITE = "src/model/flow.py:2:11"


def _can_attest(recorder):
    """can_attest from SOURCE, rewritten and compiled, recording into
    recorder."""
    tree = rewrite(ast.parse(SOURCE), "src/model/flow.py", source=SOURCE)
    namespace = {RECORDER_NAME: recorder}
    exec(compile(tree, "src/model/flow.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    return namespace["can_attest"]


def test_7e40b301():
    """Example: user.active and (user.admin or flow.public), with active,
    not admin, and a public flow
    Each leaf is recorded under its site and its left-to-right index.
    The site is entered and left around the whole condition.
    So the evaluation's path is counted: [True, False, True].
    The condition still returns the same value, "yes"."""
    recorder = Recorder()
    can_attest = _can_attest(recorder)
    user = SimpleNamespace(active=True, admin=False)
    flow = SimpleNamespace(public="yes")
    assert can_attest(user, flow) == "yes"
    assert recorder.site_paths == {SITE: {(True, False, True): 1}}


def test_7e40b303():
    """Example: user.admin or flow.public if user.active else False
    The conditional expression is one site, entered and left around it.
    Its predicate is recorded as leaf 0, the then arm's `or` as 1 and 2.
    The values it returns are unchanged."""
    source = (
        "def can_see(user, flow):\n"
        "    return user.admin or flow.public if user.active else False\n"
    )
    recorder = Recorder()
    tree = rewrite(ast.parse(source), "src/model/flow.py", source=source)
    namespace = {RECORDER_NAME: recorder}
    exec(compile(tree, "src/model/flow.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    can_see = namespace["can_see"]
    flow = SimpleNamespace(public="yes")
    assert can_see(SimpleNamespace(active=True, admin=False), flow) == "yes"
    assert can_see(SimpleNamespace(active=False, admin=True), flow) is False
    assert recorder.site_paths == {
        "src/model/flow.py:2:11": {(True, False, True): 1, (False, None, None): 1},
    }


def test_7e40b304():
    """Example: if order.big and order.new: return 5 / elif order.vip:
    return 6 / return 7, called three ways
    Only each predicate is entered and left, not the whole statement.
    So an arm that returns still has its path counted.
    The elif is a site of its own."""
    source = (
        "def fee(order):\n"
        "    if order.big and order.new:\n"
        "        return 5\n"
        "    elif order.vip:\n"
        "        return 6\n"
        "    return 7\n"
    )
    recorder = Recorder()
    namespace = {RECORDER_NAME: recorder}
    tree = rewrite(ast.parse(source), "k.py", source=source)
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    fee = namespace["fee"]
    orders = [(True, True, False), (False, False, True), (True, False, False)]
    fees = [fee(SimpleNamespace(big=b, new=n, vip=v)) for b, n, v in orders]
    assert fees == [5, 6, 7]
    assert recorder.site_paths == {
        "k.py:2:4": {(True, True): 1, (False, None): 1, (True, False): 1},
        "k.py:4:4": {(True,): 1, (False,): 1},
    }


def test_7e40b307():
    """Example: [u.name for u in users if u.active and u.admin], over an
    admin, an inactive user and an active non-admin
    The filter is entered and left around its test, once per item.
    So each item's path is counted under the filter's if keyword.
    The names it keeps are unchanged."""
    source = "def admins(users):\n    return [u.name for u in users if u.active and u.admin]\n"
    recorder = Recorder()
    namespace = {RECORDER_NAME: recorder}
    tree = rewrite(ast.parse(source), "k.py", source=source)
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    users = [
        SimpleNamespace(name="ann", active=True, admin=True),
        SimpleNamespace(name="bob", active=False, admin=True),
        SimpleNamespace(name="cat", active=True, admin=False),
    ]
    assert namespace["admins"](users) == ["ann"]
    assert recorder.site_paths == {
        "k.py:2:34": {(True, True): 1, (False, None): 1, (True, False): 1},
    }


MATCH = (
    "def fee(order):\n"
    "    match order.kind:\n"
    '        case "gold" if order.big:\n'
    "            return 1\n"
    '        case "silver":\n'
    "            return 2\n"
)


def _fee(source, recorder):
    """fee from source, rewritten and compiled, recording into recorder."""
    namespace = {RECORDER_NAME: recorder}
    tree = rewrite(ast.parse(source), "k.py", source=source)
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    return namespace["fee"]


def test_7e40b308():
    """Example: match order.kind: case "gold" if order.big: return 1 /
    case "silver": return 2, for a big gold, a small gold, a silver and a
    bronze order
    Each evaluation's path is counted under the match's keyword.
    A small gold order matches gold, fails its guard, then matches nothing.
    A bronze order matches nothing at all.
    The fees are unchanged, None where no case is taken."""
    recorder = Recorder()
    fee = _fee(MATCH, recorder)
    orders = [("gold", True), ("gold", False), ("silver", False), ("bronze", True)]
    fees = [fee(SimpleNamespace(kind=kind, big=big)) for kind, big in orders]
    assert fees == [1, None, 2, None]
    assert recorder.site_paths == {
        "k.py:2:4": {
            (True, True, None): 1,
            (True, False, False): 1,
            (False, None, True): 1,
            (False, None, False): 1,
        }
    }


def test_7e40b309():
    """Example: the same match with case _ in place of case "silver", for a
    small gold order
    The _ case must stay last, so nothing is added after it.
    It is taken, so the path ends with its pattern matched."""
    recorder = Recorder()
    fee = _fee(MATCH.replace('case "silver"', "case _"), recorder)
    assert fee(SimpleNamespace(kind="gold", big=False)) == 2
    assert recorder.site_paths == {"k.py:2:4": {(True, False, True): 1}}


def test_7e40b30a():
    """Example: the gold and silver match, for a big gold, a small gold, a
    silver and a bronze order
    The rewritten fee runs exactly the lines the original does.
    So the case it adds, and its enter, add no line to line coverage."""
    for kind, big in [("gold", True), ("gold", False), ("silver", False), ("bronze", True)]:
        order = SimpleNamespace(kind=kind, big=big)
        assert _lines_run(MATCH, True, order) == _lines_run(MATCH, False, order)


def _late(source, recorder):
    """late from source, rewritten and compiled, recording into recorder."""
    namespace = {RECORDER_NAME: recorder}
    tree = rewrite(ast.parse(source), "k.py", source=source)
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    return namespace["late"]


def test_7e40b30b():
    """Example: any(o.late for o in orders), for no orders, two on time,
    then one late
    The call is entered and left around it, its items counted.
    Each answer is noted, the last one where any stopped.
    The values it returns are unchanged."""
    recorder = Recorder()
    late = _late("def late(orders):\n    return any(o.late for o in orders)\n", recorder)
    on_time, overdue = SimpleNamespace(late=False), SimpleNamespace(late=True)
    assert [late([]), late([on_time, on_time]), late([overdue])] == [False, False, True]
    assert recorder.site_paths == {
        "k.py:2:11": {("0 items", None): 1, ("2+ items", False): 1, ("1 item", True): 1},
    }


def test_7e40b30c():
    """Example: any(o.late for o in orders) in a module defining its own
    any, which counts late orders
    That any may not be the builtin, so its call is left alone.
    Only its own filter's paths are recorded.
    It returns the module's own answer."""
    source = (
        "def any(answers):\n"
        "    return sum(1 for answer in answers if answer)\n"
        "\n"
        "def late(orders):\n"
        "    return any(o.late for o in orders)\n"
    )
    recorder = Recorder()
    late = _late(source, recorder)
    orders = [SimpleNamespace(late=True), SimpleNamespace(late=True)]
    assert late(orders) == 2
    assert list(recorder.site_paths) == ["k.py:2:39"]


def test_7e40b305():
    """Example: fee with a docstring, then if not rates: return 0 and
    if member: total -= 5, called three ways, measuring methods
    Each call's path starts just before the first decision, after the
    docstring, which stays the docstring.
    Each decision's outcome is noted, outside its site's leave.
    The early return ends its path at [True].
    The fees are unchanged."""
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
    recorder = Recorder()
    namespace = {RECORDER_NAME: recorder}
    tree = rewrite(ast.parse(source), "k.py", source=source, methods=True)
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    fee = namespace["fee"]
    assert [fee([], True), fee([1], True), fee([1], False)] == [0, 95, 100]
    assert fee.__doc__ == "The fee."
    assert recorder.paths == {"k.py:1:0": {(True,): 1, (False, True): 1, (False, False): 1}}
    assert recorder.site_paths["k.py:6:4"] == {(True,): 1, (False,): 1}


def _lines_run(source, rewritten, *args):
    """The (function name, line) pairs a trace sees run when fee from source,
    rewritten measuring methods or not, is called with args."""
    tree = ast.parse(source)
    if rewritten:
        tree = rewrite(tree, "k.py", source=source, methods=True)
    namespace = {RECORDER_NAME: Recorder()}
    exec(compile(tree, "k.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    seen = set()

    def trace(frame, event, _arg):
        """Notes each line event of code compiled from k.py."""
        if frame.f_code.co_filename == "k.py" and event == "line":
            seen.add((frame.f_code.co_name, frame.f_lineno))
        return trace

    sys.settrace(trace)
    try:
        namespace["fee"](*args)
    except ValueError:
        pass
    finally:
        sys.settrace(None)
    return seen


def test_7e40b306():
    """Example: fee whose first decision raises in its then arm, called
    so that arm never runs, measuring methods
    The rewritten fee runs exactly the lines the original does.
    So line coverage is the same with path coverage on as off; the raise
    line in particular is not reported as run."""
    source = (
        "def fee(rates, member):\n"
        "    if not rates:\n"
        '        raise ValueError("no rates")\n'
        "    total = 100\n"
        "    if member:\n"
        "        total -= 5\n"
        "    return total\n"
    )
    for args in [([1], False), ([1], True), ([], True)]:
        assert _lines_run(source, True, *args) == _lines_run(source, False, *args)


def test_7e40b302():
    """Example: the same condition with an inactive user
    The condition short-circuits after its first leaf.
    So the leaves it skips are never recorded, and stay None on its path."""
    recorder = Recorder()
    can_attest = _can_attest(recorder)
    user = SimpleNamespace(active=False, admin=True)
    assert can_attest(user, None) is False
    assert recorder.site_paths == {SITE: {(False, None, None): 1}}
    assert list(recorder.counts) == [(SITE, 0)]

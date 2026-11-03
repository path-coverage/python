import ast
from types import SimpleNamespace

from condition_coverage.rewriter import RECORD_NAME, rewrite

SOURCE = (
    "def can_attest(user, flow):\n"
    "    return user.active and (user.admin or flow.public)\n"
)


def _can_attest(recorded):
    """can_attest from SOURCE, rewritten and compiled, with each record call
    appended to recorded."""

    def record(site, index, value):
        """Notes the call and returns value, as the real recorder does."""
        recorded.append((site, index, value))
        return value

    tree = rewrite(ast.parse(SOURCE), "src/model/flow.py")
    namespace = {RECORD_NAME: record}
    exec(compile(tree, "src/model/flow.py", "exec"), namespace)  # noqa: S102 - running rewritten code is the point
    return namespace["can_attest"]


def test_7e40b301():
    """Each leaf is recorded under its site and its left-to-right index, and
    the condition still short-circuits and returns the same value."""
    recorded = []
    can_attest = _can_attest(recorded)
    user = SimpleNamespace(active=True, admin=False)
    flow = SimpleNamespace(public="yes")
    assert can_attest(user, flow) == "yes"
    assert recorded == [
        ("src/model/flow.py:2:11", 0, True),
        ("src/model/flow.py:2:11", 1, False),
        ("src/model/flow.py:2:11", 2, "yes"),
    ]


def test_7e40b302():
    """An operand skipped by short-circuiting is not recorded."""
    recorded = []
    can_attest = _can_attest(recorded)
    user = SimpleNamespace(active=False, admin=True)
    assert can_attest(user, None) is False
    assert recorded == [("src/model/flow.py:2:11", 0, False)]

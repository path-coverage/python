"""Runs the demo source tree under path coverage, as a test suite would,
writing the JSON reports to COVERAGE_DIR at exit."""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import path_coverage

HERE = Path(__file__).parent
path_coverage.start(
    root=HERE,
    cover=["source/*.py"],
    coverage_dir=Path(os.environ["COVERAGE_DIR"]),
    report=["gaps"],
)
sys.path.insert(0, str(HERE / "source"))

import fee  # noqa: E402 - imported once coverage has started, to be measured
import group  # noqa: E402
import kata  # noqa: E402
import shop  # noqa: E402
import team  # noqa: E402

# Every outcome of both operands: covered.
kata.is_id("Kp9sA2")
kata.is_id(42)
kata.is_id("Kp9")

# Over two lines; the kata is never finished: never false.
kata.is_runnable(SimpleNamespace(started=True, finished=False))
kata.is_runnable(SimpleNamespace(started=False, finished=False))

# Two conditions on one line, the second with gaps.
kata.pair_checks("Kp9sA2", "Kp9sA2")

# Every outcome of both operands: covered.
group.is_full(SimpleNamespace(size=64, open=True))
group.is_full(SimpleNamespace(size=64, open=False))
group.is_full(SimpleNamespace(size=1, open=True))

# A chain of three over two lines; no name is ever too long.
team.is_name("alice", [])
team.is_name("alice", ["alice"])
team.is_name("Al", [])

# A grouped and inside an or; no open invite is ever seen.
owner = SimpleNamespace(owner=True, editor=False, invite_open=False, active=True)
editor = SimpleNamespace(owner=False, editor=True, invite_open=False, active=True)
team.can_edit(owner)
team.can_edit(editor)

# A site inside a generator, inside an or site of its own.
team.is_led([owner])
team.is_led([])

# The shop: some choices made every way, some never.
alice = {"member": True, "banned": False, "spend": 2000, "invited": False}
bob = {"member": False, "banned": False, "spend": 0, "coupon": True}
shop.is_member(alice)
shop.is_member(bob)
# A banned member: is_member is now covered.
shop.is_member({"member": True, "banned": True})
gift = {"items": [{"price": 80}], "gift": True, "wrap": False}
pickup = {"items": [{"price": 20}], "pickup": True, "express": True}
shop.price(alice, gift)
shop.price(bob, pickup)
try:
    shop.price(bob, {"items": []})
except ValueError:
    pass  # An empty order fails, as it should.
shop.discounts([])
discount = shop.discounts([0.1, 0.2])
discount(100, 0.1)
# A zero rate, and a zero total: discount's and is covered.
discount(100, 0)
discount(0, 0.1)
items = [{"sale": True, "price": 5}, {"sale": False, "price": 20}]
shop.labels(items)
shop.on_sale(items)
shop.size({"items": []})
shop.size({"items": items})
shop.greeting({"name": "Ann"})
# No name, and a blank one: greeting is covered.
shop.greeting({})
shop.greeting({"name": " "})

# The fee: each if taken both ways, so every line and branch is covered,
# yet no member who has not paid is tried, nor a paying member with a
# small order.
fee.fee(SimpleNamespace(member=True), SimpleNamespace(paid=True, big=True))
fee.fee(SimpleNamespace(member=False), SimpleNamespace(paid=False, big=False))

"""A mock shop, written to show every shape of choice the report has to
draw: conditions and paths, inside and outside functions."""

import os

# A condition at the top level, outside any function.
VERBOSE = os.environ.get("VERBOSE", "") == "1" or "DEBUG" in os.environ

# An if at the top level, outside any function.
if VERBOSE and os.isatty(1):
    print("shop: verbose")


class Shop:
    """The shop's settings."""

    # A condition at the class's top level, outside any function.
    LIMIT = int(os.environ["LIMIT"]) if "LIMIT" in os.environ else 10


def is_member(user):
    """True for a member who is not banned."""
    return user.get("member") and not user.get("banned")


def is_vip(user):
    """True for a member who spends a lot, or was invited."""
    return is_member(user) and (user.get("spend", 0) > 1000 or user.get("invited"))


def price(user, order):
    """The price of order for user: a long function, its paths and
    conditions tightly mixed."""
    items = order["items"]
    if not items:
        raise ValueError("empty order")
    total = sum(item["price"] for item in items)
    if is_member(user) and total > 50:
        total -= 5
    if is_vip(user):
        total -= 10
    elif user.get("coupon") or order.get("coupon"):
        total -= 2
    shipping = 0 if total > 100 or order.get("pickup") else 7
    if not order.get("express"):
        shipping //= 2
    if order.get("gift") and (
        order.get("wrap") or user.get("member")
    ):
        total += 3
    else:
        total += 1 if order.get("gift") else 0
    if order.get("pickup"):
        return total
    return total + shipping


def discounts(rates):
    """A function that defines a function inside it, the discount off a
    total, None for no rates."""
    if not rates:
        return None

    def discount(total, rate):
        """The discount off total at rate, at most 20."""
        off = total * rate if rate > 0 and total > 0 else 0
        if off > 20:
            return 20
        return off

    return discount


def labels(items):
    """Choices inside a comprehension, which runs once for each item: a
    conditional expression whose else arm is another."""
    return [
        "bargain" if item["sale"] and item["price"] < 10 else "sale" if item["sale"] else "full price"
        for item in items
    ]


def on_sale(items):
    """The items on sale: a comprehension's filter."""
    return [item for item in items if item["sale"]]


def size(order):
    """A match of how many items an order has."""
    match len(order["items"]):
        case 0:
            return "empty"
        case 1 | 2:
            return "small"
        case count if count > 10:
            return "large"
        case _:
            return "medium"


def greeting(user):
    """A short function: one if with an else, so its paths are its
    branches."""
    if user.get("name") and user["name"].strip():
        return f"Hello {user['name']}"
    else:
        return "Hello"

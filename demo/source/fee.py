"""The fee for an order: 5 off for a member who has paid, and 10 off a big
order."""


def fee(user, order):
    """The fee user pays for order."""
    total = 100
    if user.member and order.paid:
        total -= 5
    if order.big:
        total -= 10
    return total

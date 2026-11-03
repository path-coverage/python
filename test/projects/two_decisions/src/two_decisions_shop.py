"""A covered module for the kernel tests: a function with two decisions."""


def fee(member, big):
    """The fee for one order."""
    total = 100
    if member:
        total -= 5
    if big:
        total -= 10
    return total

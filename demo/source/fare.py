"""A train fare, its ways many, two of them impossible."""


def fare(age, peak, weekend, return_trip, staff):
    """A fare in pence: staff travel free, children and seniors pay half,
    weekends are a tenth off, and a return is two singles less 200. The
    second staff check is dead: staff have already left."""
    if staff:
        return 0
    price = 1200 if peak else 800
    if staff:
        return price // 2
    if age < 16 or age >= 65:
        price //= 2
    if weekend:
        price = price * 9 // 10
    return price * 2 - 200 if return_trip else price

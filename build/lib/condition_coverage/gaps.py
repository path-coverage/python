"""The terminal worklist: one line per missing outcome, and nothing for a
site seen both ways."""


def lines(operands):
    """The gap lines of operands (as result.operands gives them), eg
    "k.py:2:4 operand 0 never false", in manifest order."""
    return [line for site, counts in operands.items() for line in _site_gaps(site, counts)]


def _site_gaps(site, operands):
    """One line for a site that never ran, else one per gap in its operands."""
    if all(_never_ran(counts) for counts in operands):
        return [f"{site} never reached"]
    return [
        f"{site} operand {index} {gap}"
        for index, counts in enumerate(operands)
        for gap in operand_gap(counts)
    ]


def operand_gap(counts):
    """The one outcome this operand is missing, if any; a fixed leaf, which
    can have one outcome only, needs only to run."""
    if _never_ran(counts):
        return ["never evaluated"]
    if counts.get("only"):
        return []
    if counts["truthy"] == 0:
        return ["never true"]
    if counts["falsy"] == 0:
        return ["never false"]
    return []


def _never_ran(counts):
    """True when the operand was never recorded either way."""
    return counts["truthy"] == 0 and counts["falsy"] == 0

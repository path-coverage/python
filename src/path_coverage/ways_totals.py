"""The terminal totals of a JSON report, read from its JSON alone, so a
person reads what an AI reading the same JSON finds: the ways covered,
and the functions with more paths than max paths allows."""

from .console_summary import figure


def failed(report):
    """Whether report, a JSON report as a dict, fails: a function in it has
    a path no test took, a path taken that was declared impossible, or
    more paths than its max_paths."""
    listed, over = _functions(report)
    return bool(over) or any(card["gaps"] or card["impossible_taken"] for card in listed)


def lines(report):
    """The totals lines of report, a JSON report as a dict: its listed
    functions' ways covered out of their ways, then how many functions
    have more paths than its max_paths, each such one failing."""
    listed, over = _functions(report)
    covered = sum(len(card["covered"]) for card in listed)
    ways = sum(card["ways"] for card in listed)
    return [f"Paths: {figure([covered, ways])}", f"Functions over --max-paths={report['max_paths']}: {len(over)}"]


def _functions(report):
    """(listed, over) of report's function cards: those listing their ways,
    and those with more paths than its max_paths, which list none. A top
    card, run by no call, has no taken ways, so is in neither."""
    functions = [card for card in report["cards"].values() if "taken" in card]
    return [card for card in functions if "covered" in card], [card for card in functions if "covered" not in card]

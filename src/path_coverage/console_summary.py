"""The summary reporter's lines: each total as coverage tools print theirs,
eg "Paths alone: 519 / 623 (83.31%)". With groups
configured each group is a heading, its own totals indented under it, and
there is no total over every group."""

from . import totals as path_totals
from .summary import matches, path_of


def lines(paths, flows=None, groups=None):
    """The summary lines of paths (as result.paths gives them) and, when
    flows, {def decision: [taken, size]}, are given, as they are when methods
    are measured, of flows; groups is {name: [glob, ...]}."""
    if not groups:
        return _totals_lines(totals(paths, flows))
    return grouped_lines(group_totals(paths, flows, groups))


def grouped_lines(named):
    """The lines of named, {group name: totals} as group_totals gives them
    and a JSON report's totals.groups holds them: each group a heading, its
    totals indented under it."""
    out = []
    for name, own in named.items():
        out.append(f"{name}:")
        out.extend(f"  {line}" for line in _totals_lines(own))
    return out


def totals(paths, flows):
    """{"alone": [taken, possible]} of paths, with "combined": [taken,
    possible] of flows when flows are given."""
    result = {"alone": path_totals.alone(paths)}
    if flows is not None:
        result["combined"] = path_totals.combined(flows)
    return result


def group_totals(paths, flows, groups):
    """{group name: totals} of each group's own decisions and flows alone."""
    return {
        name: totals(_own(paths, globs), None if flows is None else _own(flows, globs))
        for name, globs in groups.items()
    }


def _own(decisions, globs):
    """The entries of decisions, keyed by decision name, in a file matching any of
    globs."""
    return {decision: value for decision, value in decisions.items() if matches(path_of(decision), globs)}


def _totals_lines(named):
    """A line per total, eg "Paths combined: 1 / 4 (25.00%)"."""
    return [f"Paths {name}: {figure(pair)}" for name, pair in named.items()]


def figure(pair):
    """[taken, possible] as "taken / possible (percent)", its percent to two
    places, or - when no path is possible."""
    taken, possible = pair
    if possible == 0:
        return f"{taken} / {possible} (-)"
    return f"{taken} / {possible} ({100 * taken / possible:.2f}%)"

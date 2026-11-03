"""The two coverage totals, each [taken, possible] paths over every covered
file. They count the very paths the gap lines list as never taken."""

from .path_gaps import possible


def decisions(paths):
    """Paths within each decision: paths, as result.paths gives them, lists
    every possible path of each site with its count; one with a count above
    zero was taken."""
    every = [each for site_paths in paths.values() for each in site_paths]
    return [sum(1 for each in every if each["count"] > 0), len(every)]


def methods(found, taken):
    """Paths across each function's decisions: found, as
    path_manifest.methods gives them, each with every path through its
    decisions; taken, as the recorder counts them, holds the ones taken."""
    seen = possible_count = 0
    for site, method in found.items():
        every = possible(method.decisions)
        possible_count += len(every)
        seen += sum(1 for path in every if tuple(path) in taken.get(site, {}))
    return [seen, possible_count]

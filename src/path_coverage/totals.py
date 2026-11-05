"""The two coverage totals, each [taken, possible] paths over every covered
file."""


def decisions(paths):
    """Paths within each decision: paths, as result.paths gives them, lists
    every possible path of each site with its count; one with a count above
    zero was taken."""
    every = [each for site_paths in paths.values() for each in site_paths]
    return [sum(1 for each in every if each["count"] > 0), len(every)]


def methods(cards):
    """Paths within each function: cards is {def site: [taken, size]}, each
    function's card's paths taken of its size. Example: cards [4, 6] and
    [17, 21] give [21, 27]."""
    return [sum(taken for taken, _ in cards.values()), sum(size for _, size in cards.values())]

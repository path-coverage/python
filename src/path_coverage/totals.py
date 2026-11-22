"""The two coverage totals, each [taken, possible] paths over every covered
file."""


def alone(paths):
    """Paths alone, each decision's counted on its own: paths, as
    result.paths gives them, lists every possible path of each decision with its
    count; one with a count above zero was taken."""
    every = [each for decision_paths in paths.values() for each in decision_paths]
    return [sum(1 for each in every if each["count"] > 0), len(every)]


def combined(flows):
    """Paths combined through each function: flows is {def decision: [taken,
    size]}, each function's flow's paths taken of its size, its rows' paths
    added up. Example: flows [4, 6] and [17, 21] give [21, 27]."""
    return [sum(taken for taken, _ in flows.values()), sum(size for _, size in flows.values())]

"""The terminal worklist for function paths: one line per path a function
never took, and nothing for a function that took them all."""

OUTCOMES = (True, False)


def lines(methods, paths):
    """The gap lines of methods (as path_manifest.methods gives them) for the
    paths the recorder counted, eg
    "k.py:1:0 fee path never taken: line 3 true, line 6 true"."""
    return [
        f"{site} {method.name} path never taken: {_steps(method, path)}"
        for site, method in methods.items()
        for path in possible(method.decisions)
        if tuple(path) not in paths.get(site, {})
    ]


def possible(decisions):
    """Every path through decisions, True before False at each: one taking a
    decision's exits outcome ends there."""
    if not decisions:
        return [[]]
    first, *rest = decisions
    return [
        path
        for outcome in OUTCOMES
        for path in (
            [[outcome]]
            if outcome == first.exits
            else [[outcome, *tail] for tail in possible(rest)]
        )
    ]


def _steps(method, path):
    """path's outcomes, each named by its decision's line."""
    return ", ".join(
        f"line {method.decisions[index].line} {str(outcome).lower()}"
        for index, outcome in enumerate(path)
    )

"""The paths an evaluation of a decision can take, worked out from its condition
alone: the outcome of each leaf, in leaf order, None for a leaf that
evaluation never reaches."""

from . import kinds
from .manifest import Condition


def possible(condition):
    """Every possible path through condition, True before False, eg
    [[True, True], [True, False], [False, None]] for `a and b`."""
    return [
        [outcomes.get(id(leaf)) for leaf in condition.leaves()]
        for outcomes, _value in walk(condition)
    ]


def cases_picked(condition):
    """The index of the case each possible path of condition, a match's,
    picks, in possible's order; None for a path picking none. A path picks
    the case whose last leaf, its pattern's or its guard's, is the last
    leaf it reaches, and true there. Example: [0, 1, None] for case 0,
    then case n if n > 9, its paths [[True, None, None], [False, True,
    True], [False, True, False]]."""
    lasts = []
    for operand in condition.operands:
        first = lasts[-1] + 1 if lasts else 0
        lasts.append(first + (len(operand.leaves()) if isinstance(operand, Condition) else 1) - 1)
    picked = []
    for path in possible(condition):
        reached = max(index for index, outcome in enumerate(path) if outcome is not None)
        picked.append(lasts.index(reached) if path[reached] is True else None)
    return picked


def values(condition):
    """The value of condition as a whole on each of its possible paths, in
    possible's order, None where its kind notes none, eg [False, True,
    False, True, False] for any of a generator."""
    return [value for _outcomes, value in walk(condition)]


def walk(node):
    """[({id(leaf): outcome}, value), ...] for each way node can be
    evaluated, value being the outcome of node as a whole: a leaf's own,
    a condition's as its kind works them out."""
    if not isinstance(node, Condition):
        return _leaf(node)
    return kinds.of(node.operator).ways(node)


def _leaf(leaf):
    """The ways a leaf can be evaluated: True, then False, or its one
    outcome alone when its form fixes it."""
    outcomes = [leaf.only == "truthy"] if leaf.only else [True, False]
    return [({id(leaf): outcome}, outcome) for outcome in outcomes]

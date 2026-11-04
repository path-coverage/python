"""The paths an evaluation of a site can take, worked out from its condition
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

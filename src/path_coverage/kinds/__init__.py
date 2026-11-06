"""The kinds of condition, each a class that knows, for a condition named by
one of its OPERATORS, the ways it can be evaluated and its value in each
column of its decision's tree."""

from .block import Block
from .case import Case
from .chain import Chain
from .choice import Choice

# Every kind, each named by its operators.
ALL = (Block(), Case(), Chain(), Choice())

# {operator: kind} for every operator of every kind.
BY_OPERATOR = {operator: kind for kind in ALL for operator in kind.OPERATORS}


def of(operator):
    """The kind of a condition named operator, eg the Chain for "and"."""
    return BY_OPERATOR[operator]


def names():
    """The names of the kinds measured, eg "chain" for Chain: a report's
    fingerprint, as runs measuring different kinds list a decision's paths
    differently."""
    return [type(kind).__name__.lower() for kind in ALL]

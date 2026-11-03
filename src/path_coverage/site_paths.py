"""The paths an evaluation of a site can take, worked out from its condition
alone: the outcome of each leaf, in leaf order, None for a leaf that
evaluation never reaches."""

from .manifest import Condition

# The outcome of an operand on which each operator goes on to its next
# operand; any other outcome ends the chain there.
CONTINUES_ON = {"and": True, "or": False}


def possible(condition):
    """Every possible path through condition, True before False, eg
    [[True, True], [True, False], [False, None]] for `a and b`."""
    return [
        [outcomes.get(id(leaf)) for leaf in condition.leaves()]
        for outcomes, _value in _walk(condition)
    ]


def _walk(node):
    """[({id(leaf): outcome}, value), ...] for each way node can be
    evaluated, value being the outcome of node as a whole."""
    if not isinstance(node, Condition):
        return _leaf(node)
    if node.operator in THEN_ON:
        return _choice(node)
    return _chain(node)


# The predicate outcome on which each choice takes its then arm.
THEN_ON = {"ternary": True, "if": True}


def _choice(node):
    """The ways a choice can be evaluated: each way of its predicate, then
    each way of the condition the arm it picks holds, if it holds one; an
    if with no else arm picks none. Its value is that of no choice, so is
    None."""
    predicate, then_arm, *rest = node.operands
    else_arm = rest[0] if rest else None
    ways = []
    for outcomes, value in _walk(predicate):
        arm = then_arm if value == THEN_ON[node.operator] else else_arm
        body = arm.body if arm else None
        if body is None:
            ways.append((outcomes, None))
            continue
        ways.extend(({**outcomes, **more}, None) for more, _ in _walk(body))
    return ways


def _chain(node):
    """The ways a chain of one operator can be evaluated: each way of its
    first operand, going on to the next while each outcome is the one its
    operator goes on with."""
    first, *rest = node.operands
    goes_on = CONTINUES_ON[node.operator]
    ways = _walk(first)
    for operand in rest:
        ways = [
            way
            for outcomes, value in ways
            for way in (
                [({**outcomes, **more}, after) for more, after in _walk(operand)]
                if value == goes_on
                else [(outcomes, value)]
            )
        ]
    return ways


def _leaf(leaf):
    """The ways a leaf can be evaluated: True, then False, or its one
    outcome alone when its form fixes it."""
    outcomes = [leaf.only == "truthy"] if leaf.only else [True, False]
    return [({id(leaf): outcome}, outcome) for outcome in outcomes]

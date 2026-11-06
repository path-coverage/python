"""The tree shown under a decision's line on its file's page: a grid whose
columns are the decision's paths, never taken first."""

from . import kinds
from .kinds.choice import THEN_ON
from .manifest import Arm, Condition
from .paths_report import segment


def tree_of(source, condition, paths):
    """{"operator", "counts", "cells", "operands"} for one decision, from its
    paths, [{"path", "count"}, ...]. counts are the columns' counts. Every
    node has cells, one per column: a leaf {"text", "cells"} its outcome,
    None where unreached; a condition {"operator", "cells", "operands"} its
    value; an arm {"arm", "text", "cells", "body"} whether the column took
    it, body being its condition's tree, None for a plain arm."""
    columns = [
        taken
        for _, taken in sorted(
            enumerate(paths), key=lambda item: (0 if item[1]["count"] == 0 else 1, item[0])
        )
    ]
    outcomes = [taken["path"] for taken in columns]
    tree = _node(source, condition, outcomes, iter(range(len(condition.leaves()))))
    return {**tree, "counts": [taken["count"] for taken in columns]}


def node(source, condition, outcomes):
    """The tree of condition, as tree_of builds it, over the paths of
    outcomes, each a path's leaf outcomes, eg decision_paths.possible's."""
    return _node(source, condition, outcomes, iter(range(len(condition.leaves()))))


def _node(source, condition, outcomes, leaves):
    """The tree of condition, each leaf taking the next index of leaves, so
    leaves pair with path entries left to right: its operands first, then
    its arms, as each arm's cells follow from the predicate's."""
    operands = [
        _node(source, operand, outcomes, leaves)
        if isinstance(operand, Condition)
        else operand
        if isinstance(operand, Arm)
        else _leaf(source, operand, outcomes, next(leaves))
        for operand in condition.operands
    ]
    predicate = operands[0]
    operands = [
        _arm(
            source,
            operand,
            predicate["cells"],
            THEN_ON[condition.operator],
            outcomes,
            leaves,
        )
        if isinstance(operand, Arm)
        else operand
        for operand in operands
    ]
    return {
        "operator": condition.operator,
        "cells": kinds.of(condition.operator).value(condition.operator, operands),
        "operands": operands,
    }


def _arm(source, arm, decided, then_on, outcomes, leaves):
    """One arm of a choice: its text, an if's arm's its statements, None for
    an arm of no code, whether each column took it, from the predicate's
    cells and the outcome on which its choice takes its then arm, and the
    tree of its condition."""
    picked = then_on if arm.kind == "then" else not then_on
    body = _node(source, arm.body, outcomes, leaves) if arm.body else None
    written = arm.at or arm.extent
    return {
        "arm": arm.kind,
        "text": segment(source, *written) if written else None,
        "cells": [outcome == picked for outcome in decided],
        "body": body,
    }


def _leaf(source, leaf, outcomes, index):
    """One leaf's text and its outcome in each column."""
    text = segment(source, leaf.line, leaf.col, leaf.end_line, leaf.end_col)
    return {"text": text, "cells": [path[index] for path in outcomes]}

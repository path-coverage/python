"""How the rows of each card nest: for each row, the decision it runs inside,
the arm of that decision it is in, and the paths of that decision on which it runs,
so a reader can tell which paths reach a row."""

import ast
from dataclasses import dataclass

from . import method_statements, decision_paths, decision_tree
from .manifest import Arm, Condition
from .manifest import decisions as find_decisions

# The place of a row inside no other row's decision.
TOP = {"parent": None, "in": None, "on": None, "leaf": None, "gives": None}


@dataclass(frozen=True)
class Region:
    """Part of a decision's code that a row can be inside: an arm of code, or a
    leaf. owner is the key of the decision's row; begin and end its bytes, end
    exclusive; arm its arm's kind, None for a leaf; on the indices of the
    decision's possible paths that run it; leaf a leaf's index among the decision's
    leaves, None for an arm."""

    owner: str
    begin: int
    end: int
    arm: str | None
    on: tuple
    leaf: int | None


def of(source, path, decisions=None):
    """{def decision: {"line:col": place}} for each function in source, as
    nested places its rows. Example: def f(a): if a: x = 1 gives the write
    the if as its parent, in its then arm, on its path 0."""
    decisions = find_decisions(source, path) if decisions is None else decisions
    return {
        decision: nested(source, decisions, rows) for decision, rows in method_statements.of(source, path).items()
    }


def nested(source, decisions, rows):
    """{"line:col": place} of each of rows, a card's, decisions being {decision:
    Condition}: each placed in the innermost region of another row's decision
    holding all of its own decision's code, or, for a row that is no decision, where
    it starts. A place is {"parent": the "line:col" of that decision, "in": its
    arm's kind, "on": the indices of that decision's possible paths, as
    decision_paths.possible orders them, that run the row, "leaf": the index of
    the leaf holding it, "gives": None}; TOP for a row in no region."""
    starts = _line_starts(source)
    regions = [
        region
        for row in rows
        if row.decision
        for region in _regions(source, starts, key_of(row), decisions[row.decision])
    ]
    places = {}
    for row in rows:
        at = starts[row.line - 1] + row.column
        decision = decisions[row.decision] if row.decision else None
        span = _span(starts, decision.extent) if decision else (at, at + 1)
        places[key_of(row)] = _placed(key_of(row), span, regions, decision)
    return places


def _placed(key, span, regions, decision):
    """The place of the row keyed key, its code the bytes span, decision its
    Condition, None for a row that is no decision: in the decision owning the
    smallest region of another row holding span; TOP for none."""
    holding = [
        region
        for region in regions
        if region.owner != key and region.begin <= span[0] and span[1] <= region.end
    ]
    if not holding:
        return dict(TOP)
    owner = _smallest(holding).owner
    own = [region for region in holding if region.owner == owner]
    arm = _smallest([region for region in own if region.arm])
    on = sorted(set.intersection(*(set(region.on) for region in own)))
    leaf = _smallest([region for region in own if region.arm is None]) if decision else None
    whole = leaf is not None and (leaf.begin, leaf.end) == span
    return {
        "parent": owner,
        "in": arm.arm if arm else None,
        "on": on,
        "leaf": leaf.leaf if leaf else None,
        "gives": decision_paths.values(decision) if whole else None,
    }


def _smallest(regions):
    """The region of regions with the fewest bytes; None for none."""
    return min(regions, key=lambda region: region.end - region.begin, default=None)


def _regions(source, starts, owner, condition):
    """The regions of condition, the decision of the row keyed owner: its
    arms', then its leaves'."""
    possible = decision_paths.possible(condition)
    node = decision_tree.node(source, condition, possible)
    return (
        _arm_regions(starts, owner, condition, node)
        + _case_regions(source, starts, owner, condition)
        + _leaf_regions(starts, owner, condition, possible)
    )


def _case_regions(source, starts, owner, condition):
    """The regions of the case bodies of condition, a match's; none for
    any other decision. A case's body runs on the paths that pick it, as
    decision_paths.cases_picked gives them."""
    if condition.operator != "match":
        return []
    line, col = condition.extent[:2]
    match = next(
        node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Match) and (node.lineno, node.col_offset) == (line, col)
    )
    picked = decision_paths.cases_picked(condition)
    regions = []
    for index, case in enumerate(match.cases):
        on = tuple(i for i, each in enumerate(picked) if each == index)
        body = (case.body[0].lineno, case.body[0].col_offset, case.body[-1].end_lineno, case.body[-1].end_col_offset)
        begin, end = _span(starts, body)
        regions.append(Region(owner, begin, end, "case", on, None))
    return regions


def _leaf_regions(starts, owner, condition, possible):
    """The regions of condition's leaves, in no arm, each run on the paths
    of possible with an outcome at its index."""
    regions = []
    for index, leaf in enumerate(condition.leaves()):
        on = tuple(i for i, path in enumerate(possible) if path[index] is not None)
        begin, end = _span(starts, (leaf.line, leaf.col, leaf.end_line, leaf.end_col))
        regions.append(Region(owner, begin, end, None, on, index))
    return regions


def _arm_regions(starts, owner, condition, node):
    """The regions of the arms in condition, node its tree: of its own
    arms, and of those of each condition nested in it, in an operand or in
    an arm's body."""
    regions = []
    for operand, operand_node in zip(condition.operands, node["operands"]):
        if isinstance(operand, Condition):
            regions += _arm_regions(starts, owner, operand, operand_node)
        elif isinstance(operand, Arm):
            regions += _arm_region(starts, owner, operand, operand_node)
    return regions


def _arm_region(starts, owner, arm, node):
    """The regions of arm, node its node: its own, named by its kind and
    run on the paths that take it, none for an arm of no code, which holds
    no row; then its body's."""
    body = _arm_regions(starts, owner, arm.body, node["body"]) if arm.body else []
    if arm.extent is None:
        return body
    on = tuple(i for i, took in enumerate(node["cells"]) if took is True)
    begin, end = _span(starts, arm.extent)
    return [Region(owner, begin, end, arm.kind, on, None), *body]


def key_of(row):
    """The "line:col" key of row, from its name."""
    return ":".join(row.name.split(":")[-2:])


def _line_starts(source):
    """The byte offset where each line of source starts, first line
    first."""
    starts = [0]
    for line in source.encode().splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _span(starts, extent):
    """(begin, end) bytes of extent, (line, col, end_line, end_col) as ast
    counts them, starts being _line_starts'."""
    line, col, end_line, end_col = extent
    return (starts[line - 1] + col, starts[end_line - 1] + end_col)

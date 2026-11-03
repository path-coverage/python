"""The tree shown under a site's line on its file's HTML page."""

from .gaps import operand_gap
from .manifest import Condition


def tree_of(source, condition, counts):
    """{operator, operands} for one site, a nested condition being an operand
    of the same shape. Each leaf is {text, truthy, falsy, gap}: its text cut
    from source, its counts, and its gap in the gaps report's words (None
    for none). counts pair with the leaves left to right."""
    lines = source.encode().splitlines(keepends=True)
    return _node(lines, condition, iter(counts))


def _node(lines, condition, counts):
    """The tree of condition, each leaf taking the next of counts."""
    return {
        "operator": condition.operator,
        "operands": [
            _node(lines, operand, counts)
            if isinstance(operand, Condition)
            else _leaf(lines, operand, next(counts))
            for operand in condition.operands
        ],
    }


def _leaf(lines, leaf, counts):
    """One leaf's text, counts and gap."""
    gaps = operand_gap(counts)
    return {
        "text": text_of(lines, leaf),
        "truthy": counts["truthy"],
        "falsy": counts["falsy"],
        "gap": gaps[0] if gaps else None,
    }


def text_of(lines, leaf):
    """The source text of leaf, given the source's lines as bytes; its
    columns are byte offsets."""
    if leaf.line == leaf.end_line:
        return lines[leaf.line - 1][leaf.col : leaf.end_col].decode()
    return (
        lines[leaf.line - 1][leaf.col :]
        + b"".join(lines[leaf.line : leaf.end_line - 1])
        + lines[leaf.end_line - 1][: leaf.end_col]
    ).decode()

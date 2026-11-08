"""The leaves of a function that read a stable name: a parameter of it
whose every use in the function is a leaf, the name itself or not the
name. Nothing else reads, writes or passes on such a name, and no call can
rebind a parameter as it can a global, so two of its leaves agree, and a
way giving it both outcomes is impossible."""

import ast


def of(function, leaves):
    """{leaf span: (name, flipped)} of those of leaves, Leaf spans as
    (line, col, end_line, end_col) in function, its def's node, that read
    a stable name, flipped for a not. Example: in def f(a): if not a: ...,
    the span of not a gives ("a", True)."""
    nodes = {_span(node): node for node in ast.walk(function) if hasattr(node, "end_col_offset")}
    reading = {span: _read(nodes.get(span)) for span in set(leaves)}
    reading = {span: read for span, read in reading.items() if read}
    uses = [node.id for node in ast.walk(function) if isinstance(node, ast.Name)]
    read_by_leaves = [name for name, _ in reading.values()]
    parameters = {each.arg for each in ast.walk(function.args) if isinstance(each, ast.arg)}
    return {
        span: read
        for span, read in reading.items()
        if read[0] in parameters and uses.count(read[0]) == read_by_leaves.count(read[0])
    }


def _read(node):
    """(name, flipped) of node when it is a name, or not a name; None for
    any other node."""
    if isinstance(node, ast.Name):
        return (node.id, False)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and isinstance(node.operand, ast.Name):
        return (node.operand.id, True)
    return None


def _span(node):
    """node's (line, col, end_line, end_col), as a Leaf has them."""
    return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)

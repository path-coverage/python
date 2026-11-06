"""Where in its source each part of a decision's tree is, as [line, col,
end_line, end_col], so a page can light the code a fold row stands for."""

import re

from .manifest import Arm, Condition


def located(source, condition, tree):
    """tree with an "at" of [line, col, end_line, end_col] on it and on
    each of its operands, columns counted in characters, so the page can
    mark them in the source: a condition's and an arm's from its extent, a
    leaf's from where it is written."""
    operands = []
    for operand, node in zip(condition.operands, tree["operands"]):
        if isinstance(operand, Condition):
            node = located(source, operand, node)
        elif isinstance(operand, Arm):
            body = located(source, operand.body, node["body"]) if operand.body else None
            written = operand.at or operand.extent
            node = {**node, "body": body, "at": position(source, *written) if written else None}
        else:
            node = {**node, "at": position(source, operand.line, operand.col, operand.end_line, operand.end_col)}
        operands.append(node)
    return {**tree, "at": position(source, *condition.extent), "operands": operands}


def else_at(source, condition):
    """[line, col, line, col] of the else keyword of condition, an if, in
    source, so hovering it can open its fold, as hovering its if does; None
    for any other condition, an if with no else, or one whose else arm is an
    elif, as an elif is a decision of its own."""
    arms = [operand for operand in condition.operands if isinstance(operand, Arm) and operand.kind == "else"]
    if condition.operator != "if" or not arms:
        return None
    line, col = arms[0].extent[:2]
    lines = source.encode().splitlines(keepends=True)
    before = b"".join(lines[: line - 1]) + lines[line - 1][:col]
    found = re.search(rb"\belse\s*:\s*\Z", before)
    if not found:
        return None
    else_line = before[: found.start()].count(b"\n") + 1
    else_col = found.start() - (before.rfind(b"\n", 0, found.start()) + 1)
    return position(source, else_line, else_col, else_line, else_col + 4)


def position(source, line, col, end_line, end_col):
    """[line, col, end_line, end_col] with the byte columns ast gives as
    character columns."""
    lines = source.encode().splitlines(keepends=True)
    return [line, len(lines[line - 1][:col].decode()), end_line, len(lines[end_line - 1][:end_col].decode())]

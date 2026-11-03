"""Finds, without running it, the decisions of each function in source whose
paths are to be counted: its top-level if statements, when it has two or
more. With fewer, a function's paths are its one decision's branches, which
its site already counts."""

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    """One if a function's path passes: its line, and exits, the outcome
    whose arm always leaves the function, ending the path there, or None
    when neither arm does."""

    line: int
    exits: bool | None = None


@dataclass(frozen=True)
class PathMethod:
    """A function whose calls each take one path through its decisions, in
    source order."""

    name: str
    decisions: tuple


def methods(source, path):
    """{def site: PathMethod} for each function (method or not) in source
    with two or more top-level ifs, named "path:line:col" of its def."""
    found = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        ifs = decision_ifs(node)
        if len(ifs) >= 2:
            found[f"{path}:{node.lineno}:{node.col_offset}"] = PathMethod(
                name=node.name,
                decisions=tuple(Decision(line=i.lineno, exits=exits_of(i)) for i in ifs),
            )
    return dict(sorted(found.items(), key=lambda item: _position(item[0])))


def decision_ifs(function):
    """The if statements at the top level of function's body, in order."""
    return [statement for statement in function.body if isinstance(statement, ast.If)]


def _position(site):
    """(line, col) of a site name, for sorting sites into source order."""
    line, col = site.rsplit(":", 2)[1:]
    return int(line), int(col)


def exits_of(statement):
    """The outcome of statement whose arm always leaves the function: True
    for its then arm, False for its else arm (an elif being no else), None
    for neither."""
    if _leaves(statement.body):
        return True
    if statement.orelse and not _is_elif(statement) and _leaves(statement.orelse):
        return False
    return None


def _is_elif(statement):
    """True when statement's else arm is an elif."""
    return len(statement.orelse) == 1 and isinstance(statement.orelse[0], ast.If)


def _leaves(statements):
    """True when the last of statements is a return or a raise."""
    return isinstance(statements[-1], (ast.Return, ast.Raise))

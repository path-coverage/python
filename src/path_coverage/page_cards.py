"""The cards of one file's page, as page data holds them, in the rail beside
its code: a card for each of its functions, and one for each span of its
lines holding sites outside every function; each from the card the JSON
report lists, as listed_cards lists them, each site's row with its tree's
rows folded under it."""

import re

from . import fold_rows, listed_cards, page_data
from .manifest import Arm, Condition
from .site_tree import tree_of


def of(path, source, sites, lines, recorded):
    """The cards of the file at path, its source and sites, as page data
    holds them: its functions' cards, then its top cards, lines being as
    source_lines.lines_of gives them, recorded (paths, reached), paths as
    result.paths gives them, reached each statement's runs, None when not
    known."""
    paths, reached = recorded
    fold = folds(source, sites, paths)
    functions = listed_cards.function_cards(source, (path, sites), paths, reached)
    tops = listed_cards.top_cards(source, (path, sites), lines, paths)
    return [function_card(site, card, fold) for site, card in functions.items()] + [
        top_card(card, fold) for card in tops.values()
    ]


def function_card(site, card, fold):
    """The card of the function whose def is at site, from card, as
    listed_cards gives it, its folds as fold gives them."""
    first, column = (int(part) for part in site.split(":")[-2:])
    place = {
        "first": first,
        "last": card["last"],
        "column": column,
        "status": page_data.status(card),
        "top": False,
        "sites": None,
    }
    return page_data.card(card, place, fold)


def top_card(card, fold):
    """The top card from card, as listed_cards gives it, its folds as fold
    gives them."""
    place = {
        "first": card["first"],
        "last": card["last"],
        "column": 0,
        "status": page_data.status(card),
        "top": True,
        "sites": len(card["rows"]),
    }
    return page_data.card(card, place, fold)


def folds(source, sites, paths):
    """A function from a site and its row's top to the rows of the site's
    fold, as fold_rows gives them, headed by top, eg if/else, so the two
    always read the same."""

    def fold(site, top):
        """The rows of site's fold, headed by top."""
        condition = sites[site]
        tree = located(source, condition, tree_of(source, condition, paths[site]))
        return fold_rows.rows({**tree, "else_at": else_at(source, condition), "label": top})

    return fold


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
    elif, as an elif is a site of its own."""
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

"""The tree of a site, from site_tree.tree_of, as its row's fold in a card
shows it: a grid whose columns are the site's paths, as page data holds its
rows, each a kind, a branch, a label, where its code is and a cell per
path."""

import re

from . import code_tokens, kinds
from .kinds.block import ITEMS

# The branches joining each operand's row to its operator's. A branch is
# a string of kinds, one letter per cell: t a tee, l an ell, v a bar, h a
# dash, s a space. TEE is the branch to an operand with more after it, ELL
# to the last; BAR the indent under an operand with more after it, its bar
# running on down to them, GAP under the last.
TEE, ELL, BAR, GAP = "ths", "lhs", "vss", "sss"

# [text, mark, hover] of a leaf's or a condition's cell, by the value it
# took on the path: a letter, or a block call's count of items.
OUTCOMES = {True: ["T"], False: ["F"], None: [""], **{item: [text] for item, text in zip(ITEMS, "01*")}}

# [text, mark] of a ternary's arm's cell: taken on a path that took it,
# else blank.
TAKEN = {True: ["", "taken"], False: [""]}

# [text, mark] of the cell of an arm that returns or raises: leaves on a
# path that took it, so left the function there, else blank.
LEAVES = {True: ["", "leaves"], False: [""]}

# An arm's code that leaves the function, and the word that says how.
LEAVING = re.compile(r"(return|raise)\b")


def rows(site):
    """The rows of site's fold, a site tree located as page_cards locates
    it: its own row, naming its operator, or its label, eg if/else, each
    path's count, and where its else keyword is, if it has one; then the
    rows of its operands."""
    own = {
        "kind": "site",
        "branch": "",
        "label": code_tokens.label_code(site.get("label", site["operator"])),
        "at": site.get("at"),
        "else": site.get("else_at"),
        "counts": site["counts"],
    }
    return [own, *_operand_rows(site, "")]


def values(cells, names=OUTCOMES):
    """The cells of a row, as page data holds them, each [text, mark, hover]
    as names gives it, None for a mark or hover it has none of. Example:
    True and False give ["T", None, None], ["F", None, None]."""
    return [[*names[value], None, None][:3] for value in cells]


def shown(condition):
    """The operands of condition a fold shows: a ternary's arms, as its arms
    are part of its one expression; for any other, eg an if or a filter, no
    arm, as which arm a path takes follows from its predicate, but each
    arm's body, and, for an arm that returns or raises, where paths leave
    the function."""
    operands = condition["operands"]
    if condition["operator"] == "ternary":
        return operands
    found = []
    for operand in operands:
        if "arm" not in operand:
            found.append(operand)
            continue
        found += [part for part in (operand["body"], _leaving(operand)) if part]
    return found


def _leaving(arm):
    """{"leaves": return or raise, "cells", "at"} for arm when its code
    returns or raises, cells marking the paths that took it, so left the
    function, at where its code is; None for an arm that does neither."""
    found = LEAVING.match(arm["text"] or "")
    return found and {"leaves": found.group(1), "cells": arm["cells"], "at": arm.get("at")}


def _operand_rows(condition, indent):
    """The rows of a condition's operands, each branching from its operator
    after indent; a nested condition's operands, and those of an arm's
    condition, follow its own row, indented under its branch."""
    operands = shown(condition)
    found = []
    for i, operand in enumerate(operands):
        tip = i == len(operands) - 1
        branch = indent + (ELL if tip else TEE)
        under = indent + (GAP if tip else BAR)
        found += _node_rows(operand, branch, under)
    return found


def _node_rows(operand, branch, under):
    """The rows of one operand of a condition, branching after branch, any
    operands of its own indented to under."""
    if "arm" in operand:
        return _arm_rows(operand, branch, under)
    if "leaves" in operand:
        cells = values(operand["cells"], LEAVES)
        label = code_tokens.code(operand["leaves"])
        return [{"kind": "leaves", "branch": branch, "label": label, "at": operand["at"], "cells": cells}]
    if "operator" not in operand:
        return [_operand_row(operand, branch)]
    label = code_tokens.label_code(operand.get("label", operand["operator"]))
    own = {"kind": "subtree", "branch": branch, "label": label, "at": operand.get("at"), "cells": values(operand["cells"])}
    return [own, *_operand_rows(operand, under)]


def _arm_rows(arm, branch, under):
    """A ternary's arm's row, ? for then and : for else: an arm holding a
    condition showing the condition's operator and value, its operands
    below; a plain arm its text, marking the paths taking it."""
    body = arm["body"]
    label = code_tokens.ternary_arm_code(kinds.of("ternary").arm_label(arm, "ternary"))
    cells = values(body["cells"]) if body else values(arm["cells"], TAKEN)
    own = {"kind": "arm", "branch": branch, "label": label, "at": arm.get("at"), "cells": cells}
    return [own, *_operand_rows(body, under)] if body else [own]


def _operand_row(operand, branch):
    """One operand's row: its branch, text, coloured as the code it is,
    written over more than one line read as one, each line break and the
    indent around it one space, and its outcome on each path."""
    one_line = re.sub(r"\s*\n\s*", " ", operand["text"])
    label = code_tokens.code(one_line)
    return {"kind": "operand", "branch": branch, "label": label, "at": operand.get("at"), "cells": values(operand["cells"])}

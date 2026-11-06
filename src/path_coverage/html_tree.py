"""The tree of a site, from site_tree.tree_of, as its row's fold in a card
shows it: a grid whose columns are the site's paths."""

from html import escape

from . import html_syntax, kinds
from .kinds.block import ITEMS
from .kinds.choice import NAMED_ARMS

# The branches joining each operand's row to its operator's. A branch is
# a string of kinds, one letter per cell: t a tee, l an ell, v a bar, h a
# dash, s a space. CSS draws each kind as lines a whole row tall, so a
# branch joins the rows above and below it. TEE is the branch to an
# operand with more after it, ELL to the last; BAR the indent under an
# operand with more after it, its bar running on down to them, GAP under
# the last.
TEE, ELL, BAR, GAP = "ths", "lhs", "vss", "sss"

# [text, mark] of a leaf's or a condition's cell, by the value it took on
# the path: a letter, or a block call's count of items.
OUTCOMES = {True: ["T"], False: ["F"], None: [""], **{item: [text] for item, text in zip(ITEMS, "01*")}}

# [text, mark] of an arm's cell: taken on a path that took it, else blank.
TAKEN = {True: ["", "taken"], False: [""]}

# [class, mark] of a path's count cell, by whether its count is zero.
MARKS = {True: ("count never", "0"), False: ("count", "*")}


def site_rows(site):
    """A site's rows: its own, naming its operator, or its label, eg elif,
    and each path's count, then the rows of its operands."""
    return [_row(_at(site), _operator(site), counts(site["counts"])), *_operand_rows(site, "")]


def counts(values):
    """One cell per path: 0 for a path never taken, marked as a gap, * for
    one taken any number of times, as whether it was taken is what counts;
    how many times shows on hover, so a count in the thousands never widens
    the cell. Example: counts 0, 2 and 1284 give 0, * and *."""
    cells = []
    for count in values:
        css, mark = MARKS[count == 0]
        cells.append(f'<span class="{css}" data-count="" data-hover="{times(count)}">{mark}</span>')
    return "".join(cells)


def times(count):
    """How many times a path was taken, as its mark's hover reads it, its
    thousands apart, so a big count still reads. Example: 1 gives 1 time,
    1284 gives 1,284 times."""
    return f"{count:,} {'time' if count == 1 else 'times'}"


def branch_cell(branch):
    """The cell drawing branch: a cell of each of its kinds, hidden from
    screen readers, as the rows' order already says how they nest. Example:
    ths gives a tee, a dash and a space cell."""
    cells = "".join(f'<span class="bx" data-bx="{kind}"></span>' for kind in branch)
    return f'<span class="branch" data-branch="" aria-hidden="true">{cells}</span>'


def cells(values, names=OUTCOMES):
    """The cells of values, each named as names gives it."""
    return "".join(_cell(*names[value]) for value in values)


def _cell(text, mark=None):
    """One cell: text, and its mark, when it has one, which CSS draws."""
    marked = f' data-mark="{mark}"' if mark else ""
    return f'<span class="cell" data-cell=""{marked}>{text}</span>'


def _at(node):
    """The data-at attribute of a node located in its source, "" for one
    that is not."""
    at = node.get("at")
    return f' data-at="{",".join(str(n) for n in at)}"' if at else ""


def _operand_rows(condition, indent):
    """The rows of a condition's operands, each branching from its operator
    after indent; a nested condition's operands, and those of an arm's
    condition, follow its own row, indented under its branch."""
    rows = []
    last = len(condition["operands"]) - 1
    for i, operand in enumerate(condition["operands"]):
        tip = i == last
        branch = indent + (ELL if tip else TEE)
        under = indent + (GAP if tip else BAR)
        rows.extend(_node_rows(operand, branch, under, condition["operator"]))
    return rows


def _node_rows(operand, branch, under, choice):
    """The rows of one operand of a condition whose operator is choice."""
    if "arm" in operand:
        return _arm_rows(operand, branch, under, choice)
    if "operator" not in operand:
        return [_operand_row(operand, branch)]
    lead = branch_cell(branch) + _operator(operand)
    row = _row(f' data-subtree=""{_at(operand)}', lead, cells(operand["cells"]))
    return [row, *_operand_rows(operand, under)]


def _arm_rows(arm, branch, under, choice):
    """An arm's row: a ternary's, ? for then and : for else, an arm holding
    a condition showing the condition's operator and value, its operands
    below, a plain arm its text; an if's named then or else, a filter's
    keep or drop. A label naming its arm, with no such word in the code, is
    plain and marked as a name; any other is coloured as the code it is. A
    plain arm marks the paths taking it."""
    body = arm["body"]
    values = cells(body["cells"]) if body else cells(arm["cells"], TAKEN)
    label = kinds.of(choice).arm_label(arm, choice)
    named = choice in NAMED_ARMS and (choice != "if" or arm["arm"] == "then")
    flag = ' data-named=""' if named else ""
    text = escape(label) if named else _label(label, choice)
    lead = branch_cell(branch) + f'<span class="arm" data-label=""{flag}>{text}</span>'
    row = _row(f' data-arm=""{_at(arm)}', lead, values)
    return [row, *_operand_rows(body, under)] if body else [row]


def _label(label, choice):
    """An arm's label as HTML, coloured as the code it quotes: a ternary's
    as html_syntax.ternary_arm has it, any other, eg else, as code."""
    return html_syntax.ternary_arm(label) if choice == "ternary" else html_syntax.fragment(label)


def _row(attrs, lead, values):
    """A row of the grid, with attrs, lead's cells naming it, then values,
    its cells for each path."""
    return f'<div class="row"{attrs}>{lead}{values}</div>'


def _operator(condition):
    """The cell naming a condition's operator, or its label when it has
    one, eg elif, coloured as the code it is part of."""
    name = html_syntax.fragment(condition.get("label", condition["operator"]))
    return f'<span class="operator" data-operator="">{name}</span>'


def _operand_row(operand, branch):
    """One operand's row: its branch, text, coloured as the code it is, and
    its outcome on each path."""
    text = html_syntax.fragment(operand["text"] or "")
    lead = branch_cell(branch) + f'<span class="text" data-text="">{text}</span>'
    return _row(f' data-operand=""{_at(operand)}', lead, cells(operand["cells"]))

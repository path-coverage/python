"""The HTML report: index.html, one sortable row per covered file, and
files/<path>.html for each, its source with each site's line number a button
that opens the site's grid of paths, and, when methods are measured, a grid
of each function's paths beside it."""

import ast
import re
from html import escape
from itertools import groupby
from pathlib import Path

from . import path_manifest, summary
from .manifest import Arm, Condition
from .path_gaps import possible
from .site_tree import tree_of
from .source_lines import line_of, lines_of

ASSETS = Path(__file__).parent / "html"
JUMP_LISTS = {"covered": "Covered", "gaps": "Gaps"}
TEE, ELBOW, BAR, DASH = "&#9500;", "&#9492;", "&#9474;", "&#9472;"
OUTCOMES = {True: "T", False: "F", None: ""}
# A bullet marks a path taking a plain arm.
TAKEN = {True: "&#8226;", False: ""}
# The choices whose arms are named by their kind, then or else, as their
# text is statements.
NAMED_ARMS = ("if",)


def write(operands, files, coverage_dir, paths, methods=None, taken=None):
    """Writes index.html and files/<path>.html into coverage_dir. operands
    and paths are as result.operands and result.paths give them; files is
    {path relative to root: (source, sites)} for each covered file; methods
    and taken, the functions whose paths are counted and the paths they
    took, are given when methods are measured."""
    rows = summary.files(paths, methods, taken)
    (coverage_dir / "index.html").write_text(index_page(rows, summary.total(rows)))
    for path, (source, sites) in files.items():
        out = coverage_dir / "files" / f"{path}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        own = None if methods is None else path_manifest.methods(source, path)
        out.write_text(_file_page(path, source, sites, operands, paths, own, taken))


def _file_page(path, source, sites, operands, paths, methods, taken):
    """The whole page of the covered file at path, written at
    files/<path>.html, so it links back to the index one folder up for each
    folder in that."""
    lines = lines_of(source, sites, operands)
    trees = {}
    for site, condition in sites.items():
        first = lines[line_of(site) - 1]["span"][0]
        tree = tree_of(source, condition, paths[site])
        trees.setdefault(first, []).append(_located(source, condition, tree))
    return _fill(
        _asset("file.html"),
        path=escape(path),
        index="../" * (path.count("/") + 1) + "index.html",
        style=_asset("style.css"),
        script=_asset("toggle.js") + _asset("side.js"),
        jumps=jumps(lines),
        listing=listing(lines, trees),
        grids=grids(source, methods, taken or {}) if methods else "",
    )


def _asset(name):
    """The text of one of the report's template, style or script files."""
    return (ASSETS / name).read_text()


def _fill(template, **values):
    """template with each {{name}} replaced by values[name]."""
    return re.sub(r"\{\{(\w+)\}\}", lambda match: values[match.group(1)], template)


# The heading of the across column, there only when methods are measured.
ACROSS = (
    '<th class="num" aria-sort="none"><button type="button" data-column="3"'
    f' data-type="number">{escape("Across a function's decisions")}</button></th>'
)


def index_page(rows, total):
    """The whole index page: the files table, sortable by any column, with
    one row per summary.files row, and total, as summary.total gives it, as
    its footer."""
    return _fill(
        _asset("index.html"),
        style=_asset("style.css"),
        script=_asset("sort.js"),
        across=ACROSS if total["methods"] is not None else "",
        rows="\n".join(index_row(row) for row in rows),
        total=_counts_row(_cell("Total", "Total"), total),
    )


def index_row(row):
    """The index table row of one summary.files row; each cell has a
    data-sort value for the page's column sorting."""
    path = escape(row["path"])
    return _counts_row(_cell(path, f'<a href="files/{path}.html">{path}</a>'), row)


def _counts_row(first, row):
    """A row of first, then row's sites, its total within each decision,
    and, when methods are measured, its total across a function's
    decisions."""
    cells = [first, _cell(row["sites"], row["sites"]), _paths_cell(row["decisions"])]
    if row["methods"] is not None:
        cells.append(_paths_cell(row["methods"]))
    return f"<tr>{''.join(cells)}</tr>"


def _paths_cell(pair):
    """A cell showing [taken, possible] paths, eg 3 / 6 (50%), sorted by its
    percent. With no paths to take, as in a file with no function of two or
    more decisions, it shows -, titled with why, with an empty sort value,
    which sort.js keeps last whichever way the column is sorted."""
    taken, possible_count = pair
    if possible_count == 0:
        return _cell("", "-", "no function with two or more decisions")
    percent = round(100 * taken / possible_count)
    return _cell(percent, f"{taken} / {possible_count} ({percent}%)")


def _cell(sort_value, content, title=None):
    """One table cell, sorted by sort_value, showing content, with title as
    its hover text when there is one."""
    hover = f' title="{title}"' if title else ""
    return f'<td data-sort="{sort_value}"{hover}>{content}</td>'


def jumps(lines):
    """The file page header's lists of links to the first line of each
    span: those covered, then those with gaps."""
    firsts = [line for line in lines if line["span"] and line["span"][0] == line["number"]]
    lists = [
        _jump_list(status, label, [line["number"] for line in firsts if line["status"] == status])
        for status, label in JUMP_LISTS.items()
    ]
    return f'<nav class="jumps" aria-label="Sites">{"".join(lists)}</nav>'


def _jump_list(status, label, numbers):
    """One labelled list of links to lines."""
    links = "".join(f'<a class="jump" data-status="{status}" href="#L{n}">{n}</a>' for n in numbers)
    return (
        f'<div class="jump-list" data-jumps="{status}">'
        f'<span class="jump-label">{label}</span>{links}</div>'
    )


def listing(lines, trees):
    """The source listing of lines (as source_lines.lines_of gives them):
    each run of lines sharing a span is one block, followed by its tree.
    trees is {span's first line: [site_tree.tree_of, ...]}."""
    blocks = [
        list(group)
        for _, group in groupby(lines, key=lambda line: line["span"] or ("line", line["number"]))
    ]
    gaps = [block[0]["number"] for block in blocks if block[0]["status"] == "gaps"]
    body = "\n".join(_block(block, trees, gaps) for block in blocks)
    return f'<div class="code">\n{body}\n</div>'


def _block(lines, trees, gaps):
    """A plain line, or the lines of one span behind one button with the
    span's tree straight after them; either way after its nav cell."""
    first = lines[0]
    cell = _nav_cell(first["number"], gaps)
    if first["span"] is None:
        return f'<div class="line">{cell}{_number(first["number"])}{_code(first)}</div>'
    site_trees = trees.get(first["number"], [])
    return _span_block(lines, len(site_trees), cell) + _tree(
        first["number"], site_trees, first["status"] == "gaps"
    )


def _span_block(lines, sites, cell):
    """The lines of one span after their nav cell: one button over all their
    numbers, and how many sites it opens when two or more, beside their code."""
    numbers = "".join(_number(line["number"]) for line in lines)
    codes = "".join(_code(line) for line in lines)
    count = f'<span class="site-count" data-site-count="">{sites}</span>' if sites > 1 else ""
    first = lines[0]
    button = (
        f'<button type="button" class="lnum" data-status="{first["status"]}"'
        f' aria-expanded="{"true" if first["status"] == "gaps" else "false"}"'
        f' aria-controls="tree-{first["number"]}">{count}{numbers}</button>'
    )
    return f'<div class="block">{cell}{button}<div class="srcs">{codes}</div></div>'


def _nav_cell(number, gaps):
    """The cell left of a row's number: at a span with gaps, links to the
    previous and next such span, wrapping round at the ends; empty on every
    other row, so the numbers stay aligned."""
    links = ""
    if number in gaps:
        index = gaps.index(number)
        previous, following = gaps[index - 1], gaps[(index + 1) % len(gaps)]
        links = (
            f'<a data-prev="" href="#L{previous}" aria-label="Previous gap, line {previous}">&#9650;</a>'
            f'<a data-next="" href="#L{following}" aria-label="Next gap, line {following}">&#9660;</a>'
        )
    return f'<span class="nav" data-nav="">{links}</span>'


def _number(number):
    """One line's number, the target of a link to #L<number>."""
    return f'<span class="lineno" id="L{number}" data-line="{number}">{number}</span>'


def _code(line):
    """One line's code, escaped."""
    return f'<span class="src" data-src="">{escape(line["text"], quote=False)}</span>'


def _tree(number, site_trees, open_):
    """The tree of a span, open when its sites have gaps, else hidden: each
    site's rows in a group of their own."""
    groups = "".join(
        f'<div class="site" data-site="">{"".join(_site_rows(site))}</div>' for site in site_trees
    )
    hidden = "" if open_ else ' hidden="hidden"'
    return f'<div class="tree" id="tree-{number}"{hidden}>{groups}</div>'


def _site_rows(site):
    """A site's row, naming its operator and each path's count, then the
    rows of its operands."""
    counts = "".join(
        f'<span class="{"count never" if count == 0 else "count"}" data-count="">{count}</span>'
        for count in site["counts"]
    )
    return [_row(_at(site), _operator(site), counts), *_operand_rows(site, "")]


def _cells(values, names=OUTCOMES):
    """One cell per path, naming each value with names."""
    return "".join(f'<span class="cell" data-cell="">{names[value]}</span>' for value in values)


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
        branch = indent + (f"{ELBOW}{DASH} " if tip else f"{TEE}{DASH} ")
        under = indent + ("   " if tip else f"{BAR}  ")
        rows.extend(_node_rows(operand, branch, under, condition["operator"]))
    return rows


def _node_rows(operand, branch, under, choice):
    """The rows of one operand of a condition whose operator is choice."""
    if "arm" in operand:
        return _arm_rows(operand, branch, under, choice)
    if "operator" not in operand:
        return [_operand_row(operand, branch)]
    lead = _branch(branch) + _operator(operand)
    row = _row(f' data-subtree=""{_at(operand)}', lead, _cells(operand["cells"]))
    return [row, *_operand_rows(operand, under)]


def _arm_rows(arm, branch, under, choice):
    """An arm's row: a ternary's ? for then and : for else, an arm holding a
    condition showing the condition's operator and value, its operands
    below, a plain arm its text; an if's named then or else. A plain arm
    marks the paths taking it."""
    body = arm["body"]
    values = _cells(body["cells"]) if body else _cells(arm["cells"], TAKEN)
    lead = _branch(branch) + f'<span class="arm" data-label="">{escape(_arm_label(arm, choice))}</span>'
    row = _row(f' data-arm=""{_at(arm)}', lead, values)
    return [row, *_operand_rows(body, under)] if body else [row]


def _arm_label(arm, choice):
    """The name of an arm of a condition whose operator is choice."""
    if choice in NAMED_ARMS:
        return arm["arm"]
    mark = "?" if arm["arm"] == "then" else ":"
    body = arm["body"]
    return f"{mark} {body['operator'] if body else arm['text']}"


def _row(attrs, lead, values):
    """A row of the grid, with attrs, lead's cells naming it, then values,
    its cells for each path."""
    return f'<div class="row"{attrs}>{lead}{values}</div>'


def _operator(condition):
    """The cell naming a condition's operator."""
    return f'<span class="operator" data-operator="">{escape(condition["operator"])}</span>'


def _operand_row(operand, branch):
    """One operand's row: its branch, text, and its outcome on each path."""
    lead = _branch(branch) + f'<span class="text" data-text="">{escape(operand["text"] or "")}</span>'
    return _row(f' data-operand=""{_at(operand)}', lead, _cells(operand["cells"]))


def _branch(branch):
    """The cell drawing a row's branch from its operator."""
    return f'<span class="branch" data-branch="">{branch}</span>'


def _located(source, condition, tree):
    """tree with an "at" of [line, col, end_line, end_col] on each leaf and
    on each conditional expression's arm, columns counted in characters, so
    side.js can mark them in the source."""
    operands = []
    for operand, node in zip(condition.operands, tree["operands"]):
        if isinstance(operand, Condition):
            node = _located(source, operand, node)
        elif isinstance(operand, Arm):
            body = operand.body and _located(source, operand.body, node["body"])
            node = {**node, "body": body or None}
            if operand.at:
                node["at"] = _position(source, *operand.at)
        else:
            node = {**node, "at": _position(source, operand.line, operand.col, operand.end_line, operand.end_col)}
        operands.append(node)
    return {**tree, "operands": operands}


def _position(source, line, col, end_line, end_col):
    """[line, col, end_line, end_col] with the byte columns ast gives as
    character columns."""
    lines = source.encode().splitlines(keepends=True)
    return [
        line,
        len(lines[line - 1][:col].decode()),
        end_line,
        len(lines[end_line - 1][:end_col].decode()),
    ]


def grids(source, methods, taken):
    """The hidden grids of every function in methods, as
    path_manifest.methods gives them, from the paths taken, as the recorder
    counts them; side.js moves each into the rail beside its def."""
    tree = ast.parse(source)
    ends = {
        node.lineno: node.end_lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    arms = {
        node.lineno: _if_parts(source, node) for node in ast.walk(tree) if isinstance(node, ast.If)
    }
    return "\n".join(
        _grid(site, method, taken.get(site, {}), ends, arms) for site, method in methods.items()
    )


def _if_parts(source, node):
    """The lines of an if's parts: head, its if and predicate; then, its
    then arm; else, its else (or elif) through its arm. Each is [first,
    last], None when absent. Python has no end keyword, so no end."""
    start = node.lineno
    then_arm = [node.body[0].lineno, node.body[-1].end_lineno]
    else_part = None
    if node.orelse:
        first = node.orelse[0]
        if isinstance(first, ast.If) and len(node.orelse) == 1:
            else_part = [first.lineno, node.end_lineno]
        else:
            else_part = [_else_line(source, first.lineno), node.orelse[-1].end_lineno]
    body = min(then_arm[0], else_part[0] if else_part else then_arm[0])
    return {"head": [start, max(start, body - 1)], "then": then_arm, "else": else_part, "end": None}


def _else_line(source, first):
    """The line of the else keyword before the statement on line first."""
    lines = source.splitlines()
    number = first - 1
    while number > 1 and not lines[number - 1].strip().startswith("else"):
        number -= 1
    return number


def _grid(site, method, taken, ends, arms):
    """One function's grid: its calls row, level with its def, then a row
    per decision, level with that decision's line."""
    first = int(site.split(":")[-2])
    every = possible(method.decisions)
    ordered = [
        path
        for _, path in sorted(
            enumerate(every), key=lambda item: (1 if tuple(item[1]) in taken else 0, item[0])
        )
    ]
    missing = sum(1 for path in every if tuple(path) not in taken)
    rows = [_calls_row(first, ordered, taken, method, len(every) - missing)]
    rows += [
        _decision_row(decision, index, ordered, taken, arms)
        for index, decision in enumerate(method.decisions)
    ]
    status = "covered" if missing == 0 else "gaps"
    attrs = (
        f'id="paths-{first}" data-first="{first}" data-col="{site.split(":")[-1]}"'
        f' data-last="{ends.get(first, first)}" data-status="{status}"'
    )
    return f'<div class="pathgrid" {attrs} hidden="hidden">{"".join(rows)}</div>'


def _calls_row(first, ordered, taken, method, seen):
    """The row level with the def: how many calls took each path,
    never-taken ones marked."""
    cells = "".join(
        f'<span class="{"pcell never" if taken.get(tuple(path), 0) == 0 else "pcell taken"}">'
        f"{taken.get(tuple(path), 0)}</span>"
        for path in ordered
    )
    name = escape(method.name)
    label = f'<span class="plabel">{seen}/{len(ordered)}</span>'
    title = f' title="{name}: {seen} of {len(ordered)} paths taken"'
    return f'<div class="prow calls" data-line="{first}"{title}>{label}{cells}</div>'


def _decision_row(decision, index, ordered, taken, arms):
    """The row level with a decision: T or F for each path that makes it,
    those of never-taken paths marked, blank for a path that ended before
    it."""
    cells = []
    for path in ordered:
        if index >= len(path):
            cells.append('<span class="pcell ended"></span>')
            continue
        outcome = path[index]
        never = "" if tuple(path) in taken else " never"
        cells.append(
            f'<span class="pcell {str(outcome).lower()}{never}">{"T" if outcome else "F"}</span>'
        )
    arm = arms.get(decision.line, {})
    parts = " ".join(
        f'data-{part}="{",".join(str(n) for n in arm[part]) if arm.get(part) else ""}"'
        for part in ("head", "then", "else", "end")
    )
    label = f'<span class="plabel">{decision.line}</span>'
    return f'<div class="prow" data-line="{decision.line}" {parts}>{label}{"".join(cells)}</div>'

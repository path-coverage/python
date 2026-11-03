"""The HTML report: index.html, one sortable row per covered file, and
files/<path>.html for each, its source with each condition's line number a
button that opens the condition's tree."""

import re
from html import escape
from itertools import groupby
from pathlib import Path

from . import summary
from .site_tree import tree_of
from .source_lines import line_of, lines_of

ASSETS = Path(__file__).parent / "html"
JUMP_LISTS = {"covered": "Covered", "gaps": "Gaps"}
HEADINGS = ["condition", "true", "false", "gap"]
TEE, ELBOW, BAR, DASH = "&#9500;", "&#9492;", "&#9474;", "&#9472;"


def write(operands, files, coverage_dir):
    """Writes index.html and files/<path>.html into coverage_dir. operands
    are as result.operands gives them; files is {path relative to root:
    (source, sites)} for each covered file."""
    rows = "\n".join(index_row(row) for row in summary.files(operands))
    index = _fill(_asset("index.html"), style=_asset("style.css"), script=_asset("sort.js"), rows=rows)
    (coverage_dir / "index.html").write_text(index)
    for path, (source, sites) in files.items():
        out = coverage_dir / "files" / f"{path}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_file_page(path, source, sites, operands))


def _file_page(path, source, sites, operands):
    """The whole page of the covered file at path, written at
    files/<path>.html, so it links back to the index one folder up for each
    folder in that."""
    lines = lines_of(source, sites, operands)
    trees = {}
    for site, condition in sites.items():
        first = lines[line_of(site) - 1]["span"][0]
        trees.setdefault(first, []).append(tree_of(source, condition, operands[site]))
    return _fill(
        _asset("file.html"),
        path=escape(path),
        index="../" * (path.count("/") + 1) + "index.html",
        style=_asset("style.css"),
        script=_asset("toggle.js"),
        jumps=jumps(lines),
        listing=listing(lines, trees),
    )


def _asset(name):
    """The text of one of the report's template, style or script files."""
    return (ASSETS / name).read_text()


def _fill(template, **values):
    """template with each {{name}} replaced by values[name]."""
    return re.sub(r"\{\{(\w+)\}\}", lambda match: values[match.group(1)], template)


def index_row(row):
    """The index table row of one summary.files row; each cell has a
    data-sort value for the page's column sorting."""
    path = escape(row["path"])
    link = f'<a href="files/{path}.html">{path}</a>'
    seen = f'{row["seen"]} / {row["outcomes"]} &middot; {row["percent"]}%'
    cells = [
        _cell(path, link),
        _cell(row["sites"], row["sites"]),
        _cell(row["percent"], seen),
        _cell(row["missing"], row["missing"]),
    ]
    return f"<tr>{''.join(cells)}</tr>"


def _cell(sort_value, content):
    """One table cell, sorted by sort_value, showing content."""
    return f'<td data-sort="{sort_value}">{content}</td>'


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
    """The tree of a span, open when its sites have gaps, else hidden: a
    heading row, then each site's rows in a group of their own."""
    headings = "".join(f"<span>{name}</span>" for name in HEADINGS)
    groups = "".join(
        f'<div class="site" data-site="">{"".join(_site_rows(site))}</div>' for site in site_trees
    )
    hidden = "" if open_ else ' hidden="hidden"'
    return (
        f'<div class="tree" id="tree-{number}"{hidden}>'
        f'<div class="row headings" data-heading="">{headings}</div>{groups}</div>'
    )


def _site_rows(site):
    """A site's operator row, then the rows of its operands."""
    return [f'<div class="row">{_operator(site)}</div>', *_operand_rows(site, "")]


def _operand_rows(condition, indent):
    """The rows of a condition's operands, each branching from its operator
    after indent; a nested condition's operands follow its own row, indented
    under its branch."""
    rows = []
    last = len(condition["operands"]) - 1
    for i, operand in enumerate(condition["operands"]):
        tip = i == last
        branch = indent + (f"{ELBOW}{DASH} " if tip else f"{TEE}{DASH} ")
        if "operator" not in operand:
            rows.append(_operand_row(operand, branch))
            continue
        rows.append(
            f'<div class="row" data-subtree="">{_branch(branch)}{_operator(operand)}</div>'
        )
        rows.extend(_operand_rows(operand, indent + ("   " if tip else f"{BAR}  ")))
    return rows


def _operator(condition):
    """The cell naming a condition's operator."""
    return f'<span class="operator" data-operator="">{escape(condition["operator"])}</span>'


def _operand_row(operand, branch):
    """One operand's row: its branch, text, true and false counts, and gap."""
    cells = "".join(
        f'<span class="{name}" data-{name}="">'
        f'{escape("" if operand[name] is None else str(operand[name]))}</span>'
        for name in ("text", "truthy", "falsy", "gap")
    )
    return f'<div class="row" data-operand="">{_branch(branch)}{cells}</div>'


def _branch(branch):
    """The cell drawing a row's branch from its operator."""
    return f'<span class="branch" data-branch="">{branch}</span>'

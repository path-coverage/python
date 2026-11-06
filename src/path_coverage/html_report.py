"""The HTML report: index.html, one sortable row per covered file, and
files/<path>.html for each, its source beside the rail of its cards: one
for each function, and one for each span of lines holding sites outside
every function, each site's row folding its tree under it."""

import shutil

from . import html_file, html_index, html_statements, html_syntax, html_tree, listed_cards, method_statements, summary
from .html_file import Card
from .manifest import Arm, Condition
from .site_tree import tree_of
from .source_lines import lines_of


def write(operands, files, coverage_dir, paths, cards, reached, groups=None):
    """Writes index.html and files/<path>.html into coverage_dir. operands
    and paths are as result.operands and result.paths give them; files is
    {path relative to root: (source, sites)} for each covered file; cards,
    {card site: [taken, size]}, as method_statements.cards gives them, with
    reached, each statement's runs, None when not known; groups, {name:
    [glob, ...]}, each get a tab of the index page. The files dir is
    emptied first, so it holds no page for a file no longer covered."""
    shutil.rmtree(coverage_dir / "files", ignore_errors=True)
    rows = summary.files(paths, cards)
    tabs = summary.groups(rows, groups) if groups else []
    (coverage_dir / "index.html").write_text(html_index.page(rows, summary.total(rows), tabs))
    for path, (source, sites) in files.items():
        out = coverage_dir / "files" / f"{path}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(file_page(path, source, sites, operands, paths, reached))


def file_page(path, source, sites, operands, paths, reached):
    """The page of the covered file at path, its source with its sites,
    from operands and paths, its cards' rows' taken from reached too: its
    functions' cards, then a card for each span of its sites outside every
    function."""
    lines = _coloured(source, lines_of(source, sites, operands))

    def tree(site):
        """The rows of site's tree, for its row's fold in a card."""
        return _fold(source, path, sites, paths, site)

    cards = method_cards(source, path, paths, reached, tree) + top_cards(source, path, lines, paths, tree)
    return html_file.page(path, lines, cards)


def method_cards(source, path, paths, reached, tree=None):
    """The Card of each function in source, at path, its rows' taken from
    paths, as result.paths gives them, and reached; tree, when given,
    giving each site row's fold."""
    names = method_statements.names(source, path)
    lasts = method_statements.lasts(source, path)
    found = []
    for site, rows in method_statements.of(source, path).items():
        taken = method_statements.taken(rows, paths, reached)
        html = html_statements.card(site, names[site], rows, taken, lasts[site], tree)
        first, column = (int(part) for part in site.split(":")[-2:])
        status = html_statements.status(rows, taken)
        found.append(Card(first, lasts[site], column, status, False, None, html))
    return found


def top_cards(source, path, lines, paths, tree=None):
    """A top Card for each span of lines holding sites outside every
    function in source, at path, as each span's lines share one button: a
    row per site in it, titled by its scope. lines are as
    source_lines.lines_of gives them."""
    scope = listed_cards.scopes(source)
    found = []
    for (first, last), rows in listed_cards.spans(source, path, lines).items():
        taken = method_statements.taken(rows, paths)
        site = f"{path}:{first}:0"
        html = html_statements.top_card(site, scope(first), rows, taken, last, tree)
        status = html_statements.status(rows, taken)
        found.append(Card(first, last, 0, status, True, len(rows), html))
    return found


def _fold(source, path, sites, paths, site):
    """The rows of site's tree, as a file's page draws them, for its row's
    fold in a card; an elif's labelled elif, as it is written."""
    condition = sites[site]
    tree = _located(source, condition, tree_of(source, condition, paths[site]))
    line, column = (int(part) for part in site.split(":")[-2:])
    written = source.splitlines()[line - 1].encode()[column:]
    if condition.operator == "if" and written.startswith(b"elif"):
        tree = {**tree, "label": "elif"}
    return "".join(html_tree.site_rows(tree))


def _coloured(source, lines):
    """lines, as source_lines.lines_of gives them for source, each with its
    coloured tokens, as html_syntax.of gives them."""
    tokens = html_syntax.of(source)
    return [{**line, "tokens": tokens.get(line["number"], [])} for line in lines]


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

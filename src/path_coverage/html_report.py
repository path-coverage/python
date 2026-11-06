"""The HTML report: index.html, one sortable row per covered file, and
files/<path>.html for each, its source beside the rail of its cards: one
for each function, and one for each span of lines holding sites outside
every function, each site's row folding its tree under it. Each page is its
data, as page_data gives it, in the shared renderer's page, as html_template
writes it."""

import shutil

from . import code_tokens, html_template, page_cards, page_data, summary
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
    tables = [["All files", rows, summary.total(rows)], *tabs]
    (coverage_dir / "index.html").write_text(html_template.page(page_data.index(tables, [])))
    for path, (source, sites) in files.items():
        out = coverage_dir / "files" / f"{path}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html_template.page(file_data(path, source, sites, operands, (paths, reached))))


def file_data(path, source, sites, operands, recorded):
    """The data of the page of the covered file at path, its source with
    its sites, from operands, its cards from recorded, (paths, reached):
    its lines, each coloured, its functions' cards, then a card for each
    span of its sites outside every function."""
    lines = lines_of(source, sites, operands)
    tokens = code_tokens.of(source)
    coloured = [{**line, "tokens": tokens.get(line["number"], [])} for line in lines]
    return page_data.file(path, coloured, page_cards.of(path, source, sites, lines, recorded))

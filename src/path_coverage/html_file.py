"""One covered file's HTML page: its source beside the rail of its cards,
one open at a time. A function's def number opens its card; a site outside
every function has one button over its lines' numbers that opens their top
card. The header's jumps, and the arrows in the gutter, lead from card to
card."""

from dataclasses import dataclass
from html import escape
from itertools import groupby

from . import html_syntax
from .html_template import asset, page as template_page

# Each status's arrows, gaps first, and how a label names it.
NAV_KINDS = {"gaps": "with gaps", "covered": "covered"}

# Each arrow's way and how its label names it.
WAYS = {"prev": "Previous", "next": "Next"}


@dataclass(frozen=True)
class Card:
    """One card of a file's page, as the page lays out the code around it:
    its first and last lines, its def's column, its status, gaps or
    covered, whether it is a top card, of sites outside every function, how
    many sites a top card holds, its button showing that count, None for a
    function's, and its HTML."""

    first: int
    last: int
    column: int
    status: str
    top: bool
    sites: int | None
    html: str

    def holds(self, line):
        """True when line is one of the card's lines."""
        return self.first <= line <= self.last


def page(path, lines, cards):
    """The whole page for the file at path (relative to root), written at
    files/<path>.html, so it links back to the index one folder up for each
    folder in that; lines as source_lines.lines_of gives them, each with its
    tokens, as html_syntax.of gives them."""
    return template_page(
        "file.html",
        path=escape(path),
        index="../" * (path.count("/") + 1) + "index.html",
        script="".join(asset(name) for name in ("side.js", "settings.js", "theme.js")),
        rail="\n".join(card.html for card in cards),
        jumps=jumps(cards),
        listing=listing(lines, cards),
    )


def listing(lines, cards):
    """The source listing of lines, marked with the functions of cards: a
    row per line, but one row over all the lines of a site outside every
    function."""
    methods = [card for card in cards if not card.top]
    tops = {card.first: card for card in cards if card.top}
    body = []
    for key, group in groupby(lines, key=lambda line: _row_key(line, methods)):
        rows = list(group)
        if isinstance(key, tuple):
            body.append(_loose_block(rows, cards, tops.get(key[0])))
        else:
            body.append(_line(rows[0], cards, methods))
    return '<div class="code">\n' + "\n".join(body) + "\n</div>"


def _row_key(line, methods):
    """The span of line's site when it is outside every function, so its
    lines share one row; else line's own number."""
    span = line["span"]
    return span if span and _loose(methods, span[0]) else line["number"]


def _line(line, cards, methods):
    """A line of its own, after its gutter, folded when it is in a
    function's body."""
    number = line["number"]
    css = "line method-folded" if _folded(methods, number) else "line"
    parts = _number(number, methods) + _code(line, methods)
    return f'<div class="{css}">{nav_cell([number], cards)}{parts}</div>'


def _loose_block(lines, cards, top):
    """The lines of a site outside every function after their gutter: one
    button over all their numbers, opening their top card, top, and how
    many sites it opens when that is two or more, beside their code."""
    numbers = [line["number"] for line in lines]
    spans = "".join(_number(number, []) for number in numbers)
    button = _button(lines[0], top, _site_count(top) + spans)
    codes = "".join(_code(line, []) for line in lines)
    return f'<div class="block">{nav_cell(numbers, cards)}{button}<div class="srcs">{codes}</div></div>'


def _site_count(top):
    """The count of a top card's sites, shown only for two or more."""
    sites = top.sites if top else 0
    return f'<span class="site-count" data-site-count="">{sites}</span>' if sites > 1 else ""


def _button(first, top, numbers):
    """The button over a loose site's numbers, wearing its top card's
    status, else its first line's, closed until its card opens."""
    status = top.status if top else first["status"]
    return (
        f'<button type="button" class="lnum loose" data-status="{status}" aria-expanded="false"'
        f' aria-controls="paths-{first["number"]}">{numbers}</button>'
    )


def _number(number, methods):
    """One line's number, the target of a link to #L<number>; a def's
    marked to open its function's card."""
    css = _number_attributes(methods, number)
    return f'<span {css} id="L{number}" data-line="{number}">{number}</span>'


def _code(line, methods):
    """One line's code, escaped, each of its tokens, if any, in a span of
    its colour's class, marked with its functions."""
    number, plain = line["number"], line["text"]
    text = html_syntax.html(plain, line.get("tokens", []))
    return f'<span {_src_attributes(methods, number, plain)} data-src="">{text}</span>'


def _src_attributes(methods, number, text):
    """The attributes of the code of line number, its text text: in a
    function, its innermost one's status and def's column, marked as its def
    line, with its text's length, or as its last line when it is; plain in
    none. Example: line 3, f's def at column 4, gives class="src in-method
    def-line" data-method-status="covered" style="--def-col: 4; --def-end:
    15"."""
    holders = [card for card in methods if card.holds(number)]
    if not holders:
        return 'class="src"'
    inner = max(holders, key=lambda card: card.first)
    marks = [
        mark
        for mark, lines in (
            ("def-line", [card.first for card in methods]),
            ("method-end", [card.last for card in methods]),
        )
        if number in lines
    ]
    style = f"--def-col: {inner.column}"
    if inner.first == number:
        style += f"; --def-end: {len(text)}"
    css = " ".join(["src", "in-method", *marks])
    return f'class="{css}" data-method-status="{inner.status}" style="{style}"'


def _number_attributes(methods, number):
    """The attributes a def's number adds, opening its function's card,
    which starts closed: none on any other line."""
    card = next((card for card in methods if card.first == number), None)
    if card is None:
        return 'class="lineno"'
    return f'class="lineno mdef" data-status="{card.status}" aria-expanded="false"'


def _folded(methods, number):
    """True when line number's row starts folded: in a function's body,
    after its def line."""
    return any(card.first < number <= card.last for card in methods)


def _loose(methods, number):
    """True when line number is in no function, so its site's button opens
    its lines' top card."""
    return not any(card.holds(number) for card in methods)


def jumps(cards):
    """The header's row of jumps, labelled Gaps, to the first line of each
    card with gaps, in line order; marked empty when there are none, so the
    header keeps its height."""
    links = "".join(
        f'<a class="jump" data-status="gaps" href="#L{first}">{first}</a>' for first in _firsts(cards, "gaps")
    )
    empty = "" if links else ' data-empty=""'
    name = '<span class="jump-label">Gaps</span>'
    return f'<nav class="jumps" aria-label="Cards"><div class="jump-list"{empty}>{name}{links}</div></nav>'


def _firsts(cards, status):
    """The first lines of the cards of status, in line order."""
    return sorted(card.first for card in cards if card.status == status)


def nav_cell(numbers, cards):
    """The gutter of the row of numbers: by each card's first line, an
    arrow to the card of its status before it, and one to the one after,
    wrapping round at either end; empty on every other row, so the numbers
    stay aligned."""
    links = []
    for status in NAV_KINDS:
        firsts = _firsts(cards, status)
        for first in [first for first in firsts if first in numbers]:
            index = firsts.index(first)
            links.append(_arrow("prev", firsts[index - 1], status))
            links.append(_arrow("next", firsts[(index + 1) % len(firsts)], status))
    return f'<span class="nav" data-nav="">{"".join(links)}</span>'


def _arrow(way, line, status):
    """One arrow, way prev or next, to the card of status at line; CSS
    draws its glyph, in its status's colour."""
    label = f"{WAYS[way]} card {NAV_KINDS[status]}, line {line}"
    return f'<a data-{way}="" data-status="{status}" href="#L{line}" aria-label="{label}"></a>'

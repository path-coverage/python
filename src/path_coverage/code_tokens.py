"""The colours of a file's code on its page, as page data holds them: each
token Python's own tokenize finds gets the class of its kind, eg k for a
keyword, so the page colours it.

A file is tokenized whole, once, and every fragment of it, eg a decision's
operand or a ternary's arm, takes the tokens of its span: a fragment alone
is no valid Python, eg one ending in a comment that would swallow its
closing bracket, so it is never tokenized alone. A label, eg and or
if/else, is no fragment of the file but words, coloured as keywords."""

import functools
import io
import keyword
import re
import tokenize

# The class of each coloured token type that is not a name: n a number, s
# a string, or a part of an f-string or t-string that is no expression, c
# a comment.
CLASSES = {
    "NUMBER": "n",
    "STRING": "s",
    "FSTRING_START": "s",
    "FSTRING_MIDDLE": "s",
    "FSTRING_END": "s",
    "TSTRING_START": "s",
    "TSTRING_MIDDLE": "s",
    "TSTRING_END": "s",
    "COMMENT": "c",
}

# A line break in a fragment and the space around it, which the fragment's
# one line reads as one space.
BREAK = re.compile(r"\s*\n\s*")


def of(source):
    """{line number: [[from, to, class], ...]} for the lines of source that
    have coloured tokens, columns counting characters, a token over many
    lines having a range on each, touching ranges of one class joined.
    Example: "x = 1\\n" gives {1: [[4, 5, "n"]]}."""
    lengths = [len(line) for line in source.splitlines()]
    lines = {}
    for (start, end), css in _classed(source):
        for number, first, last in _ranges(lengths, start, end):
            lines.setdefault(number, []).append([first, last, css])
    return {number: _joined(sorted(ranges)) for number, ranges in lines.items()}


@functools.lru_cache(maxsize=8)
def colours(source):
    """The Colours of source, a whole file, tokenized once however many of
    its fragments are coloured."""
    return Colours(source)


class Colours:
    """The coloured tokens of one whole file, as of gives them, from which
    each of its lines and fragments takes its own."""

    def __init__(self, source):
        """The colours of source, a file that parsed."""
        self.lines = source.splitlines()
        self.tokens = of(source)

    def each_line(self):
        """Each line of the file, as page data holds it: its text and its
        coloured tokens."""
        return [{"text": text, "tokens": self.tokens.get(number, [])} for number, text in enumerate(self.lines, start=1)]

    def span(self, at, _text):
        """The fragment of the file at at, [line, col, end_line, end_col],
        columns in characters, as page data holds it: read as one line,
        each line break and the space around it one space, and the tokens
        of the file within it, moved to where that line puts them."""
        line, col, end_line, end_col = at
        pieces = self.lines[line - 1 : end_line]
        pieces[-1] = pieces[-1][:end_col]
        pieces[0] = pieces[0][col:]
        segment = "\n".join(pieces)
        breaks = [(found.start(), found.end()) for found in BREAK.finditer(segment)]
        found = []
        offset = -col
        for number, piece in zip(range(line, end_line + 1), pieces):
            starts = offset + (col if number == line else 0)
            for first, last, css in self.tokens.get(number, []):
                inside = (max(first + offset, starts), min(last + offset, starts + len(piece)))
                found += [[_moved(inside[0], breaks), _moved(inside[1], breaks), css]] if inside[0] < inside[1] else []
            offset = starts + len(piece) + 1
        return {"text": BREAK.sub(" ", segment), "tokens": found}


class _Plain:
    """The colours of a fragment given as text alone, with no file to take
    tokens from, as a tree a test builds has: none."""

    def span(self, _at, text):
        """text read as one line, as Colours.span reads it, uncoloured."""
        return {"text": BREAK.sub(" ", text), "tokens": []}


# The colours of a fragment with no file.
PLAIN = _Plain()


def _moved(offset, breaks):
    """offset, a character's in a fragment, moved to where it is once each
    of breaks, (start, end) of each line break and the space around it, is
    one space."""
    return offset - sum(end - start - 1 for start, end in breaks if end <= offset)


def label_code(text):
    """The code of a label, eg a row's top, and, or if/else, as page data
    holds it: each of its words that is a keyword coloured k. Labels are
    no fragment of a file, so are never tokenized. Example: if/else gives
    if and else, each a keyword."""
    words = re.finditer(r"\w+", text)
    return {"text": text, "tokens": [[word.start(), word.end(), "k"] for word in words if keyword.iskeyword(word.group())]}


def marked_code(mark, other):
    """The code of a ternary's arm's label: mark, ? or :, coloured as an
    operator, then a space, then other, its code."""
    return joined_code({"text": mark, "tokens": [[0, len(mark), "o"]]}, " ", other)


def joined_code(one, between, other):
    """The code of one, then between, uncoloured, then other, other's
    ranges moved on past one and between. Example: if, / and else give
    if/else, else's range moved on by 3."""
    shift = len(one["text"]) + len(between)
    moved = [[first + shift, last + shift, css] for first, last, css in other["tokens"]]
    return {"text": one["text"] + between + other["text"], "tokens": one["tokens"] + moved}


def _ranges(lengths, start, end):
    """[(line number, first column, last column), ...] of the characters
    from start to end, each a (line, column) pair, on each line they reach,
    kept within the line; none on a line where they hold no character."""
    (first_line, first_col), (last_line, last_col) = start, end
    ranges = []
    for number in range(first_line, last_line + 1):
        first = first_col if number == first_line else 0
        last = last_col if number == last_line else lengths[number - 1]
        if first < last:
            ranges.append((number, first, last))
    return ranges


def _classed(source):
    """[((start, end), class), ...], where each coloured token of source
    starts and ends, as tokenize gives them, and its class. source is
    always a whole file that parsed, never a fragment of one."""
    found = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        css = _class_of(token)
        if css:
            found.append(((token.start, token.end), css))
    return found


def _class_of(token):
    """The class of token: k for a keyword, t for a name starting with a
    capital, as a class's or a constant's does, else as CLASSES has its
    type; None for a token left uncoloured."""
    name = tokenize.tok_name[token.type]
    if name == "NAME":
        if keyword.iskeyword(token.string):
            return "k"
        return "t" if token.string[:1].isupper() else None
    return CLASSES.get(name)


def _joined(ranges):
    """ranges, in order, each touching one of the same class joined to
    it."""
    out = []
    for first, last, css in ranges:
        if out and out[-1][1] == first and out[-1][2] == css:
            out[-1][1] = last
        else:
            out.append([first, last, css])
    return out

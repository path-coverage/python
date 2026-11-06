"""The colours of a file's code on its page, as page data holds them: each
token Python's own tokenize finds gets the class of its kind, eg k for a
keyword, so the page colours it."""

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


def code(text):
    """text, a fragment of code on one line, eg a site tree's operand or a
    card's top, as page data holds it: its text and the [from, to, class]
    of each range coloured as the code it is part of. Example: "if" gives
    {"text": "if", "tokens": [[0, 2, "k"]]}."""
    return {"text": text, "tokens": of(text).get(1, [])}


def label_code(text):
    """The code of a row's or a fold's label, coloured as code colours it;
    but a label naming a choice and its else, eg if/else, each of its
    words, as code would read the / as division. Example: if/else gives if
    and else, each a keyword."""
    if not re.fullmatch(r"\w+/else", text):
        return code(text)
    first, other = text.split("/")
    return joined_code(code(first), "/", code(other))


def ternary_arm_code(label):
    """The code of a ternary's arm's label, eg ? total > 100: its ? or :
    coloured as an operator, the code after it as code."""
    mark, _, rest = label.partition(" ")
    marked = {"text": mark, "tokens": [[0, len(mark), "o"]]}
    return joined_code(marked, " ", code(rest))


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
    always whole code: a file that parsed, or the text of one ast node or
    keyword."""
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

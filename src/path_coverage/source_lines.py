"""The lines of one file, each with the status of the conditions on it,
and the span of lines it shares with them."""

from .gaps import operand_gap


def lines_of(source, sites, operands):
    """[{number, text, status, span}] for each line of source. Lines in one
    span (a (first, last) line pair) share one button on the page; status
    ("covered" or "gaps") and span are None on a line with no condition."""
    marks = _marks(sites, operands)
    return [
        {"number": number, "text": text, **marks.get(number, {"status": None, "span": None})}
        for number, text in enumerate(source.splitlines(), start=1)
    ]


def _marks(sites, operands):
    """{line number: {status, span}} for each line a site covers, every line
    of a merged span sharing that span."""
    marks = {}
    for (first, last), status in _merged(_spans_of(sites, operands)):
        for number in range(first, last + 1):
            marks[number] = {"status": status, "span": (first, last)}
    return marks


def _spans_of(sites, operands):
    """[(span, status)] for each site: from the line its code starts on,
    which may be before the line it is named on, eg an or named at its
    keyword on a line after its first operand's, to the line its last
    operand ends on."""
    return [
        ((condition.extent[0], condition.leaves()[-1].end_line), _status_of(operands[site]))
        for site, condition in sites.items()
    ]


def _merged(spans):
    """The spans merged wherever they overlap, in line order. A merged span
    has gaps if any of its sites has."""
    blocks = []
    for (first, last), status in sorted(spans):
        if blocks and blocks[-1][0][1] >= first:
            (block_first, block_last), block_status = blocks[-1]
            worse = "gaps" if "gaps" in (block_status, status) else "covered"
            blocks[-1] = ((block_first, max(block_last, last)), worse)
        else:
            blocks.append(((first, last), status))
    return blocks


def _status_of(counts):
    """"covered" when no operand has a gap, else "gaps"."""
    gaps = [gap for operand in counts for gap in operand_gap(operand)]
    return "gaps" if gaps else "covered"

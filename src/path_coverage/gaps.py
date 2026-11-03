"""The terminal worklist: one line per path a site never took, and nothing
for a site that took them all."""

import re


def lines(operands, paths, texts):
    """The gap lines, in manifest order, of operands and paths (as
    result.operands and result.paths give them), each leaf named by its
    source text in texts ({site: [text, ...]}), eg
    "k.py:2:4 path never taken: `ok(id)` true, `new(id)` false"."""
    return [
        line
        for site, counts in operands.items()
        for line in _site_gaps(site, counts, paths.get(site, []), texts.get(site, []))
    ]


def _site_gaps(site, operands, paths, texts):
    """One line for a site none of whose leaves ever ran, else one per path
    it never took."""
    if all(_never_ran(counts) for counts in operands):
        return [f"{site} never reached"]
    return [
        f"{site} path never taken: {_steps(each['path'], texts)}"
        for each in paths
        if each["count"] == 0
    ]


def _steps(path, texts):
    """Each leaf path reaches, by its text, with its outcome."""
    return ", ".join(
        f"{code(text)} {str(outcome).lower()}"
        for outcome, text in zip(path, texts)
        if outcome is not None
    )


def code(text):
    """text as a Markdown code span on one line: each run of whitespace one
    space, fenced by a run of backticks one longer than any inside it, with
    a space inside the fence when text starts or ends with one."""
    text = re.sub(r"\s+", " ", text)
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def operand_gap(counts):
    """The one outcome this operand is missing, if any; a fixed leaf, which
    can have one outcome only, needs only to run."""
    if _never_ran(counts):
        return ["never evaluated"]
    if counts.get("only"):
        return []
    if counts["truthy"] == 0:
        return ["never true"]
    if counts["falsy"] == 0:
        return ["never false"]
    return []


def _never_ran(counts):
    """True when the operand was never recorded either way."""
    return counts["truthy"] == 0 and counts["falsy"] == 0

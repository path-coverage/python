"""The terminal worklist: one line per path a decision never took, and nothing
for a decision that took them all."""

import re


def lines(operands, paths, texts):
    """The gap lines, in manifest order, of operands and paths (as
    result.operands and result.paths give them), each leaf named by its
    source text in texts ({decision: [text, ...]}), eg
    "k.py:2:4 path never taken: `ok(id)` true, `new(id)` false"."""
    return [
        line
        for decision, counts in operands.items()
        for line in _decision_gaps(decision, counts, paths.get(decision, []), texts.get(decision, []))
    ]


def _decision_gaps(decision, operands, paths, texts):
    """One line for a decision none of whose leaves ever ran, else one per path
    it never took."""
    if sum(counts["truthy"] + counts["falsy"] for counts in operands) == 0:
        return [f"{decision} never reached"]
    return [
        f"{decision} path never taken: {_steps(each['path'], texts)}"
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
    """text, a leaf's source, as a Markdown code span on one line: each run
    of whitespace one space, fenced by a run of backticks one longer than
    any inside it. A leaf's backticks are only ever inside its strings, so
    it never starts or ends with one, which a fence would need padding
    for."""
    text = re.sub(r"\s+", " ", text)
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    return f"{fence}{text}{fence}"


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

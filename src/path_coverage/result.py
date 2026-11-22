"""What a run found: every decision the manifest knows of, with the counts its
operands were recorded with, and the paths its evaluations took. Every
reporter builds on this."""

from .decision_paths import possible
from .tally import Tally


def paths(decisions, decision_paths):
    """{decision: [{"path": [outcome, ...], "tests": Tally}, ...]} for
    decisions ({decision: Condition}, from the manifest), listing every
    possible path of each, in decision_paths.possible order, with the Tally
    decision_paths ({decision: {(outcome, ...): Tally}}, from Evaluations)
    has for it, or the empty Tally."""
    return {
        decision: [
            {"path": path, "tests": decision_paths.get(decision, {}).get(tuple(path), Tally())}
            for path in possible(condition)
        ]
        for decision, condition in decisions.items()
    }


def operands(decisions, counts):
    """{decision: [counts of operand 0, counts of operand 1, ...]} for decisions
    ({decision: Condition}, from the manifest) and counts ({(decision, index): counts},
    from Evaluations), with empty Tallies for an operand that never ran, and
    only naming the one outcome a fixed leaf can have."""
    return {
        decision: [_leaf(counts, decision, index, leaf) for index, leaf in enumerate(condition.leaves())]
        for decision, condition in decisions.items()
    }


def _leaf(counts, decision, index, leaf):
    """The counts of one leaf, or empty Tallies, with only when it is
    fixed."""
    found = dict(counts.get((decision, index), {"truthy": Tally(), "falsy": Tally()}))
    if leaf.only:
        found["only"] = leaf.only
    return found

"""What a run found: every decision the manifest knows of, with the counts its
operands were recorded with, and the paths its evaluations took. Every
reporter builds on this."""

from .decision_paths import possible


def paths(decisions, decision_paths):
    """{decision: [{"path": [outcome, ...], "count": n}, ...]} for decisions
    ({decision: Condition}, from the manifest), listing every possible path of
    each, in decision_paths.possible order, with the count decision_paths ({decision:
    {(outcome, ...): n}}, from the recorder) has for it, or 0."""
    return {
        decision: [
            {"path": path, "count": decision_paths.get(decision, {}).get(tuple(path), 0)}
            for path in possible(condition)
        ]
        for decision, condition in decisions.items()
    }


def operands(decisions, counts):
    """{decision: [counts of operand 0, counts of operand 1, ...]} for decisions
    ({decision: Condition}, from the manifest) and counts ({(decision, index): counts},
    from the recorder), with zero counts for an operand that never ran, and
    only naming the one outcome a fixed leaf can have."""
    return {
        decision: [_leaf(counts, decision, index, leaf) for index, leaf in enumerate(condition.leaves())]
        for decision, condition in decisions.items()
    }


def _leaf(counts, decision, index, leaf):
    """The counts of one leaf, or zeros, with only when it is fixed."""
    found = dict(counts.get((decision, index), {"truthy": 0, "falsy": 0}))
    if leaf.only:
        found["only"] = leaf.only
    return found

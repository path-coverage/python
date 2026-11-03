"""What a run found: every site the manifest knows of, with the counts its
operands were recorded with. Every reporter builds on this."""


def operands(sites, counts):
    """{site: [counts of operand 0, counts of operand 1, ...]} for sites
    ({site: Condition}, from the manifest) and counts ({(site, index): counts},
    from the recorder), with zero counts for an operand that never ran, and
    only naming the one outcome a fixed leaf can have."""
    return {
        site: [_leaf(counts, site, index, leaf) for index, leaf in enumerate(condition.leaves())]
        for site, condition in sites.items()
    }


def _leaf(counts, site, index, leaf):
    """The counts of one leaf, or zeros, with only when it is fixed."""
    found = dict(counts.get((site, index), {"truthy": 0, "falsy": 0}))
    if leaf.only:
        found["only"] = leaf.only
    return found

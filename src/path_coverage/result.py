"""What a run found: every site the manifest knows of, with the counts its
operands were recorded with, and the paths its evaluations took. Every
reporter builds on this."""

from .site_paths import possible


def paths(sites, site_paths):
    """{site: [{"path": [outcome, ...], "count": n}, ...]} for sites
    ({site: Condition}, from the manifest), listing every possible path of
    each, in site_paths.possible order, with the count site_paths ({site:
    {(outcome, ...): n}}, from the recorder) has for it, or 0."""
    return {
        site: [
            {"path": path, "count": site_paths.get(site, {}).get(tuple(path), 0)}
            for path in possible(condition)
        ]
        for site, condition in sites.items()
    }


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

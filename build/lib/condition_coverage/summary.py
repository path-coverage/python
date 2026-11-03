"""The per-file numbers the HTML index page shows."""

import re


def files(operands):
    """One row per file that has sites in operands (as result.operands gives
    them), in path order."""
    by_path = {}
    for site, site_operands in operands.items():
        by_path.setdefault(path_of(site), []).append(site_operands)
    return [_row(path, sites) for path, sites in sorted(by_path.items())]


def _row(path, sites):
    """The summary row of one file, from the operands of each of its sites."""
    operands = [counts for site_operands in sites for counts in site_operands]
    outcomes = sum(1 if counts.get("only") else 2 for counts in operands)
    seen = sum((counts["truthy"] > 0) + (counts["falsy"] > 0) for counts in operands)
    return {
        "path": path,
        "sites": len(sites),
        "seen": seen,
        "outcomes": outcomes,
        "percent": round(100 * seen / outcomes),
        "missing": outcomes - seen,
    }


def path_of(site):
    """The file a site is in: its name minus :line:column."""
    return re.sub(r":\d+:\d+\Z", "", site)

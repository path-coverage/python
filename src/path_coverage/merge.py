"""Adds several runs' results together, so a report shows only the gaps
that every run left. Counts are summed: a union that de-duplicates, as
coverage.py's combine does for lines, would lose them."""


def merge(runs):
    """The operands of runs (each as result.operands gives them) with each
    operand's truthy and falsy counts added across them, keeping only."""
    merged = {}
    for run in runs:
        for site, operands in run.items():
            if site not in merged:
                merged[site] = [dict(counts) for counts in operands]
                continue
            for total, counts in zip(merged[site], operands):
                total["truthy"] += counts["truthy"]
                total["falsy"] += counts["falsy"]
    return merged


def merge_paths(runs):
    """The paths of runs (each as result.paths gives them) with each path's
    count added across them, in the order the paths first appear."""
    merged = {}
    for run in runs:
        for site, paths in run.items():
            totals = merged.setdefault(site, {})
            for each in paths:
                key = tuple(each["path"])
                totals[key] = totals.get(key, 0) + each["count"]
    return {
        site: [{"path": list(path), "count": count} for path, count in totals.items()]
        for site, totals in merged.items()
    }

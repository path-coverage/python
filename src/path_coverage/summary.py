"""The per-file numbers the HTML index page shows, and their total over
every file."""

import re
from pathlib import PurePosixPath

from . import totals


def files(paths, cards):
    """One row per file that has sites in paths (as result.paths gives
    them), in path order: its sites, its decisions total, and its methods
    total, its cards in cards, {card site: [taken, size]}, added up."""
    by_path = {}
    for site, site_paths in paths.items():
        by_path.setdefault(path_of(site), {})[site] = site_paths
    return [
        {
            "path": path,
            "sites": len(sites),
            "decisions": totals.decisions(sites),
            "methods": _methods_of(path, cards),
        }
        for path, sites in sorted(by_path.items())
    ]


def _methods_of(path, cards):
    """The methods total of the file at path, its functions' cards added
    up; [0, 0] for a file with no function."""
    return totals.methods({site: card for site, card in cards.items() if path_of(site) == path})


def total(rows):
    """The sum of each column over rows; no rows, as for a group no file is
    in, gives 0 sites and [0, 0] totals."""
    return {
        "sites": sum(row["sites"] for row in rows),
        "decisions": _add(row["decisions"] for row in rows),
        "methods": _add(row["methods"] for row in rows),
    }


def groups(rows, named):
    """[name, rows, total] for each of named, {name: [glob, ...]}, in order:
    the rows whose path matches any of its globs, and their total. Then
    Ungrouped, the rows no group matches, when there are any."""
    grouped = []
    for name, globs in named.items():
        own = [row for row in rows if matches(row["path"], globs)]
        grouped.append([name, own, total(own)])
    every = [glob for globs in named.values() for glob in globs]
    rest = [row for row in rows if not matches(row["path"], every)]
    if rest:
        grouped.append(["Ungrouped", rest, total(rest)])
    return grouped


def matches(path, globs):
    """True when path, relative to root, matches any of globs, as cover
    globs match."""
    return any(PurePosixPath(path).full_match(glob) for glob in globs)


def _add(pairs):
    """[taken, possible] pairs added together; [0, 0] for no pairs, as a
    group matching no file has."""
    taken = possible = 0
    for pair_taken, pair_possible in pairs:
        taken += pair_taken
        possible += pair_possible
    return [taken, possible]


def path_of(site):
    """The file a site is in: its name minus :line:column."""
    return re.sub(r":\d+:\d+\Z", "", site)

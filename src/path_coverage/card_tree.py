"""How the rows of each card nest: for each row, the site it runs inside,
the arm of that site it is in, and the paths of that site on which it runs,
so a reader can tell which paths reach a row."""

from dataclasses import dataclass

from . import method_statements, site_paths, site_tree
from .manifest import Arm, Condition
from .manifest import sites as find_sites

# The place of a row inside no other row's site.
TOP = {"parent": None, "in": None, "on": None, "leaf": None, "gives": None}


@dataclass(frozen=True)
class Region:
    """Part of a site's code that a row can be inside: an arm of code, or a
    leaf. owner is the key of the site's row; begin and end its bytes, end
    exclusive; arm its arm's kind, None for a leaf; on the indices of the
    site's possible paths that run it; leaf a leaf's index among the site's
    leaves, None for an arm."""

    owner: str
    begin: int
    end: int
    arm: str | None
    on: tuple
    leaf: int | None


def of(source, path, sites=None):
    """{def site: {"line:col": place}} for each function in source, as
    nested places its rows. Example: def f(a): if a: x = 1 gives the write
    the if as its parent, in its then arm, on its path 0."""
    sites = find_sites(source, path) if sites is None else sites
    return {
        site: nested(source, sites, rows) for site, rows in method_statements.of(source, path).items()
    }


def nested(source, sites, rows):
    """{"line:col": place} of each of rows, a card's, sites being {site:
    Condition}: each placed in the innermost region of another row's site
    holding all of its own site's code, or, for a row that is no site, where
    it starts. A place is {"parent": the "line:col" of that site, "in": its
    arm's kind, "on": the indices of that site's possible paths, as
    site_paths.possible orders them, that run the row, "leaf": the index of
    the leaf holding it, "gives": None}; TOP for a row in no region."""
    starts = _line_starts(source)
    regions = [
        region
        for row in rows
        if row.site
        for region in _regions(source, starts, key_of(row), sites[row.site])
    ]
    places = {}
    for row in rows:
        at = starts[row.line - 1] + row.column
        site = sites[row.site] if row.site else None
        span = _span(starts, site.extent) if site else (at, at + 1)
        places[key_of(row)] = _placed(key_of(row), span, regions, site)
    return places


def _placed(key, span, regions, site):
    """The place of the row keyed key, its code the bytes span, site its
    Condition, None for a row that is no site: in the site owning the
    smallest region of another row holding span; TOP for none."""
    holding = [
        region
        for region in regions
        if region.owner != key and region.begin <= span[0] and span[1] <= region.end
    ]
    if not holding:
        return dict(TOP)
    owner = _smallest(holding).owner
    own = [region for region in holding if region.owner == owner]
    arm = _smallest([region for region in own if region.arm])
    on = sorted(set.intersection(*(set(region.on) for region in own)))
    leaf = _smallest([region for region in own if region.arm is None]) if site else None
    whole = leaf is not None and (leaf.begin, leaf.end) == span
    return {
        "parent": owner,
        "in": arm.arm if arm else None,
        "on": on,
        "leaf": leaf.leaf if leaf else None,
        "gives": site_paths.values(site) if whole else None,
    }


def _smallest(regions):
    """The region of regions with the fewest bytes; None for none."""
    return min(regions, key=lambda region: region.end - region.begin, default=None)


def regions_of(source, owner, condition):
    """The regions of condition, the site of the row keyed owner, in
    source, as nested finds them."""
    return _regions(source, _line_starts(source), owner, condition)


def text_of(source, region):
    """The source text of region's bytes."""
    return source.encode()[region.begin : region.end].decode()


def _regions(source, starts, owner, condition):
    """The regions of condition, the site of the row keyed owner: its
    arms', then its leaves'."""
    possible = site_paths.possible(condition)
    node = site_tree.node(source, condition, possible)
    return _arm_regions(starts, owner, condition, node) + _leaf_regions(
        starts, owner, condition, possible
    )


def _leaf_regions(starts, owner, condition, possible):
    """The regions of condition's leaves, in no arm, each run on the paths
    of possible with an outcome at its index."""
    regions = []
    for index, leaf in enumerate(condition.leaves()):
        on = tuple(i for i, path in enumerate(possible) if path[index] is not None)
        begin, end = _span(starts, (leaf.line, leaf.col, leaf.end_line, leaf.end_col))
        regions.append(Region(owner, begin, end, None, on, index))
    return regions


def _arm_regions(starts, owner, condition, node):
    """The regions of the arms in condition, node its tree: of its own
    arms, and of those of each condition nested in it, in an operand or in
    an arm's body."""
    regions = []
    for operand, operand_node in zip(condition.operands, node["operands"]):
        if isinstance(operand, Condition):
            regions += _arm_regions(starts, owner, operand, operand_node)
        elif isinstance(operand, Arm):
            regions += _arm_region(starts, owner, operand, operand_node)
    return regions


def _arm_region(starts, owner, arm, node):
    """The regions of arm, node its node: its own, named by its kind and
    run on the paths that take it, none for an arm of no code, which holds
    no row; then its body's."""
    body = _arm_regions(starts, owner, arm.body, node["body"]) if arm.body else []
    if arm.extent is None:
        return body
    on = tuple(i for i, took in enumerate(node["cells"]) if took is True)
    begin, end = _span(starts, arm.extent)
    return [Region(owner, begin, end, arm.kind, on, None), *body]


def key_of(row):
    """The "line:col" key of row, from its name."""
    return ":".join(row.name.split(":")[-2:])


def _line_starts(source):
    """The byte offset where each line of source starts, first line
    first."""
    starts = [0]
    for line in source.encode().splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _span(starts, extent):
    """(begin, end) bytes of extent, (line, col, end_line, end_col) as ast
    counts them, starts being _line_starts'."""
    line, col, end_line, end_col = extent
    return (starts[line - 1] + col, starts[end_line - 1] + end_col)

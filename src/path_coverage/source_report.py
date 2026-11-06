"""What a renderer needs of each covered file beyond the JSON report's
counts, worked out from its source, so it can draw the file's page without
parsing the source itself."""

from . import code_tokens, fold_rows, site_locations, site_tree, summary

# The version of the source report's shape.
SCHEMA = 1


def of(files, paths, cards, groups):
    """The source report of a run: no operators ignored, the covered files
    of each of groups, {name: [glob, ...]} or None, each top of the rows of
    cards, {card site: card}, coloured, and each of files', {path: (source,
    sites)}, lines and sites, each site's paths as paths has them, its fold
    headed by its row's top."""
    rows = [row for card in cards.values() for row in card["rows"]]
    tops = {row["site"]: row["top"] for row in rows}
    shown = {path: _file(source, sites, paths, tops) for path, (source, sites) in files.items()}
    return {
        "schema": SCHEMA,
        "ignored": [],
        "groups": {name: [path for path in shown if summary.matches(path, globs)] for name, globs in (groups or {}).items()},
        "labels": {top: code_tokens.label_code(top) for top in dict.fromkeys(row["top"] for row in rows)},
        "files": shown,
    }


def _file(source, sites, paths, tops):
    """One file's lines and sites."""
    shown = {name: site(source, sites, name, paths[name], tops[name]) for name in sites}
    return {"lines": lines(source), "sites": shown}


def lines(source):
    """Example: "ok(1)\\n" gives [{"text": "ok(1)", "tokens": [[3, 4, "n"]]}].
    Each line of source: its text and its coloured tokens."""
    tokens = code_tokens.of(source)
    return [{"text": text, "tokens": tokens.get(number, [])} for number, text in enumerate(source.splitlines(), start=1)]


def site(source, sites, name, paths, top):
    """Example: ok(id) and new(id) on line 2 gives span [2, 2].
    The site named name, of sites, {name: Condition}, in source: the
    [first, last] lines it spans, from the line its code starts on, and its
    fold's rows, headed by top, its row's top, a column for each of paths,
    [{"path", "count"}], in their order, with no counts."""
    condition = sites[name]
    span = [condition.extent[0], condition.leaves()[-1].end_line]
    return {"span": span, "fold": _fold(source, condition, paths, top)}


def _fold(source, condition, paths, top):
    """The rows of condition's fold, headed by top, its site row with no
    counts."""
    tree = site_tree.node(source, condition, [taken["path"] for taken in paths])
    located = site_locations.located(source, condition, tree)
    else_at = site_locations.else_at(source, condition)
    own, *rest = fold_rows.rows({**located, "counts": None, "else_at": else_at, "label": top})
    return [{key: value for key, value in own.items() if key != "counts"}, *rest]

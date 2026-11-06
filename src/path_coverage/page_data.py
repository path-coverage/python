"""The data of each page of the HTML report, as the shared renderer's
schema.json has it: what the page draws, every number it shows that is not a
plain count worked out here, so the page and the console never disagree."""

from . import code_tokens

# The version of schema.json the data follows.
SCHEMA = 1


def index(tables, ignored):
    """The index page's data: tables, [name, rows, total] for All files
    then each group, rows and total as summary gives them, and the
    operators ignored. Example: an index of one file, ship.py, no groups."""
    shown = [
        {"name": name, "rows": [{"path": row["path"], **totals(row)} for row in rows], "total": totals(total)}
        for name, rows, total in tables
    ]
    return {"schema": SCHEMA, "page": "index", "tables": shown, "ignored": ignored}


def totals(row):
    """A row's sites, its [taken, possible] paths within each method, and
    their percent, rounded; None with none possible."""
    methods = row["methods"]
    return {"sites": row["sites"], "methods": methods, "percent": percent(methods)}


def percent(pair):
    """The percent of possible paths taken, rounded half up; None when none
    is possible. Example: [1, 3] gives 33, [1, 8] 13, [0, 0] None."""
    taken, possible = pair
    return None if possible == 0 else int(100 * taken / possible + 0.5)


def file(path, lines, cards):
    """A file page's data: the file at path, its lines, each with its
    tokens, as html_report colours them, and its cards, as card gives
    each."""
    return {"schema": SCHEMA, "page": "file", "path": path, "lines": [line_of(line) for line in lines], "cards": cards}


def line_of(line):
    """One line's data: its text and tokens, and the status and [first,
    last] span of the sites it is in, None for none."""
    span = line["span"]
    return {
        "text": line["text"],
        "tokens": line["tokens"],
        "status": line["status"],
        "span": list(span) if span else None,
    }


def status(card):
    """card's status, as listed_cards gives it: covered when every row's
    taken is known and is all of its paths, and its function was called, if
    it is a function's; gaps otherwise, as a row not known may have one,
    and a function never called, even of no rows, ran none of its code.
    Example: a card whose rows took all their paths, called, is covered."""
    done = all(row["taken"] == row["paths"] for row in card["rows"]) and card["calls"] != 0
    return "covered" if done else "gaps"


def card(listed, place, fold):
    """The data of a card, listed as listed_cards gives it, placed as place
    has it: its first and last lines, its column, its status, whether it is
    a top card, and a top card's count of sites. fold gives the rows of a
    site's fold, from the site and its row's top."""
    rows = listed["rows"]
    return {**place, "title": title(listed, rows), "rows": [row_of(row, fold) for row in rows]}


def title(listed, rows):
    """The title of a card: its name, how many times its function was
    called, its ways, and how many of its rows' paths were not taken, and
    how many were."""
    taken = sum(row["taken"] or 0 for row in rows)
    size = sum(row["paths"] for row in rows)
    return {
        "name": listed["name"],
        "calls": listed["calls"],
        "ways": listed["ways"],
        "notTaken": size - taken,
        "taken": taken,
    }


def row_of(row, fold):
    """One card row's data, as listed_cards lists it, its top coloured, and
    a site's row its fold."""
    site = row["site"]
    return {
        "at": row["at"],
        "site": site,
        "top": code_tokens.label_code(row["top"]),
        "paths": row["paths"],
        "taken": row["taken"],
        "fold": fold(site, row["top"]) if site else None,
    }

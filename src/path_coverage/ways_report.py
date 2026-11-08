"""A function card's taken ways, and its for loops' passes, as the JSON
report lists them, and read back from a report: each way the steps one
call, or one pass, took, in order, a decision row's {"at", "path"}, a for
loop's {"at", "path"}, its path how many passes it made, or a statement
row's {"at"}, with how many took it."""

import json


def taken(walked):
    """[{"way": [step, ...], "count": n}] of walked, {way: n}, one unit's
    ways as Evaluations.ways has them, in the order first taken. Example:
    {(("k.py:2:4", (True,)), ("k.py:4:8",)): 1} gives
    [{"way": [{"at": "2:04", "path": [True]}, {"at": "4:08"}], "count": 1}]."""
    return [{"way": way(each), "count": count} for each, count in walked.items()]


def way(steps):
    """[step, ...] of steps, one way as Evaluations.ways has it, as the
    JSON report lists a way. Example: (("k.py:4:8",),) gives
    [{"at": "4:08"}]."""
    return [_step(step) for step in steps]


def ways(report):
    """{function's entry, or for loop's name: {way: count}} of a JSON
    report's cards, as Evaluations.ways has them, from each card listing
    its taken ways and its loops' passes; a top card lists neither, as no
    call runs it."""
    found = {}
    for entry, card in report["cards"].items():
        if "taken" in card:
            found[entry] = _read(entry, card["taken"])
            for loop, passes in card["passes"].items():
                name = _name(_file(entry), loop)
                found[name] = _read(name, passes)
    return found


def listed(ways):
    """{unit's name: its ways, as taken lists them} of ways, as
    Evaluations.ways has them, eg a part's: each function's calls' and
    each for loop's passes'."""
    return {unit: taken(walked) for unit, walked in ways.items()}


def unlisted(listed_ways):
    """ways as Evaluations.ways has them, from listed_ways, as listed
    gives them."""
    return {unit: _read(unit, each) for unit, each in listed_ways.items()}


def at(name):
    """The line:column of the row or loop named name, the column two
    digits, as the card's rows have it. Example: "k.py:4:8" gives "4:08"."""
    _, line, column = name.rsplit(":", 2)
    return f"{line}:{int(column):02d}"


def _read(unit, listed_ways):
    """{way: count} of listed_ways, the unit named unit's, as the JSON
    report lists them."""
    file = _file(unit)
    return {tuple(_named(file, step) for step in each["way"]): each["count"] for each in listed_ways}


def _step(step):
    """A step as the JSON report lists it: its row's at and, for a
    decision's, or a loop's, its path; for a loop's, the distinct ways its
    passes took, ordered by their JSON text, as a set has no order."""
    if len(step) == 1:
        return {"at": at(step[0])}
    listed = {"at": at(step[0]), "path": list(step[1])}
    if len(step) == 3:
        listed["passes"] = sorted((way(each) for each in step[2]), key=json.dumps)
    return listed


def _named(file, step):
    """A step of the JSON report, in file, as Evaluations.ways has it."""
    name = _name(file, step["at"])
    if "passes" in step:
        return (name, tuple(step["path"]), frozenset(tuple(_named(file, each) for each in way) for way in step["passes"]))
    if "path" in step:
        return (name, tuple(step["path"]))
    return (name,)


def _name(file, at_label):
    """The name in file of the row or loop at at_label, as at gives it.
    Example: "k.py" and "4:08" give "k.py:4:8"."""
    line, column = at_label.split(":")
    return f"{file}:{line}:{int(column)}"


def _file(name):
    """The file of the unit, row or loop named name."""
    return name.rsplit(":", 2)[0]

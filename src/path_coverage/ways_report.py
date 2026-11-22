"""A function flow's taken ways, and its for loops' passes, as the JSON
report lists them, and read back from a report: each way the steps one
call, or one pass, took, in order, a decision row's {"at", "path"}, a for
loop's {"at", "path"}, its path how many passes it made, or a statement
row's {"at"}, with the Tally of the tests that took it."""

import json

from . import tally


def taken(walked):
    """[{"way": [step, ...], "tests": Tally}] of walked, {way: Tally}, one
    unit's ways as Evaluations.ways has them, in the order first taken.
    Example: {(("k.py:2:4", (True,)), ("k.py:4:8",)): t} gives
    [{"way": [{"at": "2:04", "path": [True]}, {"at": "4:08"}], "tests": t}]."""
    return [{"way": way(each), "tests": counted} for each, counted in walked.items()]


def way(steps):
    """[step, ...] of steps, one way as Evaluations.ways has it, as the
    JSON report lists a way. Example: (("k.py:4:8",),) gives
    [{"at": "4:08"}]."""
    return [_step(step) for step in steps]


def ways(report):
    """{function's entry, or for loop's name: {way: Tally}} of a JSON
    report's flows, as Evaluations.ways has them, from each flow listing
    its taken ways and its loops' passes, by the report's tests; a top
    flow lists neither, as no call runs it."""
    found = {}
    for entry, flow in report["flows"].items():
        if "taken" in flow:
            found[entry] = _read(entry, flow["taken"], report["tests"])
            for loop, passes in flow["passes"].items():
                name = _name(_file(entry), loop)
                found[name] = _read(name, passes, report["tests"])
    return found


def listed(ways):
    """{unit's name: its ways, as taken lists them} of ways, as
    Evaluations.ways has them, eg a part's: each function's calls' and
    each for loop's passes'."""
    return {unit: taken(walked) for unit, walked in ways.items()}


def unlisted(listed_ways, tests):
    """ways as Evaluations.ways has them, from listed_ways, as listed
    gives them in a JSON file whose tests are tests, {key: test id}."""
    return {unit: _read(unit, each, tests) for unit, each in listed_ways.items()}


def at(name):
    """The line:column of the row or loop named name, the column two
    digits, as the flow's rows have it. Example: "k.py:4:8" gives "4:08"."""
    _, line, column = name.rsplit(":", 2)
    return f"{line}:{int(column):02d}"


def _read(unit, listed_ways, tests):
    """{way: Tally} of listed_ways, the unit named unit's, as the JSON
    report lists them, tests being its {key: test id}."""
    file = _file(unit)
    return {tuple(_named(file, step) for step in each["way"]): tally.read(each["tests"], tests) for each in listed_ways}


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

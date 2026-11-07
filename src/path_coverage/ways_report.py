"""A function card's taken ways as the JSON report lists them, and read
back from a report: each way the steps one call took, in order, a
decision row's {"at", "path"} or a statement row's {"at"}, with how many
calls took it."""


def taken(walked):
    """[{"way": [step, ...], "count": calls}] of walked, {way: calls}, one
    function's ways as Evaluations.ways has them, in the order first
    taken. Example: {(("k.py:2:4", (True,)), ("k.py:4:8",)): 1} gives
    [{"way": [{"at": "2:04", "path": [True]}, {"at": "4:08"}], "count": 1}]."""
    listed = []
    for way, count in walked.items():
        listed.append({"way": [_step(step) for step in way], "count": count})
    return listed


def ways(report):
    """{function's entry: {way: calls}} of a JSON report's cards, as
    Evaluations.ways has them, from each card listing its taken ways; a
    top card lists none, as no call runs it."""
    found = {}
    for entry, card in report["cards"].items():
        if "taken" in card:
            file = entry.rsplit(":", 2)[0]
            found[entry] = {tuple(_named(file, step) for step in each["way"]): each["count"] for each in card["taken"]}
    return found


def _step(step):
    """A step as the JSON report lists it: its row's at, line:column, the
    column two digits, as the card's rows have it, and, for a decision's,
    its path."""
    _, line, column = step[0].rsplit(":", 2)
    at = f"{line}:{int(column):02d}"
    if len(step) == 1:
        return {"at": at}
    return {"at": at, "path": list(step[1])}


def _named(file, step):
    """A step of the JSON report, in file, as Evaluations.ways has it."""
    line, column = step["at"].split(":")
    name = f"{file}:{line}:{int(column)}"
    if "path" in step:
        return (name, tuple(step["path"]))
    return (name,)

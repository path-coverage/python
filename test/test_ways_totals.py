from path_coverage.ways_totals import failed, lines
from tallies import untested

WAY = [{"at": "4:08", "path": [True]}, {"at": "6:04"}]


def test_b81f4a01():
    """Example: a report of total, 3 ways, 2 covered, and price, more
    paths than max_paths 8 allows, beside a top flow, reported with
    max_paths 8
    The totals are read from the report's JSON alone: the ways covered
    out of every listed function's ways, then how many functions have
    more paths than max_paths, naming its value. A top flow, which no
    call runs, counts in neither."""
    total = {
        "name": "total", "ways": 3, "taken": [], "covered": [{"way": WAY, "tests": untested(1)}] * 2, "gaps": [WAY], "impossible_taken": [],
    }
    price = {"name": "price", "ways": 27, "taken": []}
    top = {"name": "<module>", "ways": 2}
    report = {"max_paths": 8, "flows": {"src/a.py:1:0": total, "src/b.py:3:0": price, "src/b.py:1:0": top}}
    assert lines(report) == [
        "Paths: 2 / 3 (66.67%)",
        "Functions over --max-paths=8: 1",
    ]


def test_b81f4a02():
    """Example: reports with no function over max_paths 8: total, 3 ways,
    2 covered, its other way a gap; total with all 3 covered; no function
    at all; two functions, all covered; and two, one with a gap
    A report with a path no test took fails, as one with a function over
    max_paths does; one with every path taken does not, nor one with no
    function."""
    gapped = {
        "name": "total", "ways": 3, "taken": [], "covered": [{"way": WAY, "tests": untested(1)}] * 2, "gaps": [WAY], "impossible_taken": [],
    }
    tested = {**gapped, "covered": [{"way": WAY, "tests": untested(1)}] * 3, "gaps": []}
    listings = [[gapped], [tested], [], [tested, tested], [tested, gapped]]
    reports = [{"max_paths": 8, "flows": {f"src/a.py:{line}:0": flow for line, flow in enumerate(flows, 1)}} for flows in listings]
    assert [failed(report) for report in reports] == [True, False, False, False, True]


def test_b81f4a03():
    """Example: a report of retry, every possible path taken, but a call
    took a path its # path: impossible comment declared impossible
    A report where a call took a path declared impossible fails: the
    declaration is wrong, and the worklist says to remove it."""
    retry = {"name": "retry", "ways": 1, "taken": [], "covered": [{"way": WAY, "tests": untested(1)}], "gaps": [], "impossible_taken": [WAY]}
    assert failed({"max_paths": 8, "flows": {"src/retry.py:2:0": retry}}) is True

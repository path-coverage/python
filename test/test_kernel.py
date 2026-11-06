import json
import sys
from pathlib import Path

import pytest

import path_coverage

PROJECTS = Path(__file__).parent / "projects"


def _imported(project, module_name):
    """module_name imported from project's src/, which is then taken off
    sys.path and out of sys.modules so no other test sees it."""
    src = str(project / "src")
    sys.path.insert(0, src)
    try:
        return __import__(module_name)
    finally:
        sys.path.remove(src)
        sys.modules.pop(module_name, None)


NEW = '`trails[trail_id]["new"]`'
LEAVES = [["6:11", "6:29"], ["6:34", "6:57"]]


def _taken(tt, tf, f):
    """single_and_trails' decision's paths, taken tt, tf and f times."""
    return [
        {"path": [True, True], "count": tt},
        {"path": [True, False], "count": tf},
        {"path": [False, None], "count": f},
    ]


def test_e5a70c01(tmp_path, capsys):
    """Example: trail_id in trails and trails[trail_id]["new"], called
    with a new trail, then with no trails
    A covered module imported after start is instrumented.
    The report at exit writes every decision's counts and paths as JSON.
    Each path has its count, and each leaf its line:col span.
    It names the kinds measured, as runs measuring others differ.
    It lists each card, is_new's here, a row for its and, its 3 ways and
    its 2 calls, and how each card's rows nest: the and at the top, inside
    no other decision.
    is_new's entry is reached on each call; it has no row that is no decision.
    It prints the one path never taken: true, then false."""
    project = PROJECTS / "single_and"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/**/*.py"],
        coverage_dir=tmp_path,
        on_exit=exits.append,
    )
    try:
        trails = _imported(project, "single_and_trails")
        assert trails.is_new("T1", {"T1": {"new": True}}) is True
        assert trails.is_new("T2", {}) is False
    finally:
        path_coverage.stop()
    [report] = exits
    report()
    decision = "src/single_and_trails.py:6:30"
    assert json.loads((tmp_path / "path_coverage.json").read_text()) == {
        "$schema": "https://path-coverage.github.io/schemas/v1/path_coverage.schema.json",
        "decisions": {
            decision: [
                {"truthy": 1, "falsy": 1},
                {"truthy": 1, "falsy": 0},
            ]
        },
        "paths": {decision: {"leaves": LEAVES, "taken": _taken(1, 0, 1)}},
        "kinds": ["block", "case", "chain", "choice"],
        "reached": {"src/single_and_trails.py:4:0": 2},
        "totals": {"alone": [2, 3], "combined": [2, 3]},
        "cards": {
            "src/single_and_trails.py:4:0": {
                "name": "is_new",
                "first": 4,
                "last": 6,
                "ways": 3,
                "calls": 2,
                "rows": [{"at": "6:30", "top": "and", "paths": 3, "taken": 2, "decision": decision}],
            }
        },
        "tree": {
            "src/single_and_trails.py": {
                "4:0": {
                    "6:30": {"parent": None, "in": None, "on": None, "leaf": None, "gives": None}
                }
            }
        },
    }
    assert capsys.readouterr().out == (
        f"{decision} path never taken: `trail_id in trails` true, {NEW} false\n"
    )


def test_e5a70c17(tmp_path, capsys):
    """Example: trail_id in trails and trails[trail_id]["new"], called
    with a new trail
    The report at exit writes the source report beside the JSON report:
    each covered file's lines, all 6 of single_and_trails.py's, and its
    decisions, and each card row's top coloured, and here."""
    project = PROJECTS / "single_and"
    exits = []
    path_coverage.start(root=project, cover=["src/**/*.py"], coverage_dir=tmp_path, on_exit=exits.append)
    try:
        trails = _imported(project, "single_and_trails")
        assert trails.is_new("T1", {"T1": {"new": True}}) is True
    finally:
        path_coverage.stop()
    [report] = exits
    report()
    capsys.readouterr()
    source = json.loads((tmp_path / "path_coverage.source.json").read_text())
    file = source["files"]["src/single_and_trails.py"]
    assert len(file["lines"]) == 6
    assert list(file["decisions"]) == ["src/single_and_trails.py:6:30"]
    assert source["labels"] == {"and": {"text": "and", "tokens": [[0, 3, "k"]]}}


def test_e5a70c02(tmp_path, capsys):
    """start_from_env takes root, comma-separated cover globs and the
    coverage dir from PATH_COVERAGE_* variables."""
    project = PROJECTS / "single_and"
    exits = []
    started = path_coverage.start_from_env(
        {
            "PATH_COVERAGE_ROOT": str(project),
            "PATH_COVERAGE_COVER": "lib/*.py,src/**/*.py",
            "PATH_COVERAGE_DIR": str(tmp_path),
        },
        on_exit=exits.append,
    )
    try:
        trails = _imported(project, "single_and_trails")
        assert trails.is_new("T3", {"T3": {"new": False}}) is False
    finally:
        path_coverage.stop()
    assert started is True
    [report] = exits
    report()
    decision = "src/single_and_trails.py:6:30"
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["paths"][decision]["taken"] == _taken(0, 1, 0)
    assert capsys.readouterr().out == (
        f"{decision} path never taken: `trail_id in trails` true, {NEW} true\n"
        f"{decision} path never taken: `trail_id in trails` false\n"
    )


def test_e5a70c04(tmp_path, capsys):
    """Example: an xdist worker taking two of the and's paths, and the
    main run none
    A part run writes only its own part file.
    The main run clears stale parts as it starts.
    At exit it adds every part's counts and paths to its own.
    Then it writes the report and prints the one path left untaken."""
    project = PROJECTS / "single_and"
    stale = tmp_path / "path_coverage.gw7.json"
    stale.parent.mkdir(exist_ok=True)
    stale.write_text('{"decisions": {}}')
    settings = {"root": project, "cover": ["src/**/*.py"], "coverage_dir": tmp_path}
    main_exits, worker_exits = [], []
    path_coverage.start(**settings, on_exit=main_exits.append)
    path_coverage.stop()
    assert not stale.exists()
    path_coverage.start(**settings, part="gw0", on_exit=worker_exits.append)
    try:
        trails = _imported(project, "single_and_trails")
        assert trails.is_new("T4", {"T4": {"new": True}}) is True
        assert trails.is_new("T5", {"T5": {"new": False}}) is False
    finally:
        path_coverage.stop()
    worker_exits[0]()
    assert capsys.readouterr().out == ""
    assert sorted(p.name for p in tmp_path.iterdir()) == ["path_coverage.gw0.json"]
    main_exits[0]()
    decision = "src/single_and_trails.py:6:30"
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["decisions"] == {
        decision: [
            {"truthy": 2, "falsy": 0},
            {"truthy": 1, "falsy": 1},
        ]
    }
    assert report["paths"][decision]["taken"] == _taken(1, 1, 0)
    assert capsys.readouterr().out == (
        f"{decision} path never taken: `trail_id in trails` false\n"
    )


def test_e5a70c05(tmp_path, capsys):
    """start_from_env passes a part name through to start."""
    project = PROJECTS / "single_and"
    exits = []
    path_coverage.start_from_env(
        {
            "PATH_COVERAGE_ROOT": str(project),
            "PATH_COVERAGE_COVER": "src/**/*.py",
            "PATH_COVERAGE_DIR": str(tmp_path),
        },
        part="gw3",
        on_exit=exits.append,
    )
    path_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == ""
    assert [p.name for p in tmp_path.iterdir()] == ["path_coverage.gw3.json"]


def test_e5a70c06(tmp_path, capsys):
    """A covered file the run never imported is still reported, every decision
    in it as never reached."""
    project = PROJECTS / "never_imported"
    exits = []
    path_coverage.start(
        root=project, cover=["src/*.py"], coverage_dir=tmp_path, on_exit=exits.append
    )
    try:
        flows = _imported(project, "never_imported_flows")
        assert flows.is_public({"public": False, "owner": "everyone"}) is True
        assert flows.is_public({"public": True, "owner": "kosli"}) is True
    finally:
        path_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == (
        "src/never_imported_flows.py:6:26 path never taken: "
        '`flow["public"]` false, `flow["owner"] == "everyone"` false\n'
        "src/never_imported_policies.py:6:29 never reached\n"
    )


def test_e5a70c07(tmp_path, capsys):
    """report=[] writes the JSON report and the source report, and prints
    nothing. The source report has each decision's tree folded under it,
    coloured as code."""
    project = PROJECTS / "single_and"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/**/*.py"],
        coverage_dir=tmp_path,
        report=[],
        on_exit=exits.append,
    )
    try:
        trails = _imported(project, "single_and_trails")
        assert trails.is_new("T6", {}) is False
    finally:
        path_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == ""
    source = json.loads((tmp_path / "path_coverage.source.json").read_text())
    decisions = source["files"]["src/single_and_trails.py"]["decisions"]
    leaf = decisions["src/single_and_trails.py:6:30"]["fold"][2]["label"]
    assert leaf == {"text": 'trails[trail_id]["new"]', "tokens": [[17, 22, "s"]]}


def test_e5a70c08(tmp_path):
    """An unknown reporter is refused by name, listing the known ones, eg
    html, whose report html-reporter draws from the JSON."""
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            root=PROJECTS / "single_and",
            cover=["src/**/*.py"],
            coverage_dir=tmp_path,
            report=["gaps", "html"],
            on_exit=lambda report: None,
        )
    assert str(refused.value) == "unknown reporter 'html'; the reporters are: gaps, post, summary"


def test_e5a70c09(tmp_path, capsys):
    """start_from_env takes the reporters, comma-separated, from
    PATH_COVERAGE_REPORT: summary alone prints the totals, none of the and's
    3 paths taken as nothing was imported, and no gaps."""
    exits = []
    path_coverage.start_from_env(
        {
            "PATH_COVERAGE_ROOT": str(PROJECTS / "single_and"),
            "PATH_COVERAGE_COVER": "src/**/*.py",
            "PATH_COVERAGE_DIR": str(tmp_path),
            "PATH_COVERAGE_REPORT": "summary",
        },
        on_exit=exits.append,
    )
    path_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == (
        "Paths alone: 0 / 3 (0.00%)\n"
        "Paths combined: 0 / 3 (0.00%)\n"
    )


def test_e5a70c0a(tmp_path, capsys):
    """Example: fee, a write, if member, if big and a return, called once
    with member and not big
    Each call of fee is counted, as its entry reached, and each run of a
    row that is no decision, its return; its writes are no rows.
    The report prints each if's own path never taken, as a decision.
    The JSON totals are [taken, possible]: alone [2, 4], one of each if's
    two paths, and combined [3, 5], fee's card: 1+1+1 of 2+2+1."""
    project = PROJECTS / "two_decisions"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/*.py"],
        coverage_dir=tmp_path,
        on_exit=exits.append,
    )
    try:
        shop = _imported(project, "two_decisions_shop")
        assert shop.fee(True, False) == 95
    finally:
        path_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == (
        "src/two_decisions_shop.py:7:4 path never taken: `member` false\n"
        "src/two_decisions_shop.py:9:4 path never taken: `big` true\n"
    )
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["reached"] == {
        "src/two_decisions_shop.py:4:0": 1,
        "src/two_decisions_shop.py:11:4": 1,
    }
    assert report["totals"] == {"alone": [2, 4], "combined": [3, 5]}


def test_e5a70c0b(tmp_path):
    """Example: measure=["decisions", "methods"]
    Every run measures paths alone and combined.
    So there is no measure to choose, and the setting is refused."""
    with pytest.raises(TypeError) as refused:
        path_coverage.start(
            root=PROJECTS / "single_and",
            cover=["src/**/*.py"],
            coverage_dir=tmp_path,
            measure=["decisions", "methods"],
            on_exit=lambda report: None,
        )
    assert str(refused.value) == "start() got an unexpected keyword argument 'measure'"


def test_e5a70c0c(tmp_path, capsys):
    """Example: report=["post"] to a collector, then render of the runs it
    saved
    At exit the run POSTs its JSON report to the collector, printing
    nothing.
    render merges every saved run's counts and reaches, then runs the
    reporters as a run would: here big's gap, and the combined total."""
    import socket
    import threading

    from path_coverage.collector import serve

    runs = tmp_path / "runs"
    runs.mkdir()
    server = socket.create_server(("127.0.0.1", 0))
    stop = threading.Event()
    thread = threading.Thread(target=serve, args=(server, runs, stop), daemon=True)
    thread.start()
    project = PROJECTS / "two_decisions"
    settings = {"root": project, "cover": ["src/*.py"]}
    try:
        for member in (True, False):
            exits = []
            path_coverage.start(
                **settings,
                coverage_dir=tmp_path / f"run-{member}",
                report=["post"],
                collector=f"http://127.0.0.1:{server.getsockname()[1]}/runs",
                on_exit=exits.append,
            )
            try:
                assert _imported(project, "two_decisions_shop").fee(member, False) in (95, 100)
            finally:
                path_coverage.stop()
            exits[0]()
    finally:
        stop.set()
        thread.join(5)
        server.close()
    assert capsys.readouterr().out == ""
    saved = sorted(runs.glob("*.json"))
    assert [path.name for path in saved] == ["run-0001.json", "run-0002.json"]
    path_coverage.render(**settings, coverage_dir=tmp_path / "merged", runs=saved)
    assert capsys.readouterr().out == (
        "src/two_decisions_shop.py:9:4 path never taken: `big` true\n"
    )
    report = json.loads((tmp_path / "merged" / "path_coverage.json").read_text())
    assert report["reached"] == {
        "src/two_decisions_shop.py:4:0": 2,
        "src/two_decisions_shop.py:11:4": 2,
    }
    assert report["totals"] == {"alone": [3, 4], "combined": [4, 5]}


def test_e5a70c12(tmp_path, capsys):
    """Example: render of a run whose JSON names kinds chain, choice and
    contains, as a version measuring contains would write it
    Runs measuring other kinds list a decision's paths differently.
    So render refuses it, naming the run, and writes no report."""
    project = PROJECTS / "single_and"
    settings = {"root": project, "cover": ["src/**/*.py"]}
    exits = []
    path_coverage.start(**settings, coverage_dir=tmp_path / "run", on_exit=exits.append)
    try:
        _imported(project, "single_and_trails").is_new("T2", {})
    finally:
        path_coverage.stop()
    exits[0]()
    capsys.readouterr()
    run = tmp_path / "run" / "path_coverage.json"
    report = json.loads(run.read_text())
    report["kinds"] = ["chain", "choice", "contains"]
    run.write_text(json.dumps(report))
    with pytest.raises(ValueError) as refused:
        path_coverage.render(**settings, coverage_dir=tmp_path / "merged", runs=[run])
    assert str(refused.value) == f"{run} measured other kinds"
    assert not (tmp_path / "merged").exists()


def test_e5a70c0d(tmp_path):
    """Example: report=["post"] with no collector
    The post reporter needs a collector to send to, so it is refused."""
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            root=PROJECTS / "single_and",
            cover=["src/**/*.py"],
            coverage_dir=tmp_path,
            report=["post"],
            on_exit=lambda report: None,
        )
    assert str(refused.value) == "the post reporter needs a collector url"


def test_e5a70c0e(tmp_path, capsys):
    """Example: cover src/*.py, skip src/*_policies.py, once as skip=,
    once as PATH_COVERAGE_SKIP
    A file a skip glob matches is not covered, though a cover glob
    matches it too.
    So never_imported_policies.py is not reported, not even as never
    reached; never_imported_flows.py still is."""
    project = PROJECTS / "never_imported"
    starts = [
        lambda on_exit: path_coverage.start(
            root=project,
            cover=["src/*.py"],
            skip=["src/*_policies.py"],
            coverage_dir=tmp_path,
            on_exit=on_exit,
        ),
        lambda on_exit: path_coverage.start_from_env(
            {
                "PATH_COVERAGE_ROOT": str(project),
                "PATH_COVERAGE_COVER": "src/*.py",
                "PATH_COVERAGE_SKIP": "lib/*.py,src/*_policies.py",
                "PATH_COVERAGE_DIR": str(tmp_path),
            },
            on_exit=on_exit,
        ),
    ]
    for start in starts:
        exits = []
        start(exits.append)
        path_coverage.stop()
        exits[0]()
        assert capsys.readouterr().out == "src/never_imported_flows.py:6:26 never reached\n"


def _is_public_twice(project, start):
    """Starts with start, imports never_imported_flows.py and calls is_public
    twice, taking two of its three paths, then stops and runs the report;
    never_imported_policies.py is never imported."""
    exits = []
    start(exits.append)
    try:
        flows = _imported(project, "never_imported_flows")
        assert flows.is_public({"public": False, "owner": "everyone"}) is True
        assert flows.is_public({"public": True, "owner": "kosli"}) is True
    finally:
        path_coverage.stop()
    exits[0]()


def test_e5a70c0f(tmp_path, capsys):
    """Example: report=["summary"], no groups, flows taking 2 of its 3
    paths and policies none of its 3
    The summary reporter prints the paths taken of all possible alone,
    then combined, over every covered file."""
    project = PROJECTS / "never_imported"
    _is_public_twice(
        project,
        lambda on_exit: path_coverage.start(
            root=project,
            cover=["src/*.py"],
            coverage_dir=tmp_path,
            report=["summary"],
            on_exit=on_exit,
        ),
    )
    assert capsys.readouterr().out == (
        "Paths alone: 2 / 6 (33.33%)\n"
        "Paths combined: 2 / 6 (33.33%)\n"
    )


def test_e5a70c10(tmp_path, capsys):
    """Example: groups flows and policies, report summary, once as
    groups=, once as PATH_COVERAGE_GROUPS
    The summary prints each group as a heading, its totals indented under
    it, with no total over every group.
    The JSON report's totals hold each group's own totals too.
    The source report lists each group's files."""
    project = PROJECTS / "never_imported"
    starts = [
        lambda on_exit: path_coverage.start(
            root=project,
            cover=["src/*.py"],
            coverage_dir=tmp_path,
            report=["summary"],
            groups={"flows": ["src/*_flows.py"], "policies": ["src/*_policies.py"]},
            on_exit=on_exit,
        ),
        lambda on_exit: path_coverage.start_from_env(
            {
                "PATH_COVERAGE_ROOT": str(project),
                "PATH_COVERAGE_COVER": "src/*.py",
                "PATH_COVERAGE_DIR": str(tmp_path),
                "PATH_COVERAGE_REPORT": "summary",
                "PATH_COVERAGE_GROUPS": "flows:src/*_flows.py,policies:src/*_policies.py",
            },
            on_exit=on_exit,
        ),
    ]
    for start in starts:
        _is_public_twice(project, start)
        assert capsys.readouterr().out == (
            "flows:\n"
            "  Paths alone: 2 / 3 (66.67%)\n"
            "  Paths combined: 2 / 3 (66.67%)\n"
            "policies:\n"
            "  Paths alone: 0 / 3 (0.00%)\n"
            "  Paths combined: 0 / 3 (0.00%)\n"
        )
        report = json.loads((tmp_path / "path_coverage.json").read_text())
        assert report["totals"] == {
            "alone": [2, 6],
            "combined": [2, 6],
            "groups": {
                "flows": {"alone": [2, 3], "combined": [2, 3]},
                "policies": {"alone": [0, 3], "combined": [0, 3]},
            },
        }
        source = json.loads((tmp_path / "path_coverage.source.json").read_text())
        assert source["groups"] == {
            "flows": ["src/never_imported_flows.py"],
            "policies": ["src/never_imported_policies.py"],
        }


def test_e5a70c11(tmp_path):
    """Example: groups shop and none, fee called once
    Each group's JSON totals have a combined total too.
    none matches no file, so its totals are all 0 / 0."""
    project = PROJECTS / "two_decisions"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/*.py"],
        coverage_dir=tmp_path,
        report=[],
        groups={"shop": ["src/*_shop.py"], "none": ["lib/*.py"]},
        on_exit=exits.append,
    )
    try:
        assert _imported(project, "two_decisions_shop").fee(True, False) == 95
    finally:
        path_coverage.stop()
    exits[0]()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["totals"]["groups"] == {
        "shop": {"alone": [2, 4], "combined": [3, 5]},
        "none": {"alone": [0, 0], "combined": [0, 0]},
    }


def test_e5a70c18(tmp_path, capsys):
    """Example: return "café" if a and b else "x", é one character of two
    bytes, called once
    Every column the reports give counts characters, as the leaf spans
    do: the conditional is named at its if, column 18, the and at its
    keyword, column 23, and the return's two rows, its two decisions, are
    at the same columns."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "cafe_label.py").write_text(
        'def label(a, b):\n    return "café" if a and b else "x"\n', encoding="utf-8"
    )
    exits = []
    path_coverage.start(root=tmp_path, cover=["src/*.py"], coverage_dir=tmp_path, report=[], on_exit=exits.append)
    try:
        assert _imported(tmp_path, "cafe_label").label(True, True) == "café"
    finally:
        path_coverage.stop()
    exits[0]()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert sorted(report["decisions"]) == ["src/cafe_label.py:2:18", "src/cafe_label.py:2:23"]
    rows = report["cards"]["src/cafe_label.py:1:0"]["rows"]
    assert [row["at"] for row in rows] == ["2:18", "2:23"]
    assert list(report["tree"]["src/cafe_label.py"]["1:0"]) == ["2:18", "2:23"]


def test_e5a70c13(tmp_path):
    """Example: fee never called
    The JSON report says no statement was reached: reached is {}.
    So fee's rows are known, and not taken: combined [0, 5]."""
    project = PROJECTS / "two_decisions"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/*.py"],
        coverage_dir=tmp_path,
        report=[],
        on_exit=exits.append,
    )
    path_coverage.stop()
    exits[0]()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["reached"] == {}
    assert report["totals"] == {"alone": [0, 4], "combined": [0, 5]}


def test_e5a70c14(tmp_path):
    """Example: fee called with member and not big, its report's reached
    then dropped, as a run that counted no statement writes it, then
    render of that report
    So render cannot say fee's return, a row that is no decision, was reached.
    It counts as not taken: combined [2, 5], never more than ran.
    Its merged report has no reached either."""
    project = PROJECTS / "two_decisions"
    exits = []
    run = tmp_path / "run"
    path_coverage.start(root=project, cover=["src/*.py"], coverage_dir=run, report=[], on_exit=exits.append)
    try:
        assert _imported(project, "two_decisions_shop").fee(True, False) == 95
    finally:
        path_coverage.stop()
    exits[0]()
    saved = run / "path_coverage.json"
    unreached = json.loads(saved.read_text())
    del unreached["reached"]
    saved.write_text(json.dumps(unreached))
    path_coverage.render(
        root=project,
        cover=["src/*.py"],
        coverage_dir=tmp_path / "merged",
        runs=[saved],
        report=[],
    )
    report = json.loads((tmp_path / "merged" / "path_coverage.json").read_text())
    assert "reached" not in report
    assert report["totals"] == {"alone": [2, 4], "combined": [2, 5]}


def test_e5a70c03():
    """Without PATH_COVERAGE_COVER, start_from_env starts nothing."""
    exits = []
    started = path_coverage.start_from_env(
        {"PATH_COVERAGE_ROOT": "/app"}, on_exit=exits.append
    )
    assert started is False
    assert exits == []


def test_e5a70c15(tmp_path):
    """Example: cover *.py and skip vendored.py under root, then imports of
    covered.py, vendored.py, lib/other.py, a namespace package, a module
    outside root, and one that does not exist
    Only covered.py is instrumented, its run recorded: the skipped one, the
    one no cover glob matches, the one outside root and the namespace
    package, which has no source, are loaded as they would be without path
    coverage, and the missing one still fails to import."""
    root, outside = tmp_path / "root", tmp_path / "outside"
    for file in (root / "covered.py", root / "vendored.py", root / "lib" / "other.py", outside / "away.py"):
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("VALUE = 1\n")
    (root / "spaced").mkdir()
    sys.path[:0] = [str(root), str(root / "lib"), str(outside)]
    path_coverage.start(root=root, cover=["*.py"], skip=["vendored.py"], coverage_dir=tmp_path, on_exit=lambda report: None)
    try:
        imported = [__import__(name) for name in ("covered", "vendored", "other", "spaced", "away")]
        with pytest.raises(ModuleNotFoundError):
            __import__("nowhere_at_all")
    finally:
        path_coverage.stop()
        del sys.path[:3]
        for name in ("covered", "vendored", "other", "spaced", "away"):
            sys.modules.pop(name)
    instrumented = [module.__name__ for module in imported if "__path_coverage__" in vars(module)]
    assert instrumented == ["covered"]


def test_e5a70c16(tmp_path, capsys):
    """Example: start_from_env with PATH_COVERAGE_COLLECTOR, a collector's
    url, and no PATH_COVERAGE_REPORT
    The reporters default to post, so the exit report is sent to that
    collector, which saves it, and nothing is printed."""
    import socket
    import threading

    from path_coverage.collector import serve

    server = socket.create_server(("127.0.0.1", 0))
    stop = threading.Event()
    thread = threading.Thread(target=serve, args=(server, tmp_path / "runs", stop))
    (tmp_path / "runs").mkdir()
    thread.start()
    exits = []
    path_coverage.start_from_env(
        {
            "PATH_COVERAGE_ROOT": str(PROJECTS / "single_and"),
            "PATH_COVERAGE_COVER": "src/**/*.py",
            "PATH_COVERAGE_DIR": str(tmp_path / "coverage"),
            "PATH_COVERAGE_COLLECTOR": f"http://127.0.0.1:{server.getsockname()[1]}/runs",
        },
        on_exit=exits.append,
    )
    path_coverage.stop()
    exits[0]()
    stop.set()
    thread.join(5)
    server.close()
    assert capsys.readouterr().out == ""
    assert [path.name for path in (tmp_path / "runs").iterdir()] == ["run-0001.json"]

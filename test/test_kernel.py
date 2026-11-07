import json
import platform
import sys
from pathlib import Path

import pytest

import path_coverage
from path_coverage import wrapped_leaves

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
        "measured_by": {
            "python": platform.python_version(),
            "path_coverage": path_coverage.__version__,
        },
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
                "taken": [
                    {"way": [{"at": "6:30", "path": [True, True]}], "count": 1},
                    {"way": [{"at": "6:30", "path": [False, None]}], "count": 1},
                ],
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
    At exit it adds every part's counts, paths and ways to its own.
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
    assert report["cards"]["src/single_and_trails.py:4:0"]["taken"] == [
        {"way": [{"at": "6:30", "path": [True, True]}], "count": 1},
        {"way": [{"at": "6:30", "path": [True, False]}], "count": 1},
    ]
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


def test_e5a70c1a(tmp_path, capsys):
    """Example: the JSON report of a run names, under "measured_by", each
    tool that parsed or measured it and its version: Python and
    path_coverage. A change to either can list a file's decisions or paths
    differently, so their runs are never merged."""
    project = PROJECTS / "single_and"
    exits = []
    path_coverage.start(
        root=project, cover=["src/**/*.py"], coverage_dir=tmp_path, on_exit=exits.append
    )
    try:
        _imported(project, "single_and_trails").is_new("T2", {})
    finally:
        path_coverage.stop()
    exits[0]()
    capsys.readouterr()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["measured_by"] == {
        "python": platform.python_version(),
        "path_coverage": path_coverage.__version__,
    }


def test_e5a70c1b(tmp_path, capsys):
    """Example: render of a run whose JSON names Python 3.12.0 under
    "measured_by", as another Python would write it
    Another version of a tool can find a file's decisions or paths
    differently, so render refuses it, naming the run, rather than credit
    one path's count to another, and writes no report."""
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
    report["measured_by"] = {"python": "3.12.0", "path_coverage": "0.0.1"}
    run.write_text(json.dumps(report))
    with pytest.raises(ValueError) as refused:
        path_coverage.render(**settings, coverage_dir=tmp_path / "merged", runs=[run])
    assert str(refused.value) == f"{run} was measured by other tools"
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
                "PATH_COVERAGE_SKIP": "src/*_rules.py,src/*_policies.py",
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
    """Example: group shop, fee called once
    Each group's JSON totals have a combined total too."""
    project = PROJECTS / "two_decisions"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/*.py"],
        coverage_dir=tmp_path,
        report=[],
        groups={"shop": ["src/*_shop.py"]},
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


def test_e5a70c19(tmp_path):
    """Example: match kata: case _ if started: return "ready", then return
    "waiting", called once started and once not
    A last case of _ with a guard does not match anything: when its guard
    is false no case is taken, a path of its own. So both paths are taken
    once, the one where nothing matched included, and there are no gaps."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "guarded_gate.py").write_text(
        "def state(kata, started):\n"
        "    match kata:\n"
        "        case _ if started:\n"
        '            return "ready"\n'
        '    return "waiting"\n'
    )
    exits = []
    path_coverage.start(root=tmp_path, cover=["src/*.py"], coverage_dir=tmp_path, report=[], on_exit=exits.append)
    try:
        gate = _imported(tmp_path, "guarded_gate")
        states = [gate.state("K5", True), gate.state("K5", False)]
    finally:
        path_coverage.stop()
    exits[0]()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert [states, report["paths"]["src/guarded_gate.py:2:4"]["taken"]] == [
        ["ready", "waiting"],
        [{"path": [True, True], "count": 1}, {"path": [True, False], "count": 1}],
    ]


ORDERS = (
    "class Order:\n"
    "    def ship(self, express, paid):\n"
    "        def carrier(heavy):\n"
    '            return "truck" if heavy else "van"\n'
    "        if express and paid:\n"
    "            return carrier(True)\n"
    "        return carrier(False)\n"
    "\n"
    "    def total(self, items, vip):\n"
    "        return sum(items) if vip or items else 0\n"
    "\n"
    "\n"
    "def refund(order, late):\n"
    "    return 10 if late else 0\n"
)


def _ordered(tmp_path, report, groups={}, cover="src/orders.py::Order.ship"):
    """The JSON report of a run covering cover, a glob of ORDERS's file
    src/orders.py, with the reporters report and the groups groups, after
    one call each of ship (an express paid order, so carrier's truck),
    total and refund."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(ORDERS)
    exits = []
    path_coverage.start(
        root=tmp_path,
        cover=[cover],
        coverage_dir=tmp_path,
        report=report,
        groups=groups,
        on_exit=exits.append,
    )
    try:
        orders = _imported(tmp_path, "orders")
        assert orders.Order().ship(True, True) == "truck"
        assert orders.Order().total([1], False) == 1
        assert orders.refund(None, True) == 10
    finally:
        path_coverage.stop()
    exits[0]()
    return json.loads((tmp_path / "path_coverage.json").read_text())


def test_e5a70c1c(tmp_path):
    """Example: cover src/orders.py::Order.ship of ORDERS, an Order whose
    ship holds a nested carrier, beside Order.total and a function refund
    A cover glob's ::qualname keeps only the decisions and cards inside
    that scope, a def nested in it included: ship's if and and, and
    carrier's conditional. total's and refund's are not measured, nor
    counted in the totals: 3 of ship's 7 paths alone, 4 of its 9
    combined, as a file holding ship alone gives. The JSON's paths, the
    statements reached, and the cards in its tree, are of that scope
    only."""
    report = _ordered(tmp_path, [])
    kept = ["src/orders.py:4:27", "src/orders.py:5:19", "src/orders.py:5:8"]
    assert [
        sorted(report["decisions"]),
        sorted(report["paths"]),
        sorted(report["cards"]),
        report["totals"],
        report["reached"],
        sorted(report["tree"]["src/orders.py"]),
    ] == [
        kept,
        kept,
        ["src/orders.py:2:4", "src/orders.py:3:8"],
        {"alone": [3, 7], "combined": [4, 9]},
        {"src/orders.py:2:4": 1, "src/orders.py:3:8": 1, "src/orders.py:6:12": 1},
        ["2:4", "3:8"],
    ]


def test_e5a70c23(tmp_path, capsys):
    """Example: cover src/orders.py::Order.ship of ORDERS
    The gaps printed are ship's and carrier's only."""
    _ordered(tmp_path, ["gaps"])
    assert capsys.readouterr().out == (
        "src/orders.py:4:27 path never taken: `heavy` false\n"
        "src/orders.py:5:8 path never taken: `express and paid` false\n"
        "src/orders.py:5:19 path never taken: `express` true, `paid` false\n"
        "src/orders.py:5:19 path never taken: `express` false\n"
    )


def test_e5a70c24(tmp_path, capsys):
    """Example: cover src/orders.py::Order.ship of ORDERS
    The summary's totals count ship's and carrier's paths only."""
    _ordered(tmp_path, ["summary"])
    assert capsys.readouterr().out == ("Paths alone: 3 / 7 (42.86%)\nPaths combined: 4 / 9 (44.44%)\n")


def test_e5a70c25(tmp_path):
    """Example: cover src/orders.py::Order.ship of ORDERS, in a group
    orders of src/orders.py
    A group's totals count only the scope's paths: ship's and carrier's,
    3 of 7 alone, 4 of 9 combined, as the run's own totals do."""
    report = _ordered(tmp_path, [], {"orders": ["src/orders.py"]})
    assert report["totals"]["groups"] == {"orders": {"alone": [3, 7], "combined": [4, 9]}}


@pytest.mark.parametrize(
    ("cover", "refusal"),
    [
        ("src/orders.py:Order.ship", "cover 'src/orders.py:Order.ship' matches no file"),
        ("Order.total", "cover 'Order.total' matches no file"),
        (" src/orders.py::Order.ship", "cover ' src/orders.py::Order.ship' matches no file"),
        ("src/orders.py::", "cover 'src/orders.py::': '' is not a qualname"),
        ("src/orders.py::Order::ship", "cover 'src/orders.py::Order::ship': 'Order::ship' is not a qualname"),
        ("src/orders.py::Order.", "cover 'src/orders.py::Order.': 'Order.' is not a qualname"),
        ("src/orders.py:: Order.ship", "cover 'src/orders.py:: Order.ship': ' Order.ship' is not a qualname"),
    ],
)
def test_e5a70c28(tmp_path, cover, refusal):
    """Example: covers mistyped beside src/orders.py of ORDERS
    A cover whose glob matches no file, or whose qualname is not names
    joined by dots, is refused at start, naming it, never measuring less
    than asked: one colon, a stray name after a comma, a space, an empty
    or ::-joined or dot-ended qualname."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(ORDERS)
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            root=tmp_path,
            cover=["src/orders.py::Order.ship", cover],
            coverage_dir=tmp_path,
            on_exit=lambda report: None,
        )
    assert str(refused.value) == refusal


@pytest.mark.parametrize("skip", ["src/migrations/*.py", "lib/*.py"])
def test_e5a70c29(tmp_path, skip):
    """Example: cover src/*.py of ORDERS in src/orders.py, beside
    lib/rates.py, with a skip of a missing dir or of an uncovered file
    A skip glob matching no covered file is refused at start, naming it,
    as it skips nothing, so is a mistake."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(ORDERS)
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "rates.py").write_text("VAT = 20\n")
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            root=tmp_path,
            cover=["src/*.py"],
            skip=[skip],
            coverage_dir=tmp_path,
            on_exit=lambda report: None,
        )
    assert str(refused.value) == f"skip {skip!r} matches no covered file"


def test_e5a70c2a(tmp_path):
    """Example: cover src/*.py of ORDERS in src/orders.py, with a group
    billing of src/billing/*.py
    A group glob matching no covered file is refused at start, naming the
    group and the glob, as the group could only ever total 0 / 0."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(ORDERS)
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            root=tmp_path,
            cover=["src/*.py"],
            groups={"billing": ["src/billing/*.py"]},
            coverage_dir=tmp_path,
            on_exit=lambda report: None,
        )
    assert str(refused.value) == "group 'billing': 'src/billing/*.py' matches no covered file"


@pytest.mark.parametrize(
    ("variable", "value", "refusal"),
    [
        ("PATH_COVERAGE_COVER", "src/*.py,", "PATH_COVERAGE_COVER has an empty entry: 'src/*.py,'"),
        ("PATH_COVERAGE_SKIP", "src/*_policies.py,", "PATH_COVERAGE_SKIP has an empty entry: 'src/*_policies.py,'"),
        ("PATH_COVERAGE_SKIP", "", "PATH_COVERAGE_SKIP has an empty entry: ''"),
        ("PATH_COVERAGE_REPORT", "gaps,,summary", "PATH_COVERAGE_REPORT has an empty entry: 'gaps,,summary'"),
        (
            "PATH_COVERAGE_GROUPS",
            "flows:src/*_flows.py,",
            "PATH_COVERAGE_GROUPS has an empty entry: 'flows:src/*_flows.py,'",
        ),
        ("PATH_COVERAGE_GROUPS", "flows", "PATH_COVERAGE_GROUPS entry 'flows' is not name:glob"),
        ("PATH_COVERAGE_GROUPS", "flows:", "PATH_COVERAGE_GROUPS entry 'flows:' is not name:glob"),
        ("PATH_COVERAGE_GROUPS", ":src/*_flows.py", "PATH_COVERAGE_GROUPS entry ':src/*_flows.py' is not name:glob"),
    ],
)
def test_e5a70c2b(tmp_path, variable, value, refusal):
    """Example: PATH_COVERAGE_* lists mistyped, over never_imported
    A list variable set with an empty entry (a stray or trailing comma,
    or set to ''), or a group entry that is not a name and a glob, is
    refused at start, naming the variable and its value; never dropped."""
    env = {
        "PATH_COVERAGE_ROOT": str(PROJECTS / "never_imported"),
        "PATH_COVERAGE_COVER": "src/*.py",
        "PATH_COVERAGE_DIR": str(tmp_path),
    }
    with pytest.raises(ValueError) as refused:
        path_coverage.start_from_env({**env, variable: value}, on_exit=lambda report: None)
    assert str(refused.value) == refusal


@pytest.mark.parametrize(
    ("settings", "refusal"),
    [
        ({"cover": []}, "cover is empty, so nothing would be measured"),
        ({"cover": ["src/*.py", ""]}, "cover has an empty entry: ['src/*.py', '']"),
        ({"skip": [""]}, "skip has an empty entry: ['']"),
        ({"groups": {"flows": []}}, "group 'flows' has no globs"),
        ({"groups": {"": ["src/*_flows.py"]}}, "a group has an empty name: {'': ['src/*_flows.py']}"),
        ({"groups": {"flows": [""]}}, "group 'flows' has an empty entry: ['']"),
    ],
)
def test_e5a70c2c(tmp_path, settings, refusal):
    """Example: start's lists mistyped, over never_imported
    An empty cover, an empty entry in cover, skip or a group's globs, a
    group with no globs, or a group with no name, is refused at start,
    naming it, as each would quietly measure or total less than asked."""
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            **{
                "root": PROJECTS / "never_imported",
                "cover": ["src/*.py"],
                "coverage_dir": tmp_path,
                "on_exit": lambda report: None,
                **settings,
            }
        )
    assert str(refused.value) == refusal


def test_e5a70c27(tmp_path):
    """Example: cover src/orders.py::Order.ship of ORDERS
    The source report shows all 14 of the file's lines, but only the
    scope's decisions, ship's and carrier's, so total's and refund's
    show as plain code."""
    _ordered(tmp_path, [])
    source = json.loads((tmp_path / "path_coverage.source.json").read_text())
    file = source["files"]["src/orders.py"]
    assert [len(file["lines"]), sorted(file["decisions"])] == [
        14,
        ["src/orders.py:4:27", "src/orders.py:5:19", "src/orders.py:5:8"],
    ]


def test_e5a70c26(tmp_path):
    """Example: render, covering src/orders.py::Order.ship, the JSON
    report of a run that covered ORDERS whole, calling ship, total and
    refund
    The merged report keeps only the scope: its decisions, totals and
    reached are ship's and carrier's, though the run counted total's and
    refund's too."""
    _ordered(tmp_path, [], cover="src/orders.py")
    path_coverage.render(
        root=tmp_path,
        cover=["src/orders.py::Order.ship"],
        coverage_dir=tmp_path / "merged",
        runs=[tmp_path / "path_coverage.json"],
        report=[],
    )
    merged = json.loads((tmp_path / "merged" / "path_coverage.json").read_text())
    assert [sorted(merged["decisions"]), merged["totals"], merged["reached"]] == [
        ["src/orders.py:4:27", "src/orders.py:5:19", "src/orders.py:5:8"],
        {"alone": [3, 7], "combined": [4, 9]},
        {"src/orders.py:2:4": 1, "src/orders.py:3:8": 1, "src/orders.py:6:12": 1},
    ]


def test_e5a70c1d(tmp_path):
    """Example: cover src/orders.py::Order.size, where size is a property
    whose getter and setter are both defs named size
    A ::qualname naming two defs keeps both: the getter's conditional and
    the setter's and, and their two cards. total's are not measured."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(
        "class Order:\n"
        "    @property\n"
        "    def size(self):\n"
        '        return "big" if self.big else "small"\n'
        "\n"
        "    @size.setter\n"
        "    def size(self, weight):\n"
        "        self.big = weight > 5 and weight < 50\n"
        "\n"
        "    def total(self, items, vip):\n"
        "        return sum(items) if vip or items else 0\n"
    )
    exits = []
    path_coverage.start(
        root=tmp_path,
        cover=["src/orders.py::Order.size"],
        coverage_dir=tmp_path,
        report=[],
        on_exit=exits.append,
    )
    try:
        order = _imported(tmp_path, "orders").Order()
        order.size = 10
        assert [order.size, order.total([1], False)] == ["big", 1]
    finally:
        path_coverage.stop()
    exits[0]()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert [sorted(report["decisions"]), sorted(report["cards"])] == [
        ["src/orders.py:4:21", "src/orders.py:8:30"],
        ["src/orders.py:3:4", "src/orders.py:7:4"],
    ]


def test_e5a70c1e(tmp_path):
    """A cover whose ::qualname names nothing in a file its glob matches is
    refused at start, naming the cover, the deepest def or class found,
    and the name it lacks, eg Order.post in an orders.py whose Order has
    only ship."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(
        "class Order:\n"
        "    def ship(self, express):\n"
        '        return "air" if express else "sea"\n'
    )
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            root=tmp_path,
            cover=["src/orders.py::Order.post"],
            coverage_dir=tmp_path,
            on_exit=lambda report: None,
        )
    assert str(refused.value) == ("cover 'src/orders.py::Order.post': class Order in src/orders.py has no post")


def test_e5a70c1f(tmp_path):
    """A cover whose glob matches two files, only one of them holding
    its ::qualname, is refused at start, naming the cover, the file
    without it and the name it lacks, eg Order.ship over orders.py and
    refunds.py."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(
        "class Order:\n"
        "    def ship(self, express):\n"
        '        return "air" if express else "sea"\n'
    )
    (tmp_path / "src" / "refunds.py").write_text(
        "def refund(order, late):\n"
        "    return 10 if late else 0\n"
    )
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            root=tmp_path,
            cover=["src/*.py::Order.ship"],
            coverage_dir=tmp_path,
            on_exit=lambda report: None,
        )
    assert str(refused.value) == "cover 'src/*.py::Order.ship': src/refunds.py has no Order"


def test_e5a70c20(tmp_path):
    """A cover whose ::qualname goes deeper than a file's defs is refused
    at start, naming the deepest def found and the name it lacks, eg
    Order.ship.helper when ship holds no helper."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(
        "class Order:\n"
        "    def ship(self, express):\n"
        '        return "air" if express else "sea"\n'
    )
    with pytest.raises(ValueError) as refused:
        path_coverage.start(
            root=tmp_path,
            cover=["src/orders.py::Order.ship.helper"],
            coverage_dir=tmp_path,
            on_exit=lambda report: None,
        )
    assert str(refused.value) == (
        "cover 'src/orders.py::Order.ship.helper': def Order.ship in src/orders.py has no helper"
    )


def test_e5a70c21(tmp_path):
    """Example: cover src/text.py::newline, where newline is defined once
    in an if and once in its else
    A ::qualname names defs inside an if as it names any other: both
    newlines' conditionals are kept, and their cards; width's are not."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "text.py").write_text(
        "import sys\n"
        "\n"
        'if sys.platform == "win32":\n'
        "    def newline(raw):\n"
        '        return "\\n" if raw else "\\r\\n"\n'
        "else:\n"
        "    def newline(raw):\n"
        '        return "\\r" if raw else "\\n"\n'
        "\n"
        "\n"
        "def width(text, wide):\n"
        "    return 2 if wide else 1\n"
    )
    exits = []
    path_coverage.start(
        root=tmp_path,
        cover=["src/text.py::newline"],
        coverage_dir=tmp_path,
        report=[],
        on_exit=exits.append,
    )
    try:
        text = _imported(tmp_path, "text")
        assert [text.newline(False), text.width("ab", False)] == ["\n", 1]
    finally:
        path_coverage.stop()
    exits[0]()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert [sorted(report["decisions"]), sorted(report["cards"])] == [
        ["src/text.py:5:20", "src/text.py:8:20"],
        ["src/text.py:4:4", "src/text.py:7:4"],
    ]


def test_e5a70c22(tmp_path):
    """Example: cover src/orders.py::Order.carrier, carrier a @property,
    beside Order.total
    Code outside a ::qualname's scope runs as plain Python: total gets no
    monitoring events and no leaf of it is wrapped. carrier, decorated,
    gets both, its scope starting at its decorator."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "orders.py").write_text(
        "class Order:\n"
        "    express = True\n"
        "    paid = True\n"
        "\n"
        "    @property\n"
        "    def carrier(self):\n"
        "        return self.express and self.paid\n"
        "\n"
        "    def total(self, items, vip):\n"
        "        return sum(items) if vip or items else 0\n"
    )
    path_coverage.start(
        root=tmp_path,
        cover=["src/orders.py::Order.carrier"],
        coverage_dir=tmp_path,
        report=[],
        on_exit=lambda report: None,
    )
    try:
        order = _imported(tmp_path, "orders").Order
        tool = path_coverage.monitor._tool
        carrier, total = order.carrier.fget.__code__, order.total.__code__
        seen = [
            sys.monitoring.get_local_events(tool, carrier) != 0,
            sys.monitoring.get_local_events(tool, total),
            wrapped_leaves.NAME in carrier.co_names,
            wrapped_leaves.NAME in total.co_names,
        ]
    finally:
        path_coverage.stop()
    assert seen == [True, 0, True, False]


SAVE = (
    "def save(record, dry_run, db, audit):\n"
    "    if dry_run:\n"
    "        print('would save', record)\n"
    "        return None\n"
    "    db.append(record)\n"
    "    if not dry_run:\n"
    "        audit.append(record)\n"
    "    return len(db)\n"
)


def test_e5a70c2d(tmp_path, capsys):
    """Example: save called as a dry run, then twice for real
    Each card lists the ways its calls took, whole: each step a decision
    row's path or a statement row reached, in the order taken, with how
    many calls took that way."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "saving.py").write_text(SAVE)
    exits = []
    path_coverage.start(root=tmp_path, cover=["src/*.py"], coverage_dir=tmp_path, report=[], on_exit=exits.append)
    try:
        saving = _imported(tmp_path, "saving")
        saved = [saving.save("R1", True, [], []), saving.save("R2", False, [], []), saving.save("R3", False, [], [])]
    finally:
        path_coverage.stop()
    exits[0]()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert [capsys.readouterr().out, saved, report["cards"]["src/saving.py:1:0"]["taken"]] == [
        "would save R1\n",
        [None, 1, 1],
        [
            {"way": [{"at": "2:04", "path": [True]}, {"at": "4:08"}], "count": 1},
            {"way": [{"at": "2:04", "path": [False]}, {"at": "6:04", "path": [True]}, {"at": "8:04"}], "count": 2},
        ],
    ]


def test_e5a70c2e(tmp_path, capsys):
    """Example: a module setting MODE by a conditional, then save, called
    as a dry run and for real; that run's JSON report rendered
    The merged report lists the same ways save's calls took, read back
    from the report's cards; the top card, which no call runs, lists none."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "saving.py").write_text("MODE = 'cli' if __name__ == '__main__' else 'lib'\n\n\n" + SAVE)
    exits = []
    settings = {"root": tmp_path, "cover": ["src/*.py"], "report": []}
    path_coverage.start(**settings, coverage_dir=tmp_path / "run", on_exit=exits.append)
    try:
        saving = _imported(tmp_path, "saving")
        saving.save("R1", True, [], [])
        saving.save("R2", False, [], [])
    finally:
        path_coverage.stop()
    exits[0]()
    capsys.readouterr()
    path_coverage.render(**settings, coverage_dir=tmp_path / "merged", runs=[tmp_path / "run" / "path_coverage.json"])
    cards = json.loads((tmp_path / "merged" / "path_coverage.json").read_text())["cards"]
    assert [cards["src/saving.py:4:0"]["taken"], "taken" in cards["src/saving.py:1:0"]] == [
        [
            {"way": [{"at": "5:04", "path": [True]}, {"at": "7:08"}], "count": 1},
            {"way": [{"at": "5:04", "path": [False]}, {"at": "9:04", "path": [True]}, {"at": "11:04"}], "count": 1},
        ],
        False,
    ]


def test_e5a70c2f(tmp_path):
    """Example: two generators of steps, one fast and one not, resumed in
    turn, each suspended before its if
    A generator's call is one way however often it resumes: each lists its
    own if's path, never the other's."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "stepping.py").write_text(
        "def steps(fast):\n"
        "    yield 'start'\n"
        "    if fast:\n"
        "        yield 'skip'\n"
        "    yield 'done'\n"
    )
    exits = []
    path_coverage.start(root=tmp_path, cover=["src/*.py"], coverage_dir=tmp_path, report=[], on_exit=exits.append)
    try:
        stepping = _imported(tmp_path, "stepping")
        fast, slow = stepping.steps(True), stepping.steps(False)
        firsts = [next(fast), next(slow)]
        rests = [list(slow), list(fast)]
    finally:
        path_coverage.stop()
    exits[0]()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert [firsts, rests, report["cards"]["src/stepping.py:1:0"]["taken"]] == [
        ["start", "start"],
        [["done"], ["skip", "done"]],
        [
            {"way": [{"at": "3:04", "path": [True]}], "count": 1},
            {"way": [{"at": "3:04", "path": [False]}], "count": 1},
        ],
    ]


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

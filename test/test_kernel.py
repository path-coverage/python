import json
import re
import sys
from pathlib import Path

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
    """single_and_trails' site's paths, taken tt, tf and f times."""
    return [
        {"path": [True, True], "count": tt},
        {"path": [True, False], "count": tf},
        {"path": [False, None], "count": f},
    ]


def test_e5a70c01(tmp_path, capsys):
    """Example: trail_id in trails and trails[trail_id]["new"], called
    with a new trail, then with no trails
    A covered module imported after start is instrumented.
    The report at exit writes every site's counts and paths as JSON.
    Each path has its count, and each leaf its line:col span.
    It names the kinds measured, as runs measuring others differ.
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
    site = "src/single_and_trails.py:6:11"
    assert json.loads((tmp_path / "path_coverage.json").read_text()) == {
        "sites": {
            site: [
                {"truthy": 1, "falsy": 1},
                {"truthy": 1, "falsy": 0},
            ]
        },
        "paths": {site: {"leaves": LEAVES, "taken": _taken(1, 0, 1)}},
        "method_paths": {},
        "kinds": ["block", "case", "chain", "choice"],
        "totals": {"decisions": [2, 3]},
    }
    assert capsys.readouterr().out == (
        f"{site} path never taken: `trail_id in trails` true, {NEW} false\n"
    )


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
    site = "src/single_and_trails.py:6:11"
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["paths"][site]["taken"] == _taken(0, 1, 0)
    assert capsys.readouterr().out == (
        f"{site} path never taken: `trail_id in trails` true, {NEW} true\n"
        f"{site} path never taken: `trail_id in trails` false\n"
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
    stale.write_text('{"sites": {}}')
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
    site = "src/single_and_trails.py:6:11"
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["sites"] == {
        site: [
            {"truthy": 2, "falsy": 0},
            {"truthy": 1, "falsy": 1},
        ]
    }
    assert report["paths"][site]["taken"] == _taken(1, 1, 0)
    assert capsys.readouterr().out == (
        f"{site} path never taken: `trail_id in trails` false\n"
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
    """A covered file the run never imported is still reported, every site
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
        "src/never_imported_flows.py:6:11 path never taken: "
        '`flow["public"]` false, `flow["owner"] == "everyone"` false\n'
        "src/never_imported_policies.py:6:11 never reached\n"
    )


def test_e5a70c07(tmp_path, capsys):
    """report=["html"] writes index.html, linking each covered file, and
    files/<path>.html, its source with each condition's tree; with no
    "gaps" in report nothing is printed."""
    project = PROJECTS / "single_and"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/**/*.py"],
        coverage_dir=tmp_path,
        report=["html"],
        on_exit=exits.append,
    )
    try:
        trails = _imported(project, "single_and_trails")
        assert trails.is_new("T6", {}) is False
    finally:
        path_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == ""
    index = (tmp_path / "index.html").read_text()
    assert '<a href="files/src/single_and_trails.py.html">src/single_and_trails.py</a>' in index
    page = (tmp_path / "files" / "src" / "single_and_trails.py.html").read_text()
    assert '<a data-index="" href="../../index.html">Path coverage</a>' in page
    assert '<span class="text" data-text="">trails[trail_id][&quot;new&quot;]</span>' in page


def test_e5a70c08(tmp_path):
    """An unknown reporter is refused by name, listing the known ones."""
    try:
        path_coverage.start(
            root=PROJECTS / "single_and",
            cover=["src/**/*.py"],
            coverage_dir=tmp_path,
            report=["gaps", "htm"],
            on_exit=lambda report: None,
        )
    except ValueError as error:
        assert str(error) == (
            "unknown reporter 'htm'; the reporters are: gaps, html, post, summary"
        )
    else:
        path_coverage.stop()
        raise AssertionError("start accepted reporter 'htm'")


def test_e5a70c09(tmp_path, capsys):
    """start_from_env takes the reporters, comma-separated, from
    PATH_COVERAGE_REPORT."""
    exits = []
    path_coverage.start_from_env(
        {
            "PATH_COVERAGE_ROOT": str(PROJECTS / "single_and"),
            "PATH_COVERAGE_COVER": "src/**/*.py",
            "PATH_COVERAGE_DIR": str(tmp_path),
            "PATH_COVERAGE_REPORT": "html",
        },
        on_exit=exits.append,
    )
    path_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == ""
    assert (tmp_path / "index.html").exists()


def test_e5a70c0a(tmp_path, capsys):
    """Example: fee with if member and if big, called once with member
    and not big, measuring decisions and methods
    Each call records its path through fee's two decisions.
    The report prints each if's own path never taken, as a site.
    Then it prints each of fee's paths never taken, by line.
    The JSON totals are [taken, possible]: decisions [2, 4], one of each
    if's two paths, and methods [1, 4], one of fee's four."""
    project = PROJECTS / "two_decisions"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/*.py"],
        coverage_dir=tmp_path,
        measure=["decisions", "methods"],
        on_exit=exits.append,
    )
    try:
        shop = _imported(project, "two_decisions_shop")
        assert shop.fee(True, False) == 95
    finally:
        path_coverage.stop()
    exits[0]()
    method = "src/two_decisions_shop.py:4:0 fee path never taken:"
    assert capsys.readouterr().out == (
        "src/two_decisions_shop.py:7:4 path never taken: `member` false\n"
        "src/two_decisions_shop.py:9:4 path never taken: `big` true\n"
        f"{method} line 7 true, line 9 true\n"
        f"{method} line 7 false, line 9 true\n"
        f"{method} line 7 false, line 9 false\n"
    )
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    assert report["totals"] == {"decisions": [2, 4], "methods": [1, 4]}


def test_e5a70c0b(tmp_path):
    """Example: measure=["decisions", "method"]
    An unknown measure is refused by name, listing the known ones."""
    try:
        path_coverage.start(
            root=PROJECTS / "single_and",
            cover=["src/**/*.py"],
            coverage_dir=tmp_path,
            measure=["decisions", "method"],
            on_exit=lambda report: None,
        )
    except ValueError as error:
        assert str(error) == "unknown measure 'method'; the measures are: decisions, methods"
    else:
        path_coverage.stop()
        raise AssertionError("start accepted measure 'method'")


def test_e5a70c0c(tmp_path, capsys):
    """Example: report=["post"] to a collector, then render of the runs it
    saved, measuring methods
    At exit the run POSTs its JSON report to the collector, printing
    nothing.
    render merges every saved run's counts, then runs the reporters as a
    run would: here the gaps of fee's paths, and the methods total."""
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
    settings = {"root": project, "cover": ["src/*.py"], "measure": ["decisions", "methods"]}
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
    method = "src/two_decisions_shop.py:4:0 fee path never taken:"
    assert capsys.readouterr().out == (
        "src/two_decisions_shop.py:9:4 path never taken: `big` true\n"
        f"{method} line 7 true, line 9 true\n"
        f"{method} line 7 false, line 9 true\n"
    )
    report = json.loads((tmp_path / "merged" / "path_coverage.json").read_text())
    assert report["totals"] == {"decisions": [3, 4], "methods": [2, 4]}


def test_e5a70c12(tmp_path, capsys):
    """Example: render of a run whose JSON names kinds chain, choice and
    contains, as a version measuring contains would write it
    Runs measuring other kinds list a site's paths differently.
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
    try:
        path_coverage.render(**settings, coverage_dir=tmp_path / "merged", runs=[run])
    except ValueError as error:
        assert str(error) == f"{run} measured other kinds"
    else:
        raise AssertionError("render accepted a run measuring other kinds")
    assert not (tmp_path / "merged").exists()


def test_e5a70c0d(tmp_path):
    """Example: report=["post"] with no collector
    The post reporter needs a collector to send to, so it is refused."""
    try:
        path_coverage.start(
            root=PROJECTS / "single_and",
            cover=["src/**/*.py"],
            coverage_dir=tmp_path,
            report=["post"],
            on_exit=lambda report: None,
        )
    except ValueError as error:
        assert str(error) == "the post reporter needs a collector url"
    else:
        path_coverage.stop()
        raise AssertionError("start accepted post with no collector")


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
        assert capsys.readouterr().out == "src/never_imported_flows.py:6:11 never reached\n"


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
    The summary reporter prints the paths taken of all possible within
    decisions, over every covered file.
    Methods are not measured, so there is no methods line."""
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
    assert capsys.readouterr().out == "Path coverage within decisions: 2 / 6 (33.33%)\n"


def test_e5a70c10(tmp_path, capsys):
    """Example: groups flows and policies, report summary and html, once
    as groups=, once as PATH_COVERAGE_GROUPS
    The summary prints each group as a heading, its totals indented under
    it, with no total over every group.
    The JSON report's totals hold each group's own totals too.
    The index page has a tab per group after All files, and no Ungrouped
    tab, as every file is in a group."""
    project = PROJECTS / "never_imported"
    starts = [
        lambda on_exit: path_coverage.start(
            root=project,
            cover=["src/*.py"],
            coverage_dir=tmp_path,
            report=["summary", "html"],
            groups={"flows": ["src/*_flows.py"], "policies": ["src/*_policies.py"]},
            on_exit=on_exit,
        ),
        lambda on_exit: path_coverage.start_from_env(
            {
                "PATH_COVERAGE_ROOT": str(project),
                "PATH_COVERAGE_COVER": "src/*.py",
                "PATH_COVERAGE_DIR": str(tmp_path),
                "PATH_COVERAGE_REPORT": "summary,html",
                "PATH_COVERAGE_GROUPS": "flows:src/*_flows.py,policies:src/*_policies.py",
            },
            on_exit=on_exit,
        ),
    ]
    for start in starts:
        _is_public_twice(project, start)
        assert capsys.readouterr().out == (
            "flows:\n"
            "  Path coverage within decisions: 2 / 3 (66.67%)\n"
            "policies:\n"
            "  Path coverage within decisions: 0 / 3 (0.00%)\n"
        )
        report = json.loads((tmp_path / "path_coverage.json").read_text())
        assert report["totals"] == {
            "decisions": [2, 6],
            "groups": {"flows": {"decisions": [2, 3]}, "policies": {"decisions": [0, 3]}},
        }
        index = (tmp_path / "index.html").read_text()
        tabs = re.findall(r'<button type="button" role="tab"[^>]*>([^<]*)</button>', index)
        assert tabs == ["All files", "flows", "policies"]


def test_e5a70c11(tmp_path):
    """Example: measure=["decisions", "methods"], groups shop and none,
    fee called once
    Each group's JSON totals have a methods total too.
    none matches no file, so its totals are all 0 / 0."""
    project = PROJECTS / "two_decisions"
    exits = []
    path_coverage.start(
        root=project,
        cover=["src/*.py"],
        coverage_dir=tmp_path,
        report=[],
        measure=["decisions", "methods"],
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
        "shop": {"decisions": [2, 4], "methods": [1, 4]},
        "none": {"decisions": [0, 0], "methods": [0, 0]},
    }


def test_e5a70c03():
    """Without PATH_COVERAGE_COVER, start_from_env starts nothing."""
    exits = []
    started = path_coverage.start_from_env(
        {"PATH_COVERAGE_ROOT": "/app"}, on_exit=exits.append
    )
    assert started is False
    assert exits == []

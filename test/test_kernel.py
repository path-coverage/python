import json
import sys
from pathlib import Path

import condition_coverage

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


def test_e5a70c01(tmp_path, capsys):
    """A covered module imported after start is instrumented, and the report
    at exit writes every site's counts as JSON and prints the gaps."""
    project = PROJECTS / "single_and"
    exits = []
    condition_coverage.start(
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
        condition_coverage.stop()
    [report] = exits
    report()
    site = "src/single_and_trails.py:6:11"
    assert json.loads((tmp_path / "condition_coverage.json").read_text()) == {
        "sites": {
            site: [
                {"truthy": 1, "falsy": 1},
                {"truthy": 1, "falsy": 0},
            ]
        }
    }
    assert capsys.readouterr().out == f"{site} operand 1 never false\n"


def test_e5a70c02(tmp_path, capsys):
    """start_from_env takes root, comma-separated cover globs and the
    coverage dir from CONDITION_COVERAGE_* variables."""
    project = PROJECTS / "single_and"
    exits = []
    started = condition_coverage.start_from_env(
        {
            "CONDITION_COVERAGE_ROOT": str(project),
            "CONDITION_COVERAGE_COVER": "lib/*.py,src/**/*.py",
            "CONDITION_COVERAGE_DIR": str(tmp_path),
        },
        on_exit=exits.append,
    )
    try:
        trails = _imported(project, "single_and_trails")
        assert trails.is_new("T3", {"T3": {"new": False}}) is False
    finally:
        condition_coverage.stop()
    assert started is True
    [report] = exits
    report()
    site = "src/single_and_trails.py:6:11"
    assert json.loads((tmp_path / "condition_coverage.json").read_text()) == {
        "sites": {
            site: [
                {"truthy": 1, "falsy": 0},
                {"truthy": 0, "falsy": 1},
            ]
        }
    }
    assert capsys.readouterr().out == (
        f"{site} operand 0 never false\n" f"{site} operand 1 never true\n"
    )


def test_e5a70c04(tmp_path, capsys):
    """A part run (eg an xdist worker) writes only its own part file; the
    main run clears stale parts as it starts, and at exit adds every part's
    counts to its own before writing the report and printing the gaps."""
    project = PROJECTS / "single_and"
    stale = tmp_path / "condition_coverage.gw7.json"
    stale.parent.mkdir(exist_ok=True)
    stale.write_text('{"sites": {}}')
    settings = {"root": project, "cover": ["src/**/*.py"], "coverage_dir": tmp_path}
    main_exits, worker_exits = [], []
    condition_coverage.start(**settings, on_exit=main_exits.append)
    condition_coverage.stop()
    assert not stale.exists()
    condition_coverage.start(**settings, part="gw0", on_exit=worker_exits.append)
    try:
        trails = _imported(project, "single_and_trails")
        assert trails.is_new("T4", {"T4": {"new": True}}) is True
        assert trails.is_new("T5", {"T5": {"new": False}}) is False
    finally:
        condition_coverage.stop()
    worker_exits[0]()
    assert capsys.readouterr().out == ""
    assert sorted(p.name for p in tmp_path.iterdir()) == ["condition_coverage.gw0.json"]
    main_exits[0]()
    site = "src/single_and_trails.py:6:11"
    assert json.loads((tmp_path / "condition_coverage.json").read_text()) == {
        "sites": {
            site: [
                {"truthy": 2, "falsy": 0},
                {"truthy": 1, "falsy": 1},
            ]
        }
    }
    assert capsys.readouterr().out == f"{site} operand 0 never false\n"


def test_e5a70c05(tmp_path, capsys):
    """start_from_env passes a part name through to start."""
    project = PROJECTS / "single_and"
    exits = []
    condition_coverage.start_from_env(
        {
            "CONDITION_COVERAGE_ROOT": str(project),
            "CONDITION_COVERAGE_COVER": "src/**/*.py",
            "CONDITION_COVERAGE_DIR": str(tmp_path),
        },
        part="gw3",
        on_exit=exits.append,
    )
    condition_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == ""
    assert [p.name for p in tmp_path.iterdir()] == ["condition_coverage.gw3.json"]


def test_e5a70c06(tmp_path, capsys):
    """A covered file the run never imported is still reported, every site
    in it as never reached."""
    project = PROJECTS / "never_imported"
    exits = []
    condition_coverage.start(
        root=project, cover=["src/*.py"], coverage_dir=tmp_path, on_exit=exits.append
    )
    try:
        flows = _imported(project, "never_imported_flows")
        assert flows.is_public({"public": False, "owner": "everyone"}) is True
        assert flows.is_public({"public": True, "owner": "kosli"}) is True
    finally:
        condition_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == (
        "src/never_imported_flows.py:6:11 operand 1 never false\n"
        "src/never_imported_policies.py:6:11 never reached\n"
    )


def test_e5a70c07(tmp_path, capsys):
    """report=["html"] writes index.html, linking each covered file, and
    files/<path>.html, its source with each condition's tree; with no
    "gaps" in report nothing is printed."""
    project = PROJECTS / "single_and"
    exits = []
    condition_coverage.start(
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
        condition_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == ""
    index = (tmp_path / "index.html").read_text()
    assert '<a href="files/src/single_and_trails.py.html">src/single_and_trails.py</a>' in index
    page = (tmp_path / "files" / "src" / "single_and_trails.py.html").read_text()
    assert '<a data-index="" href="../../index.html">Condition coverage</a>' in page
    assert '<span class="text" data-text="">trails[trail_id][&quot;new&quot;]</span>' in page


def test_e5a70c08(tmp_path):
    """An unknown reporter is refused by name, listing the known ones."""
    try:
        condition_coverage.start(
            root=PROJECTS / "single_and",
            cover=["src/**/*.py"],
            coverage_dir=tmp_path,
            report=["gaps", "htm"],
            on_exit=lambda report: None,
        )
    except ValueError as error:
        assert str(error) == "unknown reporter 'htm'; the reporters are: gaps, html"
    else:
        condition_coverage.stop()
        raise AssertionError("start accepted reporter 'htm'")


def test_e5a70c09(tmp_path, capsys):
    """start_from_env takes the reporters, comma-separated, from
    CONDITION_COVERAGE_REPORT."""
    exits = []
    condition_coverage.start_from_env(
        {
            "CONDITION_COVERAGE_ROOT": str(PROJECTS / "single_and"),
            "CONDITION_COVERAGE_COVER": "src/**/*.py",
            "CONDITION_COVERAGE_DIR": str(tmp_path),
            "CONDITION_COVERAGE_REPORT": "html",
        },
        on_exit=exits.append,
    )
    condition_coverage.stop()
    exits[0]()
    assert capsys.readouterr().out == ""
    assert (tmp_path / "index.html").exists()


def test_e5a70c03():
    """Without CONDITION_COVERAGE_COVER, start_from_env starts nothing."""
    exits = []
    started = condition_coverage.start_from_env(
        {"CONDITION_COVERAGE_ROOT": "/app"}, on_exit=exits.append
    )
    assert started is False
    assert exits == []

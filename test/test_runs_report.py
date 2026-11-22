import json
import sys

import pytest

import path_coverage
from path_coverage import runs_report
from test_kernel import _imported

TOTAL = (
    "def total(orders):\n"
    "    amount = 0\n"
    "    for order in orders:\n"
    "        if order['paid']:\n"
    "            amount += order['amount']\n"
    "    return amount\n"
)


def _saved_run(root):
    """The JSON report of a run of total, written into root/src, called
    on no orders and on a paid and an unpaid one, so every path is
    taken, with loops on or off."""
    (root / "src").mkdir()
    (root / "src" / "loop_orders.py").write_text(TOTAL)
    exits = []
    path_coverage.start(root=root, cover=["src/*.py"], coverage_dir=root / "run", report=[], on_exit=exits.append)
    try:
        loop_orders = _imported(root, "loop_orders")
        orders = [{"paid": True, "amount": 12}, {"paid": False, "amount": 7}]
        assert [loop_orders.total([]), loop_orders.total(orders)] == [0, 12]
    finally:
        path_coverage.stop()
    exits[0]()
    return root / "run" / "path_coverage.json"


def test_7c2d9101(tmp_path, capsys):
    """Example: path_coverage_report --loops ROOT 'src/*.py' OUT RUN, of
    a saved run of total, a for loop whose body holds an if
    The command reports the saved runs into OUT, each loop a fork with
    --loops: total's flow has 3 ways, 0 items, or 1+ items then the if
    true or false, all covered. It prints its totals, read from the JSON
    it wrote, even when no way is untested."""
    run = _saved_run(tmp_path)
    out = tmp_path / "reported"
    assert runs_report.main(["--loops", str(tmp_path), "src/*.py", str(out), str(run)]) == 0
    assert capsys.readouterr().out == "Paths: 3 / 3 (100.00%)\nFunctions over --max-paths=4096: 0\n"
    flow = json.loads((out / "path_coverage.json").read_text())["flows"]["src/loop_orders.py:1:0"]
    assert (flow["ways"], flow["gaps"]) == (3, [])


def test_7c2d9103(tmp_path, capsys):
    """Example: path_coverage_report --max-paths 1 ROOT 'src/*.py' OUT RUN,
    of a saved run of total, whose 2 ways are more than 1
    A function with more paths than --max-paths fails: it is named, with
    what to do, before the totals, and the command exits 1."""
    run = _saved_run(tmp_path)
    out = tmp_path / "reported"
    assert runs_report.main(["--max-paths", "1", str(tmp_path), "src/*.py", str(out), str(run)]) == 1
    assert capsys.readouterr().out == (
        "src/loop_orders.py:1 total() has 2 paths, more than --max-paths allows.\n"
        "Split it into smaller functions.\n"
        "Paths: 0 / 0 (-)\n"
        "Functions over --max-paths=1: 1\n"
    )


def test_7c2d9102(monkeypatch, capsys):
    """Example: path_coverage_report -h, its entry point run in this
    process
    It prints its usage, with an example, and exits 0."""
    monkeypatch.setattr(sys, "argv", ["path_coverage_report", "-h"])
    with pytest.raises(SystemExit) as exited:
        runs_report.command()
    assert exited.value.code == 0
    assert capsys.readouterr().out == (
        "Usage: path_coverage_report [--loops] [--max-paths N] SOURCE_ROOT GLOBS REPORT_DIR RUN_JSON...\n"
        "\n"
        "Reports the saved runs RUN_JSON... as one, writing the report into\n"
        "REPORT_DIR, then prints each function's untested paths and the totals.\n"
        "Exits 0 when every path is taken, and 1 when any is not.\n"
        "\n"
        "  SOURCE_ROOT  the directory holding the covered source\n"
        "  GLOBS        comma-separated globs of the covered files, relative to SOURCE_ROOT\n"
        "  REPORT_DIR   the directory it writes its report into\n"
        "  RUN_JSON...  one or more saved runs' JSON files, space-separated\n"
        "\n"
        "Options:\n"
        "  -h             Show this help\n"
        "  --loops        Count each loop as a decision: 0 items or 1+ items\n"
        "  --max-paths N  Fail each function with more than N paths\n"
        "                 (default 4096, at most 65536)\n"
        "\n"
        "Example:\n"
        "  path_coverage_report --max-paths 8 /app 'src/**/*.py' report runs/*.json\n"
    )

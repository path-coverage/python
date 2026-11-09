import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).parent / "projects" / "single_and"
SRC = Path(__file__).parent.parent / "src"


def test_b8e2f601(tmp_path):
    """Example: pytest -p path_coverage.pytest_plugin, with PATH_COVERAGE_*
    covering single_and's src/, running a test that calls is_new once with
    a new trail
    The plugin starts path coverage before the tests import is_new, so it
    is instrumented, and writes the report as pytest ends: is_new called
    once, its and's true-true path taken."""
    (tmp_path / "test_trails.py").write_text(
        "import single_and_trails\n"
        "\n"
        "def test_new():\n"
        "    assert single_and_trails.is_new('T1', {'T1': {'new': True}})\n"
    )
    env = {
        **os.environ,
        "PATH_COVERAGE_ROOT": str(PROJECT),
        "PATH_COVERAGE_COVER": "src/**/*.py",
        "PATH_COVERAGE_DIR": str(tmp_path / "coverage"),
        "PATH_COVERAGE_REPORT": "summary",
        "PYTHONPATH": f"{SRC}{os.pathsep}{PROJECT / 'src'}",
    }
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "path_coverage.pytest_plugin", "-p", "no:cacheprovider", "-q", "test_trails.py"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    report = json.loads((tmp_path / "coverage" / "path_coverage.json").read_text())
    assert report["reached"] == {"src/single_and_trails.py:4:0": 1}
    counts = {tuple(each["path"]): each["count"] for each in report["paths"]["src/single_and_trails.py:6:38"]["taken"]}
    assert counts == {(True, True): 1, (True, False): 0, (False, None): 0}

"""Self-coverage: path_coverage measuring its own src/ and test/ while its
own tests run. A pytest plugin, loaded by bin/test.sh with -p self_coverage,
so it starts before any test module, or path_coverage itself, is imported.

The code measured and the tool measuring are the same package in one
process, so the tool runs as a copy of src/path_coverage, in a temporary
dir, renamed path_coverage_self, so no module is shared with the code it
measures. Each claims a sys.monitoring tool id of its own, so the tests
start and stop path_coverage as they always do, untouched.

Pytest rewrites a test module's asserts as it imports it, as it would
without path coverage; the copy measures the code pytest compiled."""

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import suites

ROOT = Path(__file__).resolve().parent.parent
REPORTS = Path(os.environ.get("PATH_COVERAGE_SELF_DIR", ROOT / "reports" / "paths"))
SELF_IMPORT = re.compile(r"^(\s*)(from|import) path_coverage\b", re.MULTILINE)

_reports = []


def copy(into):
    """Copies src/path_coverage into the dir into as package
    path_coverage_self, every absolute self-import renamed too; returns
    the copy's dir."""
    package = into / "path_coverage_self"
    shutil.copytree(
        ROOT / "src" / "path_coverage", package, ignore=shutil.ignore_patterns("__pycache__")
    )
    for file in package.rglob("*.py"):
        file.write_text(SELF_IMPORT.sub(r"\1\2 path_coverage_self", file.read_text()))
    return package


def start():
    """Copies the package, then starts the copy covering src/ and test/,
    groups code and test, reporting html and JSON into REPORTS when pytest
    unconfigures. This file and suites.py, loaded before it starts, run
    outside the measured run, so are skipped; so are the files the suite
    leaves out, which never run."""
    into = Path(tempfile.mkdtemp(prefix="path_coverage_self."))
    copy(into)
    sys.path.insert(0, str(into))
    import path_coverage_self

    path_coverage_self.start(
        root=ROOT,
        cover=["src/**/*.py", "test/**/*.py"],
        skip=["test/projects/**", "test/self_coverage.py", "test/suites.py", *suites.excluded()],
        coverage_dir=REPORTS,
        report=[],
        groups={"code": ["src/**/*.py"], "test": ["test/**/*.py"]},
        on_exit=_reports.append,
    )
    _reports.append(lambda: shutil.rmtree(into))


def pytest_unconfigure(config):
    """Writes the self-coverage report, once every test has run, then
    removes the copy."""
    while _reports:
        _reports.pop(0)()


start()

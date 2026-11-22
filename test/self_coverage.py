"""Self-coverage: path_coverage measuring its own src/ and test/ while its
own tests run. A pytest plugin, loaded by bin/test.sh with -p self_coverage,
so it starts before any test module, or path_coverage itself, is imported.

The code measured and the tool measuring are the same package in one
process, so the tool runs as a copy of src/path_coverage, in a temporary
dir, renamed path_coverage_self, the name its wrapped operands call
renamed too, so no name is shared with the code it measures. Each claims a
sys.monitoring tool id of its own, and the tests start and stop
path_coverage as they always do, untouched, as it is a different package
with its own finder on sys.meta_path.

The copy's finder goes in front of pytest's assertion rewriting hook, so
the copy's loader rewrites a test module's asserts, after its own
wrapping, as pytest would have."""

import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest
import suites
from _pytest.assertion.rewrite import rewrite_asserts

ROOT = Path(__file__).resolve().parent.parent
REPORTS = Path(os.environ.get("PATH_COVERAGE_SELF_DIR", ROOT / "reports" / "paths"))
# Each name the copy must not share with the code it measures, and its
# name in the copy.
RENAMES = {"__path_coverage__": "__path_coverage_self__"}
SELF_IMPORT = re.compile(r"^(\s*)(from|import) path_coverage\b", re.MULTILINE)

_reports = []


def copy(into):
    """Copies src/path_coverage into the dir into as package
    path_coverage_self, every injected name renamed as RENAMES says and
    every absolute self-import renamed too; returns the copy's dir."""
    package = into / "path_coverage_self"
    shutil.copytree(
        ROOT / "src" / "path_coverage", package, ignore=shutil.ignore_patterns("__pycache__")
    )
    for file in package.rglob("*.py"):
        text = file.read_text()
        for name, renamed in RENAMES.items():
            text = text.replace(name, renamed)
        file.write_text(SELF_IMPORT.sub(r"\1\2 path_coverage_self", text))
    return package


def _asserting_loader(kernel):
    """A subclass of kernel's loader that, for a test module, rewrites its
    asserts as pytest does, after kernel's own wrapping."""

    class AssertingLoader(kernel._Loader):
        """The copy's loader, with pytest's assertion rewriting of test
        modules, which the copy's finder takes from pytest's own hook."""

        def compiled(self, tree, path):
            """tree, the module's wrapped parse, compiled, a test module's
            asserts rewritten first."""
            if Path(path).name.startswith("test_"):
                rewrite_asserts(tree, self.get_data(path), path)
            return super().compiled(tree, path)

    return AssertingLoader


def start():
    """Copies the package, then starts the copy covering src/ and test/,
    groups code and test, reporting html and JSON into REPORTS when pytest
    unconfigures, in the events mode PATH_COVERAGE_SELF_EVENTS names,
    monitoring when it is not set. This file and suites.py, loaded before it starts, run
    outside the measured run, so are skipped; so are the files the suite
    leaves out, which never run. Returns the copy's kernel, which counts
    each test under its node id as the test runs."""
    into = Path(tempfile.mkdtemp(prefix="path_coverage_self."))
    copy(into)
    sys.path.insert(0, str(into))
    import path_coverage_self
    from path_coverage_self import kernel

    kernel._Loader = _asserting_loader(kernel)
    path_coverage_self.start(
        root=ROOT,
        cover=["src/**/*.py", "test/**/*.py"],
        skip=["test/projects/**", "test/self_coverage.py", "test/suites.py", *suites.excluded()],
        coverage_dir=REPORTS,
        report=[],
        groups={"code": ["src/**/*.py"], "test": ["test/**/*.py"]},
        events=os.environ.get("PATH_COVERAGE_SELF_EVENTS", "monitoring"),
        on_exit=_reports.append,
    )
    _reports.append(lambda: shutil.rmtree(into))
    return kernel


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Counts item's setup, call and teardown under its node id in the
    self-coverage report, then what follows under no test."""
    KERNEL.testing(item.nodeid)
    yield
    KERNEL.testing(KERNEL.tally.NO_TEST)


def pytest_unconfigure(config):
    """Writes the self-coverage report, once every test has run, then
    removes the copy; with PATH_COVERAGE_SELF_PROGRESS on, says when the
    report starts and how long it took, as it prints nothing else."""
    started = time.monotonic()
    _progress("self-coverage: writing the report")
    while _reports:
        _reports.pop(0)()
    _progress(f"self-coverage: report written in {time.monotonic() - started:.1f}s")


def _progress(line):
    """Prints line when PATH_COVERAGE_SELF_PROGRESS is on, as
    bin/test.sh --progress sets it; a plain run prints nothing."""
    if os.environ.get("PATH_COVERAGE_SELF_PROGRESS") == "on":
        print(line, flush=True)


KERNEL = start()

"""A pytest plugin, loaded with `-p path_coverage.pytest_plugin`, that
starts path coverage from the PATH_COVERAGE_* variables before any
conftest is imported, so covered modules a conftest imports are measured
too. Without PATH_COVERAGE_COVER it does nothing.

Once a run has started, each test's setup, call and teardown are counted
under its node id, so the report tells which tests take which paths; what
runs between tests, eg a module's import, is counted under tally.NO_TEST.

Under pytest-xdist each worker reports as a part named by its worker id, and
the controller adds the parts to its own report. Reports run as pytest
unconfigures rather than at exit, since a worker may exit without running
its exit handlers."""

import os

import pytest

from .kernel import start_from_env, testing
from .tally import NO_TEST

_reports = []


class _Tests:
    """The hook marking each test, registered only as a run starts, as
    only a run can count under a test."""

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        """Counts item's setup, call and teardown under its node id, then
        what follows under NO_TEST."""
        testing(item.nodeid)
        yield
        testing(NO_TEST)


def pytest_load_initial_conftests(early_config, parser, args):
    """Starts path coverage ahead of the initial conftests; a run that
    starts marks each test from then on."""

    def started(report):
        """Keeps the run's report, which start hands over as the run
        starts, for unconfigure, and marks each test from now on."""
        _reports.append(report)
        early_config.pluginmanager.register(_Tests())

    start_from_env(os.environ, part=os.environ.get("PYTEST_XDIST_WORKER"), on_exit=started)


def pytest_unconfigure(config):
    """Writes this process's report: a worker's part, or the whole."""
    while _reports:
        _reports.pop()()

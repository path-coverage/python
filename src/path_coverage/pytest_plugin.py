"""A pytest plugin, loaded with `-p path_coverage.pytest_plugin`, that
starts path coverage from the PATH_COVERAGE_* variables before any
conftest is imported, so covered modules a conftest imports are measured
too. Without PATH_COVERAGE_COVER it does nothing.

Under pytest-xdist each worker reports as a part named by its worker id, and
the controller adds the parts to its own report. Reports run as pytest
unconfigures rather than at exit, since a worker may exit without running
its exit handlers."""

import os

from .kernel import start_from_env

_reports = []


def pytest_load_initial_conftests(early_config, parser, args):
    """Starts path coverage ahead of the initial conftests."""
    start_from_env(os.environ, part=os.environ.get("PYTEST_XDIST_WORKER"), on_exit=_reports.append)


def pytest_unconfigure(config):
    """Writes this process's report: a worker's part, or the whole."""
    while _reports:
        _reports.pop()()

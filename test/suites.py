"""The suites a run can be, each the test files it runs and whether its
coverage is checked: all, every test; core, the hand-written tests, without
the generated ones in test/property, neither run nor measured; property,
those alone, whose coverage covers only part of the code, so, as a run of
chosen tests, is not checked. The one place a suite is decided: a pytest
plugin, loaded by bin/test.sh with -p suites, which collects only the
suite's files; read by test/self_coverage.py, which skips the files the
suite leaves out; and run by bin/test.sh as a script, which says whether
the suite's coverage is checked. PATH_COVERAGE_SUITE names the suite, all
when unset."""

import os
import sys
from pathlib import Path, PurePath

ROOT = Path(__file__).resolve().parent.parent

# The generated tests and the grammar they are generated from.
PROPERTY = "test/property/**"

TABLE = {
    "all": {"runs": "test/**", "without": [], "checked": True},
    "core": {"runs": "test/**", "without": [PROPERTY], "checked": True},
    "property": {"runs": PROPERTY, "without": [], "checked": False},
}


def name():
    """The current suite's name, from PATH_COVERAGE_SUITE; exits naming the
    suites there are for a name TABLE does not have."""
    named = os.environ.get("PATH_COVERAGE_SUITE", "all")
    if named not in TABLE:
        sys.exit(f"no suite named {named}: use one of {', '.join(TABLE)}")
    return named


def excluded():
    """The globs, relative to the root, of the files the current suite
    leaves out, so neither runs nor measures."""
    return TABLE[name()]["without"]


def runs(path):
    """True for path, a file or dir, when the current suite runs the tests
    in it: under its runs glob, or a dir above it, and not left out."""
    relative = PurePath(path).relative_to(ROOT)
    suite = TABLE[name()]
    inside = relative.full_match(suite["runs"]) or PurePath(suite["runs"]).is_relative_to(relative)
    return inside and not any(relative.full_match(glob) for glob in suite["without"])


def checked():
    """True when the current suite's coverage is checked: its line and
    branch coverage, and its paths' totals."""
    return TABLE[name()]["checked"]


def pytest_ignore_collect(collection_path, config):
    """True for a path under test/ that the current suite does not run, so
    pytest neither collects nor imports it; None, pytest deciding, for any
    other."""
    return None if runs(collection_path) else True


if __name__ == "__main__":
    print("checked" if checked() else "unchecked")

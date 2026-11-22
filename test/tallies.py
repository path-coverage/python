"""Tallies as the package's own tests see them: each runs measured code
directly, under no test switch, so all it counts is outside every test."""

from path_coverage import tally
from path_coverage.tally import NO_TEST, Tally


def untested(count):
    """The Tally of count happenings outside every test; empty for 0."""
    return Tally({NO_TEST: count} if count else {})


def listed_untested(count):
    """untested(count) as the JSON report lists it, by NO_TEST's key."""
    return tally.listed(untested(count))


# The JSON report's tests when everything it counts ran outside every test.
UNTESTED_TESTS = {tally.key(NO_TEST): NO_TEST}

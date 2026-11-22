import pytest

from path_coverage import tally
from path_coverage.tally import NO_TEST, Tally

MANIFEST = "test/test_manifest.py::test_5c1e9a1a"
MONITOR = "test/test_monitor.py::test_d86a1f18"


def test_7c3e9101():
    """A tally counts each happening under the test that made it happen,
    and its total is the sum over its tests."""
    counted = Tally()
    counted.add(MANIFEST)
    counted.add(MONITOR)
    counted.add(MANIFEST)
    assert counted == Tally({MANIFEST: 2, MONITOR: 1})
    assert counted.total == 3


def test_7c3e9102():
    """Two tallies add test by test, a test in one only keeping its own
    count, neither tally changed."""
    first = Tally({MANIFEST: 2})
    second = Tally({MANIFEST: 1, NO_TEST: 4})
    assert first + second == Tally({MANIFEST: 3, NO_TEST: 4})
    assert first == Tally({MANIFEST: 2})


def test_7c3e9103():
    """A tally holds only tests that made something happen: a count below
    1 is refused, naming the test, as an empty entry would claim a test
    took part that never did."""
    with pytest.raises(ValueError, match=r"test/test_manifest.py::test_5c1e9a1a counted 0"):
        Tally({MANIFEST: 0})


def test_7c3e9104():
    """A test's key is the first 12 hex digits of the sha256 of its id."""
    assert tally.key(MANIFEST) == "ebded4bbf7ae"
    assert tally.key(NO_TEST) == "9a8e6a205ed4"


def test_7c3e9105():
    """A tally is listed in JSON by its tests' keys, and read back, by the
    report's tests, as the same tally."""
    counted = Tally({MANIFEST: 2, MONITOR: 1})
    tests = tally.named([MANIFEST, MONITOR])
    assert tally.listed(counted) == {"ebded4bbf7ae": 2, "8314e0658747": 1}
    assert tests == {"ebded4bbf7ae": MANIFEST, "8314e0658747": MONITOR}
    assert tally.read(tally.listed(counted), tests) == counted


def test_7c3e9107():
    """Example: a report whose flow.py and took [True, True] in
    test_5c1e9a1a twice and outside every test once, its ship reached in
    test_d86a1f18
    A report is made JSON by listing each of its tallies by key, wherever
    it is, and naming every key's test in its tests, gathered from those
    same tallies, so no test is named that no tally counts."""
    report = {
        "paths": {"flow.py:2:23": {"taken": [{"path": [True, True], "tests": Tally({MANIFEST: 2, NO_TEST: 1})}]}},
        "reached": {"flow.py:1:0": Tally({MONITOR: 1})},
        "kinds": ["and"],
    }
    assert tally.jsonable(report) == {
        "paths": {"flow.py:2:23": {"taken": [{"path": [True, True], "tests": {"ebded4bbf7ae": 2, "9a8e6a205ed4": 1}}]}},
        "reached": {"flow.py:1:0": {"8314e0658747": 1}},
        "kinds": ["and"],
        "tests": {"8314e0658747": MONITOR, "9a8e6a205ed4": NO_TEST, "ebded4bbf7ae": MANIFEST},
    }


def test_7c3e9108():
    """A tally shows as it is built, so a failing assertion names each
    test and its count."""
    assert repr(Tally({MANIFEST: 2})) == "Tally({'test/test_manifest.py::test_5c1e9a1a': 2})"


def test_7c3e9106():
    """Reports' tests join into one {key: id}; a key naming two ids is
    refused, naming both, as their counts would be added as one test's."""
    first = {"ebded4bbf7ae": MANIFEST}
    second = {"ebded4bbf7ae": MONITOR, "9a8e6a205ed4": NO_TEST}
    assert tally.joined([first, {"ebded4bbf7ae": MANIFEST}]) == first
    with pytest.raises(ValueError, match=r"ebded4bbf7ae names both .*test_5c1e9a1a and .*test_d86a1f18"):
        tally.joined([first, second])

from path_coverage.path_gaps import lines, possible
from path_coverage.path_manifest import Decision, PathMethod

FEE = PathMethod(name="fee", decisions=(Decision(line=4), Decision(line=7)))


def test_3e8d5b01():
    """Example: fee's two decisions, neither leaving the function
    Every path through them is possible, True before False at each."""
    assert possible(FEE.decisions) == [
        [True, True],
        [True, False],
        [False, True],
        [False, False],
    ]


def test_3e8d5b02():
    """Example: a first decision whose then arm returns
    A path taking that outcome ends there, as [True].
    Only the other outcome goes on to the second decision."""
    decisions = (Decision(line=3, exits=True), Decision(line=6))
    assert possible(decisions) == [[True], [False, True], [False, False]]


def test_3e8d5b03():
    """Example: fee called with True then False only
    One line per path never taken, each decision named by its line."""
    paths = {"src/fee.py:1:0": {(True, False): 1}}
    assert lines({"src/fee.py:1:0": FEE}, paths) == [
        "src/fee.py:1:0 fee path never taken: line 4 true, line 7 true",
        "src/fee.py:1:0 fee path never taken: line 4 false, line 7 true",
        "src/fee.py:1:0 fee path never taken: line 4 false, line 7 false",
    ]

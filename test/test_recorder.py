from path_coverage.recorder import Recorder


def test_a91d2e01():
    """record counts each operand's truthy and falsy outcomes, keyed by
    (site, index), and returns the value unchanged."""
    recorder = Recorder()
    site = "src/model/flow.py:2:11"
    assert recorder.record(site, 0, "flow-1") == "flow-1"
    assert recorder.record(site, 0, "") == ""
    assert recorder.record(site, 0, "flow-2") == "flow-2"
    assert recorder.record(site, 1, None) is None
    assert recorder.counts == {
        (site, 0): {"truthy": 2, "falsy": 1},
        (site, 1): {"truthy": 0, "falsy": 1},
    }


def test_a91d2e02():
    """Example: ok(id) and new(id), evaluated twice
    enter starts a trail for one evaluation of the site.
    Each record notes its leaf's outcome on that trail.
    leave counts the trail as a path, and returns the value unchanged.
    A leaf the evaluation never reached stays None on the path."""
    recorder = Recorder()
    site = "src/model/flow.py:2:11"
    for ok, new in [(True, False), (False, None)]:
        trail = recorder.enter(site, 2)
        value = recorder.record(site, 0, ok) and recorder.record(site, 1, new)
        assert recorder.leave(trail, value) is value
    assert recorder.site_paths == {
        site: {(True, False): 1, (False, None): 1},
    }


def test_a91d2e04():
    """Example: fee with two decisions, called with member and not big,
    then with an early return at its first decision
    path starts one call's path through the function's 2 decisions.
    decide notes each decision's outcome and returns its value unchanged.
    The path is counted once its last decision is made.
    A decision taking its exits outcome ends and counts the path early."""
    recorder = Recorder()
    site = "src/fee.py:1:0"
    path = recorder.path(site, 2)
    assert recorder.decide(path, 0, "member") == "member"
    assert recorder.decide(path, 1, 0) == 0
    early = recorder.path(site, 2)
    recorder.decide(early, 0, True, exits=True)
    assert recorder.paths == {site: {(True, False): 1, (True,): 1}}


def test_a91d2e03():
    """Example: a site evaluated inside an evaluation of itself, as in
    a recursive call
    Each evaluation fills in a trail of its own.
    So the inner path does not mix with the outer one."""
    recorder = Recorder()
    site = "src/model/tree.py:3:11"
    outer = recorder.enter(site, 2)
    recorder.record(site, 0, True)
    inner = recorder.enter(site, 2)
    recorder.record(site, 0, False)
    recorder.leave(inner, False)
    recorder.record(site, 1, True)
    recorder.leave(outer, True)
    assert recorder.site_paths == {
        site: {(False, None): 1, (True, True): 1},
    }

from condition_coverage.recorder import Recorder


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

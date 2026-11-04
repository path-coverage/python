from path_coverage import kinds
from path_coverage.kinds.block import Block
from path_coverage.kinds.case import Case
from path_coverage.kinds.chain import Chain
from path_coverage.kinds.choice import Choice


def test_4b7a2e01():
    """Example: the operators and, or, case, ternary, if, filter, match,
    any and all
    Each names the kind that knows its paths and values.
    and, or and a match's case are chains.
    ternary, if and filter are choices.
    match is a Case.
    any and all are Blocks."""
    operators = ["and", "or", "case", "ternary", "if", "filter", "match", "any", "all"]
    found = [type(kinds.of(operator)) for operator in operators]
    assert found == [Chain, Chain, Chain, Choice, Choice, Choice, Case, Block, Block]


def test_4b7a2e03():
    """Example: the arms of the filter in [u for u in users if u.active]
    Its arms hold no text of their own.
    So they are named for what they do to the item: keep and drop."""
    choice = kinds.of("filter")
    arms = [{"arm": arm, "text": None, "cells": [True], "body": None} for arm in ("then", "else")]
    assert [choice.arm_label(arm, "filter") for arm in arms] == ["keep", "drop"]


def test_4b7a2e02():
    """Example: the kinds measured
    Their names, in order, are a report's fingerprint.
    Runs measuring different kinds list a site's paths differently."""
    assert kinds.names() == ["block", "case", "chain", "choice"]

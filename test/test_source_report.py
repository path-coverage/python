from path_coverage import decision_paths, manifest, source_report
from tallies import untested

KATA = "def kata(id):\n    while ok(id) and new(id): break\n"

PATHS = [
    {"path": [True, True], "tests": untested(1)},
    {"path": [True, False], "tests": untested(0)},
    {"path": [False, None], "tests": untested(2)},
]


def test_5e2a9110():
    """Example: def kata(id): while ok(id) and new(id): break
    Each line of a file's source, as the source report has it: its text and
    its coloured tokens, so a renderer can draw the code without parsing it.
    A line with no decision has its line too."""
    assert source_report.lines(KATA) == [
        {"text": "def kata(id):", "tokens": [[0, 3, "k"]]},
        {"text": "    while ok(id) and new(id): break", "tokens": [[4, 9, "k"], [17, 20, "k"], [30, 35, "k"]]},
    ]


def test_5e2a9120():
    """Example: ok(id) and new(id)
    A decision, as the source report has it: the lines it spans and its fold's
    rows, headed by its row's top, a column per path in the order the JSON
    report lists them, and no counts, which the JSON report has."""
    decisions = manifest.decisions(KATA, "k.py")
    assert source_report.decision(KATA, decisions, "k.py:2:17", PATHS, "and") == {
        "span": [2, 2],
        "fold": [
            {"kind": "decision", "branch": "", "label": {"text": "and", "tokens": [[0, 3, "k"]]},
             "at": [2, 10, 2, 28], "else": None},
            {"kind": "operand", "branch": "ths", "label": {"text": "ok(id)", "tokens": []},
             "at": [2, 10, 2, 16], "cells": [["T", None, None], ["T", None, None], ["F", None, None]]},
            {"kind": "operand", "branch": "lhs", "label": {"text": "new(id)", "tokens": []},
             "at": [2, 21, 2, 28], "cells": [["T", None, None], ["F", None, None], ["", None, None]]},
        ],
    }


def test_5e2a9130():
    """Example: k.py's kata, in groups Katas, k*.py, and Other, x.py
    The source report of a run: no operators ignored, the covered files of
    each group, each flow row's top coloured, a return's too, and each
    covered file's lines and decisions, each decision's fold headed by its flow
    row's top."""
    decisions = manifest.decisions(KATA, "k.py")
    files = {"k.py": (KATA, decisions)}
    flows = {
        "k.py:1:0": {"rows": [{"decision": "k.py:2:17", "top": "and"}, {"decision": None, "top": "return"}]}
    }
    groups = {"Katas": ["k*.py"], "Other": ["x.py"]}
    assert source_report.of(files, {"k.py:2:17": PATHS}, flows, groups) == {
        "$schema": "https://path-coverage.github.io/schemas/v3/path_coverage.source.schema.json",
        "schema": 1,
        "ignored": [],
        "groups": {"Katas": ["k.py"], "Other": []},
        "labels": {
            "and": {"text": "and", "tokens": [[0, 3, "k"]]},
            "return": {"text": "return", "tokens": [[0, 6, "k"]]},
        },
        "files": {
            "k.py": {
                "lines": source_report.lines(KATA),
                "decisions": {"k.py:2:17": source_report.decision(KATA, decisions, "k.py:2:17", PATHS, "and")},
            }
        },
    }


def test_5e2a9140():
    """Example: no groups given
    The source report of a run with no groups has none."""
    assert source_report.of({}, {}, {}, None)["groups"] == {}


def _labels(source, kind):
    """The labels of the fold rows of kind, eg operand, of the one decision
    in source, the file k.py, as the source report gives them."""
    decisions = manifest.decisions(source, "k.py")
    [name] = decisions
    paths = [{"path": path, "tests": untested(0)} for path in decision_paths.possible(decisions[name])]
    fold = source_report.decision(source, decisions, name, paths, "return")["fold"]
    return [row["label"] for row in fold if row["kind"] == kind]


def test_5e2a9150():
    """Example: return f(a,  # first, then b) and c on the next line
    The operand reads as one line, its line break and the indent after it
    one space, coloured as the file colours it: its comment, which alone
    would leave its bracket unclosed, is still a comment."""
    labels = _labels("def ok(a, b, c):\n    return f(a,  # first\n             b) and c\n", "operand")
    assert labels[0] == {"text": "f(a,  # first b)", "tokens": [[6, 13, "c"]]}


def test_5e2a9160():
    """Example: return f(1, then 2) and c on the next line
    Each number of the operand is coloured where the one line it reads as
    puts it."""
    labels = _labels("def ok(c):\n    return f(1,\n             2) and c\n", "operand")
    assert labels[0] == {"text": "f(1, 2)", "tokens": [[2, 3, "n"], [5, 6, "n"]]}


def test_5e2a9170():
    """Example: return c if a else f(1, then 2) on the next line
    The else arm reads as one line, as an operand does, its numbers on
    both lines coloured, after its : coloured as an operator."""
    labels = _labels("def ok(a, c):\n    return c if a else f(1,\n                         2)\n", "arm")
    assert labels[1] == {"text": ": f(1, 2)", "tokens": [[0, 1, "o"], [4, 5, "n"], [7, 8, "n"]]}

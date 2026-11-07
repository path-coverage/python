from path_coverage import decision_paths, manifest, source_report

KATA = "def kata(id):\n    return ok(id) and new(id)\n"

PATHS = [
    {"path": [True, True], "count": 1},
    {"path": [True, False], "count": 0},
    {"path": [False, None], "count": 2},
]


def test_5e2a9110():
    """Example: def kata(id): return ok(id) and new(id)
    Each line of a file's source, as the source report has it: its text and
    its coloured tokens, so a renderer can draw the code without parsing it.
    A line with no decision has its line too."""
    assert source_report.lines(KATA) == [
        {"text": "def kata(id):", "tokens": [[0, 3, "k"]]},
        {"text": "    return ok(id) and new(id)", "tokens": [[4, 10, "k"], [18, 21, "k"]]},
    ]


def test_5e2a9120():
    """Example: ok(id) and new(id)
    A decision, as the source report has it: the lines it spans and its fold's
    rows, headed by its row's top, a column per path in the order the JSON
    report lists them, and no counts, which the JSON report has."""
    decisions = manifest.decisions(KATA, "k.py")
    assert source_report.decision(KATA, decisions, "k.py:2:18", PATHS, "and") == {
        "span": [2, 2],
        "fold": [
            {"kind": "decision", "branch": "", "label": {"text": "and", "tokens": [[0, 3, "k"]]},
             "at": [2, 11, 2, 29], "else": None},
            {"kind": "operand", "branch": "ths", "label": {"text": "ok(id)", "tokens": []},
             "at": [2, 11, 2, 17], "cells": [["T", None, None], ["T", None, None], ["F", None, None]]},
            {"kind": "operand", "branch": "lhs", "label": {"text": "new(id)", "tokens": []},
             "at": [2, 22, 2, 29], "cells": [["T", None, None], ["F", None, None], ["", None, None]]},
        ],
    }


def test_5e2a9130():
    """Example: k.py's kata, in groups Katas, k*.py, and Other, x.py
    The source report of a run: no operators ignored, the covered files of
    each group, each card row's top coloured, a return's too, and each
    covered file's lines and decisions, each decision's fold headed by its card
    row's top."""
    decisions = manifest.decisions(KATA, "k.py")
    files = {"k.py": (KATA, decisions)}
    cards = {
        "k.py:1:0": {"rows": [{"decision": "k.py:2:18", "top": "and"}, {"decision": None, "top": "return"}]}
    }
    groups = {"Katas": ["k*.py"], "Other": ["x.py"]}
    assert source_report.of(files, {"k.py:2:18": PATHS}, cards, groups) == {
        "$schema": "https://path-coverage.github.io/schemas/v1/path_coverage.source.schema.json",
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
                "decisions": {"k.py:2:18": source_report.decision(KATA, decisions, "k.py:2:18", PATHS, "and")},
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
    paths = [{"path": path, "count": 0} for path in decision_paths.possible(decisions[name])]
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

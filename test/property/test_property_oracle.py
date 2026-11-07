import json
import sys
from collections import Counter

import oracle
from function_grammar import FunctionGrammar

import path_coverage

SEEDS = range(1, 121)


def _generated(root):
    """{seed: (FunctionGrammar, source)} for each of SEEDS, each source
    written into root as generated_{seed}.py."""
    found = {}
    for seed in SEEDS:
        grammar = FunctionGrammar(seed)
        found[seed] = (grammar, grammar.source())
        (root / f"generated_{seed}.py").write_text(found[seed][1])
    return found


def _calls(run, grammar):
    """[value, trace] of run, the function grammar generated, on every
    combination of its leaf parameters' values, each with spies."""
    return [oracle.traced(run, grammar.spies, values) for values in oracle.combinations(grammar.leaves)]


def _plainly(source):
    """The run function source defines, compiled with no path coverage."""
    namespace = {}
    exec(compile(source, "plain.py", "exec"), namespace)  # noqa: S102 - running generated code is the point
    return namespace["run"]


def _covered(root, seeds):
    """({seed: the run function of generated_{seed}.py in root, imported
    under path coverage}, the function that writes its report into root),
    each module then taken out of sys.modules."""
    exits = []
    names = [f"generated_{seed}" for seed in seeds]
    path_coverage.start(root=root, cover=["*.py"], coverage_dir=root, report=[], on_exit=exits.append)
    sys.path.insert(0, str(root))
    try:
        runs = {seed: __import__(name).run for seed, name in zip(seeds, names)}
    finally:
        path_coverage.stop()
        sys.path.remove(str(root))
        for name in names:
            sys.modules.pop(name)
    return runs, exits[0]


def test_b61d3f01(tmp_path):
    """Every function FunctionGrammar generates from SEEDS, called with
    spies on every combination of its leaves' values, returns or raises,
    and logs each leaf and statement, in order, exactly as it does compiled
    plainly: path coverage evaluates no leaf twice, skips none, runs none
    out of order, and skips no statement."""
    generated = _generated(tmp_path)
    plain = {seed: _calls(_plainly(source), grammar) for seed, (grammar, source) in generated.items()}
    runs, _ = _covered(tmp_path, list(generated))
    assert {seed: _calls(runs[seed], grammar) for seed, (grammar, _) in generated.items()} == plain


def test_b61d3f02(tmp_path):
    """Every function FunctionGrammar generates from SEEDS, called with
    spies on every combination of its leaves' values: the paths each
    decision took, as the oracle derives them from each call's trace, are
    counted in path_coverage.json exactly, decision by decision, and the
    runs of each statement the marks say ran, in reached."""
    generated = _generated(tmp_path)
    runs, write = _covered(tmp_path, list(generated))
    oracles = []
    for seed, (grammar, source) in generated.items():
        oracles.append(oracle.Oracle(source, f"generated_{seed}.py"))
        for values, (_, trace) in zip(oracle.combinations(grammar.leaves), _calls(runs[seed], grammar)):
            oracles[-1].add(values, trace)
    write()
    report = json.loads((tmp_path / "path_coverage.json").read_text())
    taken = {decision: {tuple(path["path"]): path["count"] for path in each["taken"] if path["count"]} for decision, each in report["paths"].items()}
    derived = {name: dict(counts) for each in oracles for name, counts in each.counts.items()}
    reached = sum((each.reached for each in oracles), Counter())
    assert ({decision: paths for decision, paths in taken.items() if paths}, report["reached"]) == (derived, dict(reached))

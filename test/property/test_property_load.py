import itertools
import sys

from function_grammar import FunctionGrammar

import path_coverage

SEEDS = range(1, 41)


def _outcomes(run):
    """What run gives on each combination of its boolean parameters, in
    order: its value, or "raised" for a Stop."""
    combinations = itertools.product([True, False], repeat=run.__code__.co_argcount)
    return [_outcome(run, args) for args in combinations]


def _outcome(run, args):
    """run's value for args, or "raised" when it raises its module's Stop."""
    try:
        return run(*args)
    except run.__globals__["Stop"]:
        return "raised"


def _plainly(source):
    """The run function source defines, compiled with no path coverage."""
    namespace = {}
    exec(compile(source, "plain.py", "exec"), namespace)  # noqa: S102 - running generated code is the point
    return namespace["run"]


def _covered(root, names):
    """The run function of each module of names in root, each imported
    under path coverage, then taken out of sys.modules; with the report
    written at exit, so writing it is checked too."""
    exits = []
    path_coverage.start(root=root, cover=["*.py"], coverage_dir=root, report=[], on_exit=exits.append)
    sys.path.insert(0, str(root))
    try:
        runs = [__import__(name).run for name in names]
    finally:
        path_coverage.stop()
        sys.path.remove(str(root))
        for name in names:
            sys.modules.pop(name)
    exits[0]()
    return runs


def test_9d2b6a01(tmp_path):
    """Every function FunctionGrammar generates from SEEDS imports under path
    coverage and, on every combination of its parameters, returns or raises
    exactly as it does compiled plainly; and its report is written."""
    sources = {seed: FunctionGrammar(seed).source() for seed in SEEDS}
    for seed, source in sources.items():
        (tmp_path / f"generated_{seed}.py").write_text(source)
    plain = {seed: _outcomes(_plainly(source)) for seed, source in sources.items()}
    runs = _covered(tmp_path, [f"generated_{seed}" for seed in sources])
    covered = {seed: _outcomes(run) for seed, run in zip(sources, runs)}
    assert covered == plain

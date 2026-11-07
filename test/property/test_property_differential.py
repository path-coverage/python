import ast

import oracle
from function_grammar import FunctionGrammar
from reference.reference_recorder import Recorder
from reference.reference_rewriter import RECORDER_NAME, rewrite

from path_coverage import monitor, wrapped_leaves
from path_coverage.evaluations import Evaluations

SEEDS = range(1, 121)


def _run_all(namespace, grammar):
    """Calls the run function namespace defines, which grammar generated,
    with spies on every combination of its leaves' values, a raise of its
    Stop ending that call alone."""
    for values in oracle.combinations(grammar.leaves):
        oracle.traced(namespace["run"], grammar.spies, values)


def _referenced(path, source, grammar):
    """(paths, reached) of source, the file path grammar generated,
    rewritten by the reference rewrite and run on every combination, as
    its recorder counts them."""
    recorder = Recorder()
    namespace = {RECORDER_NAME: recorder}
    exec(compile(rewrite(ast.parse(source), path, source=source), path, "exec"), namespace)  # noqa: S102 - running generated code is the point
    _run_all(namespace, grammar)
    return recorder.decision_paths, recorder.reached


def _monitored(path, source, grammar):
    """(paths, reached) of source, the file path grammar generated,
    measured by path_coverage and run on every combination, as its
    Evaluations count them."""
    evaluations = Evaluations()
    code, record = monitor.instrument(source, path, path, evaluations, monitor.compiled)
    namespace = {wrapped_leaves.NAME: record}
    exec(code, namespace)  # noqa: S102 - running generated code is the point
    _run_all(namespace, grammar)
    evaluations.flush()
    return evaluations.decision_paths, evaluations.reached


def test_e3f1a701():
    """For every function FunctionGrammar generates from SEEDS, called on
    every combination of its leaves' values, path_coverage counts each path
    of each decision, and each run of each statement, exactly as the
    reference rewrite does."""
    grammars = {f"generated_{seed}.py": FunctionGrammar(seed) for seed in SEEDS}
    sources = {path: grammar.source() for path, grammar in grammars.items()}
    assert {path: _monitored(path, source, grammars[path]) for path, source in sources.items()} == {
        path: _referenced(path, source, grammars[path]) for path, source in sources.items()
    }

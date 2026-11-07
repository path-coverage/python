import ast
import itertools

from function_grammar import FunctionGrammar
from reference.reference_recorder import Recorder
from reference.reference_rewriter import RECORDER_NAME, rewrite

from path_coverage import last_operands, monitor
from path_coverage.evaluations import Evaluations

SEEDS = range(1, 121)


def _run_all(namespace):
    """Calls the run function namespace defines on every combination of its
    boolean parameters, a raise of its Stop ending that call alone."""
    run = namespace["run"]
    for args in itertools.product([True, False], repeat=run.__code__.co_argcount):
        try:
            run(*args)
        except namespace["Stop"]:
            pass


def _referenced(path, source):
    """(paths, reached) of source, the file path, rewritten by the reference
    rewrite and run on every combination, as its recorder counts them."""
    recorder = Recorder()
    namespace = {RECORDER_NAME: recorder}
    exec(compile(rewrite(ast.parse(source), path, source=source), path, "exec"), namespace)  # noqa: S102 - running generated code is the point
    _run_all(namespace)
    return recorder.decision_paths, recorder.reached


def _monitored(path, source):
    """(paths, reached) of source, the file path, measured by path_coverage
    and run on every combination, as its Evaluations count them."""
    evaluations = Evaluations()
    code, record = monitor.instrument(source, path, path, evaluations, monitor.compiled)
    namespace = {last_operands.NAME: record}
    exec(code, namespace)  # noqa: S102 - running generated code is the point
    _run_all(namespace)
    evaluations.flush()
    return evaluations.decision_paths, evaluations.reached


def test_e3f1a701():
    """For every function FunctionGrammar generates from SEEDS, called on
    every combination of its parameters, path_coverage counts each path of
    each decision, and each run of each statement, exactly as the reference
    rewrite does."""
    sources = {f"generated_{seed}.py": FunctionGrammar(seed).source() for seed in SEEDS}
    assert {path: _monitored(path, source) for path, source in sources.items()} == {
        path: _referenced(path, source) for path, source in sources.items()
    }

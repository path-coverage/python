import oracle
from function_grammar import FunctionGrammar

from path_coverage import inserted_records, monitor, rewrite, scopes
from path_coverage.evaluations import Evaluations

SEEDS = range(1, 121)


def _run_all(namespace, grammar):
    """Calls the run function namespace defines, which grammar generated,
    with spies on every combination of its leaves' values, a raise of its
    Stop ending that call alone."""
    for values in oracle.combinations(grammar.leaves):
        oracle.traced(namespace["run"], grammar.spies, values)


def _measured(instrument, path, source, grammar):
    """The Evaluations of source, the file path grammar generated, measured
    by instrument, monitor's or rewrite's, and run on every combination,
    every way ended."""
    evaluations = Evaluations()
    code, record = instrument(source, path, path, evaluations, monitor.compiled, scopes.whole(source))
    namespace = {inserted_records.NAME: record}
    exec(code, namespace)  # noqa: S102 - running generated code is the point
    _run_all(namespace, grammar)
    evaluations.flush()
    evaluations.close()
    return evaluations


def _generated():
    """{path: (source, grammar)} of each function FunctionGrammar generates
    from SEEDS."""
    grammars = {f"generated_{seed}.py": FunctionGrammar(seed) for seed in SEEDS}
    return {path: (grammar.source(), grammar) for path, grammar in grammars.items()}


def test_e3f1a702():
    """For every function FunctionGrammar generates from SEEDS, called on
    every combination of its leaves' values, path_coverage counts the same
    in rewrite mode as in monitoring mode: each path of each decision, each
    run of each statement, and each way of each call."""
    generated = _generated()
    modes = [
        {path: _measured(instrument, path, *each) for path, each in generated.items()}
        for instrument in (monitor.instrument, rewrite.instrument)
    ]
    monitored, rewritten = (
        {path: (each.decision_paths, each.reached, each.ways) for path, each in mode.items()} for mode in modes
    )
    assert rewritten == monitored

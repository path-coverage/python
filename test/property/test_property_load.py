import ast
import itertools
import random
import sys

from function_grammar import FunctionGrammar

import path_coverage
from path_coverage import code_map, last_operands
from path_coverage.evaluations import Evaluations

SEEDS = range(1, 41)

# Statements that parse but that Python refuses to compile, each added to a
# generated function to break it.
REFUSED = [
    "break",
    "await t",
    "nonlocal t",
    "match t:\n        case _:\n            pass\n        case 1:\n            pass",
    "match t:\n        case n:\n            pass\n        case 1:\n            pass",
]


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


def _compiles(source):
    """True when Python compiles source; False when it refuses it."""
    try:
        compile(source, "k.py", "exec", dont_inherit=True)
        return True
    except SyntaxError:
        return False


def _wrapped_compiles(source):
    """True when path_coverage's wrapping of source's last operands
    compiles; False when source does not parse, or its wrapping does not
    compile."""
    try:
        found = code_map.Source(source, "k.py")
        tree = last_operands.rewrite(ast.parse(source), found, last_operands.Lasts(Evaluations()))
        compile(tree, "k.py", "exec", dont_inherit=True)
        return True
    except SyntaxError:
        return False


def _broken(seed, source):
    """source made one Python refuses: run's last statement preceded by one
    of REFUSED, drawn by seed."""
    refused = random.Random(seed).choice(REFUSED)
    return source.replace("    return t\n", f"    {refused}\n    return t\n")


def _unparsable(source):
    """source with run's def missing its colon, so it does not parse."""
    return source.replace("):\n", ")\n", 1)


def test_9d2b6a03():
    """For every function FunctionGrammar generates from SEEDS, for it broken
    so it parses but Python refuses it, and for it broken so it does not
    parse, path_coverage's wrapping of its and/ors' last operands compiles
    exactly when the source does: it never breaks valid code, nor makes
    broken code valid."""
    generated = {seed: FunctionGrammar(seed).source() for seed in SEEDS}
    sources = [
        variant
        for seed, source in generated.items()
        for variant in (source, _broken(seed, source), _unparsable(source))
    ]
    assert [_wrapped_compiles(source) for source in sources] == [_compiles(source) for source in sources]

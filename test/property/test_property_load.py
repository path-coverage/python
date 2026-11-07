import ast
import random

from function_grammar import FunctionGrammar

from path_coverage import code_map, scopes, wrapped_leaves
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


def _compiles(source):
    """True when Python compiles source; False when it refuses it."""
    try:
        compile(source, "k.py", "exec", dont_inherit=True)
        return True
    except SyntaxError:
        return False


def _wrapped_compiles(source):
    """True when path_coverage's wrapping of source's leaves compiles;
    False when source does not parse, or its wrapping does not compile."""
    try:
        found = code_map.Source(source, "k.py", scopes.whole(source))
        tree = wrapped_leaves.rewrite(ast.parse(source), found, wrapped_leaves.Leaves(Evaluations()))
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
    parse, path_coverage's wrapping of its leaves compiles
    exactly when the source does: it never breaks valid code, nor makes
    broken code valid."""
    generated = {seed: FunctionGrammar(seed).source() for seed in SEEDS}
    sources = [
        variant
        for seed, source in generated.items()
        for variant in (source, _broken(seed, source), _unparsable(source))
    ]
    assert [_wrapped_compiles(source) for source in sources] == [_compiles(source) for source in sources]

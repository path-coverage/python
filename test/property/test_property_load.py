import ast
import random
from pathlib import Path

from function_grammar import FunctionGrammar

from path_coverage import inserted_records, scopes, source_map
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


def _inserted(source, mode):
    """The parse of source, the file k.py, with the records mode inserts."""
    found = source_map.Source(source, "k.py", scopes.whole(source))
    return inserted_records.rewrite(ast.parse(source), found, inserted_records.Recorder(Evaluations()), mode)


def _wrapped_compiles(source, mode):
    """True when path_coverage's records, as mode inserts them into
    source, compile; False when source does not parse, or its records do
    not compile."""
    try:
        compile(_inserted(source, mode), "k.py", "exec", dont_inherit=True)
        return True
    except SyntaxError:
        return False


class _Stripped(ast.NodeTransformer):
    """A parse with every inserted record taken out: each call wrapping a
    node back to that node, each record statement gone."""

    def visit_Call(self, node):
        """The node an inserted call wraps, a record statement's call being
        gone before its call is seen; any other call as it is, what it
        holds stripped."""
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == inserted_records.NAME:
            return node.args[1]
        return node

    def visit_Expr(self, node):
        """None, removing it, for an inserted record statement; any other
        expression statement as it is, what it holds stripped."""
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == inserted_records.NAME:
            return None
        return self.generic_visit(node)


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
    parse, path_coverage's records, as each mode inserts them, compile
    exactly when the source does: they never break valid code, nor make
    broken code valid."""
    generated = {seed: FunctionGrammar(seed).source() for seed in SEEDS}
    sources = [
        variant
        for seed, source in generated.items()
        for variant in (source, _broken(seed, source), _unparsable(source))
    ]
    compiles = [_compiles(source) for source in sources]
    assert [[_wrapped_compiles(source, mode) for source in sources] for mode in inserted_records.INSERTS] == [compiles] * 2


def test_9d2b6a04():
    """For every function FunctionGrammar generates from SEEDS, and every
    Python file in this repo's src/ and test/, each mode's records taken
    back out leave the parse exactly as it was: a record only wraps a node
    or is a statement of its own, and nothing else in the tree changes."""
    root = Path(__file__).resolve().parents[2]
    sources = [FunctionGrammar(seed).source() for seed in SEEDS]
    sources += [path.read_text() for folder in ("src", "test") for path in sorted((root / folder).rglob("*.py")) if "projects" not in path.parts]
    for mode in inserted_records.INSERTS:
        stripped = [ast.dump(_Stripped().visit(_inserted(source, mode))) for source in sources]
        assert stripped == [ast.dump(ast.parse(source)) for source in sources]

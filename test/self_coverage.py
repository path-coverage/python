"""Self-coverage: path_coverage measuring its own src/ and test/ while its
own tests run. A pytest plugin, loaded by bin/test.sh with -p self_coverage,
so it starts before any test module, or path_coverage itself, is imported.

The code measured and the tool measuring are the same package in one
process, so the tool runs as a copy of src/path_coverage, in a temporary
dir, renamed path_coverage_self, the names its rewritten code calls
renamed too, so no name is shared with the code it measures. The tests
start and stop path_coverage as they always do, untouched, as it is a
different package with its own finder on sys.meta_path.

The copy's finder goes in front of pytest's assertion rewriting hook, so
the copy's loader rewrites a test module's asserts, after its own
rewrite, as pytest would have."""

import ast
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from _pytest.assertion.rewrite import rewrite_asserts

ROOT = Path(__file__).resolve().parent.parent
REPORTS = Path(os.environ.get("PATH_COVERAGE_SELF_DIR", ROOT / "reports" / "paths"))
# Each name the copy must not share with the code it measures, and its
# name in the copy.
RENAMES = {
    "__path_coverage_path__": "__path_coverage_self_path__",
    "__path_coverage__": "__path_coverage_self__",
}
SELF_IMPORT = re.compile(r"^(\s*)(from|import) path_coverage\b", re.MULTILINE)

_reports = []


def copy(into):
    """Copies src/path_coverage into the dir into as package
    path_coverage_self, every injected name renamed as RENAMES says and
    every absolute self-import renamed too; returns the copy's dir."""
    package = into / "path_coverage_self"
    shutil.copytree(
        ROOT / "src" / "path_coverage", package, ignore=shutil.ignore_patterns("__pycache__")
    )
    for file in package.rglob("*.py"):
        text = file.read_text()
        for name, renamed in RENAMES.items():
            text = text.replace(name, renamed)
        file.write_text(SELF_IMPORT.sub(r"\1\2 path_coverage_self", text))
    return package


def _asserting_loader(kernel):
    """A subclass of kernel's loader that, for a test module, rewrites its
    asserts as pytest does, after kernel's own rewrite."""

    class AssertingLoader(kernel._Loader):
        """The copy's loader, with pytest's assertion rewriting of test
        modules, which the copy's finder takes from pytest's own hook."""

        def get_code(self, fullname):
            """The module's code compiled from its rewritten AST, a test
            module's asserts rewritten too."""
            path = self.get_filename(fullname)
            source = self.get_data(path)
            relative = self.config.relative(path)
            tree = kernel.rewrite(
                ast.parse(source, path), relative, source=source, methods=self.config.methods
            )
            if Path(path).name.startswith("test_"):
                rewrite_asserts(tree, source, path)
            return compile(tree, path, "exec", dont_inherit=True)

    return AssertingLoader


def start():
    """Copies the package, then starts the copy covering src/ and test/,
    groups code and test, reporting html and JSON into REPORTS when pytest
    unconfigures."""
    into = Path(tempfile.mkdtemp(prefix="path_coverage_self."))
    copy(into)
    sys.path.insert(0, str(into))
    import path_coverage_self
    from path_coverage_self import kernel

    kernel._Loader = _asserting_loader(kernel)
    path_coverage_self.start(
        root=ROOT,
        cover=["src/**/*.py", "test/**/*.py"],
        skip=["test/projects/**", "test/self_coverage.py"],
        coverage_dir=REPORTS,
        measure=["decisions", "methods"],
        report=["html"],
        groups={"code": ["src/**/*.py"], "test": ["test/**/*.py"]},
        on_exit=_reports.append,
    )
    _reports.append(lambda: shutil.rmtree(into))


def pytest_unconfigure(config):
    """Writes the self-coverage report, once every test has run, then
    removes the copy."""
    while _reports:
        _reports.pop(0)()


start()

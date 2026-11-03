"""The kernel: an import hook that instruments each covered module as it is
imported, and the report at exit. It is never itself instrumented, since an
instrumented recorder would record itself."""

import ast
import atexit
import importlib.machinery
import json
import sys
from pathlib import Path

from . import gaps, html_report, manifest, result
from .merge import merge

REPORTERS = ("gaps", "html")
from .recorder import Recorder
from .rewriter import RECORD_NAME, rewrite

_recorder = Recorder()
_finder = None


class _Config:
    """Where covered files are and where reports go."""

    def __init__(self, root, cover, coverage_dir, report):
        """Resolves root and coverage_dir; cover is a list of globs relative
        to root; report names the reporters to run."""
        self.root = Path(root).resolve()
        self.cover = list(cover)
        self.coverage_dir = Path(coverage_dir)
        self.report = list(report)

    def relative(self, path):
        """path relative to root, as sites name it."""
        return Path(path).resolve().relative_to(self.root).as_posix()

    def covers(self, path):
        """True when path is under root and matches a cover glob."""
        try:
            relative = Path(self.relative(path))
        except ValueError:
            return False
        return any(relative.full_match(glob) for glob in self.cover)


class _Loader(importlib.machinery.SourceFileLoader):
    """Loads a covered module from its rewritten source, never from (or into)
    the bytecode cache, which holds the uninstrumented code."""

    def __init__(self, fullname, path, config):
        """A loader for the covered file at path."""
        super().__init__(fullname, path)
        self.config = config

    def get_code(self, fullname):
        """The covered file's code, compiled from its rewritten AST."""
        path = self.get_filename(fullname)
        source = self.get_data(path)
        tree = rewrite(ast.parse(source, path), self.config.relative(path))
        return compile(tree, path, "exec", dont_inherit=True)

    def exec_module(self, module):
        """Runs module with the record call its rewritten code makes."""
        module.__dict__[RECORD_NAME] = _recorder.record
        super().exec_module(module)


class _Finder:
    """A meta path finder that hands each covered module to _Loader and
    leaves every other import to the finders after it."""

    def __init__(self, config):
        """A finder for the files config covers."""
        self.config = config

    def find_spec(self, fullname, path, target=None):
        """The spec of a covered module, with _Loader as its loader; None
        for any other module."""
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or not isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            return None
        if not self.config.covers(spec.origin):
            return None
        spec.loader = _Loader(fullname, spec.origin, self.config)
        return spec


def start(*, root, cover, coverage_dir, report=("gaps",), part=None, on_exit=atexit.register):
    """Instruments every covered module imported from now on and reports at
    exit, counting afresh. A run given a part name (eg an xdist worker's)
    writes only its part file; the main run clears stale parts now and adds
    every part to its own report at exit. on_exit is atexit.register except
    in tests, which must not print a report as their own process exits."""
    global _finder, _recorder
    for name in report:
        if name not in REPORTERS:
            raise ValueError(f"unknown reporter {name!r}; the reporters are: {', '.join(REPORTERS)}")
    recorder = _recorder = Recorder()
    config = _Config(root, cover, coverage_dir, report)
    if part is None:
        for stale in _parts(config):
            stale.unlink()
    _finder = _Finder(config)
    sys.meta_path.insert(0, _finder)
    on_exit(lambda: _report(config, recorder, part))


def start_from_env(env, part=None, on_exit=atexit.register):
    """Starts from settings in env alone, for a run whose code cannot be
    changed: covers the comma-separated CONDITION_COVERAGE_COVER globs under
    CONDITION_COVERAGE_ROOT, reporting into CONDITION_COVERAGE_DIR with the
    comma-separated CONDITION_COVERAGE_REPORT reporters (default gaps), as
    part when given one. Returns whether it started; without
    CONDITION_COVERAGE_COVER it starts nothing."""
    if "CONDITION_COVERAGE_COVER" not in env:
        return False
    start(
        root=env["CONDITION_COVERAGE_ROOT"],
        cover=env["CONDITION_COVERAGE_COVER"].split(","),
        coverage_dir=env["CONDITION_COVERAGE_DIR"],
        report=env.get("CONDITION_COVERAGE_REPORT", "gaps").split(","),
        part=part,
        on_exit=on_exit,
    )
    return True


def stop():
    """Stops instrumenting modules imported from now on."""
    sys.meta_path.remove(_finder)


def _report(config, recorder, part):
    """For a part, writes recorder's counts as that part's JSON file. For
    the main run, adds every part's counts to recorder's, writes the JSON
    report into coverage_dir, then runs the chosen reporters."""
    files = {}
    for glob in config.cover:
        for path in sorted(config.root.glob(glob)):
            source = path.read_text()
            relative = config.relative(path)
            files[relative] = (source, manifest.sites(source, relative))
    sites = {site: c for _, file_sites in files.values() for site, c in file_sites.items()}
    operands = result.operands(sites, recorder.counts)
    config.coverage_dir.mkdir(parents=True, exist_ok=True)
    if part is not None:
        _write(config.coverage_dir / f"condition_coverage.{part}.json", operands)
        return
    parts = [json.loads(path.read_text())["sites"] for path in _parts(config)]
    operands = merge([operands, *parts])
    _write(config.coverage_dir / "condition_coverage.json", operands)
    if "gaps" in config.report:
        for line in gaps.lines(operands):
            print(line)
    if "html" in config.report:
        html_report.write(operands, files, config.coverage_dir)


def _parts(config):
    """The part files in coverage_dir, in name order."""
    return sorted(config.coverage_dir.glob("condition_coverage.*.json"))


def _write(path, operands):
    """Writes operands to path as {"sites": operands}."""
    path.write_text(json.dumps({"sites": operands}, indent=2))

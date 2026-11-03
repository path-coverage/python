"""The kernel: an import hook that instruments each covered module as it is
imported, and the report at exit. It is never itself instrumented, since an
instrumented recorder would record itself."""

import ast
import atexit
import importlib.machinery
import json
import sys
from pathlib import Path

from . import (
    gaps,
    html_report,
    manifest,
    path_gaps,
    path_manifest,
    paths_report,
    post,
    result,
    totals,
)
from .merge import merge, merge_paths
from .recorder import Recorder
from .rewriter import RECORDER_NAME, rewrite

REPORTERS = ("gaps", "html", "post")
MEASURES = ("decisions", "methods")

_recorder = Recorder()
_finder = None


class _Config:
    """Where covered files are, what is measured, and where reports go."""

    def __init__(self, root, cover, coverage_dir, report, measure, collector):
        """Resolves root and coverage_dir; cover is a list of globs relative
        to root; report names the reporters to run, measure what is measured
        (paths within each decision, and, with "methods", across each
        function's decisions too), and collector the url the post reporter
        sends to."""
        self.root = Path(root).resolve()
        self.cover = list(cover)
        self.coverage_dir = Path(coverage_dir)
        self.report = list(report)
        self.methods = "methods" in measure
        self.collector = collector

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
        relative = self.config.relative(path)
        tree = rewrite(ast.parse(source, path), relative, methods=self.config.methods)
        return compile(tree, path, "exec", dont_inherit=True)

    def exec_module(self, module):
        """Runs module with the recorder its rewritten code calls."""
        module.__dict__[RECORDER_NAME] = _recorder
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


def _check(setting, names, known):
    """Refuses any of names not in known, naming it and listing known."""
    for name in names:
        if name not in known:
            raise ValueError(f"unknown {setting} {name!r}; the {setting}s are: {', '.join(known)}")


def _config(root, cover, coverage_dir, report, measure, collector):
    """The settings, each checked: unknown reporters and measures are
    refused by name, as is the post reporter with no collector."""
    _check("reporter", report, REPORTERS)
    _check("measure", measure, MEASURES)
    if "post" in report and not collector:
        raise ValueError("the post reporter needs a collector url")
    return _Config(root, cover, coverage_dir, report, measure, collector)


def start(
    *,
    root,
    cover,
    coverage_dir,
    report=("gaps",),
    measure=("decisions",),
    collector=None,
    part=None,
    on_exit=atexit.register,
):
    """Instruments every covered module imported from now on and reports at
    exit, counting afresh. measure is "decisions" (the default) for the
    paths within each decision, with "methods" for the paths across each
    function's decisions too. report names the reporters: "gaps" (the
    default) prints the paths never taken, "html" writes pages, and "post"
    sends the JSON report to collector, a url. A run given a part name (eg
    an xdist worker's) writes only its part file; the main run clears stale
    parts now and adds every part to its own report at exit. on_exit is
    atexit.register except in tests, which must not print a report as their
    own process exits."""
    global _finder, _recorder
    config = _config(root, cover, coverage_dir, report, measure, collector)
    recorder = _recorder = Recorder()
    if part is None:
        for stale in _parts(config):
            stale.unlink()
    _finder = _Finder(config)
    sys.meta_path.insert(0, _finder)
    on_exit(lambda: _report(config, recorder, part))


def start_from_env(env, part=None, on_exit=atexit.register):
    """Starts from settings in env alone, for a run whose code cannot be
    changed: covers the comma-separated PATH_COVERAGE_COVER globs under
    PATH_COVERAGE_ROOT, reporting into PATH_COVERAGE_DIR with the
    comma-separated PATH_COVERAGE_REPORT reporters and PATH_COVERAGE_MEASURE
    measures (default decisions), as part when given one. With
    PATH_COVERAGE_COLLECTOR, a url, the reporters default to post, sending
    there; otherwise to gaps. Returns whether it started; without
    PATH_COVERAGE_COVER it starts nothing."""
    if "PATH_COVERAGE_COVER" not in env:
        return False
    collector = env.get("PATH_COVERAGE_COLLECTOR")
    start(
        root=env["PATH_COVERAGE_ROOT"],
        cover=env["PATH_COVERAGE_COVER"].split(","),
        coverage_dir=env["PATH_COVERAGE_DIR"],
        report=env.get("PATH_COVERAGE_REPORT", "post" if collector else "gaps").split(","),
        measure=env.get("PATH_COVERAGE_MEASURE", "decisions").split(","),
        collector=collector,
        part=part,
        on_exit=on_exit,
    )
    return True


def stop():
    """Stops instrumenting modules imported from now on."""
    sys.meta_path.remove(_finder)


def render(*, root, cover, coverage_dir, runs, report=("gaps",), measure=("decisions",)):
    """Runs the reporters from the JSON reports at runs (eg those a collector
    saved), their counts added together, parsing each covered file afresh,
    so the report shows only the gaps that every run left. It writes the
    merged JSON report into coverage_dir too."""
    config = _config(root, cover, coverage_dir, report, measure, None)
    files = _files(config)
    reports = [json.loads(Path(path).read_text()) for path in runs]
    sites = _sites(files)
    operands = merge([result.operands(sites, {}), *(each["sites"] for each in reports)])
    paths = merge_paths([result.paths(sites, {}), *(_taken(each) for each in reports)])
    method_paths = merge_paths([each.get("method_paths", {}) for each in reports])
    _finish(config, files, operands, paths, method_paths)


def _report(config, recorder, part):
    """For a part, writes recorder's counts as that part's JSON file. For
    the main run, adds every part's counts to recorder's, writes the JSON
    report into coverage_dir, then runs the chosen reporters."""
    files = _files(config)
    sites = _sites(files)
    operands = result.operands(sites, recorder.counts)
    paths = result.paths(sites, recorder.site_paths)
    method_paths = _listed(recorder.paths)
    config.coverage_dir.mkdir(parents=True, exist_ok=True)
    if part is not None:
        part_file = config.coverage_dir / f"path_coverage.{part}.json"
        part_file.write_text(json.dumps(_report_json(operands, paths, files, method_paths), indent=2))
        return
    parts = [json.loads(path.read_text()) for path in _parts(config)]
    operands = merge([operands, *(each["sites"] for each in parts)])
    paths = merge_paths([paths, *(_taken(each) for each in parts)])
    method_paths = merge_paths([method_paths, *(each.get("method_paths", {}) for each in parts)])
    _finish(config, files, operands, paths, method_paths)


def _finish(config, files, operands, paths, method_paths):
    """Writes the JSON report, with its totals, into coverage_dir, then runs
    the chosen reporters."""
    taken = {
        site: {tuple(each["path"]): each["count"] for each in listed}
        for site, listed in method_paths.items()
    }
    methods = _methods(files) if config.methods else None
    report = _report_json(operands, paths, files, method_paths)
    report["totals"] = {"decisions": totals.decisions(paths)}
    if methods is not None:
        report["totals"]["methods"] = totals.methods(methods, taken)
    text = json.dumps(report, indent=2)
    config.coverage_dir.mkdir(parents=True, exist_ok=True)
    (config.coverage_dir / "path_coverage.json").write_text(text)
    if "gaps" in config.report:
        for line in gaps.lines(operands, paths, paths_report.texts(files)):
            print(line)
        for line in path_gaps.lines(methods or {}, taken):
            print(line)
    if "html" in config.report:
        html_report.write(operands, files, config.coverage_dir, paths, methods, taken)
    if "post" in config.report:
        post.deliver(text, config.collector)


def _files(config):
    """{path relative to root: (source, sites)} for every covered file,
    whether or not the run imported it."""
    files = {}
    for glob in config.cover:
        for path in sorted(config.root.glob(glob)):
            source = path.read_text()
            relative = config.relative(path)
            files[relative] = (source, manifest.sites(source, relative))
    return files


def _sites(files):
    """Every site of files, in one manifest."""
    return {site: c for _, file_sites in files.values() for site, c in file_sites.items()}


def _methods(files):
    """The functions whose paths are counted, of every covered file, in one
    manifest."""
    return {
        site: method
        for relative, (source, _) in files.items()
        for site, method in path_manifest.methods(source, relative).items()
    }


def _listed(paths):
    """The recorder's {site: {(outcome, ...): n}} as {site: [{"path": [...],
    "count": n}]}, the form JSON holds and merge_paths adds."""
    return {
        site: [{"path": list(path), "count": count} for path, count in taken.items()]
        for site, taken in paths.items()
    }


def _parts(config):
    """The part files in coverage_dir, in name order."""
    return sorted(config.coverage_dir.glob("path_coverage.*.json"))


def _taken(report):
    """The paths of a JSON report, as result.paths gives them."""
    return {site: each["taken"] for site, each in report.get("paths", {}).items()}


def _report_json(operands, paths, files, method_paths):
    """The JSON report: {"sites": operands, "paths": {site: {"leaves":
    [...], "taken": [...]}}, "method_paths": {site: [{"path", "count"}]}}."""
    return {
        "sites": operands,
        "paths": paths_report.of(paths, files),
        "method_paths": method_paths,
    }

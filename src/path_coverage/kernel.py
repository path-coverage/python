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
    console_summary,
    gaps,
    html_report,
    kinds,
    listed_cards,
    manifest,
    method_statements,
    paths_report,
    post,
    result,
)
from .merge import merge, merge_paths
from .recorder import Recorder
from .rewriter import RECORDER_NAME, rewrite

REPORTERS = ("gaps", "html", "post", "summary")

_recorder = Recorder()
_finder = None


class _Config:
    """Where covered files are, what is reported, and where reports go."""

    def __init__(self, root, cover, coverage_dir, report, collector, skip=(), groups=None):
        """Resolves root and coverage_dir; cover is a list of globs relative
        to root, and skip of globs of files not covered though a cover glob
        matches them; report names the reporters to run, collector the url
        the post reporter sends to, and groups {name: [glob, ...]}, each
        group's files, relative to root."""
        self.root = Path(root).resolve()
        self.cover = list(cover)
        self.skip = list(skip)
        self.coverage_dir = Path(coverage_dir)
        self.report = list(report)
        self.collector = collector
        self.groups = {name: list(globs) for name, globs in (groups or {}).items()}

    def relative(self, path):
        """path relative to root, as sites name it."""
        return Path(path).resolve().relative_to(self.root).as_posix()

    def covers(self, path):
        """True when path is under root and matches a cover glob and no
        skip glob."""
        try:
            relative = Path(self.relative(path))
        except ValueError:
            return False
        return any(relative.full_match(glob) for glob in self.cover) and not self.skips(relative)

    def skips(self, relative):
        """True when relative, a path relative to root, matches a skip
        glob."""
        return any(Path(relative).full_match(glob) for glob in self.skip)


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
        tree = rewrite(ast.parse(source, path), relative, source=source)
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


def _config(root, cover, coverage_dir, report, collector, skip, groups=None):
    """The settings, each checked: unknown reporters are refused by name,
    as is the post reporter with no collector."""
    _check("reporter", report, REPORTERS)
    if "post" in report and not collector:
        raise ValueError("the post reporter needs a collector url")
    return _Config(root, cover, coverage_dir, report, collector, skip, groups)


def start(
    *,
    root,
    cover,
    coverage_dir,
    skip=(),
    report=("gaps",),
    collector=None,
    groups=None,
    part=None,
    on_exit=atexit.register,
):
    """Instruments every covered module imported from now on and reports at
    exit, counting afresh: the paths within each decision, and within each
    method. skip lists globs of files not covered though a cover glob
    matches them. report names the reporters: "gaps" (the default) prints the
    paths never taken, "html" writes pages, "summary" prints the totals,
    and "post" sends the JSON report to collector, a url. groups, {name:
    [glob, ...]}, names groups of covered files: each gets a tab of the
    index page, its own summary lines and its own JSON totals. A run given
    a part name (eg an xdist worker's) writes only its part file; the main
    run clears stale parts now and adds every part to its own report at
    exit. on_exit is atexit.register except in tests, which must not print
    a report as their own process exits."""
    global _finder, _recorder
    config = _config(root, cover, coverage_dir, report, collector, skip, groups)
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
    PATH_COVERAGE_ROOT, skipping any matching the comma-separated
    PATH_COVERAGE_SKIP globs, reporting into PATH_COVERAGE_DIR with the
    comma-separated PATH_COVERAGE_REPORT reporters, and the comma-separated
    name:glob
    PATH_COVERAGE_GROUPS, as part when given one. With
    PATH_COVERAGE_COLLECTOR, a url, the reporters default to post, sending
    there; otherwise to gaps. Returns whether it started; without
    PATH_COVERAGE_COVER it starts nothing."""
    if "PATH_COVERAGE_COVER" not in env:
        return False
    collector = env.get("PATH_COVERAGE_COLLECTOR")
    start(
        root=env["PATH_COVERAGE_ROOT"],
        cover=env["PATH_COVERAGE_COVER"].split(","),
        skip=[glob for glob in env.get("PATH_COVERAGE_SKIP", "").split(",") if glob],
        coverage_dir=env["PATH_COVERAGE_DIR"],
        report=env.get("PATH_COVERAGE_REPORT", "post" if collector else "gaps").split(","),
        collector=collector,
        groups=_env_groups(env.get("PATH_COVERAGE_GROUPS", "")),
        part=part,
        on_exit=on_exit,
    )
    return True


def _env_groups(text):
    """{name: [glob, ...]} of text, comma-separated name:glob pairs, eg
    "code:src/**/*.py,test:test/**/*.py"; a name given twice gets both
    globs."""
    groups = {}
    for pair in filter(None, text.split(",")):
        name, glob = pair.split(":", 1)
        groups.setdefault(name, []).append(glob)
    return groups


def stop():
    """Stops instrumenting modules imported from now on."""
    sys.meta_path.remove(_finder)


def render(
    *,
    root,
    cover,
    coverage_dir,
    runs,
    skip=(),
    report=("gaps",),
    groups=None,
):
    """Runs the reporters from the JSON reports at runs (eg those a collector
    saved), their counts added together, parsing each covered file afresh,
    so the report shows only the gaps that every run left, and each
    statement's reaches added up. It writes the merged JSON report into
    coverage_dir too. A run that measured other kinds is refused, as it
    lists a site's paths differently."""
    config = _config(root, cover, coverage_dir, report, None, skip, groups)
    files = _files(config)
    reports = [_same_kinds(path) for path in runs]
    sites = _sites(files)
    operands = merge([result.operands(sites, {}), *(each["sites"] for each in reports)])
    paths = merge_paths([result.paths(sites, {}), *(_taken(each) for each in reports)])
    _finish(config, files, operands, paths, _reached([each.get("reached") for each in reports]))


def _reached(runs):
    """runs' reaches, each {name: runs} or None for a run that counted
    none, with each statement's added up; None when no run counted any, so
    a report cannot say what was reached. Example: {"k.py:2:4": 2} and
    {"k.py:2:4": 1} give {"k.py:2:4": 3}."""
    counted = [run for run in runs if run is not None]
    if not counted:
        return None
    total = {}
    for run in counted:
        for name, count in run.items():
            total[name] = total.get(name, 0) + count
    return total


def _same_kinds(path):
    """The JSON report at path, when it measured the kinds this version
    measures; ValueError naming path when not."""
    report = json.loads(Path(path).read_text())
    if report.get("kinds") != kinds.names():
        raise ValueError(f"{path} measured other kinds")
    return report


def _report(config, recorder, part):
    """For a part, writes recorder's counts as that part's JSON file. For
    the main run, adds every part's counts to recorder's, writes the JSON
    report into coverage_dir, then runs the chosen reporters."""
    files = _files(config)
    sites = _sites(files)
    operands = result.operands(sites, recorder.counts)
    paths = result.paths(sites, recorder.site_paths)
    reached = recorder.reached
    config.coverage_dir.mkdir(parents=True, exist_ok=True)
    if part is not None:
        part_file = config.coverage_dir / f"path_coverage.{part}.json"
        part_file.write_text(json.dumps(_report_json(operands, paths, files, reached), indent=2))
        return
    parts = [json.loads(path.read_text()) for path in _parts(config)]
    operands = merge([operands, *(each["sites"] for each in parts)])
    paths = merge_paths([paths, *(_taken(each) for each in parts)])
    reached = _reached([reached, *(each.get("reached") for each in parts)])
    _finish(config, files, operands, paths, reached)


def _finish(config, files, operands, paths, reached):
    """Writes the JSON report, with its totals, into coverage_dir, then runs
    the chosen reporters. reached is each statement's runs, None when not
    known."""
    cards = method_statements.cards(files, paths, reached)
    report = _report_json(operands, paths, files, reached)
    report["totals"] = console_summary.totals(paths, cards)
    if config.groups:
        report["totals"]["groups"] = console_summary.group_totals(paths, cards, config.groups)
    report["cards"] = listed_cards.of(files, operands, paths, reached)
    report["tree"] = listed_cards.tree(files, operands)
    text = json.dumps(report, indent=2)
    config.coverage_dir.mkdir(parents=True, exist_ok=True)
    (config.coverage_dir / "path_coverage.json").write_text(text)
    if "gaps" in config.report:
        for line in gaps.lines(operands, paths, paths_report.texts(files)):
            print(line)
    if "html" in config.report:
        html_report.write(
            operands, files, config.coverage_dir, paths, cards, reached, config.groups
        )
    if "summary" in config.report:
        for line in console_summary.lines(paths, cards, config.groups):
            print(line)
    if "post" in config.report:
        post.deliver(text, config.collector)


def _files(config):
    """{path relative to root: (source, sites)} for every covered file,
    whether or not the run imported it, and none a skip glob matches."""
    files = {}
    for glob in config.cover:
        for path in sorted(config.root.glob(glob)):
            relative = config.relative(path)
            if config.skips(relative):
                continue
            source = path.read_text()
            files[relative] = (source, manifest.sites(source, relative))
    return files


def _sites(files):
    """Every site of files, in one manifest."""
    return {site: c for _, file_sites in files.values() for site, c in file_sites.items()}


def _parts(config):
    """The part files in coverage_dir, in name order."""
    return sorted(config.coverage_dir.glob("path_coverage.*.json"))


def _taken(report):
    """The paths of a JSON report, as result.paths gives them."""
    return {site: each["taken"] for site, each in report.get("paths", {}).items()}


def _report_json(operands, paths, files, reached):
    """The JSON report: {"sites": operands, "paths": {site: {"leaves":
    [...], "taken": [...]}}, "kinds": [name, ...]}, the kinds naming what
    was measured, and "reached": {name: runs} when reached is known, even
    empty, as a run that reached no statement says so."""
    report = {"sites": operands, "paths": paths_report.of(paths, files), "kinds": kinds.names()}
    if reached is not None:
        report["reached"] = reached
    return report

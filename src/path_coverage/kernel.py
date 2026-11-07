"""The kernel: an import hook that measures each covered module as it is
imported, with sys.monitoring and a call around each leaf no branch tells,
and the report at exit."""

import atexit
import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

from . import (
    console_summary,
    gaps,
    kinds,
    listed_cards,
    manifest,
    measured_by,
    method_statements,
    monitor,
    paths_report,
    post,
    result,
    scopes,
    source_report,
    summary,
    wrapped_leaves,
)
from .evaluations import Evaluations
from .merge import merge, merge_paths

REPORTERS = ("gaps", "post", "summary")

# The URL of the schema the JSON report follows.
SCHEMA_URL = "https://path-coverage.github.io/schemas/v1/path_coverage.schema.json"


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
        """path relative to root, as decisions name it."""
        return Path(path).resolve().relative_to(self.root).as_posix()

    def covers(self, path):
        """True when path is under root and matches a cover glob and no
        skip glob."""
        try:
            relative = self.relative(path)
        except ValueError:
            return False
        return summary.matches(relative, map(scopes.glob, self.cover)) and not self.skips(relative)

    def skips(self, relative):
        """True when relative, a path relative to root, matches a skip
        glob."""
        return summary.matches(relative, self.skip)


class _Loader(importlib.machinery.SourceFileLoader):
    """Loads a covered module from its source, each leaf no branch tells
    wrapped, its code measured, never from (or into) the bytecode cache,
    which holds the unwrapped code."""

    def __init__(self, fullname, path, config, evaluations):
        """A loader for the covered file at path, logging on evaluations."""
        super().__init__(fullname, path)
        self.config = config
        self.evaluations = evaluations

    def compiled(self, tree, path):
        """tree, the covered file's wrapped parse, compiled as the module of
        the file path."""
        return monitor.compiled(tree, path)

    def exec_module(self, module):
        """Runs module's measured code, with the call its wrapped operands
        make bound in it."""
        path = self.get_filename(module.__name__)
        text = importlib.util.decode_source(self.get_data(path))
        name = self.config.relative(path)
        code, record = monitor.instrument(text, name, path, self.evaluations, self.compiled, self.config.lines[name])
        module.__dict__[wrapped_leaves.NAME] = record
        exec(code, module.__dict__)  # noqa: S102 - running the module is the point


class _Finder:
    """A meta path finder that hands each covered module to _Loader and
    leaves every other import to the finders after it."""

    def __init__(self, config, evaluations):
        """A finder for the files config covers, logging on evaluations."""
        self.config = config
        self.evaluations = evaluations

    def find_spec(self, fullname, path, target=None):
        """The spec of a covered module, with _Loader as its loader; None
        for any other module."""
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or not isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            return None
        if not self.config.covers(spec.origin):
            return None
        spec.loader = _Loader(fullname, spec.origin, self.config, self.evaluations)
        return spec


_finder = None


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
    config = _Config(root, cover, coverage_dir, report, collector, skip, groups)
    _check_lists(config)
    config.lines = _lines(config)
    _check_filters(config)
    return config


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
    """Measures every covered module imported from now on and reports at
    exit, counting afresh: the paths within each decision, and within each
    method. skip lists globs of files not covered though a cover glob
    matches them. report names the reporters: "gaps" (the default) prints the
    paths never taken, "summary" prints the totals, and "post" sends the
    JSON report to collector, a url. groups, {name: [glob, ...]}, names
    groups of covered files: each gets its own summary lines, its own JSON
    totals, and its list of files in the source report, which
    html-reporter makes a tab of its index page. A run given
    a part name (eg an xdist worker's) writes only its part file; the main
    run clears stale parts now and adds every part to its own report at
    exit. on_exit is atexit.register except in tests, which must not print
    a report as their own process exits."""
    global _finder
    config = _config(root, cover, coverage_dir, report, collector, skip, groups)
    evaluations = Evaluations()
    if part is None:
        for stale in _parts(config):
            stale.unlink()
    _finder = _Finder(config, evaluations)
    sys.meta_path.insert(0, _finder)
    on_exit(lambda: _report(config, evaluations, part))


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
        cover=_env_list(env, "PATH_COVERAGE_COVER", []),
        skip=_env_list(env, "PATH_COVERAGE_SKIP", []),
        coverage_dir=env["PATH_COVERAGE_DIR"],
        report=_env_list(env, "PATH_COVERAGE_REPORT", ["post" if collector else "gaps"]),
        collector=collector,
        groups=_env_groups(_env_list(env, "PATH_COVERAGE_GROUPS", [])),
        part=part,
        on_exit=on_exit,
    )
    return True


def _env_list(env, variable, absent):
    """The comma-separated entries of env's variable, absent when it is
    not set; ValueError naming the variable and its value when an entry
    is empty, eg from a stray or trailing comma, or the variable set to
    '', as dropping it would quietly change what is measured."""
    if variable not in env:
        return absent
    value = env[variable]
    entries = value.split(",")
    _refuse_empty(variable, entries, value)
    return entries


def _refuse_empty(label, entries, shown):
    """ValueError "label has an empty entry: shown" when any of entries is
    '', so an empty entry is never quietly dropped or globbed."""
    if "" in entries:
        raise ValueError(f"{label} has an empty entry: {shown!r}")


def _check_lists(config):
    """Refuses an empty cover, an empty entry in cover, skip or a group's
    globs, a group with no globs and a group with no name, naming it: each
    would quietly measure or total less than asked."""
    if not config.cover:
        raise ValueError("cover is empty, so nothing would be measured")
    _refuse_empty("cover", config.cover, config.cover)
    _refuse_empty("skip", config.skip, config.skip)
    if "" in config.groups:
        raise ValueError(f"a group has an empty name: {config.groups!r}")
    for name, globs in config.groups.items():
        if not globs:
            raise ValueError(f"group {name!r} has no globs")
        _refuse_empty(f"group {name!r}", globs, globs)


def _env_groups(entries):
    """{name: [glob, ...]} of entries, PATH_COVERAGE_GROUPS's name:glob
    pairs, eg ["code:src/**/*.py", "test:test/**/*.py"]; a name given
    twice gets both globs. An entry without both a name and a glob is
    refused, naming it."""
    groups = {}
    for entry in entries:
        name, colon, glob = entry.partition(":")
        if not (name and colon and glob):
            raise ValueError(f"PATH_COVERAGE_GROUPS entry {entry!r} is not name:glob")
        groups.setdefault(name, []).append(glob)
    return groups


def stop():
    """Stops measuring modules imported from now on; those already
    imported are still measured."""
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
    coverage_dir too. A run that measured other kinds, or was measured by
    other tools or versions of them, is refused, as it can list a
    decision's paths differently."""
    config = _config(root, cover, coverage_dir, report, None, skip, groups)
    files = _files(config)
    reports = [_same_measuring(path) for path in runs]
    decisions = _decisions(files)
    operands = merge([result.operands(decisions, {}), *(each["decisions"] for each in reports)])
    paths = merge_paths([result.paths(decisions, {}), *(_taken(each) for each in reports)])
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


def _same_measuring(path):
    """The JSON report at path, when it measured the kinds this version
    measures and was measured by the same tools at the same versions;
    ValueError naming path and which differs when not, as either can list
    a decision's paths differently."""
    report = json.loads(Path(path).read_text())
    if report.get("kinds") != kinds.names():
        raise ValueError(f"{path} measured other kinds")
    if report.get("measured_by") != measured_by.versions():
        raise ValueError(f"{path} was measured by other tools")
    return report


def _report(config, evaluations, part):
    """For a part, writes evaluations' counts, every logged event rebuilt,
    as that part's JSON file. For the main run, adds every part's counts to
    evaluations', writes the JSON report into coverage_dir, then runs the
    chosen reporters."""
    evaluations.flush()
    files = _files(config)
    decisions = _decisions(files)
    operands = result.operands(decisions, evaluations.counts)
    paths = result.paths(decisions, evaluations.decision_paths)
    reached = evaluations.reached
    config.coverage_dir.mkdir(parents=True, exist_ok=True)
    if part is not None:
        part_file = config.coverage_dir / f"path_coverage.{part}.json"
        part_file.write_text(json.dumps(_report_json(operands, paths, files, reached), indent=2))
        return
    parts = [json.loads(path.read_text()) for path in _parts(config)]
    operands = merge([operands, *(each["decisions"] for each in parts)])
    paths = merge_paths([paths, *(_taken(each) for each in parts)])
    reached = _reached([reached, *(each.get("reached") for each in parts)])
    _finish(config, files, operands, paths, reached)


def _finish(config, files, operands, paths, reached):
    """Writes the JSON report, with its totals, and the source report into
    coverage_dir, then runs the chosen reporters. reached is each
    statement's runs, None when not known. A cover's ::qualname keeps
    only the decisions and cards inside its scope."""
    cards = method_statements.cards(files, paths, reached)
    listed = listed_cards.of(files, operands, paths, reached)
    kept_operands = _kept(operands, config.lines)
    kept_paths = _kept(paths, config.lines)
    kept_cards = _kept(cards, config.lines)
    kept_reached = None if reached is None else _kept(reached, config.lines)
    report = _report_json(kept_operands, kept_paths, files, kept_reached)
    report["totals"] = console_summary.totals(kept_paths, kept_cards)
    if config.groups:
        report["totals"]["groups"] = console_summary.group_totals(kept_paths, kept_cards, config.groups)
    report["cards"] = _kept(listed, config.lines)
    report["tree"] = _carded(listed_cards.tree(files, operands), report["cards"])
    text = json.dumps(report, indent=2)
    config.coverage_dir.mkdir(parents=True, exist_ok=True)
    (config.coverage_dir / "path_coverage.json").write_text(text)
    kept_files = {path: (source, _kept(decisions, config.lines)) for path, (source, decisions) in files.items()}
    source = source_report.of(kept_files, paths, report["cards"], config.groups)
    (config.coverage_dir / "path_coverage.source.json").write_text(json.dumps(source))
    if "gaps" in config.report:
        for line in gaps.lines(kept_operands, kept_paths, paths_report.texts(files)):
            print(line)
    if "summary" in config.report:
        for line in console_summary.lines(kept_paths, kept_cards, config.groups):
            print(line)
    if "post" in config.report:
        post.deliver(text, config.collector)


def _matched(config, glob):
    """{path relative to root: path} of each file glob matches, in path
    order, skipped or not."""
    matched = {}
    for path in sorted(config.root.glob(glob)):
        matched[config.relative(path)] = path
    return matched


def _found(config, glob):
    """{path relative to root: source} of each file glob matches and no
    skip glob does, in path order."""
    found = {}
    for relative, path in _matched(config, glob).items():
        if not config.skips(relative):
            found[relative] = path.read_text()
    return found


def _check_filters(config):
    """Refuses a skip glob matching no file a cover glob matches, and a
    group glob matching no covered file, naming it: a filter that matches
    nothing can only be a mistake."""
    matched = {}
    for cover in config.cover:
        matched.update(_matched(config, scopes.glob(cover)))
    for skip in config.skip:
        if not _any_matches(matched, skip):
            raise ValueError(f"skip {skip!r} matches no covered file")
    for name, globs in config.groups.items():
        for glob in globs:
            if not _any_matches(config.lines, glob):
                raise ValueError(f"group {name!r}: {glob!r} matches no covered file")


def _any_matches(paths, glob):
    """True when any of paths, relative to root, matches glob, as
    summary.matches decides it."""
    for path in paths:
        if summary.matches(path, [glob]):
            return True
    return False


def _files(config):
    """{path relative to root: (source, decisions)} for every covered file,
    whether or not the run imported it, all its decisions, as _finish
    keeps only those on config.lines."""
    files = {}
    for cover in config.cover:
        for relative, source in _found(config, scopes.glob(cover)).items():
            files[relative] = (source, manifest.decisions(source, relative))
    return files


def _lines(config):
    """{path relative to root: line numbers} the lines measured in each
    covered file, as scopes.parse's kept gives them for its cover. Two
    covers of one file keep the lines of both. A cover whose glob
    matches no file is refused, naming it, as it would measure nothing."""
    lines = {}
    for cover in config.cover:
        glob, kept = scopes.parse(cover)
        found = _found(config, glob)
        if not found:
            raise ValueError(f"cover {cover!r} matches no file")
        for relative, source in found.items():
            lines[relative] = lines.get(relative, frozenset()) | kept(source, relative)
    return lines


def _carded(tree, cards):
    """tree, as listed_cards.tree gives it, {path: {"line:col": rows}},
    with only the cards in cards, {"path:line:col": card}, so the tree
    and the cards always list the same cards."""
    return {path: {at: rows for at, rows in nested.items() if f"{path}:{at}" in cards} for path, nested in tree.items()}


def _kept(named, lines):
    """named, {"path:line:col": value}, with only the entries scopes.keeps
    keeps for lines."""
    return {name: value for name, value in named.items() if scopes.keeps(name, lines)}


def _decisions(files):
    """Every decision of files, in one manifest."""
    return {decision: c for _, file_decisions in files.values() for decision, c in file_decisions.items()}


def _parts(config):
    """The part files in coverage_dir, in name order."""
    return sorted(config.coverage_dir.glob("path_coverage.*.json"))


def _taken(report):
    """The paths of a JSON report, as result.paths gives them."""
    return {decision: each["taken"] for decision, each in report.get("paths", {}).items()}


def _report_json(operands, paths, files, reached):
    """The JSON report: {"$schema": its schema's URL, "decisions": operands,
    "paths": {decision: {"leaves": [...], "taken": [...]}}, "kinds": [name,
    ...], "measured_by": {tool: version}}, the kinds naming what was
    measured and measured_by the tools that measured it, and "reached":
    {name: runs} when reached is known, even empty, as a run that reached
    no statement says so."""
    report = {
        "$schema": SCHEMA_URL,
        "decisions": operands,
        "paths": paths_report.of(paths, files),
        "kinds": kinds.names(),
        "measured_by": measured_by.versions(),
    }
    if reached is not None:
        report["reached"] = reached
    return report

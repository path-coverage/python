"""The kernel: measures each covered module, with sys.monitoring, as it
starts, changing none of its code, and writes the report at exit."""

import atexit
import json
from pathlib import Path

from . import (
    code_map,
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
    source_report,
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
            relative = Path(self.relative(path))
        except ValueError:
            return False
        return any(map(relative.full_match, self.cover)) and not self.skips(relative)

    def skips(self, relative):
        """True when relative, a path relative to root, matches a skip
        glob."""
        return any(map(Path(relative).full_match, self.skip))


def _adopter(config, evaluations):
    """What a starting module's code is offered to: a function that
    measures it, logging on evaluations, when its file is one config
    covers, parsing the file as it is now; and ignores it otherwise, as
    for code compiled from text under a name that is no file."""

    def adopt(code):
        """Measures code, a module's, when config covers its file."""
        if Path(code.co_filename).is_file() and config.covers(code.co_filename):
            path = Path(code.co_filename)
            monitor.measure(code, code_map.Source(path.read_text(), config.relative(path)), evaluations)

    return adopt


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
    """Measures every covered module that starts from now on and reports at
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
    config = _config(root, cover, coverage_dir, report, collector, skip, groups)
    evaluations = Evaluations()
    if part is None:
        for stale in _parts(config):
            stale.unlink()
    monitor.start(_adopter(config, evaluations))
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
    """Stops measuring modules that start from now on; those already
    started are still measured."""
    monitor.stop()


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
    statement's runs, None when not known."""
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
    source = source_report.of(files, paths, report["cards"], config.groups)
    (config.coverage_dir / "path_coverage.source.json").write_text(json.dumps(source))
    if "gaps" in config.report:
        for line in gaps.lines(operands, paths, paths_report.texts(files)):
            print(line)
    if "summary" in config.report:
        for line in console_summary.lines(paths, cards, config.groups):
            print(line)
    if "post" in config.report:
        post.deliver(text, config.collector)


def _files(config):
    """{path relative to root: (source, decisions)} for every covered file,
    whether or not the run imported it, and none a skip glob matches."""
    files = {}
    for glob in config.cover:
        for path in sorted(config.root.glob(glob)):
            relative = config.relative(path)
            if config.skips(relative):
                continue
            source = path.read_text()
            files[relative] = (source, manifest.decisions(source, relative))
    return files


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

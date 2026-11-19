"""The path_coverage_report command: reports saved runs' JSON reports, eg
those a collector saved, as one, each loop a fork only when asked."""

import json
import sys
from pathlib import Path

from . import ways_totals
from .kernel import report

HELP = """\
Usage: path_coverage_report [--loops] [--max-paths N] SOURCE_ROOT GLOBS REPORT_DIR RUN_JSON...

Reports the saved runs RUN_JSON... as one, writing the report into
REPORT_DIR, then prints each function's untested paths and the totals.
Exits 0 when every path is taken, and 1 when any is not.

  SOURCE_ROOT  the directory holding the covered source
  GLOBS        comma-separated globs of the covered files, relative to SOURCE_ROOT
  REPORT_DIR   the directory it writes its report into
  RUN_JSON...  one or more saved runs' JSON files, space-separated

Options:
  -h             Show this help
  --loops        Count each loop as a decision: 0 items or 1+ items
  --max-paths N  Fail each function with more than N paths
                 (default 4096, at most 65536)

Example:
  path_coverage_report --max-paths 8 /app 'src/**/*.py' report runs/*.json
"""


def main(argv):
    """Reports the runs argv names, [--loops] [--max-paths N] SOURCE_ROOT
    GLOBS REPORT_DIR RUN_JSON..., as HELP says, printing the untested
    paths, then the totals, read from the JSON it wrote, so a run with no
    untested path still prints them; -h prints HELP. Returns the exit
    status: 1 when the report fails, as ways_totals.failed says, else 0."""
    if argv[:1] == ["-h"]:
        print(HELP, end="")
        return 0
    options = {"loops": False}
    while argv[:1] in (["--loops"], ["--max-paths"]):
        if argv[0] == "--loops":
            options["loops"], argv = True, argv[1:]
        else:
            options["max_paths"], argv = int(argv[1]), argv[2:]
    source_root, globs, report_dir, *run_jsons = argv
    report(root=source_root, cover=globs.split(","), coverage_dir=report_dir, runs=run_jsons, report=["ways"], **options)
    written = json.loads((Path(report_dir) / "path_coverage.json").read_text())
    for line in ways_totals.lines(written):
        print(line)
    return 1 if ways_totals.failed(written) else 0


def command():
    """The installed path_coverage_report script's entry point."""
    sys.exit(main(sys.argv[1:]))

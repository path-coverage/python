"""Prints each group's path totals from a path_coverage JSON report, as the
summary reporter prints them, then where the report's index page is."""

import json
import sys
from pathlib import Path

from path_coverage.console_summary import grouped_lines

HELP = """Usage: bin/print_path_totals.py [OPTIONS] [REPORT]

Prints each group's path coverage totals (within decisions, within
methods) from REPORT, a path_coverage.json with groups configured, then
where its HTML report is. REPORT defaults to reports/paths/path_coverage.json,
which bin/test.sh writes.

Options:
  -h    Show this help

Example:
  PYTHONPATH=src python bin/print_path_totals.py reports/paths/path_coverage.json"""

ROOT = Path(__file__).resolve().parent.parent


def main(args):
    """Prints the totals of the report args names, or the help for -h;
    returns the exit status."""
    if args[:1] == ["-h"]:
        print(HELP)
        return 0
    report = Path(args[0]) if args else ROOT / "reports" / "paths" / "path_coverage.json"
    groups = json.loads(report.read_text())["totals"].get("groups", {})
    for line in grouped_lines(groups):
        print(line)
    print(f"Path coverage report: {report.resolve().parent / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

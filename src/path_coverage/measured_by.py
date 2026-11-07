"""The tools that parse and measure a run, each with its version: Python
and path_coverage itself. The parser is the stdlib ast, which has no
version of its own, so Python's version stands for it. A change to any of
them can list a file's decisions or paths differently, so a report names
them as it is written, and reports merge only when they name the same."""

import platform

from .version import __version__


def versions():
    """{tool name: its version} of this process, eg {"python": "3.13.5",
    "path_coverage": "0.0.1"}, the tools a report merges only with."""
    return {"python": platform.python_version(), "path_coverage": __version__}

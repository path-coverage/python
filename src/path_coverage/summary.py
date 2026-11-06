"""Which file a decision is in, and whether a file is in a group."""

import re
from pathlib import PurePosixPath


def matches(path, globs):
    """True when path, relative to root, matches any of globs, as cover
    globs match."""
    return any(map(PurePosixPath(path).full_match, globs))


def path_of(decision):
    """The file a decision is in: its name minus :line:column."""
    return re.sub(r":\d+:\d+\Z", "", decision)

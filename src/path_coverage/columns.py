"""Columns as the reports give them. ast counts a column in UTF-8 bytes,
which the code inside path_coverage keeps to; every column a report
gives counts characters, so a line holding eg an é names its decisions
where an editor shows them."""


class Columns:
    """The columns of one source, its lines encoded once."""

    def __init__(self, source):
        """Columns of source."""
        self._lines = source.encode().splitlines(keepends=True)

    def char(self, line, byte_col):
        """Example: line 2 '  "é" if a else b', byte 8 gives 7.
        The character column of byte_col on line, 1-based."""
        return len(self._lines[line - 1][:byte_col].decode())

    def name(self, path, line, byte_col):
        """The "path:line:column" naming what starts at byte_col on line,
        its column in characters."""
        return f"{path}:{line}:{self.char(line, byte_col)}"

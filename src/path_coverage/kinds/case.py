"""A match statement, its cases tried in order."""

from .chain import Chain


class Case(Chain):
    """A match statement: its cases tried in order, each reached only while
    no earlier one held, as a chain of `or` is. Its paths and values are a
    chain's, so it differs from Chain only in what it is named."""

    OPERATORS = ("match",)

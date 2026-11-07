"""Whether code leaves the function where it stands, decided once, from the
AST, for every part of the package that asks."""

import ast

# The word for each statement that leaves the function wherever it runs.
WORDS = {ast.Return: "return", ast.Raise: "raise"}


def word(statement):
    """"return" or "raise" for a statement that leaves the function; None for
    any other, an if holding a return among them, as it leaves only when its
    predicate holds."""
    return WORDS.get(type(statement))


def of(statements):
    """The word of the first of statements, an arm's, that leaves the
    function, wherever it is among them; None when none leaves."""
    return next((found for found in map(word, statements) if found), None)

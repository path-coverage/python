"""A chain of one operator, eg a and b and c."""

from .. import decision_paths

# The outcome of an operand on which each operator goes on to its next
# operand; any other outcome ends the chain there. A case goes on to its
# guard only when its pattern matches; a match stops at a case that holds.
CONTINUES_ON = {"and": True, "or": False, "case": True, "match": False}


class Chain:
    """A chain of one operator, each operand reached only while every one
    before it gave the outcome its operator goes on with: an `and`, an
    `or`, or a match's case, its pattern then its guard."""

    OPERATORS = ("and", "or", "case")

    def ways(self, node):
        """The ways node can be evaluated: each way of its first operand,
        going on to the next while each outcome is the one its operator
        goes on with."""
        first, *rest = node.operands
        goes_on = CONTINUES_ON[node.operator]
        ways = decision_paths.walk(first)
        for operand in rest:
            ways = [
                way
                for outcomes, value in ways
                for way in (
                    [({**outcomes, **more}, after) for more, after in decision_paths.walk(operand)]
                    if value == goes_on
                    else [(outcomes, value)]
                )
            ]
        return ways

    def value(self, _operator, operands):
        """Its value in each column: that of the last operand it reached."""
        columns = zip(*(operand["cells"] for operand in operands))
        return [
            next((cell for cell in reversed(column) if cell is not None), None)
            for column in columns
        ]

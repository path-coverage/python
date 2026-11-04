"""A builtin's call of a generator, eg any(o.late for o in orders)."""

# How many items a block call's generator gave.
ITEMS = ("0 items", "1 item", "2+ items")

# Every path a stop-early block call can take: how many items its
# generator gave, and its last answer, none with no items.
STOP_EARLY_PATHS = (
    (ITEMS[0], None),
    (ITEMS[1], True),
    (ITEMS[1], False),
    (ITEMS[2], True),
    (ITEMS[2], False),
)

# A block call's value from whether its generator gave no items, and its
# last answer.
VALUES = {
    "any": lambda none, answer: not none and answer,
    "all": lambda none, answer: none or answer,
}


class Block:
    """A builtin's call of a generator, eg any(o.late for o in orders): how
    many items the generator gave, and its last answer, its value following
    from them. Nothing else is evaluated, eg len(orders)."""

    OPERATORS = tuple(VALUES)

    def ways(self, node):
        """The ways node can be evaluated, fixed by its builtin, its value
        following from each."""
        items, answer = node.operands
        return [
            ({id(items): count, id(answer): last}, self.path_value(node.operator, count, last))
            for count, last in STOP_EARLY_PATHS
        ]

    def value(self, operator, operands):
        """Its value in each column, from its count of items and its last
        answer there; None where it was not reached."""
        items, answer = operands
        return [
            count and self.path_value(operator, count, last)
            for count, last in zip(items["cells"], answer["cells"])
        ]

    def path_value(self, operator, items, answer):
        """Its value on a path: eg False for any given 0 items, True for all
        given 0 items."""
        return VALUES[operator](items == ITEMS[0], answer)

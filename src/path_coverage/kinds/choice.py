"""A condition whose predicate picks an arm: a ternary, an if or a
comprehension's filter."""

from .. import site_paths

# The predicate outcome on which each choice takes its then arm.
THEN_ON = {"ternary": True, "if": True, "filter": True}

# The names of the arms of each choice whose arms have no text to show: an
# if's are statements, a filter's are what it does to an item.
NAMED_ARMS = {
    "if": {"then": "then", "else": "else"},
    "filter": {"then": "keep", "else": "drop"},
}


class Choice:
    """A condition whose predicate picks an arm: a conditional expression
    (a ternary), an if statement, an elif being its else arm, or a
    comprehension's filter, whose then arm keeps an item."""

    OPERATORS = ("ternary", "if", "filter")

    def ways(self, node):
        """The ways node can be evaluated: each way of its predicate, then
        each way of the condition the arm it picks holds, if it holds one;
        an if with no else arm picks none. Its value is that of no choice,
        so is None."""
        predicate, then_arm, *rest = node.operands
        else_arm = rest[0] if rest else None
        ways = []
        for outcomes, value in site_paths.walk(predicate):
            arm = then_arm if value == THEN_ON[node.operator] else else_arm
            body = arm.body if arm else None
            if body is None:
                ways.append((outcomes, None))
                continue
            ways.extend(({**outcomes, **more}, None) for more, _ in site_paths.walk(body))
        return ways

    def arm_label(self, arm, choice):
        """The name of one of its arms, of a condition named choice: then
        or else for an if's, as its text is statements; keep or drop for a
        filter's; ? or : for a ternary's, then its condition's operator, or
        its text for a plain arm."""
        if choice in NAMED_ARMS:
            return NAMED_ARMS[choice][arm["arm"]]
        mark = "?" if arm["arm"] == "then" else ":"
        body = arm["body"]
        return f"{mark} {body['operator'] if body else arm['text']}"

    def value(self, _operator, operands):
        """Its value in each column: its taken arm's body's, None for a
        plain arm or a column that took no arm."""
        arms = operands[1:]
        return [
            next(
                (arm["body"]["cells"][column] if arm["body"] else None)
                for arm in arms
                if arm["cells"][column]
            )
            if any(arm["cells"][column] for arm in arms)
            else None
            for column in range(len(arms[0]["cells"]))
        ]

"""The number of ways one call can go through each card, folded over its
tree, as card_tree places its rows. Each row gives a pair, (ways that go on,
ways that leave the function): a return or a raise leaves, so each path of a
decision taking an arm that holds one leaves there, as that row runs on it.
Rows one after another multiply, but only the ways that go on reach the next
row; a decision adds up its paths, each with the rows it runs on that path one
after another; and a row that is the whole of a leaf counts only those of its
paths that give the leaf the outcome the path has, so no impossible way is
counted where gives knows it."""

from . import card_tree, method_statements, decision_paths
from .manifest import decisions as find_decisions


def of(source, path):
    """{def decision: its ways} for each function in source. Example:
    {"k.py:1:0": 3} for def f(a, b): if a: return 0, then a conditional
    expression of b: 1 way leaves, 2 go on."""
    decisions = find_decisions(source, path)
    return {
        decision: card(source, decisions, rows)
        for decision, rows in method_statements.of(source, path).items()
    }


def card(source, decisions, rows):
    """The ways through a card of rows in source, decisions being {decision:
    Condition}."""
    places = card_tree.nested(source, decisions, rows)
    return sum(_Fold(rows, places, decisions).total())


def sequence(pairs):
    """The pair of rows one after another, from their pairs: the ways that
    go on through them all, and those that leave at one of them, having
    gone on through every one before it."""
    on, left = 1, 0
    for more, leaving in pairs:
        on, left = on * more, left + on * leaving
    return (on, left)


def added(pairs):
    """pairs added up, each part on its own."""
    return (sum(pair[0] for pair in pairs), sum(pair[1] for pair in pairs))


class _Fold:
    """The fold of a card's rows, placed as places has them."""

    def __init__(self, rows, places, decisions):
        """rows a card's, placed as card_tree places them, each decision
        row's Condition among decisions."""
        self.rows = {card_tree.key_of(row): row for row in rows}
        self.places = places
        self.decisions = decisions
        self.children = {}
        for key, place in places.items():
            self.children.setdefault(place["parent"], []).append(key)

    def total(self):
        """The pair of the card: its top rows' pairs, one after another."""
        return sequence([self.pair_of(key) for key in self.children.get(None, [])])

    def pair_of(self, key):
        """The pair of the row keyed key: a decision's adds up its paths' pairs;
        any other row is a return or a raise, as no other is a row, so
        leaves."""
        row = self.rows[key]
        if row.decision is None:
            return (0, 1)
        paths = range(len(self._possible(row.decision)))
        return added([self.pair_on(key, path) for path in paths])

    def pair_on(self, key, path):
        """The pair of the decision row keyed key on its path at index path: the
        rows it runs on that path, one after another, each given that path's
        outcomes, a return or raise among them leaving there."""
        outcomes = self._possible(self.rows[key].decision)[path]
        running = [
            child for child in self.children.get(key, []) if path in self.places[child]["on"]
        ]
        return sequence([self._child_pair(child, outcomes) for child in running])

    def _child_pair(self, child, outcomes):
        """The pair of the row keyed child, its parent's path having
        outcomes: all of its own, for a row that gives nothing; else those of
        only its paths that give its leaf that path's outcome, or that give
        what is not known."""
        place = self.places[child]
        gives = place["gives"]
        if gives is None:
            return self.pair_of(child)
        fits = (None, outcomes[place["leaf"]])
        return added(
            [
                self.pair_on(child, path) if given in fits else (0, 0)
                for path, given in enumerate(gives)
            ]
        )

    def _possible(self, decision):
        """The possible paths of the decision named decision."""
        return decision_paths.possible(self.decisions[decision])

"""How often something happened, by test: every count of what a run did is
a Tally, {test id: n}, so a report can tell which tests take which paths.
Its total is the sum over its tests, never stored beside it. The JSON
report lists a tally by its tests' keys, each the first 12 hex digits of
the sha256 of the test's id, and names each key's test once, in its
tests."""

import hashlib

# The id of what runs outside every test, eg a module's import.
NO_TEST = "(no test)"

# How many hex digits of a test id's sha256 its key keeps.
KEY_DIGITS = 12


class Tally:
    """{test id: n} of the tests that made something happen, each n at
    least 1."""

    __slots__ = ("by_test",)

    def __init__(self, by_test=()):
        """The tally of by_test, {test id: n}; ValueError naming a test
        whose n is below 1."""
        self.by_test = dict(by_test)
        for test, count in self.by_test.items():
            if count < 1:
                raise ValueError(f"{test} counted {count}")

    def add(self, test):
        """Counts one more happening, made by test."""
        self.by_test[test] = self.by_test.get(test, 0) + 1

    @property
    def total(self):
        """How often it happened, over every test."""
        return sum(self.by_test.values())

    def __add__(self, other):
        """The tally of self's happenings and other's, test by test."""
        summed = dict(self.by_test)
        for test, count in other.by_test.items():
            summed[test] = summed.get(test, 0) + count
        return Tally(summed)

    def __eq__(self, other):
        """True when other, a Tally, counts the same tests, each the same
        number of times. A bare count is no Tally, so comparing one fails
        loudly rather than coming out quietly unequal."""
        return self.by_test == other.by_test

    def __repr__(self):
        """Tally({test id: n}), as it is built."""
        return f"Tally({self.by_test!r})"


def add(tallies, at, test):
    """Counts one more happening of at, by test, in tallies, {at: Tally},
    making at's Tally on its first, as a run counts on every event."""
    counted = tallies.get(at)
    if counted is None:
        counted = tallies[at] = Tally()
    counted.add(test)


def key(test):
    """The key the JSON report lists test's counts under."""
    return hashlib.sha256(test.encode()).hexdigest()[:KEY_DIGITS]


def named(tests):
    """{key: test id} of tests, as the JSON report's tests lists them;
    ValueError when two share a key, as joined refuses."""
    return joined([{key(test): test} for test in tests])


def joined(maps):
    """{key: test id} of maps, each a report's tests, joined; ValueError
    naming a key and both ids when maps give it two, as their counts would
    be added as one test's."""
    found = {}
    for each in maps:
        for at, test in each.items():
            if found.setdefault(at, test) != test:
                raise ValueError(f"key {at} names both {found[at]} and {test}")
    return found


def jsonable(report):
    """report, a dict of dicts, lists and values, with every Tally in it
    listed, and "tests" naming the key of each test those tallies count,
    in id order: the one place a report's tests come from, so its tests
    and its tallies always agree."""
    ids = set()
    body = _listed_in(report, ids)
    body["tests"] = named(sorted(ids))
    return body


def _listed_in(value, ids):
    """value with every Tally in it listed, each Tally's tests added to
    ids."""
    if isinstance(value, Tally):
        ids.update(value.by_test)
        return listed(value)
    if isinstance(value, dict):
        return {at: _listed_in(each, ids) for at, each in value.items()}
    if isinstance(value, list):
        return [_listed_in(each, ids) for each in value]
    return value


def listed(counted):
    """{key: n} of counted, a Tally, as the JSON report lists it."""
    return {key(test): count for test, count in counted.by_test.items()}


def read(listed_counts, tests):
    """The Tally of listed_counts, {key: n} as listed gives it, tests being
    the report's {key: test id}."""
    return Tally({tests[at]: count for at, count in listed_counts.items()})

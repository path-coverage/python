from path_coverage.path_manifest import Decision, PathMethod, methods

FEE = (
    "def fee(member, big):\n"
    '    """The fee for one order."""\n'
    "    total = 100\n"
    "    if member:\n"
    "        total -= 5\n"
    "    if big:\n"
    "        total -= 10\n"
    "    return total\n"
)


def test_9f2c4a01():
    """Example: fee with two top-level ifs
    The def is a method whose paths are counted, named at its def.
    Each top-level if is one of its decisions, by its line.
    Neither if's arms leave the function, so exits is None."""
    assert methods(FEE, "k.py") == {
        "k.py:1:0": PathMethod(
            name="fee", decisions=(Decision(line=4, exits=None), Decision(line=6, exits=None))
        )
    }


def test_9f2c4a02():
    """Example: a def with one top-level if, and one with an if only
    inside a for loop
    With fewer than two top-level ifs a def's paths are its branches.
    So neither is a method whose paths are counted."""
    source = (
        "def one(x):\n"
        "    if x:\n"
        "        return 1\n"
        "    return 2\n"
        "\n"
        "def loop(xs):\n"
        "    for x in xs:\n"
        "        if x:\n"
        "            print(x)\n"
        "        if not x:\n"
        "            print(0)\n"
    )
    assert methods(source, "k.py") == {}


def test_9f2c4a03():
    """Example: if not rates: return 0 / if member: ... else: raise
    The first if's then arm always returns, so exits is True.
    The second's else arm always raises, so exits is False.
    A path taking that outcome ends there."""
    source = (
        "class Shop:\n"
        "    def fee(self, rates, member):\n"
        "        if not rates:\n"
        "            return 0\n"
        "        if member:\n"
        "            rate = 5\n"
        "        else:\n"
        '            raise ValueError("no fee")\n'
        "        return rate\n"
    )
    assert methods(source, "k.py") == {
        "k.py:2:4": PathMethod(
            name="fee", decisions=(Decision(line=3, exits=True), Decision(line=5, exits=False))
        )
    }

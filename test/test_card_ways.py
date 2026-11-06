from path_coverage import card_ways


def test_3e0b9d01():
    """Example: fee, an if holding a conditional expression of an and;
    two, two conditional expressions one after another; led, an or of an
    any whose generator's element is an and.
    The ways through a card fold its tree: rows one after another
    multiply, and a decision adds up its paths, each times the ways of the rows
    it runs on that path; a row that is the whole of a leaf counts only its
    paths that give the leaf the outcome the path has.
    fee: then 3, else 1, so 4. two: 2 times 2, so 4. led: the or's true
    path takes the 2 any paths giving true, 1 way each; each false path
    takes its 3 giving false, 1 + 2 + 2."""
    source = (
        "def fee(member, paid, big):\n"
        "    if member:\n"
        "        cost = 5 if paid and big else 10\n"
        "    else:\n"
        "        cost = 0\n"
        "    return cost\n"
        "def two(a, b):\n"
        "    x = 1 if a else 2\n"
        "    y = 3 if b else 4\n"
        "    return [x, y]\n"
        "def led(xs):\n"
        "    return any(x % 2 and x > 1 for x in xs) or not xs\n"
    )
    assert card_ways.of(source, "k.py") == {"k.py:1:0": 4, "k.py:7:0": 4, "k.py:11:0": 12}


def test_3e0b9d02():
    """Example: guard, an if whose arm returns, then a conditional
    expression; twice, two such ifs on their own lines, then a return;
    must, an if whose arm raises, then a conditional expression.
    A way that returns or raises leaves the function there, so it goes on
    to none of the rows after it: each is 3 ways, the one that leaves early
    and the 2 that go on, not 2 times 2."""
    source = (
        "def guard(a, b):\n"
        "    if a:\n"
        "        return 0\n"
        "    return 1 if b else 2\n"
        "def twice(a, b):\n"
        "    if a: return 0\n"
        "    if b: return 1\n"
        "    return 2\n"
        "def must(a, b):\n"
        "    if not a:\n"
        "        raise ValueError(a)\n"
        "    return 1 if b else 2\n"
    )
    assert card_ways.of(source, "k.py") == {"k.py:1:0": 3, "k.py:5:0": 3, "k.py:9:0": 3}

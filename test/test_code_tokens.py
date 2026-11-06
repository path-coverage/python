from path_coverage import code_tokens


def test_c0d7e301():
    """Example: a string over lines 1 to 3
    A token over many lines is coloured on each line it reaches."""
    assert code_tokens.of('x = """a\nb\nc"""\n') == {1: [[4, 8, "s"]], 2: [[0, 1, "s"]], 3: [[0, 4, "s"]]}


def test_c0d7e303():
    """Example: a string over lines 1 to 3, its line 2 empty
    An empty line holds none of the string's characters, so has no range."""
    assert code_tokens.of('x = """a\n\nc"""\n') == {1: [[4, 8, "s"]], 3: [[0, 4, "s"]]}


def test_c0d7e304():
    """Example: f"hi {n}!"
    An f-string's start and its text before {n} are tokens of their own,
    but touch and are both strings, so are coloured as one range; so are
    its text after {n} and its end."""
    assert code_tokens.of('x = f"hi {n}!"\n') == {1: [[4, 9, "s"], [12, 14, "s"]]}


def test_c0d7e302():
    """Example: the labels if/else and elif, and a ternary's arm, ? n > 1
    A label naming a choice and its else is coloured word by word, each a
    keyword, as code would read its / as division. Any other label is
    coloured as code. A ternary's arm's ? is an operator, the code after
    it code."""
    assert [code_tokens.label_code("if/else"), code_tokens.label_code("elif")] == [
        {"text": "if/else", "tokens": [[0, 2, "k"], [3, 7, "k"]]},
        {"text": "elif", "tokens": [[0, 4, "k"]]},
    ]
    assert code_tokens.ternary_arm_code("? n > 1") == {"text": "? n > 1", "tokens": [[0, 1, "o"], [6, 7, "n"]]}

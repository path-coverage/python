"""Which lines a cover glob's ::qualname keeps: those of the def or class
it names, every def nested in it included, so a run can report one
function or class alone. Example: cover "src/orders.py::Order.ship"."""

import ast

# Between a cover glob and the qualname it narrows to.
SEPARATOR = "::"

# The nodes a qualname's names name.
DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def parse(cover):
    """(glob, kept) of a cover entry: its file glob, and kept(source,
    path), the lines measured in the file at path, of source: all of
    them, as whole gives them, for a cover with no ::; those of the defs
    and classes its qualname names for one with, ValueError naming cover,
    path and the first name missing for a file holding none. A qualname
    that is not names joined by dots is refused, naming it. Example:
    "src/orders.py::Order.ship" gives "src/orders.py" and ship's lines."""
    glob, separator, qualname = cover.partition(SEPARATOR)
    if not separator:
        return glob, lambda source, path: whole(source)
    if not _is_qualname(qualname):
        raise ValueError(f"cover {cover!r}: {qualname!r} is not a qualname")
    return glob, lambda source, path: _named(cover, qualname, source, path)


def glob(cover):
    """The file glob of a cover entry, without any ::qualname. Example:
    "src/orders.py::Order.ship" gives "src/orders.py"."""
    return cover.partition(SEPARATOR)[0]


def _is_qualname(text):
    """True when text is names joined by dots, each a Python identifier,
    eg Order.ship; False for '', 'Order.', 'Order::ship' or ' Order'."""
    for part in text.split("."):
        if not part.isidentifier():
            return False
    return True


def _named(cover, qualname, source, path):
    """The lines of the defs and classes qualname names in source, the
    file at path; ValueError naming cover, path and the first name
    missing, for a file holding none."""
    kept = lines(source, qualname)
    if not kept:
        raise ValueError(f"cover {cover!r}: {lacking(source, qualname, path)}")
    return kept


def whole(source):
    """The line numbers of all of source, 0 among them for its top level,
    as a file covered whole keeps them."""
    return frozenset(range(len(source.splitlines()) + 1))


def lines(source, qualname):
    """The line numbers of every def or class in source that qualname,
    names from the module down joined by dots, names, each from its first
    decorator, or its def line, to its last; empty when it names none.
    Example: "Order.ship" gives ship's lines, both defs' for a property's
    getter and setter. A decorated def's code starts at its decorator."""
    kept = set()
    for node in _found(ast.parse(source), qualname.split(".")):
        first = node.decorator_list[0].lineno if node.decorator_list else node.lineno
        kept.update(range(first, node.end_lineno + 1))
    return frozenset(kept)


def lacking(source, qualname, path):
    """What the file at path, of source, lacks of qualname: the deepest
    def or class it names, and the first name not under it. Example:
    "class Order in src/orders.py has no post"; "src/refunds.py has no
    Order" when not even the first name is there."""
    tree = ast.parse(source)
    parts = qualname.split(".")
    depth = 0
    while _found(tree, parts[: depth + 1]):
        depth += 1
    if depth == 0:
        return f"{path} has no {parts[0]}"
    holder = _found(tree, parts[:depth])[0]
    kind = "class" if isinstance(holder, ast.ClassDef) else "def"
    return f"{kind} {'.'.join(parts[:depth])} in {path} has no {parts[depth]}"


def _found(node, parts):
    """The defs and classes under node that parts, names from node down,
    name; [node] itself when parts is empty."""
    if not parts:
        return [node]
    found = []
    for child in _defs(node):
        if child.name == parts[0]:
            found.extend(_found(child, parts[1:]))
    return found


def _defs(node):
    """The defs and classes directly under node, looking through any node
    that is neither, eg an if holding a def."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, DEFS):
            yield child
        else:
            yield from _defs(child)


def line(name):
    """The line of name, a decision's or card's "path:line:col"."""
    return int(name.rsplit(":", 2)[1])


def keeps(name, lines):
    """True when name, a decision's or card's "path:line:col", is on one
    of the lines kept for its path in lines, {path: line numbers}."""
    return line(name) in lines[name.rsplit(":", 2)[0]]

"""The terminal worklist of untested paths through each function: for each
function, a heading, then each path no run took, as the choices a test must
make to take it."""

from .gaps import steps


def lines(cards, texts, parents):
    """The lines of cards, {function's key: card}, as report["cards"] has
    them, each choice's leaves named by their text in texts ({decision:
    [text, ...]}); a decision whose parent, in parents ({decision: its
    parent decision}), is stepped on the same path is named there, and the
    parent left out."""
    out = []
    for key, card in cards.items():
        # A module's top card, run by no call, lists no ways to take.
        if "gaps" not in card:
            continue
        decisions = {row["at"]: row["decision"] for row in card["rows"]}
        named = lambda way: _choices(way, decisions, texts, parents)  # noqa: E731
        where = f"{_where(key)} {card['name']}"
        gaps, taken = card["gaps"], card["impossible_taken"]
        out += _section(f"{where} has {_paths(len(gaps), 'untested ')}.", UNTESTED, gaps, named)
        out += _section(f"{where} took {_paths(len(taken), '')} declared impossible.", DECLARED, taken, named)
    return out


# The instruction under a function's untested paths.
UNTESTED = "Add tests that take each of these paths:"
# The instruction under the impossible paths a function's calls took.
DECLARED = "Remove the # path: impossible comment that declares it:"


def _section(heading, instruction, ways, named):
    """heading and instruction, then each of ways numbered, its choices as
    named gives them; no lines at all when ways is empty."""
    if not ways:
        return []
    return [heading, instruction, *(f"  {number}. {named(way)}" for number, way in enumerate(ways, 1))]


def _paths(count, kind):
    """count paths, of kind, eg "untested ", singular for one."""
    return f"{count} {kind}{'path' if count == 1 else 'paths'}"


def _choices(gap, decisions, texts, parents):
    """The choices of gap, a path's steps, in order: each stepped decision
    by its line and its leaves' outcomes, but for a parent of another of
    them; each loop, a step at no row, by its line and how many items it
    ran; a step with no choice is left out."""
    stepped = [step for step in gap if "path" in step]
    chosen = [decisions[step["at"]] for step in stepped if step["at"] in decisions]
    implied = {parents[decision] for decision in chosen if decision in parents}
    return ", then ".join(
        _choice(step, decisions, texts)
        for step in stepped
        if decisions.get(step["at"]) not in implied
    )


def _choice(step, decisions, texts):
    """One step's choice, after its line: a decision's leaves' outcomes, or
    a loop's items."""
    line = step["at"].split(":")[0]
    if step["at"] in decisions:
        return f"line {line} {steps(step['path'], texts[decisions[step['at']]])}"
    return f"line {line} loop: {step['path'][0]}"


def _where(key):
    """path:line of a function's key, path:line:column."""
    return key.rsplit(":", 1)[0]

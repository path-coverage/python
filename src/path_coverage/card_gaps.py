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
        count = len(card["gaps"])
        if not count:
            continue
        out.append(f"{_where(key)} {card['name']} has {count} untested {'path' if count == 1 else 'paths'}.")
        out.append("Add tests that take each of these paths:")
        decisions = {row["at"]: row["decision"] for row in card["rows"]}
        for number, gap in enumerate(card["gaps"], 1):
            out.append(f"  {number}. {_choices(gap, decisions, texts, parents)}")
    return out


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

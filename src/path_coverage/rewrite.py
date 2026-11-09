"""Measures covered code in rewrite mode: every event comes from a record
inserted_records inserts, as INSERTS lists for this mode, and nothing is
monitored. Each event is named from the parse, so none depends on how
Python compiles the code."""

from . import inserted_records


def instrument(text, name, path, evaluations, compiler, kept):
    """(code, record) of text, the source of the file path, named name as
    decisions name it: its parse with every record rewrite mode inserts
    on a kept line, kept the line numbers measured, compiled by compiler,
    logging on evaluations. The module must bind record as
    inserted_records.NAME."""
    code, record, source = inserted_records.instrumented(text, name, path, evaluations, compiler, kept, "rewrite")
    evaluations.loops.update(source.loops)
    evaluations.repeats.update(source.repeats)
    return code, record

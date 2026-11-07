# Combined is path coverage

A direction, for both implementations, from 2026-11-07. Not built yet.

## The direction

- Alone treats each primitive (an `and`, a ternary, a `return`) as a
  decision in its own right, with no concern for how they combine. It
  becomes internal: not shown in the HTML, not used in gates.
- Combined becomes the one metric, called simply path coverage.
- A path no call can take is impossible. It is dropped from path
  coverage, so a dev sees 7 / 7, not 7 / 8, and is reported as a
  second diagnostic whose target is 0.
- Gap lines follow path coverage, so every gap is one a test can
  close.

## Why

Reporting an impossible path as a gap sends a dev, or an AI, after a
test that cannot exist. Most impossible paths are dodgy code, usually
duplication, whose fix is a refactor.

## Examples

Each was run on python/ at 1dd881f, every possible way called.

A flag checked again after an early return:

    def save(record, dry_run, db, audit):
        if dry_run:
            print('would save', record)
            return None
        db.append(record)
        if not dry_run:            # always true here
            audit.append(record)
        return len(db)

    src/orders.py:6:4 path never taken: `not dry_run` false
    Paths combined: 5 / 6 (83.33%)    ways 3

Two ways exist. Wanted: path coverage 5 / 5, ways 2, and one
impossible path reported.

A name read twice in one decision:

    def can_edit(user, owner):
        return user and user.name == owner or user and user.admin

    2:39 path never taken: `user` true, `user.name == owner` false, `user` false
    2:39 path never taken: `user` false, `user` true, `user.admin` true
    2:39 path never taken: `user` false, `user` true, `user.admin` false
    Paths combined: 4 / 7    ways 7

Each gives `user` both outcomes. Wanted: 4 / 4, ways 4, three
impossible paths reported.

Literal arms, impossible only in combination:

    def role(a, b):
        return a and (1 if b else 2)

    2:13 path never taken: `a` true, `1 if b else 2` false
    Paths combined: 4 / 5    ways 5

Alone keeps this gap: as a primitive, the `and` has the path. Path
coverage drops it, as neither arm can be falsy.

## Cautions

- A false "impossible" tells the dev to delete code that is needed.
  So the rules for when two reads give one outcome (stable leaves)
  stay conservative: when in doubt, report a gap.
- Combined counts row paths on some possible way, not whole ways
  taken. Which of a card's ways were taken is not recorded yet.

## Python now

Nothing is ruled out. `method_statements.size` adds every row's
paths; `card_ways` drops only rows that are a whole leaf. Ruby rules
out correlated stable leaves: ruby/notes/impossible-combined-paths.md.

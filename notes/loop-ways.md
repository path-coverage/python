# Loops in whole ways

A call's way must not grow with the passes its loops make. So each
call's way is walked by a small state machine (`walk.Walk`), a stack of
units: the function's own, then each loop under way. A loop is a for
statement, or a generator of a list, set or dict comprehension (run in
its function's frame), named by its for keyword.

```
def total(orders):              call's way:  for 0 / 1 / 2+ items, return
    amount = 0
    for order in orders:        each pass:   its own way, counted on the for
        if order['paid']:
            amount += order['amount']
    return amount
```

`total` of 3 orders, then of 1, then of none, gives this card:

```
"taken":  [{"way": [{"at": "3:04", "path": ["2+ items"]}, {"at": "6:04"}], "count": 1},
           {"way": [{"at": "3:04", "path": ["1 item"]},   {"at": "6:04"}], "count": 1},
           {"way": [{"at": "3:04", "path": ["0 items"]},  {"at": "6:04"}], "count": 1}]
"passes": {"3:04": [{"way": [{"at": "4:08", "path": [true]}],  "count": 3},
                    {"way": [{"at": "4:08", "path": [false]}], "count": 1}]}
```

## Designs weighed

1. Log every step of a call, fold passes when the call ends. Memory
   grows with passes until the call ends: rejected.
2. A stack of units, driven by what the AST says holds each row
   (`code_map.Source.loops`, row name to its for loops, outermost
   first). Each row runs at most once per unit, so a unit's steps are
   bounded by its rows. Chosen; it matches Ruby's decided design
   (ruby/notes/unfolding.md, "A loop body is a unit of its own").
3. A precompiled automaton numbering every possible way, a way counted
   as one int. Most compact, and a way with no transition would be
   impossible, found as it happens. Larger; it can be built on 2 later,
   when impossible ways are ruled out.

## Events

- FOR_ITER left: `Pass(loop)`, a pass starts, the one before is counted.
- FOR_ITER right (reported from POP_ITER): `Exhausted(loop)`.
- A `break` or `return` sends no Exhausted: the next row outside the
  loop, a pass of another loop, or the call's end closes it.
- A missing name in `Evaluations.loops` raises, never quietly lands in
  the wrong unit.
- The start of measured code with no card (a generator expression, a
  lambda, a module) logs `Unwalked`, ending any way under way in its
  frame. CPython reuses a finished frame's id, and without this a
  generator expression's steps joined the last way left in a frame of
  that id: self-coverage's report was 280 MB, one way 19,441 steps.

Self-coverage's report: 280 MB with every loop pass a step, 104 MB with
`Unwalked`, 4.9 MB with comprehensions as loops; its longest way 493
steps, from a while loop.

## Open

- while loops: no FOR_ITER; a row in a while's body adds a step per pass.
- A for whose header holds a decision has no `for` row; its loop step's
  at names no row of the card. A comprehension's for is no row either.
- `ways` of the card (card_ways) still counts a loop body once, not as
  0/1/2+ times its passes, so the card's title can show fewer ways than
  were taken.
- Each pass logs an event: the suite went from about 40 s to 54 s.
- The html-reporter's ways tab lists taken ways only: the possible ways
  never taken need enumerating, and impossible ones (the "special zero")
  need ruling out first.

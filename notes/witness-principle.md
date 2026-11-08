# A run covers each path it witnesses

A direction for both implementations, from 2026-11-08, for how the
paths a method's machine lists are matched against what tests did.

## The principle

Each method gets a state machine built from its source. A dry run of it
lists every static path: a sequence of fork choices, eg an if taking its
then, an or's second operand true. A loop is a fork too, walked without
iterating: it runs no pass, its body in no step, or at least one, its
body walked once.

A run covers each static path it witnesses: one whose every fork choice
the run made, after the same earlier choices. Repetition collapses; which
choices were made, and in what context, is kept.

## A loop's passes

```python
def total(orders):
    amount = 0
    for order in orders:
        if order['paid']:
            amount += order['amount']
    return amount
```

Static paths:

```text
P1  for 0 items                return
P2  for 1+ items   if true     return
P3  for 1+ items   if false    return
```

`total([paid, paid, unpaid])` passes the if true, true, false, so covers
P2 and P3: each body way some pass took.

## Each fork once

A static path holds each fork at most once. A loop's own fork is whether
it is entered at all; its later tests, true for another pass, false to
leave, repeat that fork and add no choice. Leaving is implied by the
path going on; a break shows by the step before it.

```python
def drain(queue):
    while queue:
        if queue.pop():
            ...
    return queue
```

```text
0 passes    while false                 return
1+ passes   while true    if true       return
1+ passes   while true    if false      return
```

`drain([7])` tests `queue` true, pops, tests it false, returns: it
witnesses a 1+ path, the final false no step of it.

## Calls never mix

Each call is a run of its own. Choices of different calls are never put
together:

```python
def fee(member, paid):
    price = 5 if member else 10
    return price if paid else 0
```

`fee(True, True)` and `fee(False, False)` cover (true, true) and
(false, false), never (true, false): no single call made both choices.

## The cost

Collapsing passes can witness a path no single run took whole:

```python
def has_paid(orders):
    found = False
    for order in orders:
        if order['paid']:
            found = True
    if found:
        ...
```

A call whose passes go false, then true, and so takes `if found` true,
witnesses (for 1+ items, if false, if found true), which no run with only
unpaid orders can take. The static path describes the choices, not a
whole execution.

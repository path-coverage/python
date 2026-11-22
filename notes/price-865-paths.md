# price(): 865 paths, and how many can run

A worked count, from 2026-11-09, of `price()` in demo/source/shop.py
(lines 32 to 55), and what it shows about impossible paths. Not built
yet beyond what the machine already does.

## The count

The demo's flow for `price` gives `ways` 865: 862 missed, 3 taken,
0 impossible. 865 is the plain static product:

    raise (L36)                          1
    L38 member and total>50              3   (F | T,F | T,T)
    L40/42 vip / elif coupon or coupon   4   (vip | !vip: T | F,T | F,F)
    L44 total>100 or pickup              3
    L45 not express                      2
    L47 gift and (wrap or member)        4
      else arm: 1 if gift else 0        x2 on 2 of the 4  -> 6
    L53 pickup                           2
    total = 1 + 3*4*3*2*6*2 = 865

Counted three ways:

    each and/or operand outcome           865   (the flow)
      minus the gift/pickup repeats     <=385
    only each if/elif/ternary arm         145   = 1 + 2*3*2*2*3*2

So most of the size comes from counting each short-circuit outcome as
a path of its own, and seven decisions in sequence multiplying.

## Scope is already in the machine

method_machine.py builds each method as continuations: `_if` puts an
if's body only on its true arm, and a raise or return goes straight on
to its exit (`END` for an uncaught raise). So a decision inside an arm
is never counted on the paths that skip the arm, and an early exit
ends its paths. The 865 already respects that: the raise is 1 path,
and the L52 ternary doubles only its own else arm.

## What makes the rest impossible

Two rules decide it, both stated over the AST:

1. Same atom, same value. The same expression, read twice with nothing
   between that could change its inputs, gives the same truth value
   both times.
2. Short-circuited away is unread. An operand that short-circuits away
   is never read, so it puts no constraint on a later read of the same
   atom.

A path whose atoms are given contradictory values is impossible. In
price:

    gift:   L47 gift F => L52 gift F;  T,F,F => T     6 -> 4
    pickup: L44 pickup T/F => L53 same; when
            total>100 is true pickup is unread (rule 2)  6 -> 4
    feasible <= 1 + 3*4*2*4*4 = 385

So at least 480 of the 862 missed paths can never run. The machine's
`ways()` already splits paths by contradictions among `stable_names`,
but finds none here, because each repeated atom is a call,
`order.get(...)`.

Rule 2 only limits rule 1. On its own it marks no path impossible, so
it is built as part of rule 1, never apart from it.

## Rule 1 is the hard one

"Nothing between could change it" is rarely provable. Real atoms are
object references, which must be assumed mutable, and any call between
two reads may mutate them. Even the gift case assumes
`order.get("wrap")` and `user.get("member")` leave `order` alone.
`total > 50` and `total > 100` do not qualify at all, as `total` is
assigned between them.

The direction of failure decides the design. A possible path reported
as impossible hides a real gap, the error that must never happen. A
path left as missed when it is in fact impossible only costs a test
that cannot be written. When in doubt, a path stays possible.

## A repeated query is a smell

A query, eg `order.get("gift")`, read twice in one method is suspect
code in itself: it should be read once. So the tool can report it
outright:

    order.get("gift") read at L47 and L52: read it once, into a local

Once it is a local, never assigned between its reads, rule 1 needs
only the method's own assignments, which the AST shows. The caveat
left: the truth value of a mutable object, eg a list, can still change
through a call between the reads.

An exclusion that rests on an assumption is recorded with it, eg
"impossible if nothing between L47 and L52 mutates `order`", and shown
apart from the proven ones, never silently dropped.

## See also

- notes/combined-is-path-coverage.md: impossible paths are dropped
  from path coverage and reported as their own diagnostic.
- notes/path-budget-ratchet.md: the multiplied count as a metric.
- ../ruby/notes/impossible-combined-paths.md: stable leaves, and the
  oracle that checks the listed ways against the ways taken.
- ../ruby/notes/unreachable-facts.md: developer-stated facts, checked,
  never trusted.

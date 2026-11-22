# The path count as a ratchet

A direction, from 2026-11-09. Not built yet.

## The idea

Path explosion is the usual case against path coverage: decisions in
sequence multiply, so a modest method, eg `price()` in
demo/source/shop.py, has 865 paths (notes/price-865-paths.md). The
direction here is to let the multiplication show, as the metric, and
use it to force smaller, simpler methods.

## Extracting a method turns a product into a sum

Each method's paths are counted on its own flow, and paths from
different calls never mix (notes/witness-principle.md). So moving a
run of decisions into a method of its own, even one called from only
one place, replaces their product in the caller by their sum across
flows. A rough split of price:

    _discount  L38..L43   3*4      12
    _shipping  L44..L46   3*2       6
    _gift      L47..L52             6
    price      raise, pickup        3
    total                          27   vs 865

The cost: the tool no longer demands tests for combinations across
the helpers. That is right when the boundary is honest, ie the helpers
really are independent, and wrong when they share state the split
hides.

## A budget, nudged up

- Set a lowish per-method path budget to begin with. Code written to
  it, by a dev or by Claude, reaches full path coverage easily.
- Nudge the budget up over time. A higher budget allows bigger
  methods, but full coverage of them needs more tests, which take
  longer to run. Where to sit is a trade-off, chosen per codebase.

## An uncoverable path forces a rewrite

Tests are cheap for Claude to write. So a method it cannot bring to
full path coverage is strong evidence of a design problem. That is
evidence, not proof: the path is either impossible, or possible but
hard to set up, eg it needs a failing dependency. Either way the fix
is a rewrite:

- impossible: usually duplication, eg a repeated query
  (notes/price-865-paths.md); removing it removes the path.
- hard to reach: a missing seam; extract or inject so a test can
  reach it.

The guard: the rewrite keeps behaviour, its existing tests still
passing. Deleting the check that made a path hard to cover is no fix.

## Prior art

Counting paths per method is close to NPath complexity (Nejmeh,
1988), which Checkstyle and PHPMD already cap at a threshold
(../ruby/notes/complexity.md). What is new here is requiring each
counted path to be witnessed by a test, not only capping the count.

## Impossible paths stay vital

An impossible path can never be witnessed, so while the tool lists
one as missed, 100% is out of reach and the budget cannot be met
honestly. Finding impossible paths, and reporting them apart
(notes/combined-is-path-coverage.md), is what makes the ratchet fair.

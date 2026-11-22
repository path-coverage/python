# TODO: open decisions after the Ruby port

## Preamble

python/ took the principles of Ruby commits 43bcb77..8217215 (Ruby
repo, `git log -p 1959981..8217215`):

- "Does this code leave the function?" is decided once, from the
  AST, in `src/path_coverage/leaving.py`. Every reader uses that
  answer: manifest (`Arm.leaving`), decision_tree and fold_rows (the
  arm's `"leaving"` key), and method_statements. The regexes in
  fold_rows.py and card_ways.py are gone.
- An arm leaves if any of its statements returns or raises. An `if`
  inside the arm does not count.
- `manifest.irrefutable()` is the one answer to "does this pattern
  match anything?", and `manifest.left_open()` the one answer to "can
  this match be left with no case taken, its evaluation still open?",
  for code_map's marks and the rewrite's records alike.
- `test/property/` is a seeded generator of small functions. Its
  test checks that each function behaves the same imported plainly
  and under path coverage.
- `test/suites.py` defines the suites all, core and property. It is
  used by `bin/test.sh --suite NAME` and `make test_core`.

These changes were made on main from base 4013a4b; check `git log`
for whether they are committed yet. The last `bin/test.sh` printed:

    Required test coverage of 100.0% reached. Total coverage: 100.00%
    378 passed in 460.70s (0:07:40)
    code:
      Paths alone: 1190 / 1190 (100.00%)
      Paths combined: 1651 / 1651 (100.00%)
    test:
      Paths alone: 119 / 119 (100.00%)
      Paths combined: 219 / 219 (100.00%)

Numbers below marked "ran" came from running the gem on the example,
against the working tree's src and against HEAD's src. Numbers marked
"inferred" were read from the code, not run.

## 1. METHOD_MODE_CHOICES item 11 lists tops no row can have

Current state:

- `src/path_coverage/method_statements.py:249` `_Rows.rows` keeps only
  nodes that are a decision or for which `leaving.word(node)` is
  truthy.
- `_row` (line 390) gives a non-decision row the top
  `leaving.word(node)`, which is "return" or "raise".
- The KEYWORDS table (`for`, `while`, `with`, `try`, `def`, `class`,
  `=`) and the `()` and `value` tops were computed and then thrown
  away by that same filter, so they are deleted.
- METHOD_MODE_CHOICES.md lines 54-61 (item 11) still list those tops.
  It cites tests b47e3a01, b47e3a13 and b47e3a19, which do not exist,
  at base 4013a4b or now. Only b47e3a02 exists; it asserts the tops
  ["raise"] and ["return"].

Example:

    def ship(order):
        box = order.pack()
        for item in order.items:
            box.add(item)
        return box

What the dev sees (inferred from the code; the same at base 4013a4b
and now):

- One row, `return`, 1 path. There are no `=`, `for` or `()` rows.
- Paths alone has no paths at all; Paths combined 1 / 1 after one
  call.

Options:

- A. Rewrite item 11 to match the code: "Any other row is a statement
  that leaves the function; its top is leaving's word for it, return
  or raise (b47e3a02)." Drop the citations of tests that do not
  exist. No code or test change.
- B. Make item 11 true by showing every statement as a row. This is a
  large visible change:
  - every statement gets a reach call;
  - card sizes and Paths combined grow by one for each statement;
  - many tests in test_method_statements.py, test_listed_cards.py and
    test_kernel.py (the cards and totals of e5a70c01 and others)
    change.
  It also contradicts README "Methods", which says such statements
  are no rows.

Recommendation: A. The code, the README and the tests already agree
that only decisions, returns and raises are rows.

Verify: a docs-only change under A. Run `make test` to confirm
nothing cites it.

## 2. Python has no `make all`; only `test_core` exists besides `test`

Current state:

- python/Makefile:
  - line 1: `.PHONY: test test_core demo`;
  - line 9: `test` runs `bin/test.sh` (suite all) and is the default
    target;
  - line 14: `test_core` runs `bin/test.sh --suite core`.
- There is no `all`, `lint` or `test_check`.
- The property suite runs only as `bash bin/test.sh --suite property`.
- In Ruby, `all: lint test test_check` is the pre-commit gate, and
  `make all` is a single run of everything.

Example: a dev used to Ruby types `make all` in python/ and gets "No
rule to make target `all'" (inferred, not run).

Options:

- A. Add `all: test` (and `all` to .PHONY), so `make all` is the same
  single run of everything as in Ruby. Optionally add
  `test_property: bash bin/test.sh --suite property`. No test
  changes.
- B. Leave it. `make test` stays the gate, and README "Development"
  already names `make test` and `make test_core`.

Recommendation: A, with test_property. It keeps the two repos' entry
points the same at a cost of a few lines. Python has no lint or
test_check to chain, so `all` is just `test`.

Verify: `make all` prints the same summary as `make test` (378
passed, 100%). `make test_property` prints its pass count and no
totals.

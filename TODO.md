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
- `manifest.irrefutable()` and `manifest.matches_anything()` are the
  one answer to "does this case match anything?", for the manifest
  and the rewriter alike.
- The rewrite compiles exactly when the source does.
- `test/property/` is a seeded generator of small functions. Its
  tests check that each function behaves the same imported plainly
  and under path coverage, and that the rewrite compiles exactly when
  the source does.
- `test/suites.py` defines the suites all, core and property. It is
  used by `bin/test.sh --suite NAME` and `make test_core`.

These changes were made on main from base 4013a4b; check `git log`
for whether they are committed yet. The last `make test` printed:

    183 passed in 10.44s
    Required test coverage of 100.0% reached. Total coverage: 100.00%
    code:
      Paths alone: 540 / 540 (100.00%)
      Paths combined: 812 / 812 (100.00%)
    test:
      Paths alone: 24 / 24 (100.00%)
      Paths combined: 67 / 67 (100.00%)

`make test_core`: 181 passed, all 100%.
`bash bin/test.sh --suite property`: 2 passed, with no coverage check.

Numbers below marked "ran" came from running the gem on the example,
against the working tree's src and against HEAD's src. Numbers marked
"inferred" were read from the code, not run.

## 1. Irrefutable patterns other than `_` drop the "nothing matched" path

Current state:

- `src/path_coverage/manifest.py:290` `irrefutable(pattern)` follows
  CPython's rule. A pattern matches anything when it is:
  - `_` or a bare name;
  - an as-pattern of an irrefutable pattern (`_ as y`, `(n as y)`);
  - an or-pattern with an irrefutable alternative (`2 | _`).
- `manifest.py:306` `matches_anything(case)` is true when the case has
  no guard and an irrefutable pattern.
- `manifest.py:313` `_pattern_leaf` marks such a pattern's leaf
  "truthy" only.
- `src/path_coverage/rewriter.py:166` `visit_Match` uses
  `matches_anything`:
  - at line 179 (`open_ended`) to decide whether to append the
    "unmatched" case;
  - in the guard loop, to leave a non-last catch-all case unguarded,
    so invalid code stays invalid.
- At base 4013a4b, only a bare `_` or a bare name counted as
  irrefutable.

Example:

    def size_of(order):
        match order:
            case 1:
                return "one"
            case 2 | _:
                return "many"

called as `size_of(1)` and `size_of(5)`.

What the dev sees (ran, both versions):

- Base 4013a4b:
  - match row: 3 paths, 2 taken; card ways 3.
  - Gap line:

        example.py:2:4 path never taken: `1` false, `2 | _` false

  - Paths alone 2 / 3 (66.67%); Paths combined 4 / 5 (80.00%).
  - Fold: columns [0, 1, 1]; row `1` F T F; row `2 | _` F, blank, T.
- Now:
  - match row: 2 paths, 2 taken; card ways 2.
  - No gaps.
  - Paths alone 2 / 2; Paths combined 4 / 4.
  - Fold: columns [1, 1]; row `1` T F; row `2 | _` blank, T.

Options:

- A. Keep the current rule (CPython's). Totals drop by one path for
  each match whose last case is such a pattern. That path can never
  be taken, so its gap can never close. No test changes.
- B. Go back to bare `_` or name only. The gap that cannot close
  comes back.
  - Change `test/test_manifest.py::test_5c1e9a13` to expect
    [None, None, None, None].
  - Remove the README text at README.md ~250 ("A last case with no
    guard whose pattern Python finds irrefutable ...").
  - `rewriter.visit_Match` again appends an unmatched case after
    `2 | _:`. That is harmless, as the case is unreachable.
  - `test_rewriter.py::test_7e40b312` passes either way (inferred:
    only the guard loop matters there).

Recommendation: A. README.md already says that reporting a gap that
can never be closed is an error, and Python itself treats these
patterns as matching anything.

Verify: `make test tids='5c1e9a13 7e40b312 e5a70c19'`, then
`make test`.

## 2. METHOD_MODE_CHOICES item 11 lists tops no row can have

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

## 3. Rows inside a match's cases are placed at the card's top

Current state:

- `manifest.py` `visit_Match` (line 114; Condition built at line 131)
  makes `Condition("match", clauses)`. Its operands are pattern
  Leafs, or `Condition("case", (pattern, guard))`. There are no Arm
  operands, so a case body has no extent and no `leaving`.
- `src/path_coverage/card_tree.py:117` `_arm_regions` and `:130`
  `_arm_region` make regions from Arm operands only. So `nested`
  (:41) and `_placed` (:65) find no region holding a case body's
  rows, and every such row is placed at the top (parent None).
- `card_ways` (`_Fold.pair_on`) then puts those rows one after
  another after the match, so a case's return looks like it ends
  every path.
- `fold_rows.rows` (`src/path_coverage/fold_rows.py:31`) shows no
  `leaves` row for a case that returns.
- `method_statements._arms_of` (:407) lists case statements as rows
  after the match (METHOD_MODE_CHOICES item 2, test b47e3a24), so the
  rows exist; only their nesting is lost.

Example, and the same logic written with if/else:

    def grade(score, bonus):          def grade(score, bonus):
        match score:                      if score == 1:
            case 1:                           return "low"
                return "low"              else:
            case _:                           if bonus:
                if bonus:                         return "high"
                    return "high"         return "mid"
        return "mid"

called as (1, False), (2, True) and (2, False).

What the dev sees (ran, current src):

- match form:
  - card ways 2 (wrong: there are 3 ways, low, high and mid).
  - tree: rows 2:4, 4:12, 6:12 and 8:4 all have parent None; only
    7:16 nests, in the inner if.
  - match fold: columns [1, 2]; rows `1` T F and `_` blank, T. No
    `leaves` row.
- if form:
  - card ways 3.
  - tree: 3:8 in 2:4 then [0]; 5:8 in 2:4 else [1]; 6:12 in 5:8
    then [0].
  - The outer if's fold has a `return` leaves row.
- Both forms: Paths alone 4 / 4; Paths combined 7 / 7. Totals add up
  row paths, so nesting does not change them.

Options:

- A. Leave it. The totals are right, but the card's ways and tree are
  wrong for matches.
- B. Give each case an extent and a `leaving`, so card_tree can place
  rows inside the case that holds them. The case's paths are those
  that took it: its pattern true, and its guard true where it has
  one.
  - One way adds an Arm (extent = the case body, leaving =
    `leaving.of(case.body)`) to each clause in `manifest.visit_Match`.
    That touches `decision_paths`, `decision_tree._node` and
    `src/path_coverage/kinds/case.py` (not yet read).
  - A lighter way keeps the Condition as it is and adds a case-region
    table that `card_tree._regions` reads.
  - Tests:
    - new tests in test/test_card_tree.py (the match example above)
      and test/test_card_ways.py (ways 3);
    - test_manifest.py match expectations change if clauses gain
      Arms;
    - test_decision_folds.py::test_7d61a401 and test_decision_tree.py
      may change if arms appear in folds;
    - test_kernel.py tests whose JSON "tree" or "ways" holds a match
      (e5a70c19 asserts only taken paths, so it is unaffected).
  - A visible card change: the fold may gain per-case `leaves` rows.

Recommendation: B, with the region-table variant first. It fixes ways
and nesting without changing any decision's paths or the JSON paths
format, and it leaves the question of fold rows per case to a
separate choice.

Verify: new card_tree and card_ways tests, then `make test` and
`make test_core`. Rerun the comparison: the match form's ways must
equal the if form's (3).

## 4. Python has no `make all`; only `test_core` exists besides `test`

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

Verify: `make all` prints the same summary as `make test` (183
passed, 100%). `make test_property` prints 2 passed and no totals.

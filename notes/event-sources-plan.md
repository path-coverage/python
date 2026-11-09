# Plan: two event sources behind one interface

Status (2026-11-08): steps 1 to 5, 6.1 (while) and Q1 (Python) are
done; 6.2 (Handled) is not started. See "Status" at the end.

Events reach `Evaluations` from either sys.monitoring or a source
rewrite, chosen at run time. Each source translates its own raw events
into the shared actions on its own side, so bytecode quirks never leak
into the interface. Running both on the same tests is an oracle: their
ways must match.

The two modes are not mutually exclusive. Rewrite mode does all the
work itself. Monitoring mode does what bytecode gives it, and borrows
the rewrite's instrumenter only for the gaps it has to fill, as it
already borrows `wrapped_leaves` for the leaves no branch tests. One
table, decided in one place, says which source gives each action kind
in each mode:

    action kind      rewrite mode   monitoring mode
    Outcome          wrap           bytecode, + wrap (literals)
    Reach / Enter    record stmt    bytecode / PY_START
    Pass/Exhausted   wrap iterable  bytecode (for), + wrap test (while)
    Matched ...      record stmt    bytecode
    Handled          record stmt    record stmt (borrowed)

## 0. What the code holds

- The interface exists: `evaluations.note(frame_id, actions)`. The
  actions are Enter, Outcome, Matched, Opened, Unmatched, Begin, Item,
  Answer, End, Reach, Pass, Exhausted and Unwalked. `wrapped_leaves`
  and `monitor` both feed it. `kernel` calls
  `monitor.instrument(text, ...)`, which gives `(code, record)`.
- `code_map` is two things: `Source` (pure AST facts) and `tables`
  (bytecode to actions).
- Commit 8cee2dc moved from a rewrite to monitoring: "Rewriting each
  covered file risked changing the program it measured".
  Rewrite mode (`rewrite.py`) is that rewriter's successor; e3f1a702
  checks it against monitoring mode.
- Ruby rewrites with leaf wraps plus inserted reach statements
  (`PathCoverage.reach(name); `). It records no run-time ways.
- A hazard in `wrapped_leaves`: `record` calls `bool(value)`.

      if x:          __bool__ runs 2x wrapped, 1x plain
      y = 1 and x:   1x wrapped, 0x plain; a numpy-like x raises

## 1. What a rewrite may insert

This step answers 8cee2dc. A rewrite may insert only:

- a. a call wrapping an existing expression, which returns it;
- b. a record statement before a statement (after any docstring or
  `from __future__`), as Ruby's reach does.

Nothing else: no added clauses (no `case _:`, no `else:`), and no
reordering. Property tests over the generated sources and the repo's
own sources check that:

- the rewrite parses exactly when the source parses;
- stripping each (a) to its argument and dropping each (b) gives an
  equal `ast.dump`;
- the spy trace equals the plain run's (b61d3f01, under both sources);
- traceback line numbers are equal, and so is `__doc__`.

## 2. Interface cleanup first

These are pure refactors, and the tests stay green throughout.

1. `Source` moves out of `code_map` into its own module, and
   `code_map` keeps only the bytecode.
2. Unwalked goes. It is an artifact of PY_START frame-id reuse.
   Options:
   - a. each record key knows its owning def statically, and an event
     owned by another def ends a stale walk (picked);
   - b. compare `sys._getframe(1).f_code` with the walk's code;
   - c. keep Unwalked, and have the rewrite emit it too.
3. `notes/event-interface.md` says what each action means in source
   terms, and which source emits it where.

## 3. The switch

`PATH_COVERAGE_EVENTS=monitoring|rewrite` chooses the mode. `kernel`
calls `monitor.instrument` or the rewrite's, which has the same
signature. Each mode reads the table above to know which instrumenters
to run. The default stays monitoring until step 5 holds.

## 4. The rewrite source

Each action kind has its own instrumenter, so monitoring mode can
borrow it for a gap. Each kind also gets its own red test, which runs
a tiny example under both modes and asserts that the actions are
equal.

1. Outcome: every leaf is wrapped. In a test position (if, while,
   assert, not, filter, guard) `record` returns `bool(value)`, so
   `__bool__` runs once.
2. Reach: a record statement before each return and raise.
3. Enter: a record statement first in each def body.
4. Pass and Exhausted (for, inlined comprehensions): the iterable is
   wrapped, as in `for x in __pc__.items(k, xs)`. That gives an
   iterator noting Pass for each item and Exhausted at the end.
5. Match:
   - the subject is wrapped (Opened);
   - a record statement goes first in each case body (Matched);
   - one goes after the match (Unmatched), which `unmatched()`
     already ignores when a case was taken.

   Guarded cases need a spike, and three options, before choosing.
6. `any`/`all` of a genexpr is the hardest: the element runs in the
   genexpr's own frame. A spike comes first.

## 5. Parity

The two modes are compared on decision_paths, reached and ways. A
difference can only come from a cell of the table where monitoring is
native, as a borrowed cell runs the same instrumenter in both. They
are compared
over the 120 property seeds, the spy oracle, self-coverage and the
demo. Each difference is either fixed or pinned by a test as a known
gap.

## 6. What only the rewrite can give

The machine already has these forks.

1. while: the test is wrapped. True gives Pass, and false gives
   Exhausted.
2. except: a record statement first in each handler's body gives a
   new action, Handled. That makes a called function raising into the
   method's own handler visible. Modelling it in the machine stays a
   later decision.

## 7. The user's call

Which source is the default, and whether monitoring stays.

## Answered

- Q1. In `y = flag and grid`, Python never tests the truth of `grid`.
  The aim is useful path coverage, not perfect path coverage: a fork
  exists only where control actually forks. A last operand whose
  value is used is evaluated or not, and nothing more, so it has no
  outcome, no wrap and no `bool` call:

      y = flag and grid      2 paths: flag F | flag T (grid evaluated)
      if flag and grid:      3 paths, as the if tests grid

  This changes the decision counts in Python and in Ruby.
- Q3. Record statements (1b) are allowed: a record statement only,
  which the strip-and-compare check drops.
- Q2. Reports measured in different modes are refused at merge, as
  reports from different tool versions are.
- Q1's change comes after parity (step 5), in Python only, as a step
  of its own.

## Status

- `source_map.py` holds the AST facts; `code_map.py` only bytecode.
- Events are keyed `(id(frame), id(code))`, so Unwalked is gone.
- `inserted_records.py` inserts every record, by `INSERTS[mode]`;
  `monitor.py` and `rewrite.py` are the two modes; `kernel.INSTRUMENTS`
  picks one by `events=` or `PATH_COVERAGE_EVENTS`. Reports carry
  `"events"`, and render refuses another mode's.
- Parity: e3f1a702 (120 generated functions, paths, reaches and ways)
  and e5a70c38 (a kernel run) hold. Self-coverage in both modes agrees
  on every decision's paths; the counts differ only as
  `event-interface.md` explains.
- 9d2b6a03 and 9d2b6a04: each mode's records compile exactly when the
  source does, and stripped out leave every generated function and every
  repo file's parse as it was. 4a8c2e0e: traceback lines unchanged.
- while: rewrite mode only (4a8c2e0f checks its ways are machine
  paths).
- Q1 (Python): `manifest._decides` keeps a last and/or operand as a
  leaf only when its truth decides a branch (an if, while or assert
  test, a conditional expression's test, a filter, a guard, a block
  generator), through and/or, walrus, not and conditional arms.
  5c1e9a14 and 7b3d910b pin it. Fixtures about and/or paths test their
  and/or with assert. Ruby keeps the old counts.
- Differential oracle: monitoring mode and rewrite mode check each
  other (e3f1a702), the only differential oracle.
- Not started: 6.2 Handled.

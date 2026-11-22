# <img src="https://avatars.githubusercontent.com/u/353243247?v=4" alt="" width="32" height="32"> path-coverage/python

- [Overview](#overview)
- [Getting started](#getting-started)
- [Use when you cannot edit the code!](#use-when-you-cannot-edit-the-code)
- [What a run reports](#what-a-run-reports)
  - [Decisions](#decisions)
  - [Methods](#methods)
  - [Reporters](#reporters)
- [How it works](#how-it-works)
- [Roadmap](#roadmap)
- [Constraints](#constraints)
- [Development](#development)

Path coverage for Python, to run alongside coverage.py's line and branch
coverage.

## Overview

A *decision* is a choice in your code, eg an `and`, `or`, `if` or
`match`. Each way it can go is a *path*. For example

```python
def discount(member, coupon):
    return 10 if member or coupon else 0
```

has three paths: a member, a non-member with a coupon, and neither. Tests
calling `discount(True, None)` and `discount(False, None)` cover every line
and both branches of the conditional, yet no test ever tried a coupon.

Line and branch coverage can be 100% while a path was never taken.
path_coverage counts how often each path was taken: alone, each decision's
paths on their own, and combined, through each function's statements.

As the run exits it writes its report:
- `path_coverage.json`, for AIs and other tools.
- `path_coverage.source.json`, what drawing each file's code needs.

## Getting started

From code, before any covered module is imported:

```python
import path_coverage

path_coverage.start(
    root="/app",                       # cover globs and decision names are relative to it
    cover=["src/**/*.py"],             # each matching module is instrumented as it is imported
    skip=["src/migrations/**/*.py"],   # except these, though a cover glob matches them
    coverage_dir="/tmp/coverage",      # where path_coverage.json is written
    report=["gaps", "summary"],        # the reporters run at exit (default ["gaps"])
    groups={                           # optional: each group's own summary and totals
        "models": ["src/models/**/*.py"],
        "routes": ["src/routes/**/*.py"],
    },
)
```

An unknown reporter is refused by name, with the list of the ones there
are. A file matching any `skip` glob is neither instrumented nor reported.
A group's globs are relative to `root`, as cover globs are; a file can be
in several groups, or in none.

A cover glob can end in `::` and a qualname, the names of a def or class
from the module down joined by dots, eg `src/orders.py::Order.ship`. Only
that scope is measured: code outside it runs as plain Python, with no
events and nothing wrapped, and the totals, gaps and summary count
only its decisions and flows. A def nested in the scope is part of it,
as are both defs of a property's getter and setter, which share a name.
Every file the glob matches must hold the qualname, or `start` refuses
the cover, naming the file and the first name missing:

    cover 'src/orders.py::Order.post': class Order in src/orders.py has no post

`PATH_COVERAGE_COVER` takes the same form, eg
`PATH_COVERAGE_COVER=src/orders.py::Order.ship`.

`start` refuses any setting that would quietly measure less than asked,
including a stray comma in a `PATH_COVERAGE_*` list:

    cover 'src/orders.py:Order.ship' matches no file

With pytest, from the environment alone:

```sh
export PATH_COVERAGE_ROOT=/app
export PATH_COVERAGE_COVER=src/**/*.py,lib/*.py   # comma-separated
export PATH_COVERAGE_SKIP=src/migrations/**/*.py  # optional, comma-separated
export PATH_COVERAGE_DIR=/tmp/coverage
export PATH_COVERAGE_REPORT=gaps,summary          # optional, default gaps
export PATH_COVERAGE_GROUPS=models:src/models/**/*.py,routes:src/routes/**/*.py
python -m pytest -p path_coverage.pytest_plugin test/
```

`PATH_COVERAGE_GROUPS` is optional: comma-separated `name:glob` pairs, a
name given twice getting both globs.

The plugin starts before any conftest is imported, and does nothing when
`PATH_COVERAGE_COVER` is not set. Under pytest-xdist each worker writes a
part, `path_coverage.gw0.json` and so on, and the controller adds every
part's counts to its own report, so the gaps are those that every worker
left.

The plugin counts each test's setup, call and teardown under the test's
node id. In `path_coverage.json` every count of what the run did is a
tally by test, eg a path's:

```json
{ "path": [true, false], "tests": { "ebded4bbf7ae": 2, "9a8e6a205ed4": 1 } }
```

Each key is the first 12 hex digits of the sha256 of a test's node id,
and the report's `tests` names each key's test, `(no test)` being what
ran between tests, eg a module's import. So a reader can tell which
tests take which paths, eg to find the fewest tests that keep each of a
function's paths taken. Another test runner marks its tests itself:
`path_coverage.testing(test_id)` as each test starts, and
`path_coverage.testing(path_coverage.tally.NO_TEST)` as it ends.

## Use when you cannot edit the code!

A run whose own files are thrown away, such as one in a `docker build`
step, can send its report to a collector instead:

```sh
export PATH_COVERAGE_COLLECTOR=http://host.docker.internal:4570/runs
```

With a collector the reporters default to `post`. The package's
`path_coverage_collector` command (or `python -m path_coverage.collector`)
is that collector. It saves each report POSTed to it as a numbered file;
once every run is done, report them as one with `path_coverage_report`,
below.

```sh
path_coverage_collector 4570 /tmp/paths/runs   # until sent TERM
```

- A report is saved before it is answered 200, so a 200 means it is on
  disk. A report cut short, eg by a sender dying mid-send, is answered 400
  and not saved. One that cannot be saved is answered 500.
- `GET /alive` answers 200 while the collector runs.
- `GET /ready` answers 200 when its dir is writable, 503 when not. Wait for
  it before starting the runs.
- On TERM it stops accepting connections, finishes the report in hand, and
  exits 0.

### Reporting saved runs

Once every run is done, report them as one with `path_coverage_report`:

```text
path_coverage_report [--loops] [--max-paths N] SOURCE_ROOT GLOBS REPORT_DIR RUN_JSON...
```

- SOURCE_ROOT  the directory holding the covered source
- GLOBS        comma-separated globs of the covered files, relative to SOURCE_ROOT
- REPORT_DIR   the directory it writes its report into
- RUN_JSON...  one or more saved runs' JSON files, space-separated, eg runs/*.json
- --loops      count each loop as a decision: 0 items or 1+ items
- --max-paths  fail each function with more than N paths (default 4096, at most 65536)

It exits 0 when every path is taken, and 1 when any is not.

Every path taken:

```text
$ path_coverage_report /app 'src/**/*.py' report runs/*.json
Paths: 2 / 2 (100.00%)
Functions over --max-paths=4096: 0
```

Some paths untested, and a function over --max-paths:

```text
$ path_coverage_report --max-paths 8 /app 'src/**/*.py' report runs/*.json
src/orders.py:1 total() has 1 untested path.
Add tests that take each of these paths:
  1. line 4 `order['paid']` false
src/orders.py:9 fee() has 16 paths, more than --max-paths allows.
Split it into smaller functions.
Paths: 1 / 2 (50.00%)
Functions over --max-paths=8: 1
```

Each run's JSON names the kinds of decision it measured. A version that
measures other kinds lists a decision's paths differently, so a run whose
kinds differ from those of the installed version is refused.

### Not analysing a block

Sometimes a block of code is not worth testing path by path, for example
logging. Put `# path: disable` before the block and `# path: enable` after
it. The lines between them still run, but they are not analysed: any
decision in them is ignored, and they add no paths to the function they
are in.

The line straight after `# path: disable` must start with `# reason:` and
say why the block is not analysed:

```python
def ship(order, log):
    if order['express']:
        order['days'] = 1
    # path: disable
    # reason: logging is not under test
    if log.verbose:
        log.lines.append(order['id'])
    # path: enable
    return order
```

Without the `# path: disable` and `# path: enable` comments, `ship()` has
4 paths: each `if` can be true or false. With them, the second `if` is
ignored, so `ship()` has 2 paths: `order['express']` true, and
`order['express']` false.

Only a real comment that is the whole of its line is a marker. The same
text inside a string, eg a docstring or help text, is just text: it
disables nothing, and is never refused.

```python
HELP = """
# path: disable
"""   # a string, not a comment: fee() below is still analysed
```

Each of these is refused, with the file and line it is on:

- a `# path: disable` without a `# reason:` line straight after it
- a `# path: disable` without a `# path: enable` after it
- a statement that starts between the two comments and ends after the
  `# path: enable`

## What a run reports

As the process exits (or, under the pytest plugin, as pytest finishes):

- `path_coverage.json` and `path_coverage.source.json` are written to
  `coverage_dir`. Their keys, with examples, are in
  [path-coverage/schemas](https://github.com/path-coverage/schemas#path_coveragejson).
- `gaps` prints one line per decision path never taken, in manifest order,
  naming the outcome of each leaf on it:

```text
src/kata.py:3:11 path never taken: `ok(id)` true, `new(id)` false
src/kata.py:4:11 never reached
```

### Decisions

A decision is named by the `path:line:column` where it starts: the path relative
to `root`, the line 1-based, the column 0-based, in characters, as an editor
shows it. A decision in a covered file the run never imported is still
reported, as `never reached`.

A path is the outcome of each leaf one evaluation of the decision reached, in
order; a leaf that short-circuiting skipped is not on it. Each leaf is quoted
as a Markdown code span, on one line, its fence one backtick longer than any
run of backticks inside it.

A decision is an outermost condition. Its leaves are numbered across the whole
of it, nested conditions included:

```python
ok(id) and new(id) and len(id) == 6       # one `and` decision, leaves 0 1 2
ok(id) and (new(id) or len(id) == 6)      # an `or` nested in an `and` decision, 0 1 2
ok(id) and new(id) or len(id) == 6        # an `and` nested in an `or` decision, 0 1 2
any(k and k.ok for k in ids) and ok(id)   # three decisions: the and, the any, and k and k.ok
"ok" if ok(id) else "no"                  # a conditional expression decision, its predicate leaf 0
new(id) or big(id) if ok(id) else "no"    # one decision: predicate 0, then arm 1 2
[u for u in us if ok(u) and new(u)]       # a filter decision, named at its if: 0 1
```

A conditional expression is a decision even when its predicate is a single
leaf. Its predicate's leaves come first, as it is evaluated first. An arm
holding an `and`, an `or` or a conditional expression is part of its decision,
its leaves numbered after the predicate's, so the decision's paths run through
whichever arm the predicate picks. Any other arm is not part of it, though a
condition inside it is a decision of its own.

An `if` statement is a decision too, even when its predicate is a single leaf,
named at its keyword: its predicate nests in it, an `and` there being no
decision of its own, and its arms are plain, as they are statements. An `elif`
is a decision of its own, named at its keyword.

A comprehension's filter is a decision too, named at its `if` keyword. Its test
nests in it, as an `if` statement's predicate does. True keeps the item and
false drops it.

A `match` statement is a decision, named at its keyword. Each case's pattern is
a leaf, true when it matches. A guard is reached only when its pattern
matches, and its leaves follow the pattern's. A later case is reached only
when no earlier case was taken. When no case is taken, every pattern
reached is false, and that is a path of its own. A last case with no guard
whose pattern Python finds irrefutable, eg `_`, a bare name, `_ as size` or
`2 | _`, matches anything, so no path ends with nothing matched; a guarded
one, eg `case _ if big:`, does not.

```python
match order.kind:
    case "gold" if order.big:   # leaf 0 the pattern, leaf 1 the guard
        return 1
    case "silver":              # leaf 2
        return 2
```

A call of `any` or `all` with a generator is a decision, named where the call
starts. Its first leaf is how many items the generator gave: 0, 1 or 2+.
Its second is the generator's last answer, where the call stopped. So
`any(o.late for o in orders)` has five paths. With 0 items there is no
answer. With 1 item or with 2+, the last answer is true on one path and
false on the other. Nothing else is evaluated, not even `len(orders)`.

A module can bind `any` or `all` itself, eg with `from flags import any`.
A call of a name the module binds is a leaf only, as it may not be the
builtin. So is `any(flags)`, whose items have no answer to note.

A leaf whose form allows one outcome only needs only to be evaluated: a path
needing its other outcome is impossible, not a gap. `None`, `False`, `0`,
`''` and empty displays (`[]`, `{}`, `()`) can only be falsy; other
literals, displays holding an item that is not an unpacking (`[None]`, but
not `[*xs]`), lambdas, and f-strings holding literal text can only be
truthy. Calls and names are left open, even `Config()` or `DEFAULT`, since a
class can define `__bool__` or `__len__` and a constant can hold an empty
value; reporting a gap that cannot be closed is the lesser error than hiding
one that can.

```python
tags = record.get("tags") or []   # leaf 1: never evaluated, or no gap
```

### Methods

Each function has a flow, named by the `path:line:column` of its `def`,
with a row for each statement that shapes its paths: each decision, and
each `return` or `raise`, which ends a path. Any other statement, eg
`x = 1`, runs exactly when what holds it does, so is no row. A nested
`def` has a flow of its own, as its body runs only when called. A
decision's row counts its paths; a `return` or `raise` row is one path,
taken when it is reached. A function's total adds up its rows. A file's
decisions outside every function get a flow for each span of their
lines.

The JSON report's `flows` hold each flow's rows, its `ways` and its
`calls`, and its `tree` says how those rows nest.

### Reporters

- `gaps` prints the gap lines, as above.
- `ways` prints, for each function with a path through it that no run
  took, the choices a test must make to take each one, every leaf by its
  source text; a loop is named by its line and how many items it ran:

```text
src/fee.py:5 fee() has 2 untested paths.
Add tests that take each of these paths:
  1. line 8 `user.member` true, `order.paid` false, then line 10 `order.big` true
  2. line 8 `user.member` false, then line 10 `order.big` true
```

  Every run writes these lines to `path_coverage.ways.txt` in the
  coverage dir, whichever reporters print, so a later check can show them.

- `summary` prints the totals, as coverage tools print theirs; a total
  with no path possible shows `(-)`:

```text
Paths alone: 41 / 52 (78.85%)
Paths combined: 90 / 116 (77.59%)
```

  With groups configured, each group is a heading with its own totals
  indented under it, and there is no total over every group.

- `post` sends the JSON report to the collector, never through a proxy,
  and gives up in silence on a collector it cannot reach within a second,
  so the run's own output and exit status stay as they are.

## How it works

A meta path finder, placed first on `sys.meta_path`, hands each covered
module to a loader that parses its source and wraps each leaf no branch
tells (`wrapped_leaves.py`, `manifest.wrapped` deciding which) in a call
that counts its outcome and returns it unchanged:

```python
x = p or q
# compiles as
x = p or __path_coverage__(1, q)
```

Those leaves are: the last operand of every `and`/`or`, which no branch
tests when its value is used, as here, in an f-string or as a call's
argument; a leaf whose form fixes its outcome, eg `0`, which Python
compiles to no test; and a leaf that is a conditional expression, whose
literal arm Python compiles to no test, eg `if a if b else True`. Nothing
else in the tree changes, each inserted node takes the location of the
leaf it wraps,
and the loader neither reads nor writes the bytecode cache. Every other
leaf's outcome comes from `sys.monitoring` (`monitor.py`), one source per
leaf: the module's code objects, nested functions, lambdas and generators
included, have their own events turned on, and no other code has any.

Before a covered module runs, `code_map.py` maps each of its code objects
once, from where Python says each instruction came from
(`co_positions`) and the file's own parse:

- each branch, left or right, gives the outcome of the leaf whose value
  its jump tests, and of each leaf holding it whose outcome that decides,
  eg an `if` whose predicate is an `and`; a chained comparison whose
  value an `and`/`or` tests again gives its outcome only there;
- an instruction marks where a `match` starts trying its cases, where a
  case's guard or body starts (its pattern matched), and where the match is
  left with no case taken; and where each return or raise starts; each at
  every copy Python makes of a small block, eg a body that only returns;
- a function's start counts its entry.

`any` and `all` of a generator Python 3.14 runs in the caller: its check
that `any` is the builtin begins the evaluation, its loop gives each item
and its end, and its test of each answer ends it when the answer decides.

Each callback looks up what its event means and logs it, by the id of the
frame it happened in; an event that means nothing is disabled where it
happened. `evaluations.py` rebuilds each evaluation from the log, in
order, keeping each frame's evaluation of a decision apart, so a leaf
that calls the function holding the decision, or a generator resumed in
another thread, does not mix two evaluations. An evaluation is complete
when its outcomes are one of the decision's possible paths, as the
manifest gives them.

## Roadmap

Decisions covered now: `and`, `or`, the conditional expression,
`if`/`elif`/`else`, `match`, comprehension filters, and `any` and `all`
called with a generator. Each function's flow has a row for every decision
in it, and for each return and raise, as each cuts a path short.

Next:

- `next()` with a generator and a default, eg
  `next((o for o in orders if o.late), None)`: whether it found an item or
  gave the default.
- `while` loop conditions, and assert statements.

## Constraints

- CPython 3.14 or later (`sys.monitoring`'s `BRANCH_LEFT` and
  `BRANCH_RIGHT` events, and how 3.14 compiles `any` and `all`).
- A module imported before `start` is not measured, and nor is the
  script run as `__main__`; all their decisions show as `never reached`.
- A wrapped leaf, eg the last operand of an `and`/`or`, has its truth
  taken once more by the call around it, so a leaf whose `__bool__` has
  side effects sees it called more often.
- Python 3.14 drops an instruction event at the start of a line once
  another tool, eg coverage.py, disables its own line event there, so
  path_coverage keeps a line event wherever it marks an instruction.
- Counts are kept per process; the at-exit report does not run on
  `os._exit` or an uncaught signal.

## Development

`bin/test.sh` runs the tests with the python in the repo's `.venv`
(override with `PYTHON=...`), writing nothing into this repo but its
self-coverage report. The collector's tests bind local ports. Make the
`.venv` once with:

```
python3 -m venv .venv
.venv/bin/pip install pytest
```

Every run measures path_coverage's own `src/` and `test/` with
path_coverage. The code measured and the tool measuring are the same
package in one process, so `test/self_coverage.py`, a pytest plugin that
`bin/test.sh` loads with `-p` before any test module is imported, copies
`src/path_coverage` into a temporary dir as `path_coverage_self`, renaming
the name its wrapped operands call (`__path_coverage_self__`), and starts
the copy, with groups `code` (`src/**`) and `test` (`test/**`), skipping
`test/projects/**` and the files the suite leaves out. Each claims a
`sys.monitoring` tool id of its own, so the tests start and stop
`path_coverage` as they always do, its finder in front of the copy's while
they run. The copy's finder sits in front of pytest's assertion rewriting,
so the copy's loader rewrites a test module's asserts as pytest would,
after its own wrapping. Code that runs inside a monitoring callback is
never itself monitored, by the copy or by coverage.py, so the tests call
`monitor`'s callbacks directly.

The report is written to `reports/paths/` (gitignored). A full run, with
no arguments, ends by printing each group's totals:

```text
code:
  Paths alone: 1138 / 1138 (100.00%)
  Paths combined: 1592 / 1592 (100.00%)
test:
  Paths alone: 118 / 118 (100.00%)
  Paths combined: 217 / 217 (100.00%)
```

`test/suites.py` is the one place that says which test files a suite
runs and measures, and whether its coverage is checked:

- `all`, every test (`make test`, the default).
- `core`, every test but the generated ones in `test/property`, neither
  run nor measured (`make test_core`): whether the hand-written tests
  alone reach full coverage.
- `property`, the generated tests alone (`bin/test.sh --suite property`),
  whose coverage, of only part of the code, is not checked.

`test/property` generates small functions from a seeded grammar, each
leaf a spy (a call of a parameter, `p0()`), a parameter read as a name, or
a literal, each statement preceded by `mark(n, t)`. Called with spies on
every combination of its leaves' values, each logs its leaves and
statements as they run: the trace is the path the call took. The tests
check that each function under path coverage returns or raises, and
traces, exactly as compiled plainly; that the paths of each decision, as
the oracle (`test/property/oracle.py`) derives them from the traces, and
the statements' runs, are those path_coverage.json counts; that the
records each events mode inserts compile exactly when the source does,
and taken back out leave the parse as it was; and, as a second opinion,
that each function's paths, statement runs and ways are counted exactly
the same in rewrite mode as in monitoring mode.

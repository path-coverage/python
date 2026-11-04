# path_coverage

Path coverage for Python, to run alongside coverage.py's line and branch
coverage. A Python mirror of the Ruby gem of the same name
(https://rubygems.org/gems/path_coverage).

```python
def fee(user, order):
    total = order.total
    if user.member and user.paid:
        total -= 5
    if order.total > 100:
        total -= 10
    return total
```

Two tests, a paying member with a big order and a non-member with a small
one, run every line and take every branch, so coverage.py reports 100%. Yet
they can still miss paths, at two scopes, and path_coverage lists each path
no test took.

## Within each decision

The first `if` can go three ways: member and paid, member and not paid, not
a member. A member who has not paid may never have been tried.

## Within each method

The two `if`s can go four ways together. A paying member with a small order
may never have been tried.

## Use

From code, before any covered module is imported:

```python
import path_coverage

path_coverage.start(
    root="/app",                       # cover globs and site names are relative to it
    cover=["src/**/*.py"],             # each matching module is instrumented as it is imported
    skip=["src/migrations/**/*.py"],   # except these, though a cover glob matches them
    coverage_dir="/tmp/coverage",      # where path_coverage.json is written
    measure=["decisions", "methods"],  # decisions alone unless methods is named
    report=["gaps", "html", "summary"],  # the reporters run at exit (default ["gaps"])
    groups={                           # optional: each group's own tab, summary and totals
        "models": ["src/models/**/*.py"],
        "routes": ["src/routes/**/*.py"],
    },
)
```

An unknown reporter or measure is refused by name, with the list of the ones
there are. A file matching any `skip` glob is neither instrumented nor
reported. A group's globs are relative to `root`, as cover globs are; a file
can be in several groups, or in none.

With pytest, from the environment alone:

```sh
export PATH_COVERAGE_ROOT=/app
export PATH_COVERAGE_COVER=src/**/*.py,lib/*.py   # comma-separated
export PATH_COVERAGE_SKIP=src/migrations/**/*.py  # optional, comma-separated
export PATH_COVERAGE_DIR=/tmp/coverage
export PATH_COVERAGE_MEASURE=decisions,methods    # optional, default decisions
export PATH_COVERAGE_REPORT=gaps,html,summary     # optional, default gaps
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

A run whose own files are thrown away, such as one in a `docker build` step,
can send its report to a collector instead:

```sh
export PATH_COVERAGE_COLLECTOR=http://host.docker.internal:4570/runs
```

With a collector the reporters default to `post`. The package's
`path_coverage_collector` command (or `python -m path_coverage.collector`)
is that collector. It saves each report POSTed to it as a numbered file, and
once every run is done they render as one report:

```sh
path_coverage_collector 4570 /tmp/paths/runs   # until sent TERM
```

```python
from pathlib import Path
import path_coverage

path_coverage.render(
    root="/app", cover=["src/**/*.py"], coverage_dir="/tmp/coverage",
    measure=["decisions", "methods"], report=["gaps", "html"],
    runs=sorted(Path("/tmp/paths/runs").glob("*.json")),
)
```

- A report is saved before it is answered 200, so a 200 means it is on
  disk. A report cut short, eg by a sender dying mid-send, is answered 400
  and not saved. One that cannot be saved is answered 500.
- `GET /alive` answers 200 while the collector runs.
- `GET /ready` answers 200 when its dir is writable, 503 when not. Wait for
  it before starting the runs.
- On TERM it stops accepting connections, finishes the report in hand, and
  exits 0.

## What a run reports

As the process exits (or, under the pytest plugin, as pytest finishes):

- `path_coverage.json` is written to `coverage_dir`: every site of every
  covered file, with each leaf's true and false counts (`sites`), each
  site's possible paths with their counts and each leaf's `line:col` span
  (`paths`), each function's taken paths (`method_paths`), and the two
  totals as [taken, possible] paths (`totals`, `methods` only when
  measured), with, when groups are configured, each group's own two
  totals under `totals.groups`:

```json
"paths": {
  "src/kata.py:3:11": {
    "leaves": [["3:11", "3:17"], ["3:22", "3:30"]],
    "taken": [
      { "path": [true, true], "count": 2 },
      { "path": [true, false], "count": 0 },
      { "path": [false, null], "count": 1 }
    ]
  }
},
"totals": {
  "decisions": [41, 52], "methods": [9, 16],
  "groups": {
    "models": { "decisions": [30, 36], "methods": [7, 12] },
    "routes": { "decisions": [11, 16], "methods": [2, 4] }
  }
}
```

- `gaps` prints one line per path never taken, in manifest order: a site's
  naming the outcome of each leaf on it, a function's the outcome of each
  decision on it, by line:

```text
src/kata.py:3:11 path never taken: `ok(id)` true, `new(id)` false
src/kata.py:4:11 never reached
src/fee.py:1:0 fee path never taken: line 3 true, line 5 false
```

### Decisions

Measured always, as `decisions`: the paths within each decision.

A site is named by the `path:line:column` where it starts: the path relative
to `root`, the line 1-based, the column a 0-based byte offset, as Python's
`ast` gives it. A site in a covered file the run never imported is still
reported, as `never reached`.

A path is the outcome of each leaf one evaluation of the site reached, in
order; a leaf that short-circuiting skipped is not on it. Each leaf is quoted
as a Markdown code span, on one line, its fence one backtick longer than any
run of backticks inside it.

A site is an outermost condition. Its leaves are numbered across the whole
of it, nested conditions included:

```python
ok(id) and new(id) and len(id) == 6       # one `and` site, leaves 0 1 2
ok(id) and (new(id) or len(id) == 6)      # an `or` nested in an `and` site, 0 1 2
ok(id) and new(id) or len(id) == 6        # an `and` nested in an `or` site, 0 1 2
any(k and k.ok for k in ids) and ok(id)   # two sites: the generator's is its own
"ok" if ok(id) else "no"                  # a conditional expression site, its predicate leaf 0
new(id) or big(id) if ok(id) else "no"    # one site: predicate 0, then arm 1 2
```

A conditional expression is a site even when its predicate is a single
leaf. Its predicate's leaves come first, as it is evaluated first. An arm
holding an `and`, an `or` or a conditional expression is part of its site,
its leaves numbered after the predicate's, so the site's paths run through
whichever arm the predicate picks. Any other arm is not part of it, though a
condition inside it is a site of its own.

An `if` statement is a site too, even when its predicate is a single leaf,
named at its keyword: its predicate nests in it, an `and` there being no
site of its own, and its arms are plain, as they are statements. An `elif`
is a site of its own, named at its keyword.

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

With `measure=["decisions", "methods"]`, each function with two or more
top-level `if` statements also counts each call's path through them: the
outcome of each decision it reached, in order. A function is named by the
`path:line:column` of its `def`, then its name. Each decision is one outcome
on the path, however many leaves its predicate has; those are its site's to
show. A decision whose arm always leaves the function (it ends in `return`
or `raise`) ends the path there.

### Reporters

- `html` writes `index.html` to `coverage_dir`: the covered files with their
  sites and their paths taken of all possible, within each decision and,
  when `methods` is measured, within each method (eg `9 / 28 (32%)`, or
  `-` for a file with no method of two or more decisions), each column
  sortable, and a Total row for every file together. With groups
  configured, a tab bar heads the table: All files, then each group, then
  Ungrouped for the files in no group (only when there are any), each tab
  showing a table of its own files with its own Total row, each sorted on
  its own. Each file name opens `files/<path>.html`, the file's source. On
  a line holding a site the line number is a button that opens a grid of
  the site's paths: its rows are the site's tree (its operators, nested as
  Python groups them, a conditional expression's arms marked `?` and `:`,
  an `if`'s named `then` and `else`, and its leaves), its columns its paths,
  never taken first, each headed by its count. When `methods` is measured, a
  grid of each function's paths sits beside its `def`.
- `gaps` prints the gap lines, as above.
- `summary` prints the totals, as coverage tools print theirs; a total
  with no path possible shows `(-)`:

```text
Path coverage within decisions: 41 / 52 (78.85%)
Path coverage within methods: 9 / 16 (56.25%)
```

  With groups configured, each group is a heading with its own totals
  indented under it, and there is no total over every group:

```text
models:
  Path coverage within decisions: 30 / 36 (83.33%)
  Path coverage within methods: 7 / 12 (58.33%)
routes:
  Path coverage within decisions: 11 / 16 (68.75%)
  Path coverage within methods: 2 / 4 (50.00%)
```

- `post` sends the JSON report to the collector, never through a proxy,
  and gives up in silence on a collector it cannot reach within a second,
  so the run's own output and exit status stay as they are.

## How it works

A meta path finder, placed first on `sys.meta_path`, hands each covered
module to a loader that parses its source, rewrites its tree, and compiles
the changed tree, with the recorder bound in the module as
`__path_coverage__`:

```python
ok(id) and new(id)
# compiles as
__path_coverage__.leave(
    __path_coverage__.enter("k.py:2:11", 2),
    __path_coverage__.record("k.py:2:11", 0, ok(id)) and
    __path_coverage__.record("k.py:2:11", 1, new(id)))
```

`enter` starts a trail for one evaluation of the site, each `record` notes
its leaf's outcome on it and returns the leaf unchanged, and `leave` counts
the trail as a path and returns the site's value unchanged, so
short-circuiting and the value of the expression are preserved. Only an
`if` statement's predicate is wrapped, as its arms may return or raise. With
`methods` measured, each call's path starts just before a function's first
decision, and each decision's predicate is wrapped in a `decide` call.

Each inserted node takes the location of the code it wraps, so line numbers
in tracebacks, and coverage.py's line and branch figures, are those of the
file as written. The rewrite happens in memory: the loader neither reads nor
writes the bytecode cache, and no file on disk changes.

## Roadmap

- `match` statements: its patterns are not expressions, so they need
  instrumenting differently from Ruby's `case`/`when`.
- `any()` and `all()` over a generator, and comprehension filters, as Ruby's
  block methods are (`any?`, `select` and the like), noting each item's
  answer without evaluating anything the program would not; `any` and `all`
  can be shadowed, so a site must know it is the builtin.
- `while` loop conditions, and assert statements.
- Conditions and arms located in the HTML grid's source highlighting (only
  leaves are, so far).

## Constraints

- CPython 3.13 or later (`pathlib.PurePath.full_match`).
- A module imported before `start` is not instrumented, and nor is the
  script run as `__main__`; all their sites show as `never reached`.
- A leaf's truth is taken once more by the recorder (and a decision's once
  more again), so a leaf whose `__bool__` has side effects sees it called
  more often.
- Counts are kept per process; the at-exit report does not run on
  `os._exit` or an uncaught signal.

## Development

`bin/test.sh` runs the tests with the python in a sibling `server` repo's
`.venv_fast_test` (override with `PYTHON=...`), writing nothing into this
repo but its self-coverage report. The collector's tests bind local ports.

Every run measures path_coverage's own `src/` and `test/` with
path_coverage. The code measured and the tool measuring are the same
package in one process, so `test/self_coverage.py`, a pytest plugin that
`bin/test.sh` loads with `-p` before any test module is imported, copies
`src/path_coverage` into a temporary dir as `path_coverage_self`, renaming
the names its rewritten code calls (`__path_coverage_self__`,
`__path_coverage_self_path__`), and starts the copy, with groups `code`
(`src/**`) and `test` (`test/**`), skipping `test/projects/**`. The tests
start and stop `path_coverage` as they always do, its finder in front of
the copy's while they run. The copy's finder sits in front of pytest's
assertion rewriting, so the copy's loader rewrites a test module's asserts
as pytest would, after its own rewrite; an assert holding a condition
shows the inserted calls in its failure message.

The report is written to `reports/paths/index.html` (gitignored). A full
run, with no arguments, ends by printing each group's totals and where the
report is:

```text
code:
  Path coverage within decisions: 260 / 325 (80.00%)
  Path coverage within methods: 32 / 62 (51.61%)
test:
  Path coverage within decisions: 7 / 8 (87.50%)
  Path coverage within methods: 0 / 0 (-)
Path coverage report: .../path_coverage/reports/paths/index.html
```

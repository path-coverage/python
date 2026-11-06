# <img src="https://avatars.githubusercontent.com/u/353243247?v=4" alt="" width="32" height="32"> path-coverage/python

Path coverage for Python, to run alongside coverage.py's line and branch
coverage.

Status: sites cover `and`, `or`, the conditional expression,
`if`/`elif`/`else`, `match`, comprehension filters, and `any` and `all`
called with a generator. Each function's card has a row for every site
in it, and for each return and raise, as each cuts a path short.

Demo: https://path-coverage.github.io/python/ shows the HTML report for
the mock source tree in `demo/`. `make demo` builds and opens the same
report locally.

## Overview

A *site* is one decision in your code: an `and`, `or`, `if`, conditional
expression, `match`, filter, or an `any` or `all` of a generator. Each way
it can go is a *path*. For example

```python
len(name) > 2 and name.isascii()
```

has three paths: true then true, true then false, and false alone, as
`and` then skips its right side.

Line and branch coverage can be 100% while a path was never taken.
path_coverage counts how often each path was taken: alone, each site's
paths on their own, and combined, through each function's statements.

As the run exits it writes its report:
- `path_coverage.json`, for AIs and other tools.
- `path_coverage.source.json`, what drawing each file's code needs.

The HTML report, for people, is drawn from those two by
[html-reporter](https://github.com/path-coverage/html-reporter):
`index.html`, a sortable row per covered file with its paths
combined taken, and a page per file with its cards.

```sh
docker run --rm -v "$PWD/coverage:/paths" ghcr.io/path-coverage/html-reporter /paths
```

## Reading the HTML

Clicking a `def` line's number on a file's HTML page opens that function's
*card* to its left. One card is always open.

A card has a row for each statement in the function, by `line:col`, with
its counts of paths not taken and taken. Code outside every function gets
a card too, titled by the class holding it, or `file`.

Clicking a site's row opens it:
- on the left is the site's code, as a tree.
- on the right is one column for each possible path through it.
  - the column's head is `0` for a path never taken, and `*` for one
    taken (hover for its count). Look for zeros!
  - the marks in a column line up with the tree's rows, as below.

### Boolean: `T` `F`

Many parts of a site, such as `len(name) > 2`, are true or false.

- `T` the expression was true.
- `F` the expression was false.

### Unreachable: blank

Some parts of a site are not always evaluated.

- blank: the expression is never evaluated on that path.

### Taken: a tick

An `if` takes one of its arms.

- a tick marks the column whose path took that arm.

Below the predicate is one row per arm: `then` and `else` for an `if`,
`?` and `:` for a conditional expression, `keep` and `drop` for a filter.

### Count: `0` `1` `*`

`any` and `all` can be given any number of items.

- `0` the generator gave no items.
- `1` it gave one item.
- `*` it gave two or more.

## Getting started

From code, before any covered module is imported:

```python
import path_coverage

path_coverage.start(
    root="/app",                       # cover globs and site names are relative to it
    cover=["src/**/*.py"],             # each matching module is instrumented as it is imported
    skip=["src/migrations/**/*.py"],   # except these, though a cover glob matches them
    coverage_dir="/tmp/coverage",      # where path_coverage.json is written
    report=["gaps", "summary"],        # the reporters run at exit (default ["gaps"])
    groups={                           # optional: each group's own tab, summary and totals
        "models": ["src/models/**/*.py"],
        "routes": ["src/routes/**/*.py"],
    },
)
```

An unknown reporter is refused by name, with the list of the ones there
are. A file matching any `skip` glob is neither instrumented nor reported.
A group's globs are relative to `root`, as cover globs are; a file can be
in several groups, or in none.

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

## Use when you cannot edit the code!

A run whose own files are thrown away, such as one in a `docker build`
step, can send its report to a collector instead:

```sh
export PATH_COVERAGE_COLLECTOR=http://host.docker.internal:4570/runs
```

With a collector the reporters default to `post`. The package's
`path_coverage_collector` command (or `python -m path_coverage.collector`)
is that collector. It saves each report POSTed to it as a numbered file,
and once every run is done they render as one report, its two JSON files
written to `coverage_dir` for html-reporter to draw:

```sh
path_coverage_collector 4570 /tmp/paths/runs   # until sent TERM
```

```python
from pathlib import Path
import path_coverage

path_coverage.render(
    root="/app", cover=["src/**/*.py"], coverage_dir="/tmp/coverage",
    report=["gaps"],
    runs=sorted(Path("/tmp/paths/runs").glob("*.json")),
)
```

Each JSON report names the kinds of site it measured. A version that
measures other kinds lists a site's paths differently. So `render` refuses
a run whose kinds differ from those of the installed version.

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
  covered file, with each leaf's true and false counts under `sites`, each
  site's paths under `paths`, each card under `cards`, the statements
  reached under `reached`, and the paths taken of all possible under
  `totals`, as [taken, possible]: `alone`, `combined`, and, with groups,
  each group's own under `groups`. It also names the kinds of site
  measured under `kinds`.
- `path_coverage.source.json` is written beside it: each covered file's
  lines and their coloured tokens, and where each site is and its fold's
  rows, so html-reporter can draw the pages without parsing Python.

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
  "alone": [41, 52], "combined": [90, 116],
  "groups": {
    "models": { "alone": [30, 36], "combined": [70, 82] },
    "routes": { "alone": [11, 16], "combined": [20, 34] }
  }
}
```

- `gaps` prints one line per site path never taken, in manifest order,
  naming the outcome of each leaf on it:

```text
src/kata.py:3:11 path never taken: `ok(id)` true, `new(id)` false
src/kata.py:4:11 never reached
```

### Decisions

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
any(k and k.ok for k in ids) and ok(id)   # three sites: the and, the any, and k and k.ok
"ok" if ok(id) else "no"                  # a conditional expression site, its predicate leaf 0
new(id) or big(id) if ok(id) else "no"    # one site: predicate 0, then arm 1 2
[u for u in us if ok(u) and new(u)]       # a filter site, named at its if: 0 1
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

A comprehension's filter is a site too, named at its `if` keyword. Its test
nests in it, as an `if` statement's predicate does. True keeps the item and
false drops it, so the HTML names its arms keep and drop.

A `match` statement is a site, named at its keyword. Each case's pattern is
a leaf, true when it matches. A guard is reached only when its pattern
matches, and its leaves follow the pattern's. A later case is reached only
when no earlier case was taken. When no case is taken, every pattern
reached is false, and that is a path of its own. A last case of `_`, or of
a bare name, matches anything, so no path ends with nothing matched.

```python
match order.kind:
    case "gold" if order.big:   # leaf 0 the pattern, leaf 1 the guard
        return 1
    case "silver":              # leaf 2
        return 2
```

A call of `any` or `all` with a generator is a site, named where the call
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

Each function has a card, named by the `path:line:column` of its `def`,
with a row per statement, in the order written: its body's, and those of
each arm, loop, `with`, `try` and class inside it. A nested `def` is one
row, as its body runs only when called; it has a card of its own. A row
that is a site counts its paths; any other row is one path, taken when the
statement is reached. A function's total adds up its rows. A file's sites
outside every function get a card for each span of their lines.

The JSON report's `cards` hold each card's rows:

```json
"cards": {
  "label.py:1:0": {
    "name": "label", "first": 1, "last": 4,
    "rows": [
      { "at": "2:04", "top": "if", "paths": 2, "taken": 1, "site": "label.py:2:4" },
      { "at": "3:08", "top": "return", "paths": 1, "taken": 1, "site": null },
      { "at": "4:04", "top": "return", "paths": 1, "taken": 0, "site": null }
    ]
  }
}
```

### Reporters

- `gaps` prints the gap lines, as above.
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
`if` statement's predicate is wrapped, as its arms may return or raise.
Each statement of a function that is no site gets a `reach` call before it,
counting its run, for its card's row.

A `match` statement's patterns are not expressions, so they cannot be
wrapped. Instead the site is entered just before the statement. Each case
gets a guard, a `matched` call, which notes that its pattern matched and
returns the case's own guard, or True when it has none. Unless the last
case matches anything, a case is added after it. Its guard, an `unmatched`
call, notes that no case was taken and returns False, so the added case is
never taken itself.

Each inserted node takes the location of the code it wraps, so line numbers
in tracebacks, and coverage.py's line and branch figures, are those of the
file as written. The rewrite happens in memory: the loader neither reads nor
writes the bytecode cache, and no file on disk changes.

## Roadmap

- `next()` with a generator and a default, eg
  `next((o for o in orders if o.late), None)`: whether it found an item or
  gave the default.
- `while` loop conditions, and assert statements.
- Conditions and arms located in the HTML tree's source highlighting (only
  leaves are, so far).

## Constraints

- CPython 3.13 or later (`pathlib.PurePath.full_match`).
- A module imported before `start` is not instrumented, and nor is the
  script run as `__main__`; all their sites show as `never reached`.
- A leaf's truth is taken once more by the recorder, so a leaf whose
  `__bool__` has side effects sees it called more often.
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
  Paths alone: 503 / 569 (88.40%)
  Paths combined: 1321 / 1414 (93.42%)
test:
  Paths alone: 10 / 12 (83.33%)
  Paths combined: 829 / 839 (98.81%)
Path coverage report: .../path_coverage/reports/paths/index.html
```

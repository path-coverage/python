# The event interface

Every mode of measuring logs the same thing: `Evaluations.note(frame,
actions)`. `frame` is a key, `(id(frame), id(code))`, of the code that
ran: so two events share a key only within one call, or across a call
and a later call of the same function whose frame reuses the finished
one's id, which enters first. Each action is in source terms only: a
decision's Shape and a leaf index, or a row's name. How a mode finds out
that an action happened stays on its own side.

| Action | Means | monitoring mode | rewrite mode |
|---|---|---|---|
| `Enter(entry)` | a call of the def named entry starts | PY_START | record statement first in the body |
| `Outcome(shape, i, truth)` | leaf i of shape's decision had truth | branch event, or a wrapped leaf | wrapped leaf |
| `Opened(shape)` | a match starts trying its cases | instruction mark | wrapped subject |
| `Matched(shape, pattern, earlier)` | a case's pattern matched | instruction mark | record statement |
| `Unmatched(shape, patterns)` | a match left with no case taken | instruction mark | record statement after the match |
| `Begin(shape)` | a block call, eg any(...), starts | branch event | wrapped first iterable of its generator expression |
| `Item(shape)` | a block call is given an item | branch event | that wrapped iterable, per item |
| `Answer(shape, truth)` | a block call's answer for its item | branch event | wrapped element, logged by the generator frame's f_back, the caller |
| `End(shape)` | a block call is done | branch event | wrapped call |
| `Reach(name)` | a return or raise statement starts | instruction mark | record statement before it |
| `Pass(loop)` | a pass of a loop starts | FOR_ITER branch (for only) | wrapped iterable; a while's wrapped test, true |
| `Exhausted(loop)` | a loop's items are all given | FOR_ITER branch (for only) | wrapped iterable; a while's wrapped test, false |

A loop left by a break or a return sends no Exhausted: the next row
outside it, or the call's end, closes it (`walk.py`). A decision in a
while's test steps the way only on its first run: later runs repeat the
loop's fork (`Walk.step`, `Source.repeats`).

## Where the modes differ, by design

- **while**: only rewrite mode gives its passes. In monitoring mode a
  while is never opened, so its test steps the way on every run.
- **Code run inside a sys.monitoring callback** (eg a debugger's, or
  path_coverage's own monitor measured by self-coverage): CPython fires
  no events there, so monitoring mode never sees it; rewrite mode does.
  Self-coverage counted `monitor._branched_left` 2 times in monitoring
  mode, 104,682 in rewrite mode.
- **A block call in a pytest assert**: pytest rewrites the assert's AST,
  so monitoring mode's bytecode pattern for any(...) is not found; rewrite
  mode inserts its records first, so still counts it.

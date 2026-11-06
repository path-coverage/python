# path_coverage

- `bin/test.sh` runs the tests and self-coverage. The collector's tests
  bind local ports. A full run ends with each group's totals. It uses
  the repo's `.venv`: `python3 -m venv .venv` then
  `.venv/bin/pip install pytest`.
- The file page's panel is a *card*. Never call it a popout.
- The pages are drawn in the browser by the shared renderer,
  `../html-reporter`, from the data `page_data` builds. The files in
  `src/path_coverage/html/` are its copy: change them there, then run
  `bin/sync_html.sh`.
- Every site in src and test must be a card row or a top row; test
  b47e3a30 checks it.
- Test ids are 8 hex digits, a file's tests sharing the first 6. Grep a
  new id before using it.
- METHOD_MODE_CHOICES.md lists the provisional choices about cards, each
  pinned by a test, awaiting the user's confirmation.

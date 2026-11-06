#!/usr/bin/env bash
# Runs the tests with the Python in the repo's .venv, writing nothing
# into the repo (no .pytest_cache, no __pycache__) but the self-coverage
# report in reports/paths.
set -Eeu

if [ "${1:-}" = "-h" ]; then
  cat <<'EOF'
Usage: bin/test.sh [PYTEST_ARGS...]

Runs the tests in test/ against src/, using the repo's .venv python
(override with PYTHON=...), with path_coverage measuring its own src/ and
test/ (a renamed copy of src/path_coverage, test/self_coverage.py, does the
measuring), its report written to reports/paths/index.html.

A full run, given no PYTEST_ARGS, ends by printing each group's path totals
(code and test) and where the report is. With PYTEST_ARGS, a partial run,
the totals cover only part of the code, so they are not printed.

Options:
  -h    Show this help

Examples:
  bin/test.sh
  bin/test.sh -k 5c1e9a01
EOF
  exit 0
fi

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PYTHON="${PYTHON:-${ROOT}/.venv/bin/python}"
cd "${ROOT}"
export PYTHONDONTWRITEBYTECODE=1
PYTHONPATH="${ROOT}/src:${ROOT}/test" \
  "${PYTHON}" -m pytest -p no:cacheprovider -p self_coverage --quiet "$@"

if [ $# -eq 0 ]; then
  PYTHONPATH="${ROOT}/src" "${PYTHON}" bin/print_path_totals.py
fi

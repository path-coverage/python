#!/usr/bin/env bash
# Runs the tests with the Python in the repo's .venv, writing nothing
# into the repo (no .pytest_cache, no __pycache__) but the self-coverage
# report in reports/paths.
set -Eeu

if [ "${1:-}" = "-h" ]; then
  cat <<'EOF'
Usage: bin/test.sh [--suite NAME] [PYTEST_ARGS...]

Runs the tests in test/ against src/, using the repo's .venv python
(override with PYTHON=...), with path_coverage measuring its own src/ and
test/ (a renamed copy of src/path_coverage, test/self_coverage.py, does the
measuring), its JSON reports written to reports/paths, checked against
their schemas by the schemas image, then drawn there as
reports/paths/index.html by the html-reporter image, each in Docker.

A full run, given no PYTEST_ARGS, also measures line and branch coverage
of src/ and test/ with coverage.py, as pyproject.toml configures it,
listing each file with lines or branches missed, and writing
reports/coverage.json; then it prints each group's path totals (code and
test) and where the report is. With PYTEST_ARGS, a partial run, the totals
cover only part of the code, so none of this is done.

With --suite NAME, runs one suite of test/suites.py: all, every test (the
default); core, every test but the generated ones in test/property, neither
run nor measured, so its checks say whether the hand-written tests alone
reach full coverage; property, the generated tests alone, whose coverage,
of only part of the code, is not checked.

Options:
  -h              Show this help
  --suite NAME    Run the suite NAME of test/suites.py

Examples:
  bin/test.sh
  bin/test.sh -k 5c1e9a01
  bin/test.sh --suite core
EOF
  exit 0
fi

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PYTHON="${PYTHON:-${ROOT}/.venv/bin/python}"
cd "${ROOT}"
export PYTHONDONTWRITEBYTECODE=1

export PATH_COVERAGE_SUITE=all
if [ "${1:-}" = "--suite" ]; then
  PATH_COVERAGE_SUITE="${2:?--suite needs a NAME from test/suites.py}"
  shift 2
fi
# A full run of a suite whose coverage is checked checks it; any other run
# covers only part of the code.
checked=unchecked
if [ $# -eq 0 ]; then
  checked="$("${PYTHON}" test/suites.py)"
fi
readonly checked

coverage=()
if [ "${checked}" = checked ]; then
  mkdir -p "${ROOT}/reports"
  coverage=(--cov --cov-report=term-missing:skip-covered --cov-report=json)
fi
PYTHONPATH="${ROOT}/src:${ROOT}/test" \
  "${PYTHON}" -m pytest -p no:cacheprovider -p suites -p self_coverage --quiet "${coverage[@]}" "$@"

docker run --rm \
  --volume "${ROOT}/reports/paths:/paths:ro" \
  ghcr.io/path-coverage/schemas /paths > /dev/null
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "${ROOT}/reports/paths:/paths" \
  ghcr.io/path-coverage/html-reporter /paths

if [ "${checked}" = checked ]; then
  PYTHONPATH="${ROOT}/src" "${PYTHON}" bin/print_path_totals.py
fi

#!/usr/bin/env bash
# Runs the tests with the Python in the repo's .venv, writing nothing
# into the repo (no .pytest_cache, no __pycache__) but the self-coverage
# report in reports/paths.
set -Eeu

if [ "${1:-}" = "-h" ]; then
  cat <<'EOF'
Usage: bin/test.sh [--suite NAME] [--progress] [PYTEST_ARGS...]

Runs the tests in test/ against src/, using the repo's .venv python
(override with PYTHON=...), with path_coverage measuring its own src/ and
test/ (a renamed copy of src/path_coverage, test/self_coverage.py, does the
measuring), its JSON reports written to reports/paths, then checked
against their schemas by the schemas image, in Docker.

A full run, given no PYTEST_ARGS, runs the suite core, the hand-written
tests, measured: it also measures line and branch coverage of src/ and
test/ with coverage.py, as pyproject.toml configures it, listing each
file with lines or branches missed, and writing reports/coverage.json;
then it prints each group's path totals (code and test). It then runs
the suite property, the generated tests, unmeasured. With PYTEST_ARGS, a
partial run of every test, measured, the totals cover only part of the
code, so none of the checks is done.

With --suite NAME, runs one suite of test/suites.py: all, every test,
measured; core; or property, as above.

A run prints a dot per passing test. With --progress, for debugging a
slow or stuck run, it names each test as it starts, lists the slowest
tests, and says when the self-coverage report starts and how long it
took.

Options:
  -h              Show this help
  --suite NAME    Run the suite NAME of test/suites.py
  --progress      Name each test as it runs, and time the slow parts

Examples:
  bin/test.sh
  bin/test.sh -k 5c1e9a01
  bin/test.sh --suite core
  bin/test.sh --progress
EOF
  exit 0
fi

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PYTHON="${PYTHON:-${ROOT}/.venv/bin/python}"
cd "${ROOT}"
export PYTHONDONTWRITEBYTECODE=1

# A full run is the suites core then property; --suite NAME, or any
# PYTEST_ARGS, runs the one suite, all by default.
suites=(core property)
if [ "${1:-}" = "--suite" ]; then
  suites=("${2:?--suite needs a NAME from test/suites.py}")
  shift 2
fi
output=(--quiet)
export PATH_COVERAGE_SELF_PROGRESS=off
if [ "${1:-}" = "--progress" ]; then
  output=(--verbose --durations=20)
  PATH_COVERAGE_SELF_PROGRESS=on
  shift
fi
if [ $# -gt 0 ] && [ "${#suites[@]}" -gt 1 ]; then
  suites=(all)
fi

run_suite() {
  # Runs the suite $1 of test/suites.py, with the PYTEST_ARGS after it:
  # a measured suite under self-coverage, its reports then checked
  # against their schemas; a full run of a checked suite also measuring
  # line and branch coverage and printing its path totals.
  export PATH_COVERAGE_SUITE="$1"
  shift
  local kind checked measured
  kind="$("${PYTHON}" test/suites.py)"
  checked="${kind% *}"
  measured="${kind#* }"
  if [ $# -gt 0 ]; then
    checked=unchecked
  fi
  local plugins=(-p suites)
  if [ "${measured}" = measured ]; then
    plugins+=(-p self_coverage)
  fi
  local coverage=()
  if [ "${checked}" = checked ]; then
    mkdir -p "${ROOT}/reports"
    coverage=(--cov --cov-report=term-missing:skip-covered --cov-report=json)
  fi
  PYTHONPATH="${ROOT}/src:${ROOT}/test" \
    "${PYTHON}" -m pytest -p no:cacheprovider "${plugins[@]}" "${output[@]}" "${coverage[@]}" "$@"
  if [ "${measured}" = measured ]; then
    local schema_check
    schema_check="$(docker run --rm \
      --volume "${ROOT}/reports/paths:/paths:ro" \
      ghcr.io/path-coverage/schemas /paths 2>&1)" \
      || { echo "${schema_check}" >&2; exit 1; }
  fi
  if [ "${checked}" = checked ]; then
    PYTHONPATH="${ROOT}/src" "${PYTHON}" bin/print_path_totals.py
  fi
}

for suite in "${suites[@]}"; do
  run_suite "${suite}" "$@"
done

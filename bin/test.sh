#!/usr/bin/env bash
# Runs the tests with the Python in server's .venv_fast_test, writing nothing
# into the repo (no .pytest_cache, no __pycache__).
set -Eeu

if [ "${1:-}" = "-h" ]; then
  cat <<'EOF'
Usage: bin/test.sh [PYTEST_ARGS...]

Runs the tests in test/ against src/, using server's .venv_fast_test python
(override with PYTHON=...).

Options:
  -h    Show this help

Example:
  bin/test.sh -k 5c1e9a01
EOF
  exit 0
fi

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PYTHON="${PYTHON:-${ROOT}/../server/.venv_fast_test/bin/python}"
cd "${ROOT}"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${ROOT}/src" \
  "${PYTHON}" -m pytest -p no:cacheprovider --quiet "$@"

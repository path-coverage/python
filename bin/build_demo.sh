#!/usr/bin/env bash
# Builds the demo report: demo/run.py under path coverage, into site/.
set -Eeu

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PYTHON="${PYTHON:-${ROOT}/.venv/bin/python}"

if [ "${1:-}" = '-h' ]; then
  cat <<EOF
Usage: bin/build_demo.sh

Runs demo/run.py, a mock source tree under path coverage, with the
repo's .venv python (override with PYTHON=...), writing its HTML
report to site/ (index.html first), emptied first. The same site is
what the GitHub Pages workflow publishes.

Options:
  -h    Show this help

Example:
  bin/build_demo.sh
EOF
  exit 0
fi

rm -rf "${ROOT}/site"
mkdir -p "${ROOT}/site"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${ROOT}/src" COVERAGE_DIR="${ROOT}/site" \
  "${PYTHON}" "${ROOT}/demo/run.py"
echo "${ROOT}/site/index.html"

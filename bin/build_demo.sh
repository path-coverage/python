#!/usr/bin/env bash
# Builds the demo report: demo/run.py under path coverage, into site/.
set -Eeu

readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PYTHON="${PYTHON:-${ROOT}/.venv/bin/python}"

if [ "${1:-}" = '-h' ]; then
  cat <<EOF
Usage: bin/build_demo.sh

Runs demo/run.py, a mock source tree under path coverage, with the
repo's .venv python (override with PYTHON=...), writing its JSON
reports to site/, emptied first, then draws its HTML report there
(index.html first) with the html-reporter image, in Docker. The same
site is what the GitHub Pages workflow publishes.

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
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "${ROOT}/site:/site" \
  ghcr.io/path-coverage/html-reporter /site
echo "${ROOT}/site/index.html"

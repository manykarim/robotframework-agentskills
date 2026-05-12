#!/usr/bin/env bash
# Build every PyPI artifact in the workspace.
#
# The repo is a uv workspace (see [tool.uv.workspace] in pyproject.toml):
#
#   * rf-skill-eval   — root, the evaluation harness
#   * rf-agentskills  — installer/, the cross-agent installer
#
# `uv build` alone defaults to the root package (rf-skill-eval), which
# was almost certainly the wrong default for anyone trying to publish.
# This wrapper runs `uv build --all-packages` so both wheels + sdists
# land in dist/ next to each other.
#
# Usage:
#   scripts/build-packages.sh          # build all
#   scripts/build-packages.sh --clean  # remove dist/ first
#   scripts/build-packages.sh --check  # also validate with twine

set -euo pipefail
cd "$(dirname "$0")/.."

clean=0
check=0
for arg in "$@"; do
    case "$arg" in
        --clean) clean=1 ;;
        --check) check=1 ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "unknown flag: $arg" >&2
            exit 64
            ;;
    esac
done

if [ "$clean" = "1" ]; then
    echo "::: clean :::"
    rm -rf dist/ installer/dist/
fi

echo "::: uv build --all-packages :::"
uv build --all-packages

echo ""
echo "::: artifacts :::"
ls -lh dist/

if [ "$check" = "1" ]; then
    if ! command -v twine >/dev/null; then
        echo "::: twine not on PATH — installing via uv tool :::"
        uv tool install twine
    fi
    echo ""
    echo "::: twine check :::"
    twine check dist/*.whl dist/*.tar.gz
fi

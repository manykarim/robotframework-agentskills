#!/usr/bin/env bash
# Build PyPI artifacts for this monorepo.
#
# The repo is a uv workspace (see [tool.uv.workspace] in pyproject.toml):
#
#   PUBLIC (PyPI release):
#     installer/  →  rf-agentskills   (cross-agent installer)
#
#   INTERNAL (never uploaded to PyPI):
#     root        →  rf-skill-eval    (evaluation harness, classified
#                                      "Private :: Do Not Upload" so
#                                      pypi.org refuses the upload)
#
# Default behavior: build only the PUBLIC package. The internal
# evaluation harness is buildable for local development but isn't part
# of the release flow.
#
# Usage:
#   scripts/build-packages.sh          # build rf-agentskills only (PUBLIC)
#   scripts/build-packages.sh --all    # also build the internal harness
#   scripts/build-packages.sh --clean  # remove dist/ first
#   scripts/build-packages.sh --check  # also validate with twine
#
# Flags can be combined: e.g. `--clean --check` builds public, with check.

set -euo pipefail
cd "$(dirname "$0")/.."

clean=0
check=0
all=0
for arg in "$@"; do
    case "$arg" in
        --clean) clean=1 ;;
        --check) check=1 ;;
        --all)   all=1 ;;
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

if [ "$all" = "1" ]; then
    echo "::: uv build --all-packages (public + internal) :::"
    uv build --all-packages
else
    echo "::: uv build --package rf-agentskills (public only) :::"
    uv build --package rf-agentskills
fi

echo ""
echo "::: artifacts :::"
ls -lh dist/

if [ "$check" = "1" ]; then
    if ! command -v twine >/dev/null 2>&1; then
        echo "::: twine not on PATH — installing via uv tool :::"
        uv tool install twine
    fi
    echo ""
    echo "::: twine check :::"
    twine check dist/*.whl dist/*.tar.gz
fi

echo ""
if [ "$all" = "1" ]; then
    echo "Reminder: rf-skill-eval is tagged 'Private :: Do Not Upload';"
    echo "          pypi.org will reject \`twine upload dist/rf_skill_eval-*\`."
    echo "          Upload only rf_agentskills-* to PyPI:"
    echo "              twine upload dist/rf_agentskills-*"
fi

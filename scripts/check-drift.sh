#!/usr/bin/env bash
# Check for drift between root skills/ and plugin/vscode distribution copies.
# Exit 1 if any drift is found.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRIFT_FOUND=0

echo "=== Checking script drift: root skills/ vs plugin scripts/ ==="
declare -A SCRIPT_MAP=(
    ["skills/robotframework-keyword-builder/scripts/keyword_builder.py"]="plugins/rf-agentskills/scripts/keyword_builder.py"
    ["skills/robotframework-testcase-builder/scripts/testcase_builder.py"]="plugins/rf-agentskills/scripts/testcase_builder.py"
    ["skills/robotframework-resource-architect/scripts/resource_architect.py"]="plugins/rf-agentskills/scripts/resource_architect.py"
    ["skills/robotframework-libdoc-search/scripts/rf_libdoc.py"]="plugins/rf-agentskills/scripts/rf_libdoc.py"
    ["skills/robotframework-results/scripts/rf_results.py"]="plugins/rf-agentskills/scripts/rf_results.py"
)

for root_path in "${!SCRIPT_MAP[@]}"; do
    plugin_path="${SCRIPT_MAP[$root_path]}"
    root_file="$REPO_ROOT/$root_path"
    plugin_file="$REPO_ROOT/$plugin_path"

    if [ ! -f "$root_file" ]; then
        echo "MISSING: $root_path"
        DRIFT_FOUND=1
        continue
    fi
    if [ ! -f "$plugin_file" ]; then
        echo "MISSING: $plugin_path"
        DRIFT_FOUND=1
        continue
    fi

    if ! diff -q "$root_file" "$plugin_file" > /dev/null 2>&1; then
        echo "DRIFT: $root_path != $plugin_path"
        diff "$root_file" "$plugin_file" || true
        DRIFT_FOUND=1
    else
        echo "  OK: $root_path"
    fi
done

echo ""
echo "=== Checking for double-nested vscode-extension/skills/skills/ ==="
if [ -d "$REPO_ROOT/vscode-extension/skills/skills" ]; then
    echo "ERROR: Double-nested vscode-extension/skills/skills/ directory exists!"
    DRIFT_FOUND=1
else
    echo "  OK: No double nesting"
fi

echo ""
if [ $DRIFT_FOUND -eq 1 ]; then
    echo "DRIFT DETECTED! Run: bash scripts/sync-skills.sh"
    exit 1
else
    echo "All files in sync."
    exit 0
fi

#!/usr/bin/env bash
# validate_robot.sh - Validate Robot Framework .robot and .resource files
#
# Called by the PostToolUse hook after Write or Edit operations.
# Receives the file path via the TOOL_INPUT environment variable (JSON).
# Exits 0 on success or non-.robot files, exits 1 on parse failure.
#
# This script uses `robot.api.get_model` which parses the file for structural
# correctness (valid sections, proper indentation, recognizable settings)
# WITHOUT executing anything or requiring library imports to be resolvable.
#
# Design decisions:
#   - Only runs on .robot and .resource files to avoid false triggers.
#   - Uses python3 with robot.api for accurate parsing.
#   - Outputs a short message on stderr so Claude sees the validation result
#     without polluting the conversation with verbose output.
#   - Non-blocking: exits 0 for non-RF files so the hook does not interfere
#     with other file types.

set -euo pipefail

# Extract the file path from the TOOL_INPUT JSON.
# TOOL_INPUT is set by Claude Code hooks and contains the tool's input as JSON.
# For Write: {"file_path": "...", "content": "..."}
# For Edit:  {"file_path": "...", "old_string": "...", "new_string": "..."}
FILE_PATH=""
if [ -n "${TOOL_INPUT:-}" ]; then
    # Use python to extract file_path from JSON (avoids jq dependency)
    FILE_PATH=$(python3 -c "
import json, sys
try:
    data = json.loads(sys.argv[1])
    print(data.get('file_path', ''))
except Exception:
    pass
" "$TOOL_INPUT" 2>/dev/null || true)
fi

# If we could not determine the file path, exit silently.
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Only validate .robot and .resource files.
case "$FILE_PATH" in
    *.robot|*.resource)
        ;;
    *)
        exit 0
        ;;
esac

# Check that the file exists.
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# Run the parser validation.
python3 -c "
import sys
try:
    from robot.api import get_model
except ImportError:
    # robotframework is not installed -- skip validation silently.
    print('Robot Framework not installed, skipping syntax validation.', file=sys.stderr)
    sys.exit(0)

try:
    model = get_model(sys.argv[1])
    # Check for common structural issues
    errors = []
    # Verify the file has at least one recognized section
    sections = []
    if hasattr(model, 'sections'):
        sections = list(model.sections)
    if not sections:
        errors.append('No recognized sections found (expected *** Settings ***, *** Test Cases ***, *** Keywords ***, or *** Variables ***)')
    if errors:
        for e in errors:
            print(f'WARNING: {e}', file=sys.stderr)
    else:
        print(f'Robot Framework syntax OK: {sys.argv[1]}', file=sys.stderr)
    sys.exit(0)
except Exception as e:
    print(f'Robot Framework syntax error in {sys.argv[1]}: {e}', file=sys.stderr)
    sys.exit(1)
" "$FILE_PATH"

#!/usr/bin/env bash
# Validate `rf-agentskills install --agent claude-desktop`.
#
# Claude Desktop is a GUI app. Officially supported on macOS + Windows
# only; on Linux (the harness's container OS) the path used is
# ~/.config/Claude/claude_desktop_config.json (community/unofficial).
# We validate file placement; we don't run the GUI.

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

# Linux fallback path (per the adapter)
DESKTOP_DIR="$HOME/.config/Claude"
CONFIG="$DESKTOP_DIR/claude_desktop_config.json"
PLUGIN_FILES="$DESKTOP_DIR/rf-agentskills-files"

case "${1:-}" in
--post-install)
    need_file "$CONFIG"
    need_json_key "$CONFIG" 'mcpServers."rf-tools"'
    # Plugin scripts co-located
    need_file "$PLUGIN_FILES/scripts/validate_robot.mjs"
    need_file "$PLUGIN_FILES/scripts/python_runtime.json"
    need_file "$PLUGIN_FILES/servers/rf-tools-server.py"
    need_no_substitution "$PLUGIN_FILES/scripts/validate_robot.mjs"
    ;;

--post-uninstall)
    if [ -f "$CONFIG" ]; then
        if jq -e '.mcpServers."rf-tools"' "$CONFIG" >/dev/null 2>&1; then
            printf '  [check] rf-tools survived uninstall in claude_desktop_config.json\n' >&2
            exit 1
        fi
    fi
    ;;

--api-smoke)
    skip "Claude Desktop is a GUI; no headless CLI"
    ;;

*)
    echo "usage: $0 --post-install | --post-uninstall | --api-smoke" >&2
    exit 64
    ;;
esac

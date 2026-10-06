#!/usr/bin/env bash
# Validate `rf-agentskills install --agent claude-desktop`.
#
# Claude Desktop (and claude.ai) load custom Agent Skills only as a
# user-uploaded ZIP per skill — there's no on-disk folder it reads and
# no config file to merge. The installer instead writes one upload-
# ready `<skill>.zip` to $HOME/rf-agentskills-claude-desktop/ (or
# --prefix), each with the skill folder at the archive root
# (e.g. `rf-browser/SKILL.md`). We validate the archive contents; we
# don't run the GUI.
#
# Claude Desktop is officially supported on macOS + Windows only; on
# Linux (the harness's container OS) the unofficial config path is
# ~/.config/Claude/claude_desktop_config.json. Pre-content-2.1 installs
# merged an rf-tools MCP server entry into that file — a fresh install
# must not recreate it, and must not stage any plugin scripts/servers
# (there's nothing on disk for this agent besides the zip archives).

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

ZIP_DIR="$HOME/rf-agentskills-claude-desktop"
# Linux fallback path (per the adapter) — used only for the legacy
# rf-tools retirement check below, not for where we write archives.
DESKTOP_DIR="$HOME/.config/Claude"
CONFIG="$DESKTOP_DIR/claude_desktop_config.json"
PLUGIN_FILES="$DESKTOP_DIR/rf-agentskills-files"

case "${1:-}" in
--post-install)
    need_file "$ZIP_DIR/rf-browser.zip"
    if ! python3 -c "
import sys, zipfile
with zipfile.ZipFile('$ZIP_DIR/rf-browser.zip') as zf:
    sys.exit(0 if 'rf-browser/SKILL.md' in zf.namelist() else 1)
"; then
        printf '  [check] %s : missing entry rf-browser/SKILL.md\n' "$ZIP_DIR/rf-browser.zip" >&2
        exit 1
    fi
    # rf-tools MCP server was removed: no claude_desktop_config.json
    # entry, and no co-located plugin scripts/servers (only checked if
    # a pre-existing config file happens to be there).
    if [ -f "$CONFIG" ]; then
        if jq -e '.mcpServers."rf-tools"' "$CONFIG" >/dev/null 2>&1; then
            printf '  [check] claude_desktop_config.json unexpectedly has an rf-tools entry\n' >&2
            exit 1
        fi
    fi
    need_no_file "$PLUGIN_FILES/servers/rf-tools-server.py"
    ;;

--post-uninstall)
    need_no_file "$ZIP_DIR/rf-browser.zip"
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

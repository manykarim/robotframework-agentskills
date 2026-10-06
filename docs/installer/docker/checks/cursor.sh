#!/usr/bin/env bash
# Validate `rf-agentskills install --agent cursor`.
# Cursor 2.4+ install paths (per cursor.com/docs/skills):
#   $HOME/.cursor/skills/<name>/      (verbatim SKILL.md, no MDC transform)
#   $HOME/.cursor/agents/<name>.md
#   $HOME/.cursor/hooks.json          (cursor-namespaced events / matchers)
#
# No MCP server config: the rf-tools MCP server was removed and the
# installer no longer writes mcp.json.
#
# Cursor itself is a GUI app — we don't run it in the container. We
# validate file placement and config shape only. The installer's pytest
# tests cover the transform logic; this harness confirms the same
# behavior holds in a clean container.

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

CURSOR="$HOME/.cursor"
PLUGIN_FILES="$CURSOR/rf-agentskills-files"

case "${1:-}" in
--post-install)
    # Skills installed natively (Cursor 2.4+ reads SKILL.md verbatim)
    need_file "$CURSOR/skills/rf-libdoc/SKILL.md" "^name: rf-libdoc$"
    # Merged into libdoc (content 2.0.0): the old libdoc skills are not shipped
    need_no_file "$CURSOR/skills/libdoc-search/SKILL.md"
    need_no_file "$CURSOR/skills/libdoc-explain/SKILL.md"
    need_no_file "$CURSOR/skills/libdoc/SKILL.md"   # renamed to rf-libdoc in content 2.0.0
    # Subagents native
    need_file "$CURSOR/agents/rf-test-architect.md" "^name: rf-test-architect$"
    # rf-tools MCP server was removed: no mcp.json entry, and no server
    # script staged alongside the plugin's other scripts.
    if [ -f "$CURSOR/mcp.json" ]; then
        if jq -e '.mcpServers."rf-tools"' "$CURSOR/mcp.json" >/dev/null 2>&1; then
            printf '  [check] mcp.json unexpectedly has an rf-tools entry\n' >&2
            exit 1
        fi
    fi
    need_no_file "$PLUGIN_FILES/servers/rf-tools-server.py"
    # Hooks with Cursor-namespaced event names + MCP matcher form
    need_file "$CURSOR/hooks.json"
    need_json_key "$CURSOR/hooks.json" 'hooks.postToolUse'
    # Confirm MCP matcher namespacing happened (no leftover Claude-shape)
    if grep -qF 'mcp__rf-mcp__' "$CURSOR/hooks.json"; then
        printf '  [check] cursor hooks.json still has Claude-style mcp__rf-mcp__ matcher\n' >&2
        exit 1
    fi
    # Plugin scripts staged
    need_file "$PLUGIN_FILES/scripts/validate_robot.mjs"
    need_file "$PLUGIN_FILES/scripts/python_runtime.json"
    need_no_substitution "$PLUGIN_FILES/scripts/validate_robot.mjs"
    ;;

--post-uninstall)
    need_no_file "$CURSOR/skills/rf-libdoc/SKILL.md"
    need_no_file "$CURSOR/agents/rf-test-architect.md"
    need_no_file "$CURSOR/hooks.json"
    if [ -f "$CURSOR/mcp.json" ]; then
        if jq -e '.mcpServers."rf-tools"' "$CURSOR/mcp.json" >/dev/null 2>&1; then
            printf '  [check] rf-tools survived uninstall\n' >&2
            exit 1
        fi
    fi
    ;;

--api-smoke)
    skip "Cursor is a GUI; no headless CLI to drive in the container"
    ;;

*)
    echo "usage: $0 --post-install | --post-uninstall | --api-smoke" >&2
    exit 64
    ;;
esac

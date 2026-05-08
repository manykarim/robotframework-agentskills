#!/usr/bin/env bash
# Validate `rf-agentskills install --agent copilot`.
# Copilot in VS Code reads the Claude Code paths natively, so the
# installer writes to ~/.claude/skills/ and friends. We can't run VS
# Code in the container; we just confirm file placement and shape.

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

ROOT="$HOME/.claude"

case "${1:-}" in
--post-install)
    need_file "$ROOT/skills/libdoc-search/SKILL.md" "^name: libdoc-search$"
    need_file "$ROOT/agents/rf-test-architect.md"
    need_file "$ROOT/settings.json"
    need_json_key "$ROOT/settings.json" 'hooks.PostToolUse'
    need_file "$HOME/.mcp.json"
    need_json_key "$HOME/.mcp.json" 'mcpServers."rf-tools"'
    ;;

--post-uninstall)
    need_no_file "$ROOT/skills/libdoc-search/SKILL.md"
    need_no_file "$ROOT/agents/rf-test-architect.md"
    if [ -f "$HOME/.mcp.json" ]; then
        if jq -e '.mcpServers."rf-tools"' "$HOME/.mcp.json" >/dev/null 2>&1; then
            printf '  [check] rf-tools survived uninstall\n' >&2
            exit 1
        fi
    fi
    ;;

--api-smoke)
    skip "Copilot in VS Code is a GUI extension; no headless CLI"
    ;;

*)
    echo "usage: $0 --post-install | --post-uninstall | --api-smoke" >&2
    exit 64
    ;;
esac

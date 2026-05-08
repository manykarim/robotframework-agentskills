#!/usr/bin/env bash
# Validate `rf-agentskills install --agent opencode`.
# OpenCode install paths (per opencode.ai/docs/skills/, May 2026):
#   $HOME/.config/opencode/skills/<name>/
#   $HOME/.config/opencode/agents/<name>.md
#   $HOME/.config/opencode/opencode.json   (mcp.<name> block)

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

OPENCODE="$HOME/.config/opencode"
PLUGIN_FILES="$OPENCODE/rf-agentskills-files"

case "${1:-}" in
--post-install)
    # Native skill placement (verbatim copy)
    need_file "$OPENCODE/skills/libdoc-search/SKILL.md" "^name: libdoc-search$"
    need_file "$OPENCODE/skills/keyword-builder/SKILL.md"
    # Native subagent placement
    need_file "$OPENCODE/agents/rf-test-architect.md" "^name: rf-test-architect$"
    # MCP server registered under "mcp" (not "mcpServers" — OpenCode shape)
    need_file "$OPENCODE/opencode.json"
    need_json_key "$OPENCODE/opencode.json" 'mcp."rf-tools"'
    need_json_key "$OPENCODE/opencode.json" 'mcp."rf-tools".command'
    # Plugin scripts staged
    need_file "$PLUGIN_FILES/scripts/validate_robot.sh"
    need_no_substitution "$PLUGIN_FILES/scripts/validate_robot.sh"

    # API-FREE introspection: opencode ships `opencode debug skill`
    # which walks every skill discovery path and emits JSON. No LLM call.
    if opencode debug skill 2>/dev/null > /tmp/opencode-debug-skill.txt; then
        if grep -qF "$OPENCODE/skills/libdoc-search/SKILL.md" /tmp/opencode-debug-skill.txt; then
            printf '  [check] opencode debug skill sees libdoc-search\n' >&2
        else
            printf '  [check] opencode debug skill did NOT find libdoc-search\n' >&2
            head -20 /tmp/opencode-debug-skill.txt >&2 || true
            exit 1
        fi
    else
        printf '  [check] opencode debug skill failed to run\n' >&2
        # Don't fail outright — older OpenCode versions may not have this command
    fi
    ;;

--post-uninstall)
    need_no_file "$OPENCODE/skills/libdoc-search/SKILL.md"
    need_no_file "$OPENCODE/agents/rf-test-architect.md"
    if [ -f "$OPENCODE/opencode.json" ]; then
        if jq -e '.mcp."rf-tools"' "$OPENCODE/opencode.json" >/dev/null 2>&1; then
            printf '  [check] rf-tools mcp entry survived uninstall\n' >&2
            exit 1
        fi
    fi
    ;;

--api-smoke)
    if [ -z "${OPENROUTER_API_KEY:-}" ]; then
        skip "no OpenRouter token in env"
    fi
    if [ ! -f "$OPENCODE/skills/libdoc-search/SKILL.md" ]; then
        skip "no install present"
    fi
    # opencode debug skill is itself the cleanest non-API verification,
    # already done in --post-install. The 'API smoke' here just confirms
    # opencode can start with the configured provider.
    OUT=$(opencode run "ok" 2>&1 || true)
    if echo "$OUT" | grep -qi "error\|failed\|cannot"; then
        printf '  [check] opencode run failed:\n%s\n' "$OUT" >&2
        exit 1
    fi
    ;;

*)
    echo "usage: $0 --post-install | --post-uninstall | --api-smoke" >&2
    exit 64
    ;;
esac

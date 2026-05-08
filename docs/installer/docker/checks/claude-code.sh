#!/usr/bin/env bash
# Validate `rf-agentskills install --agent claude-code`.
#
# API-free checks: filesystem placement plus `claude plugin validate`
# of the staged plugin tree (validates `.claude-plugin/plugin.json`
# without making any LLM call).
#
# API smoke (if --api-smoke): spin up `claude -p "ok" --output-format
# stream-json` and grep the init event for our skills.

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

ROOT="$HOME/.claude"
PLUGIN_FILES="$ROOT/rf-agentskills-files"

case "${1:-}" in
--post-install)
    # Skills (verbatim copy)
    need_file "$ROOT/skills/libdoc-search/SKILL.md" "^name: libdoc-search$" "^description:"
    need_file "$ROOT/skills/keyword-builder/SKILL.md"
    need_file "$ROOT/skills/testcase-builder/SKILL.md"
    # Subagents (verbatim copy)
    need_file "$ROOT/agents/rf-test-architect.md" "^name: rf-test-architect$"
    need_file "$ROOT/agents/rf-debug-expert.md"
    # Hooks block in settings.json
    need_file "$ROOT/settings.json"
    need_json_key "$ROOT/settings.json" 'hooks.PostToolUse'
    need_json_key "$ROOT/settings.json" 'hooks.UserPromptSubmit'
    need_json_key "$ROOT/settings.json" 'hooks.SessionStart'
    need_json_key "$ROOT/settings.json" 'hooks.Stop'
    # MCP server registered in user-scope .mcp.json
    need_file "$HOME/.mcp.json"
    need_json_key "$HOME/.mcp.json" 'mcpServers."rf-tools"'
    # Plugin co-located scripts staged
    need_file "$PLUGIN_FILES/scripts/validate_robot.sh"
    need_file "$PLUGIN_FILES/scripts/maybe_inject_rf_context.sh"
    need_file "$PLUGIN_FILES/.claude-plugin/plugin.json"
    # Substitution actually happened (no literal ${CLAUDE_PLUGIN_ROOT} left)
    need_no_substitution "$PLUGIN_FILES/scripts/validate_robot.sh"
    need_no_substitution "$ROOT/settings.json"

    # Agent-side validation: `claude plugin validate` parses the plugin
    # manifest and reports schema errors. This is API-free.
    if claude plugin validate "$PLUGIN_FILES" >/dev/null 2>&1; then
        printf '  [check] claude plugin validate: OK\n' >&2
    else
        printf '  [check] claude plugin validate FAILED:\n' >&2
        claude plugin validate "$PLUGIN_FILES" >&2 || true
        exit 1
    fi
    ;;

--post-uninstall)
    need_no_file "$ROOT/skills/libdoc-search/SKILL.md"
    need_no_file "$ROOT/agents/rf-test-architect.md"
    # settings.json may persist if it had pre-existing keys, but the hooks
    # block we added must be gone:
    if [ -f "$ROOT/settings.json" ]; then
        if jq -e '.hooks' "$ROOT/settings.json" >/dev/null 2>&1; then
            printf '  [check] hooks block survived uninstall\n' >&2
            exit 1
        fi
    fi
    if [ -f "$HOME/.mcp.json" ]; then
        if jq -e '.mcpServers."rf-tools"' "$HOME/.mcp.json" >/dev/null 2>&1; then
            printf '  [check] rf-tools MCP entry survived uninstall\n' >&2
            exit 1
        fi
    fi
    ;;

--api-smoke)
    if [ -z "${ANTHROPIC_AUTH_TOKEN:-${ANTHROPIC_API_KEY:-${OPENROUTER_API_KEY:-}}}" ]; then
        skip "no Claude/Anthropic/OpenRouter token in env"
    fi
    # Re-install (uninstall happened before this in the entrypoint flow,
    # so we need files in place again). Caller of --api-smoke can either
    # run before --post-uninstall (preferred) or re-install here.
    if [ ! -f "$ROOT/skills/libdoc-search/SKILL.md" ]; then
        skip "no install present (--api-smoke must run before --post-uninstall)"
    fi

    # `claude -p` writes the system/init event first; it lists `skills`.
    INIT=$(claude -p "ok" --output-format stream-json --verbose \
                  --max-turns 1 --no-session-persistence 2>/dev/null \
           | head -1 || true)
    if [ -z "$INIT" ]; then
        printf '  [check] no stream output from claude (auth issue?)\n' >&2
        exit 1
    fi
    if ! echo "$INIT" | jq -e '.skills | index("libdoc-search")' >/dev/null; then
        printf '  [check] libdoc-search not in init event\n' >&2
        echo "$INIT" | jq -r '.skills' >&2 || true
        exit 1
    fi
    ;;

*)
    echo "usage: $0 --post-install | --post-uninstall | --api-smoke" >&2
    exit 64
    ;;
esac

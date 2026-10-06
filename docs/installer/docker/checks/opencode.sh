#!/usr/bin/env bash
# Validate `rf-agentskills install --agent opencode`.
# OpenCode install paths (per opencode.ai/docs/skills/, May 2026):
#   $HOME/.config/opencode/skills/<name>/
#   $HOME/.config/opencode/agents/<name>.md
#
# No MCP server config: the rf-tools MCP server was removed, and with
# it opencode.json's `mcp` block and the rf-agentskills-files/ staging
# that existed only to support the MCP server's command path.

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

OPENCODE="$HOME/.config/opencode"
PLUGIN_FILES="$OPENCODE/rf-agentskills-files"

case "${1:-}" in
--post-install)
    # Native skill placement (verbatim copy)
    need_file "$OPENCODE/skills/rf-libdoc/SKILL.md" "^name: rf-libdoc$"
    # Merged into libdoc (content 2.0.0): the old libdoc skills are not shipped
    need_no_file "$OPENCODE/skills/libdoc-search/SKILL.md"
    need_no_file "$OPENCODE/skills/libdoc-explain/SKILL.md"
    need_no_file "$OPENCODE/skills/libdoc/SKILL.md"   # renamed to rf-libdoc in content 2.0.0
    need_file "$OPENCODE/skills/rf-results/SKILL.md"
    need_file "$OPENCODE/skills/rf-language/scripts/rf_conventions.py"
    need_file "$OPENCODE/skills/rf-python-library/scripts/check_library.py"
    need_no_file "$OPENCODE/skills/keyword-builder/SKILL.md"   # retired in content 2.0.0
    # Native subagent placement
    need_file "$OPENCODE/agents/rf-test-architect.md" "^name: rf-test-architect$"
    # rf-tools MCP server was removed: no opencode.json "mcp" block, and
    # no rf-agentskills-files/ at all (it existed only to support the
    # MCP server's command path).
    if [ -f "$OPENCODE/opencode.json" ]; then
        if jq -e '.mcp."rf-tools"' "$OPENCODE/opencode.json" >/dev/null 2>&1; then
            printf '  [check] opencode.json unexpectedly has an rf-tools mcp entry\n' >&2
            exit 1
        fi
    fi
    need_no_file "$PLUGIN_FILES/scripts/validate_robot.mjs"

    # API-FREE introspection: opencode ships `opencode debug skill`
    # which walks every skill discovery path and emits JSON. No LLM call.
    if opencode debug skill 2>/dev/null > /tmp/opencode-debug-skill.txt; then
        if grep -qF "$OPENCODE/skills/rf-libdoc/SKILL.md" /tmp/opencode-debug-skill.txt; then
            printf '  [check] opencode debug skill sees libdoc\n' >&2
        else
            printf '  [check] opencode debug skill did NOT find libdoc\n' >&2
            head -20 /tmp/opencode-debug-skill.txt >&2 || true
            exit 1
        fi
    else
        printf '  [check] opencode debug skill failed to run\n' >&2
        # Don't fail outright — older OpenCode versions may not have this command
    fi
    ;;

--post-uninstall)
    need_no_file "$OPENCODE/skills/rf-libdoc/SKILL.md"
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
    if [ ! -f "$OPENCODE/skills/rf-libdoc/SKILL.md" ]; then
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

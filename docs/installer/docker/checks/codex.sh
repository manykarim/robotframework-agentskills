#!/usr/bin/env bash
# Validate `rf-agentskills install --agent codex`.
# Codex install paths (per developers.openai.com/codex/skills):
#   $HOME/.agents/skills/<name>/   (cross-vendor universal)
#   $HOME/.codex/agents/<name>.toml
#   $HOME/.codex/config.toml       ([mcp_servers.<name>])
#   $HOME/.codex/hooks.json        (gated by [features] codex_hooks=true)

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

CODEX="$HOME/.codex"
AGENTS_SKILLS="$HOME/.agents/skills"
PLUGIN_FILES="$CODEX/rf-agentskills-files"

case "${1:-}" in
--post-install)
    # Skills at the canonical cross-vendor location
    need_file "$AGENTS_SKILLS/libdoc-search/SKILL.md" "^name: libdoc-search$"
    need_file "$AGENTS_SKILLS/keyword-builder/SKILL.md"
    # Subagents transformed to TOML
    need_file "$CODEX/agents/rf-test-architect.toml"
    need_toml_key "$CODEX/agents/rf-test-architect.toml" 'name'
    need_toml_key "$CODEX/agents/rf-test-architect.toml" 'description'
    need_toml_key "$CODEX/agents/rf-test-architect.toml" 'developer_instructions'
    # MCP server registered in config.toml
    need_file "$CODEX/config.toml"
    # Key path uses dot-separator; quote semantics aren't needed since
    # ``rf-tools`` has no literal dots.
    need_toml_key "$CODEX/config.toml" 'mcp_servers.rf-tools'
    # Hooks file copied (the codex_hooks feature flag is the user's
    # responsibility — we don't toggle it)
    need_file "$CODEX/hooks.json"
    # Plugin scripts staged
    need_file "$PLUGIN_FILES/scripts/validate_robot.sh"
    need_no_substitution "$PLUGIN_FILES/scripts/validate_robot.sh"

    # API-free agent introspection: codex's bundled skill-installer
    # reads $CODEX_HOME/skills (and Codex itself reads .agents/skills).
    # The CLI itself has no `codex skills list` command, but we can
    # confirm Codex's own search path includes .agents/skills by
    # checking the installed skill-installer's source.
    if [ -f "$CODEX/skills/.system/skill-installer/scripts/install-skill-from-github.py" ]; then
        if grep -qF '"$HOME/.agents/skills"' \
            "$CODEX/skills/.system/skill-installer/scripts/install-skill-from-github.py" 2>/dev/null \
        || grep -qF '.agents/skills' \
            "$CODEX/skills/.system/skill-installer/SKILL.md" 2>/dev/null; then
            printf '  [check] codex sees .agents/skills as a search path\n' >&2
        fi
    fi
    ;;

--post-uninstall)
    need_no_file "$AGENTS_SKILLS/libdoc-search/SKILL.md"
    need_no_file "$CODEX/agents/rf-test-architect.toml"
    need_no_file "$CODEX/hooks.json"
    if [ -f "$CODEX/config.toml" ]; then
        # rf-tools entry must be gone (file may persist if user had
        # other settings — that's fine).
        if python3 -c "
import sys
try: import tomllib
except ImportError: import tomli as tomllib
d = tomllib.loads(open('$CODEX/config.toml').read())
sys.exit(1 if 'rf-tools' in d.get('mcp_servers', {}) else 0)
"; then
            :
        else
            printf '  [check] rf-tools mcp_servers entry survived uninstall\n' >&2
            exit 1
        fi
    fi
    ;;

--api-smoke)
    if [ -z "${OPENROUTER_API_KEY:-${OPENAI_API_KEY:-}}" ]; then
        skip "no OpenRouter/OpenAI token in env"
    fi
    # Use Codex's session rollout to verify skill discovery.
    if [ ! -f "$AGENTS_SKILLS/libdoc-search/SKILL.md" ]; then
        skip "no install present (--api-smoke must run before --post-uninstall)"
    fi
    codex exec --json --skip-git-repo-check "ok" >/dev/null 2>&1 || true
    ROLLOUT=$(ls -t "$CODEX"/sessions/*/*/*/rollout-*.jsonl 2>/dev/null | head -1)
    if [ -z "$ROLLOUT" ]; then
        printf '  [check] no codex rollout file produced\n' >&2
        exit 1
    fi
    if ! grep -F "/skills/libdoc-search/SKILL.md" "$ROLLOUT" >/dev/null; then
        printf '  [check] libdoc-search SKILL.md not referenced in rollout\n' >&2
        exit 1
    fi
    ;;

*)
    echo "usage: $0 --post-install | --post-uninstall | --api-smoke" >&2
    exit 64
    ;;
esac

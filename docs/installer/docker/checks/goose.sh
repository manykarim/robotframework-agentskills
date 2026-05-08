#!/usr/bin/env bash
# Validate `rf-agentskills install --agent goose`.
# Goose install paths (per goose-docs.ai .../using-skills/, v1.25+):
#   $HOME/.agents/skills/<name>/   (cross-vendor universal)
#   $HOME/.config/goose/config.yaml  (extensions block)
#   $HOME/.goosehints                 (persona text)

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

GOOSE_CONFIG="$HOME/.config/goose"
AGENTS_SKILLS="$HOME/.agents/skills"
PLUGIN_FILES="$GOOSE_CONFIG/rf-agentskills-files"

case "${1:-}" in
--post-install)
    # Skills at the cross-vendor location
    need_file "$AGENTS_SKILLS/libdoc-search/SKILL.md" "^name: libdoc-search$"
    need_file "$AGENTS_SKILLS/keyword-builder/SKILL.md"
    # MCP extension in config.yaml
    need_file "$GOOSE_CONFIG/config.yaml"
    need_yaml_key "$GOOSE_CONFIG/config.yaml" 'extensions.rf-tools'
    # Persona text in goosehints
    need_file "$HOME/.goosehints" 'rf-test-architect' 'rf-agentskills'
    # Plugin scripts staged
    need_file "$PLUGIN_FILES/scripts/validate_robot.sh"
    need_no_substitution "$PLUGIN_FILES/scripts/validate_robot.sh"

    # API-free agent introspection: try `goose info` for any
    # filesystem reflection. `goose info` doesn't list skills directly
    # but confirms config.yaml is parseable.
    if goose info >/dev/null 2>&1; then
        printf '  [check] goose info: config readable\n' >&2
    fi
    ;;

--post-uninstall)
    need_no_file "$AGENTS_SKILLS/libdoc-search/SKILL.md"
    need_no_file "$HOME/.goosehints"
    if [ -f "$GOOSE_CONFIG/config.yaml" ]; then
        if python3 -c "
import sys, yaml
d = yaml.safe_load(open('$GOOSE_CONFIG/config.yaml')) or {}
sys.exit(1 if 'rf-tools' in d.get('extensions', {}) else 0)
"; then
            :
        else
            printf '  [check] rf-tools extension survived uninstall\n' >&2
            exit 1
        fi
    fi
    ;;

--api-smoke)
    if [ -z "${OPENROUTER_API_KEY:-}" ]; then
        skip "no OpenRouter token; configure OPENROUTER_API_KEY for Goose smoke"
    fi
    if [ ! -f "$AGENTS_SKILLS/libdoc-search/SKILL.md" ]; then
        skip "no install present"
    fi
    # Goose configures via env vars. The harness entrypoint should have
    # set GOOSE_PROVIDER + GOOSE_MODEL + GOOSE_DISABLE_KEYRING already.
    OUT=$(goose run --recipe /dev/stdin --no-session 2>&1 <<'YAML' || true
version: "1.0"
title: rf-agentskills smoke
description: Smoke test for skill discovery
instructions: "Reply 'ok' and stop."
YAML
)
    if echo "$OUT" | grep -qiE 'libdoc-search|rf-tools|extension'; then
        printf '  [check] goose surfaced skill / extension reference\n' >&2
    else
        printf '  [check] no skill reference in goose run output\n' >&2
        # Goose's startup logs aren't always rich — treat absence as soft fail
        exit 1
    fi
    ;;

*)
    echo "usage: $0 --post-install | --post-uninstall | --api-smoke" >&2
    exit 64
    ;;
esac

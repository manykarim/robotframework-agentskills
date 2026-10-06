#!/usr/bin/env bash
# Validate `rf-agentskills install --agent goose`.
# Goose install paths (per goose-docs.ai .../using-skills/, v1.25+):
#   $HOME/.agents/skills/<name>/   (cross-vendor universal)
#   $HOME/.goosehints                 (persona text)
#
# No MCP server config: the rf-tools MCP server was removed, and with
# it config.yaml's "extensions" merge and the rf-agentskills-files/
# staging that existed only to support the MCP server's command path.
# The installer no longer writes config.yaml at all (a pre-existing
# one is only ever touched to retire a legacy rf-tools entry).

set -euo pipefail
. "$(dirname "$0")/_lib.sh"

GOOSE_CONFIG="$HOME/.config/goose"
AGENTS_SKILLS="$HOME/.agents/skills"
PLUGIN_FILES="$GOOSE_CONFIG/rf-agentskills-files"

case "${1:-}" in
--post-install)
    # Skills at the cross-vendor location
    need_file "$AGENTS_SKILLS/rf-libdoc/SKILL.md" "^name: rf-libdoc$"
    # Merged into libdoc (content 2.0.0): the old libdoc skills are not shipped
    need_no_file "$AGENTS_SKILLS/libdoc-search/SKILL.md"
    need_no_file "$AGENTS_SKILLS/libdoc-explain/SKILL.md"
    need_no_file "$AGENTS_SKILLS/libdoc/SKILL.md"   # renamed to rf-libdoc in content 2.0.0
    need_file "$AGENTS_SKILLS/rf-results/SKILL.md"
    need_file "$AGENTS_SKILLS/rf-language/scripts/rf_conventions.py"
    need_file "$AGENTS_SKILLS/rf-python-library/scripts/check_library.py"
    need_no_file "$AGENTS_SKILLS/keyword-builder/SKILL.md"   # retired in content 2.0.0
    # Persona text in goosehints
    need_file "$HOME/.goosehints" 'rf-test-architect' 'rf-agentskills'
    # rf-tools MCP server was removed: config.yaml isn't written by the
    # installer at all, so no "extensions.rf-tools" key should exist
    # (only checked if a pre-existing config.yaml happens to be there),
    # and no rf-agentskills-files/ staging landed on disk.
    if [ -f "$GOOSE_CONFIG/config.yaml" ]; then
        if python3 -c "
import sys, yaml
d = yaml.safe_load(open('$GOOSE_CONFIG/config.yaml')) or {}
sys.exit(0 if 'rf-tools' in d.get('extensions', {}) else 1)
"; then
            printf '  [check] config.yaml unexpectedly has an rf-tools extension\n' >&2
            exit 1
        fi
    fi
    need_no_file "$PLUGIN_FILES/scripts/validate_robot.mjs"

    # API-free agent introspection: try `goose info` for any
    # filesystem reflection. `goose info` doesn't list skills directly
    # but confirms config.yaml is parseable.
    if goose info >/dev/null 2>&1; then
        printf '  [check] goose info: config readable\n' >&2
    fi
    ;;

--post-uninstall)
    need_no_file "$AGENTS_SKILLS/rf-libdoc/SKILL.md"
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
    if [ ! -f "$AGENTS_SKILLS/rf-libdoc/SKILL.md" ]; then
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
    if echo "$OUT" | grep -qiE 'libdoc|rf-tools|extension'; then
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

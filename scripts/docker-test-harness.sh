#!/usr/bin/env bash
# Host-side wrapper for the rf-agentskills Docker test harness.
#
# Builds the image (cached after first run) and executes the
# in-container entrypoint, which installs each requested agent's
# bundle and runs API-free validation. Optional `--api` flag adds
# vendor-token-driven smoke tests for agents that support headless
# operation (Claude Code, Codex, OpenCode, Goose).
#
# Usage:
#   scripts/docker-test-harness.sh
#       Run the default sweep (all CLI agents) with API-free checks.
#
#   scripts/docker-test-harness.sh --agents claude-code codex
#       Run only the listed agents.
#
#   scripts/docker-test-harness.sh --api
#       Add API smoke tests. Requires OPENROUTER_API_KEY env var.
#
#   scripts/docker-test-harness.sh --rebuild
#       Force a fresh image build.
#
# All flags can be combined.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="rf-agentskills-test:latest"
DOCKERFILE="$REPO_ROOT/docs/installer/docker/Dockerfile"

agents="claude-code codex goose opencode cursor claude-desktop copilot"
api_mode="0"
rebuild="0"

while [ $# -gt 0 ]; do
    case "$1" in
        --agents)
            shift
            # Read remaining tokens until next flag or end
            agents=""
            while [ $# -gt 0 ] && [[ "$1" != --* ]]; do
                agents="$agents $1"
                shift
            done
            agents="${agents# }"
            ;;
        --api)
            api_mode="1"
            shift
            ;;
        --rebuild)
            rebuild="1"
            shift
            ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "unknown flag: $1" >&2
            echo "see --help" >&2
            exit 64
            ;;
    esac
done

# ── Build image ─────────────────────────────────────────────────────────────
if [ "$rebuild" = "1" ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "::: building $IMAGE :::"
    docker build -f "$DOCKERFILE" -t "$IMAGE" "$REPO_ROOT"
else
    echo "::: image $IMAGE already built (use --rebuild to refresh) :::"
fi

# ── Validate API mode prerequisites ─────────────────────────────────────────
docker_env_args=()
if [ "$api_mode" = "1" ]; then
    if [ -z "${OPENROUTER_API_KEY:-}" ]; then
        echo "error: --api requires OPENROUTER_API_KEY in env" >&2
        echo "       get a key at https://openrouter.ai/keys" >&2
        exit 1
    fi
    docker_env_args+=(
        -e "OPENROUTER_API_KEY=$OPENROUTER_API_KEY"
        -e "RF_HARNESS_API=1"
        # Claude Code reads its own env names — point all of them at OR.
        -e "ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1"
        -e "ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY"
        -e "ANTHROPIC_MODEL=anthropic/claude-haiku-4-5"
        # Goose
        -e "GOOSE_PROVIDER=openrouter"
        -e "GOOSE_MODEL=anthropic/claude-haiku-4-5"
        -e "GOOSE_DISABLE_KEYRING=1"
    )
    echo "::: --api enabled — will spend ~1¢ in OpenRouter credits :::"
fi

# ── Run ─────────────────────────────────────────────────────────────────────
echo "::: harness sweep: $agents :::"
# We bind-mount the check scripts and entrypoint over the image's
# baked-in copies so iterating on the harness itself doesn't require
# a rebuild. The image still ships a working copy as a fallback for
# `docker run` invocations that don't bind-mount.
docker run --rm --init \
    --tmpfs /root \
    --tmpfs /tmp \
    -e "RF_HARNESS_AGENTS=$agents" \
    "${docker_env_args[@]}" \
    -v "$REPO_ROOT:/work:ro" \
    -v "$REPO_ROOT/docs/installer/docker/entrypoint.sh:/usr/local/bin/rf-harness-entry:ro" \
    -v "$REPO_ROOT/docs/installer/docker/checks:/usr/local/lib/rf-harness-checks:ro" \
    "$IMAGE"

#!/usr/bin/env bash
# Shared setup for skill-eval local scripts.
# Sourced by eval-smoke.sh and eval-local.sh; safe to run standalone.
set -euo pipefail
trap 'printf "\033[31m[eval-setup] failed at line %s\033[0m\n" "$LINENO" >&2' ERR

# Resolve repo root regardless of caller CWD.
EVAL_SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${EVAL_SETUP_DIR}/.." && pwd)"
export REPO_ROOT
cd "${REPO_ROOT}"

_info()  { printf '\033[36m[eval-setup]\033[0m %s\n' "$*" >&2; }
_warn()  { printf '\033[33m[eval-setup]\033[0m %s\n' "$*" >&2; }
_err()   { printf '\033[31m[eval-setup]\033[0m %s\n' "$*" >&2; }

# Parse flags
FORCE_RFBROWSER=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE_RFBROWSER=1 ;;
  esac
done

# 1. uv required
if ! command -v uv >/dev/null 2>&1; then
  _err "'uv' not found on PATH."
  _err "Install: https://docs.astral.sh/uv/getting-started/installation/"
  _err "Quick install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
_info "uv: $(uv --version)"

# 2. claude CLI required
if ! command -v claude >/dev/null 2>&1; then
  _err "'claude' CLI not found on PATH."
  _err "Install: npm install -g @anthropic-ai/claude-code"
  exit 1
fi
_info "claude CLI: $(claude --version 2>/dev/null || echo 'installed')"

# 3. .env file
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    _warn ".env missing; copying from .env.example."
    cp .env.example .env
    _warn "Edit .env to set CLAUDE_CODE_OAUTH_TOKEN (or ANTHROPIC_API_KEY) before re-running."
    exit 1
  else
    _err ".env and .env.example both missing; create .env with CLAUDE_CODE_OAUTH_TOKEN."
    exit 1
  fi
fi

# Source .env (export every assignment) without clobbering existing exported values.
set -a
# shellcheck disable=SC1091
source .env
set +a

# 4. Auth var present
if [[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  _err "Neither CLAUDE_CODE_OAUTH_TOKEN nor ANTHROPIC_API_KEY is set in .env."
  _err "Primary auth: CLAUDE_CODE_OAUTH_TOKEN (see ADR-005)."
  exit 1
fi
if [[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
  _info "Auth: using CLAUDE_CODE_OAUTH_TOKEN (primary)."
else
  _warn "Auth: falling back to ANTHROPIC_API_KEY (OAuth token not set)."
fi

# 5. Install/refresh Python deps
_info "Syncing Python dependencies with uv..."
uv sync

# 6. rfbrowser init (idempotent via flag file)
RFBROWSER_FLAG=".venv/.rfbrowser-initialized"
if [[ "${FORCE_RFBROWSER}" -eq 1 || ! -f "${RFBROWSER_FLAG}" ]]; then
  _info "Initializing Playwright browsers (rfbrowser init)..."
  uv run rfbrowser init
  mkdir -p "$(dirname "${RFBROWSER_FLAG}")"
  touch "${RFBROWSER_FLAG}"
else
  _info "rfbrowser already initialized (use --force to re-run)."
fi

# 7. Doctor health check
_info "Running rf-skill-eval doctor..."
uv run rf-skill-eval doctor

_info "Setup complete."

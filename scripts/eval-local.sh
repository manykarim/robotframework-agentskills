#!/usr/bin/env bash
# Full local pipeline: lint + unit tests + narrow tier eval + optional realistic tier.
# Intended as a pre-push validation gate. Exits non-zero on any failed gate.
set -euo pipefail
trap 'printf "\033[31m[eval-local] failed at line %s\033[0m\n" "$LINENO" >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./eval-setup.sh
source "${SCRIPT_DIR}/eval-setup.sh"

_info() { printf '\033[36m[eval-local]\033[0m %s\n' "$*" >&2; }
_warn() { printf '\033[33m[eval-local]\033[0m %s\n' "$*" >&2; }
_err()  { printf '\033[31m[eval-local]\033[0m %s\n' "$*" >&2; }

# Gate 1: lint
_info "Gate 1/4: ruff check src tests/eval"
uv run ruff check src tests/eval

# Gate 2: unit tests
_info "Gate 2/4: pytest tests/eval"
uv run pytest tests/eval -v

# Gate 3: narrow-tier evaluation
RUN_ROOT="eval/runs/local-$(date +%s)"
NARROW_DIR="${RUN_ROOT}/narrow"
_info "Gate 3/4: narrow-tier eval -> ${NARROW_DIR}"

uv run rf-skill-eval run-batch \
  --tasks-dir eval/tasks/narrow \
  --profile treatment \
  --output "${NARROW_DIR}" \
  --concurrency 1

uv run rf-skill-eval score-batch --runs-dir "${NARROW_DIR}" --tasks-dir eval/tasks/narrow

# Gate 4: optional realistic tier
run_realistic=0
if [[ "${EVAL_LOCAL_REALISTIC:-}" == "1" ]]; then
  run_realistic=1
  _info "EVAL_LOCAL_REALISTIC=1 set; running realistic tier automatically."
else
  printf '\033[33m[eval-local]\033[0m Run realistic tier? (slow + more tokens) [y/N] ' >&2
  read -r answer || answer=""
  case "${answer}" in
    y|Y|yes|YES) run_realistic=1 ;;
    *) _info "Skipping realistic tier." ;;
  esac
fi

if [[ "${run_realistic}" -eq 1 ]]; then
  REALISTIC_DIR="${RUN_ROOT}/realistic"
  _info "Gate 4/4: realistic-tier eval -> ${REALISTIC_DIR}"
  uv run rf-skill-eval run-batch \
    --tasks-dir eval/tasks/realistic \
    --profile treatment \
    --output "${REALISTIC_DIR}" \
    --concurrency 1
  uv run rf-skill-eval score-batch --runs-dir "${REALISTIC_DIR}" --tasks-dir eval/tasks/realistic
fi

# Final report
REPORT_PATH="${RUN_ROOT}/report.md"
_info "Generating combined report..."
uv run rf-skill-eval report --runs-dir "${RUN_ROOT}" --format md --output "${REPORT_PATH}"

_info "All gates passed."
_info "Report: ${REPORT_PATH}"

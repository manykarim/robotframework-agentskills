#!/usr/bin/env bash
# Fast smoke test: one narrow task with Haiku. Target: <=5 min wall time.
set -euo pipefail
trap 'printf "\033[31m[eval-smoke] failed at line %s\033[0m\n" "$LINENO" >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./eval-setup.sh
source "${SCRIPT_DIR}/eval-setup.sh"

_info() { printf '\033[36m[eval-smoke]\033[0m %s\n' "$*" >&2; }
_err()  { printf '\033[31m[eval-smoke]\033[0m %s\n' "$*" >&2; }

TASK="eval/tasks/narrow/narrow-keyword-builder-01.yaml"
if [[ ! -f "${TASK}" ]]; then
  _err "Smoke task not found: ${TASK}"
  exit 1
fi

RUN_DIR="eval/runs/smoke-$(date +%s)"
_info "Running smoke task: ${TASK}"
_info "Output: ${RUN_DIR}"

uv run rf-skill-eval run \
  --task "${TASK}" \
  --profile treatment \
  --model claude-haiku-4-5 \
  --output "${RUN_DIR}"

_info "Scoring..."
uv run rf-skill-eval score-batch \
  --runs-dir "${RUN_DIR}" \
  --tasks-dir "$(dirname "${TASK}")"

REPORT_PATH="${RUN_DIR}/report.md"
_info "Generating report..."
uv run rf-skill-eval report \
  --runs-dir "${RUN_DIR}" \
  --format md \
  --output "${REPORT_PATH}"

_info "Report: ${REPORT_PATH}"
cat "${REPORT_PATH}"

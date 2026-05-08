#!/usr/bin/env bash
# Container entrypoint for the rf-agentskills Docker test harness.
#
# Sequence per agent:
#   1. install   →  rf-agentskills install --agent <name>
#   2. validate  →  /usr/local/lib/rf-harness-checks/<name>.sh
#   3. uninstall →  rf-agentskills uninstall --agent <name>
#   4. confirm   →  /usr/local/lib/rf-harness-checks/<name>.sh --post-uninstall
#
# Validation is API-free by default. If RF_HARNESS_API=1 and a vendor
# token is present, an additional smoke test makes one cheap LLM round-
# trip to verify the agent's init event lists the installed skill.
#
# Output: human-readable progress to stdout. Per-agent JSON summary
# appended to $RF_HARNESS_LOG so the host can parse the result.

set -euo pipefail

RF_HARNESS_LOG="${RF_HARNESS_LOG:-/tmp/rf-harness.log}"
RF_HARNESS_AGENTS="${RF_HARNESS_AGENTS:-claude-code codex goose opencode cursor claude-desktop copilot}"
RF_HARNESS_API="${RF_HARNESS_API:-0}"
CHECKS_DIR="/usr/local/lib/rf-harness-checks"

# Pretty colours when stdout is a tty; plain otherwise.
if [ -t 1 ]; then
    C_GREEN=$(printf '\033[32m'); C_RED=$(printf '\033[31m')
    C_YELLOW=$(printf '\033[33m'); C_DIM=$(printf '\033[2m')
    C_BOLD=$(printf '\033[1m'); C_RESET=$(printf '\033[0m')
else
    C_GREEN=""; C_RED=""; C_YELLOW=""; C_DIM=""; C_BOLD=""; C_RESET=""
fi

log()    { printf '%s\n' "$*" | tee -a "$RF_HARNESS_LOG" >&2; }
banner() { printf '\n%s═══ %s ═══%s\n' "$C_BOLD" "$*" "$C_RESET" >&2; }
ok()     { printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*" >&2; }
fail()   { printf '%s✗%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; }
note()   { printf '%s•%s %s\n' "$C_DIM" "$C_RESET" "$*" >&2; }

: > "$RF_HARNESS_LOG"

# ─────────────────────────────────────────────────────────────────────────────
# 0. install rf-agentskills from the mounted source
# ─────────────────────────────────────────────────────────────────────────────
banner "rf-agentskills install (from /work/installer)"
if [ ! -d /work/installer ] || [ ! -d /work/plugins/rf-agentskills ]; then
    fail "expected /work/installer and /work/plugins/rf-agentskills to be mounted"
    exit 2
fi
# /work is mounted read-only so the host source can't be polluted. The
# hatch build hook needs to write into installer/src/rf_agentskills/_assets/
# at install time, so we copy the bits we need into a writable tmpfs
# location first. Bind-mount-vs-copy is intentional: it keeps the host
# source unchanged and makes the in-container build idempotent.
INSTALL_SRC=/tmp/rf-agentskills-src
mkdir -p "$INSTALL_SRC"
cp -r /work/installer "$INSTALL_SRC/"
cp -r /work/plugins   "$INSTALL_SRC/"

cd "$INSTALL_SRC/installer"
uv pip install --system --quiet --no-deps -e .
cd /
rf-agentskills version
rf-agentskills targets || true
ok "installer ready"

# ─────────────────────────────────────────────────────────────────────────────
# 1. per-agent install / validate / uninstall sweep
# ─────────────────────────────────────────────────────────────────────────────
overall_rc=0
declare -A results

for agent in $RF_HARNESS_AGENTS; do
    banner "$agent"
    check="$CHECKS_DIR/${agent}.sh"
    if [ ! -x "$check" ]; then
        note "no check script for $agent — skipping"
        results[$agent]="skipped"
        continue
    fi

    # 1a. install
    note "rf-agentskills install --agent $agent"
    if ! rf-agentskills install --agent "$agent" >> "$RF_HARNESS_LOG" 2>&1; then
        fail "install failed for $agent (see $RF_HARNESS_LOG)"
        results[$agent]="install-failed"
        overall_rc=1
        continue
    fi

    # 1b. validate (filesystem + API-free introspection)
    if "$check" --post-install; then
        ok "$agent: post-install checks passed"
    else
        fail "$agent: post-install checks failed"
        results[$agent]="validation-failed"
        overall_rc=1
        # Don't continue: we still want uninstall to clean up.
    fi

    # 1c. optional API smoke test
    if [ "$RF_HARNESS_API" = "1" ]; then
        if "$check" --api-smoke 2>>"$RF_HARNESS_LOG"; then
            ok "$agent: API smoke test passed"
        else
            fail "$agent: API smoke test failed"
            results[$agent]="${results[$agent]:-validation-failed}"
            overall_rc=1
        fi
    fi

    # 1d. uninstall
    note "rf-agentskills uninstall --agent $agent"
    if ! rf-agentskills uninstall --agent "$agent" >> "$RF_HARNESS_LOG" 2>&1; then
        fail "uninstall failed for $agent"
        results[$agent]="uninstall-failed"
        overall_rc=1
        continue
    fi

    # 1e. confirm clean
    if "$check" --post-uninstall; then
        ok "$agent: uninstall left no traces"
        results[$agent]="${results[$agent]:-passed}"
    else
        fail "$agent: leftover files after uninstall"
        results[$agent]="uninstall-leftovers"
        overall_rc=1
    fi
done

# ─────────────────────────────────────────────────────────────────────────────
# 2. summary
# ─────────────────────────────────────────────────────────────────────────────
banner "summary"
for agent in $RF_HARNESS_AGENTS; do
    state="${results[$agent]:-not-run}"
    case "$state" in
        passed)            ok    "$agent : $state" ;;
        skipped|not-run)   note  "$agent : $state" ;;
        *)                 fail  "$agent : $state" ;;
    esac
done

if [ $overall_rc -eq 0 ]; then
    printf '\n%s%sharness PASSED%s\n' "$C_BOLD" "$C_GREEN" "$C_RESET" >&2
else
    printf '\n%s%sharness FAILED%s — see %s\n' "$C_BOLD" "$C_RED" "$C_RESET" "$RF_HARNESS_LOG" >&2
fi
exit $overall_rc

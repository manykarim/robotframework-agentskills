#!/usr/bin/env bash
# Check for drift between root skills/ and plugin/vscode distribution copies.
# Exit 1 if any drift or orphaned copy is found.
#
# REPO_ROOT can be overridden (used by tests to run against a scratch tree).
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
# Python and a root path it can open: on Windows (Git Bash) python3 may not
# exist and /d/a/... paths are not valid for a native Windows Python.
PY="$(command -v python3 || command -v python)"
if command -v cygpath >/dev/null 2>&1; then PY_ROOT="$(cygpath -m "$REPO_ROOT")"; else PY_ROOT="$REPO_ROOT"; fi
DRIFT_FOUND=0

# ── Derived from root: every non-symlink skills/*/scripts/*.py ───────────────
declare -A SCRIPT_MAP=()
while IFS= read -r src; do
    rel="${src#"$REPO_ROOT"/}"
    skill="$(basename "$(dirname "$(dirname "$src")")")"
    SCRIPT_MAP["$rel"]="plugins/rf-agentskills/skills/$skill/scripts/$(basename "$src")"
done < <(find "$REPO_ROOT/skills" -mindepth 3 -maxdepth 3 -path '*/scripts/*.py' -type f | sort)

echo "=== Checking script drift: root skills/ vs plugin skills/<skill>/scripts/ ==="
for root_path in $(printf '%s\n' "${!SCRIPT_MAP[@]}" | sort); do
    plugin_path="${SCRIPT_MAP[$root_path]}"
    root_file="$REPO_ROOT/$root_path"
    plugin_file="$REPO_ROOT/$plugin_path"

    if [ ! -f "$plugin_file" ]; then
        echo "MISSING: $plugin_path"
        DRIFT_FOUND=1
        continue
    fi

    if ! diff -q "$root_file" "$plugin_file" > /dev/null 2>&1; then
        echo "DRIFT: $root_path != $plugin_path"
        diff "$root_file" "$plugin_file" || true
        DRIFT_FOUND=1
    else
        echo "  OK: $root_path"
    fi
done

# ── VS Code copies of scripts must be byte-identical to root ────────────────
echo ""
echo "=== Checking script drift: root skills/ vs vscode-extension/skills/ ==="
for root_path in $(printf '%s\n' "${!SCRIPT_MAP[@]}" | sort); do
    skill_dir="$REPO_ROOT/$(dirname "$(dirname "$root_path")")"
    vscode_path="vscode-extension/skills/$(basename "$skill_dir")/scripts/$(basename "$root_path")"
    if [ ! -f "$REPO_ROOT/$vscode_path" ]; then
        echo "MISSING: $vscode_path"
        DRIFT_FOUND=1
    elif ! diff -q "$REPO_ROOT/$root_path" "$REPO_ROOT/$vscode_path" > /dev/null 2>&1; then
        echo "DRIFT: $root_path != $vscode_path"
        DRIFT_FOUND=1
    else
        echo "  OK: $vscode_path"
    fi
done

# ── Symlinks: no symbolic link may exist in any skill tree ──────────────────
echo ""
echo "=== Checking for symlinks in skill trees ==="
SYMLINKS=0
for tree in skills plugins/rf-agentskills/skills plugins/rf-agentskills/scripts vscode-extension/skills; do
    [ -d "$REPO_ROOT/$tree" ] || continue
    while IFS= read -r link; do
        echo "SYMLINK: ${link#"$REPO_ROOT"/}"
        SYMLINKS=1
    done < <(find "$REPO_ROOT/$tree" -type l | sort)
done
if [ $SYMLINKS -eq 1 ]; then
    DRIFT_FOUND=1
else
    echo "  OK: no symlinks"
fi

# ── Skill content: plugin + VS Code copies of every root skill ──────────────
# One identifier per skill: the channel dir name equals the root dir name.
# Plugin SKILL.md = root SKILL.md with only the script-path rewrite applied;
# VS Code SKILL.md is byte-identical; references/ and assets/ are identical.
echo ""
echo "=== Checking skill content: root skills/ vs plugin + vscode-extension ==="
plugin_transform() {
    sed -E 's#(python|--script) scripts/([a-z_]+\.py)#\1 "${CLAUDE_SKILL_DIR}/scripts/\2"#g' "$1"
}
declare -A ROOT_SKILLS=()
for skill_dir in "$REPO_ROOT"/skills/*/; do
    [ -d "$skill_dir" ] || continue
    name=$(basename "$skill_dir")
    ROOT_SKILLS["$name"]=1
    rf_name=$(head -5 "$skill_dir/SKILL.md" 2>/dev/null | grep "^name:" | sed 's/^name: *//' || true)
    if [ "$rf_name" != "$name" ]; then
        echo "NAME MISMATCH: skills/$name/SKILL.md has name: '$rf_name'"
        DRIFT_FOUND=1
    fi
    for channel in plugins/rf-agentskills/skills vscode-extension/skills; do
        copy="$REPO_ROOT/$channel/$name"
        if [ ! -d "$copy" ]; then
            echo "MISSING: $channel/$name/"
            DRIFT_FOUND=1
            continue
        fi
        if [ "$channel" = "vscode-extension/skills" ]; then
            skill_ok=0; cmp -s "$skill_dir/SKILL.md" "$copy/SKILL.md" && skill_ok=1
        else
            skill_ok=0; plugin_transform "$skill_dir/SKILL.md" | cmp -s - "$copy/SKILL.md" && skill_ok=1
        fi
        if [ $skill_ok -eq 0 ]; then
            echo "DRIFT: skills/$name/SKILL.md != $channel/$name/SKILL.md"
            DRIFT_FOUND=1
        fi
        for sub in scripts references assets; do
            if [ -d "$skill_dir/$sub" ] || [ -d "$copy/$sub" ]; then
                if ! diff -rq -x __pycache__ "$skill_dir/$sub" "$copy/$sub" > /dev/null 2>&1; then
                    echo "DRIFT: skills/$name/$sub/ != $channel/$name/$sub/"
                    DRIFT_FOUND=1
                fi
            fi
        done
    done
    echo "  checked: $name"
done

# ── Orphans: distribution copies without a root source ──────────────────────
echo ""
echo "=== Checking for orphaned distribution copies ==="

ORPHANS=0
for channel in plugins/rf-agentskills/skills vscode-extension/skills; do
    for copy in "$REPO_ROOT/$channel"/*/; do
        [ -d "$copy" ] || continue
        name=$(basename "$copy")
        [ "$channel/$name" = "vscode-extension/skills/skills" ] && continue  # double-nesting check below
        if [ -z "${ROOT_SKILLS[$name]:-}" ]; then
            echo "ORPHAN: $channel/$name/ (no root skills/$name/)"
            ORPHANS=1
        fi
    done
done

# Scripts ship per skill; any flat plugin scripts/*.py is a stale copy.
for plugin_script in "$REPO_ROOT"/plugins/rf-agentskills/scripts/*.py; do
    [ -f "$plugin_script" ] || continue
    echo "ORPHAN: plugins/rf-agentskills/scripts/$(basename "$plugin_script") (scripts ship in skills/<skill>/scripts/)"
    ORPHANS=1
done

if [ $ORPHANS -eq 1 ]; then
    DRIFT_FOUND=1
else
    echo "  OK: no orphans"
fi

# ── Command form: how SKILL.md files run bundled scripts ───────────────────
# No ${CLAUDE_PLUGIN_ROOT} in any SKILL.md (not expanded for every agent);
# no bare `python scripts/…` / `python3 scripts/…` (runs whatever python is on
# PATH instead of the project environment). Allowed prefixes: `uv run python`,
# `poetry run python`, a venv interpreter path (`.venv/bin/python`).
echo ""
echo "=== Checking script command form in SKILL.md (all channels) ==="
FORM_OUT=$(REPO_ROOT="$PY_ROOT" "$PY" - <<'PY'
import os, re, sys
from pathlib import Path
root = Path(os.environ["REPO_ROOT"])
bare = re.compile(r"(?<![\w/.\\-])python3? +(?:\"?\$\{CLAUDE_SKILL_DIR\}/)?scripts/")
bad = 0
for tree in ("skills", "plugins/rf-agentskills/skills", "vscode-extension/skills"):
    for md in sorted((root / tree).glob("*/SKILL.md")):
        rel = md.relative_to(root)
        for no, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if "${CLAUDE_PLUGIN_ROOT}" in line:
                print(f"PLUGIN_ROOT IN SKILL.md: {rel}:{no}")
                bad = 1
            for m in bare.finditer(line):
                before = line[: m.start()].rstrip()
                if before.endswith(" run") or before.endswith("`run") or before == "run":
                    continue
                print(f"BARE PYTHON: {rel}:{no}: {line.strip()}")
                bad = 1
sys.exit(bad)
PY
) && FORM_RC=0 || FORM_RC=$?
if [ -n "$FORM_OUT" ]; then echo "$FORM_OUT"; fi
if [ $FORM_RC -ne 0 ]; then
    DRIFT_FOUND=1
else
    echo "  OK: script commands use the project environment"
fi

echo ""
echo "=== Checking for double-nested vscode-extension/skills/skills/ ==="
if [ -d "$REPO_ROOT/vscode-extension/skills/skills" ]; then
    echo "ERROR: Double-nested vscode-extension/skills/skills/ directory exists!"
    DRIFT_FOUND=1
else
    echo "  OK: No double nesting"
fi

echo ""
if [ $DRIFT_FOUND -eq 1 ]; then
    echo "DRIFT DETECTED! Run: bash scripts/sync-skills.sh"
    exit 1
else
    echo "All files in sync."
    exit 0
fi

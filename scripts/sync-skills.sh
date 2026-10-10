#!/usr/bin/env bash
# Sync canonical skills/ to the plugin distribution channel.
#
# RULE: All edits happen in root skills/ only. This script propagates to:
#   - plugins/rf-agentskills/skills/   (SKILL.md transformed + scripts/references/assets copied)
#   - plugins/rf-agentskills/variants/ (Codex/OpenCode subagents and hooks, generated)
#
# Every skill ships its own scripts/ in every channel (regular files, no
# symlinks). The plugin keeps NO flat scripts/*.py copies; its scripts/ dir
# holds only the plugin-owned hook .mjs files.
#
# Run from the repository root.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
PLUGIN_DIR="$REPO_ROOT/plugins/rf-agentskills"

# ── Identity: every skill has ONE identifier, rf-<topic> ────────────────────
# The root directory name, the SKILL.md `name:` field and the directory name in
# every generated channel are the same (agentskills.io: name == parent dir).
# Sync copies; it never renames. A root dir whose name: differs is an error.
skill_name() {
    head -5 "$1/SKILL.md" 2>/dev/null | grep "^name:" | sed 's/^name: *//' || true
}
MISMATCH=0
for skill_dir in "$SKILLS_DIR"/*/; do
    dir_name=$(basename "$skill_dir")
    rf_name=$(skill_name "$skill_dir")
    if [ "$rf_name" != "$dir_name" ]; then
        echo "ERROR: skills/$dir_name/SKILL.md has name: '$rf_name' (must equal the directory name)" >&2
        MISMATCH=1
    fi
done
[ $MISMATCH -eq 0 ] || exit 1

# ── Helper: transform SKILL.md for plugin channel ───────────────────────────
# Only rewrite script COMMANDS (after `python ` or `--script `):
#   uv run python scripts/foo.py  ->  uv run python "${CLAUDE_SKILL_DIR}/scripts/foo.py"
# Claude Code substitutes ${CLAUDE_SKILL_DIR} (the plugin skill's own dir) in
# SKILL.md content; ${CLAUDE_PLUGIN_ROOT} is never written into a SKILL.md.
transform_skill_md_for_plugin() {
    sed -E 's#(python|--script) scripts/([a-z_]+\.py)#\1 "${CLAUDE_SKILL_DIR}/scripts/\2"#g' "$1" > "$2"
}

# ── Helper: copy a skill subdir as regular files (no __pycache__) ───────────
copy_tree() {
    local src="$1" dst="$2"
    rm -rf "$dst"
    [ -d "$src" ] || return 0
    mkdir -p "$dst"
    (cd "$src" && find . -type d -name __pycache__ -prune -o \( -type f -o -type l \) -print) | while IFS= read -r rel; do
        mkdir -p "$dst/$(dirname "$rel")"
        cp -L "$src/$rel" "$dst/$rel"
    done
}

# ── 0. Plugin: prune copies whose root source is gone ───────────────────────
# A plugin skill dir is kept only if a root skill of the same name exists.
# Flat plugin scripts/*.py copies are always removed (scripts ship per skill).
# Plugin-owned files (.mjs hook scripts, servers/, agents/, hooks/) are never
# touched.
echo "=== Pruning orphaned plugin copies ==="
declare -A EXPECTED_SKILL_DIRS=()
for skill_dir in "$SKILLS_DIR"/*/; do
    EXPECTED_SKILL_DIRS["$(basename "$skill_dir")"]=1
done

for plugin_skill in "$PLUGIN_DIR"/skills/*/; do
    [ -d "$plugin_skill" ] || continue
    name=$(basename "$plugin_skill")
    if [ -z "${EXPECTED_SKILL_DIRS[$name]:-}" ]; then
        rm -rf "$plugin_skill"
        echo "  removed plugin skill: $name/"
    fi
done
for plugin_script in "$PLUGIN_DIR"/scripts/*.py; do
    [ -f "$plugin_script" ] || continue
    rm -f "$plugin_script"
    echo "  removed flat plugin script: $(basename "$plugin_script")"
done
rm -rf "$PLUGIN_DIR/scripts/__pycache__"

# ── 1. Plugin: sync SKILL.md (transformed) + scripts + references + assets ──
echo ""
echo "=== Syncing skills to plugin (script-path transform only) ==="
for skill_dir in "$SKILLS_DIR"/*/; do
    name=$(basename "$skill_dir")
    plugin_skill="$PLUGIN_DIR/skills/$name"
    mkdir -p "$plugin_skill"

    if [ -f "$skill_dir/SKILL.md" ]; then
        transform_skill_md_for_plugin "$skill_dir/SKILL.md" "$plugin_skill/SKILL.md"
        echo "  $name/SKILL.md"
    fi

    for sub in scripts references assets; do
        copy_tree "$skill_dir/$sub" "$plugin_skill/$sub"
        [ -d "$skill_dir/$sub" ] && echo "  $name/$sub/"
    done
done

echo ""
echo "=== Generating per-agent variants (Codex, OpenCode) ==="
"$(command -v python3 || command -v python)" "$REPO_ROOT/scripts/build-agent-variants.py"

echo ""
echo "Sync complete."
echo "  Root skills/             <- EDIT HERE (single source of truth)"
echo "  Plugin skills/           <- auto-generated (script commands -> \${CLAUDE_SKILL_DIR})"
echo "  Plugin variants/         <- auto-generated (Codex, OpenCode)"

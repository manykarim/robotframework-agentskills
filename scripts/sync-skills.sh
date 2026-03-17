#!/usr/bin/env bash
# Sync canonical skills/ to plugin and vscode-extension distribution channels.
# Run from the repository root.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
PLUGIN_DIR="$REPO_ROOT/plugins/rf-agentskills"
VSCODE_DIR="$REPO_ROOT/vscode-extension/skills"

# ── Plugin: sync Python scripts ──────────────────────────────────────────────
echo "=== Syncing scripts from root skills/ to plugin ==="
for script in keyword_builder.py testcase_builder.py resource_architect.py rf_libdoc.py rf_results.py; do
    src=$(find "$SKILLS_DIR" -name "$script" -not -type l | head -1)
    if [ -z "$src" ]; then
        echo "WARNING: Could not find $script in $SKILLS_DIR"
        continue
    fi
    dest="$PLUGIN_DIR/scripts/$script"
    if [ -d "$PLUGIN_DIR/scripts" ]; then
        cp "$src" "$dest"
        echo "  Synced $script -> plugin/scripts/"
    fi
done

# ── VS Code extension: full skill directory generation ───────────────────────
echo ""
echo "=== Generating vscode-extension/skills/ from root skills/ ==="

# Create fresh skills directory (remove stale content)
rm -rf "$VSCODE_DIR"
mkdir -p "$VSCODE_DIR"

for skill_dir in "$SKILLS_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    vscode_skill="$VSCODE_DIR/$skill_name"
    mkdir -p "$vscode_skill"

    # Copy SKILL.md
    if [ -f "$skill_dir/SKILL.md" ]; then
        cp "$skill_dir/SKILL.md" "$vscode_skill/SKILL.md"
    fi

    # Copy scripts/ (regular files)
    if [ -d "$skill_dir/scripts" ]; then
        mkdir -p "$vscode_skill/scripts"
        for script in "$skill_dir"/scripts/*.py; do
            [ -f "$script" ] || continue
            script_name=$(basename "$script")
            if [ -L "$script" ]; then
                # Preserve symlinks (e.g., libdoc-explain -> libdoc-search)
                cp -P "$script" "$vscode_skill/scripts/$script_name"
                echo "  Synced symlink $skill_name/scripts/$script_name"
            else
                cp "$script" "$vscode_skill/scripts/$script_name"
                echo "  Synced $skill_name/scripts/$script_name"
            fi
        done
    fi

    # Copy references/
    if [ -d "$skill_dir/references" ]; then
        cp -r "$skill_dir/references" "$vscode_skill/references"
        echo "  Synced $skill_name/references/"
    fi

    # Copy assets/
    if [ -d "$skill_dir/assets" ]; then
        cp -r "$skill_dir/assets" "$vscode_skill/assets"
        echo "  Synced $skill_name/assets/"
    fi
done

echo ""
echo "Sync complete."
echo "  Plugin scripts: $PLUGIN_DIR/scripts/"
echo "  VS Code skills: $VSCODE_DIR/"

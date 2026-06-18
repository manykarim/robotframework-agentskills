#!/usr/bin/env bash
# Sync canonical skills/ to plugin and vscode-extension distribution channels.
#
# RULE: All edits happen in root skills/ only. This script propagates to:
#   - plugins/rf-agentskills/scripts/  (Python scripts, identical copies)
#   - plugins/rf-agentskills/skills/   (SKILL.md transformed + references/assets copied)
#   - vscode-extension/skills/         (identical copies of everything)
#
# Run from the repository root.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
PLUGIN_DIR="$REPO_ROOT/plugins/rf-agentskills"
VSCODE_DIR="$REPO_ROOT/vscode-extension/skills"

# ── Name mapping: root long names -> plugin short names ──────────────────────
declare -A SHORT_NAMES=(
    ["robotframework-appium-skill"]="appium"
    ["robotframework-browser-skill"]="browser"
    ["robotframework-keyword-builder"]="keyword-builder"
    ["robotframework-libdoc-explain"]="libdoc-explain"
    ["robotframework-libdoc-search"]="libdoc-search"
    ["robotframework-platynui-skill"]="platynui"
    ["robotframework-requests-skill"]="requests"
    ["robotframework-resource-architect"]="resource-architect"
    ["robotframework-restinstance-skill"]="restinstance"
    ["robotframework-results"]="results"
    ["robotframework-selenium-skill"]="selenium"
    ["robotframework-testcase-builder"]="testcase-builder"
)

# ── Helper: transform SKILL.md for plugin channel ───────────────────────────
# 1. Replace long name with short name in frontmatter
# 2. Replace "python scripts/foo.py" with python3 "${CLAUDE_PLUGIN_ROOT}/scripts/foo.py"
# 3. Replace long skill names with short names in companion skills table
transform_skill_md_for_plugin() {
    local src="$1"
    local dest="$2"
    local rf_name="$3"    # e.g., rf-browser (the name: in root SKILL.md)
    local short_name="$4" # e.g., browser (the plugin dir name)

    sed \
        -e "s|^name: ${rf_name}$|name: ${short_name}|" \
        -e 's|python scripts/\([a-z_]*\.py\)|python3 "${CLAUDE_PLUGIN_ROOT}/scripts/\1"|g' \
        -e 's|`rf-keyword-builder`|`keyword-builder`|g' \
        -e 's|`rf-testcase-builder`|`testcase-builder`|g' \
        -e 's|`rf-resource-architect`|`resource-architect`|g' \
        -e 's|`rf-libdoc-search`|`libdoc-search`|g' \
        -e 's|`rf-libdoc-explain`|`libdoc-explain`|g' \
        -e 's|`rf-results`|`results`|g' \
        "$src" > "$dest"
}

# ── 1. Plugin: sync Python scripts ──────────────────────────────────────────
echo "=== Syncing scripts to plugin ==="
for script in keyword_builder.py testcase_builder.py resource_architect.py rf_libdoc.py rf_results.py; do
    src=$(find "$SKILLS_DIR" -name "$script" -not -type l | head -1)
    if [ -z "$src" ]; then
        echo "  WARNING: Could not find $script in $SKILLS_DIR"
        continue
    fi
    cp "$src" "$PLUGIN_DIR/scripts/$script"
    echo "  $script"
done

# ── 2. Plugin: sync SKILL.md (transformed) + references + assets ────────────
echo ""
echo "=== Syncing skills to plugin (with name/path transform) ==="
for skill_dir in "$SKILLS_DIR"/*/; do
    long_name=$(basename "$skill_dir")
    short_name="${SHORT_NAMES[$long_name]:-}"
    if [ -z "$short_name" ]; then
        echo "  WARNING: No short name mapping for $long_name"
        continue
    fi
    plugin_skill="$PLUGIN_DIR/skills/$short_name"
    mkdir -p "$plugin_skill"

    # Transform SKILL.md
    if [ -f "$skill_dir/SKILL.md" ]; then
        # Read the actual name: field from frontmatter (e.g., rf-browser)
        rf_name=$(head -5 "$skill_dir/SKILL.md" | grep "^name:" | sed 's/^name: //')
        transform_skill_md_for_plugin "$skill_dir/SKILL.md" "$plugin_skill/SKILL.md" "$rf_name" "$short_name"
        echo "  $short_name/SKILL.md (transformed: $rf_name -> $short_name)"
    fi

    # Sync references/
    if [ -d "$skill_dir/references" ]; then
        rm -rf "$plugin_skill/references"
        cp -r "$skill_dir/references" "$plugin_skill/references"
        echo "  $short_name/references/"
    fi

    # Sync assets/
    if [ -d "$skill_dir/assets" ]; then
        rm -rf "$plugin_skill/assets"
        cp -r "$skill_dir/assets" "$plugin_skill/assets"
        echo "  $short_name/assets/"
    fi
done

# ── 3. VS Code extension: skill directory generation with short dir names ────
# The Agent Skills spec requires directory name == SKILL.md name: field.
# Root dirs use long names (robotframework-browser-skill/) but name: is rf-browser.
# VS Code dirs must use the rf-* name so skills load correctly.
echo ""
echo "=== Generating vscode-extension/skills/ ==="
rm -rf "$VSCODE_DIR"
mkdir -p "$VSCODE_DIR"

for skill_dir in "$SKILLS_DIR"/*/; do
    long_name=$(basename "$skill_dir")

    # Read the name: field from SKILL.md to use as directory name
    rf_name=$(head -5 "$skill_dir/SKILL.md" | grep "^name:" | sed 's/^name: //')
    if [ -z "$rf_name" ]; then
        echo "  WARNING: No name: in $long_name/SKILL.md, skipping"
        continue
    fi

    vscode_skill="$VSCODE_DIR/$rf_name"
    mkdir -p "$vscode_skill"

    # Copy SKILL.md (name: already matches the directory)
    cp "$skill_dir/SKILL.md" "$vscode_skill/SKILL.md"

    # Copy scripts/ (dereference symlinks since vsce can't follow them across renamed dirs)
    if [ -d "$skill_dir/scripts" ]; then
        mkdir -p "$vscode_skill/scripts"
        for script in "$skill_dir"/scripts/*.py; do
            [ -f "$script" ] || continue
            script_name=$(basename "$script")
            cp -L "$script" "$vscode_skill/scripts/$script_name"
        done
    fi

    # Copy references/
    if [ -d "$skill_dir/references" ]; then
        cp -r "$skill_dir/references" "$vscode_skill/references"
    fi

    # Copy assets/
    if [ -d "$skill_dir/assets" ]; then
        cp -r "$skill_dir/assets" "$vscode_skill/assets"
    fi

    echo "  $rf_name/"
done

# ── 4. Update VS Code package.json chatSkills paths ─────────────────────────
PACKAGE_JSON="$REPO_ROOT/vscode-extension/package.json"
if [ -f "$PACKAGE_JSON" ]; then
    echo ""
    echo "=== Updating vscode-extension/package.json chatSkills paths ==="
    python3 -c "
import json, os

pkg = json.load(open('$PACKAGE_JSON'))
skills_dir = '$VSCODE_DIR'
skill_dirs = sorted(d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d)))

pkg['contributes'] = pkg.get('contributes', {})
pkg['contributes']['chatSkills'] = [
    {'path': f'./skills/{d}/SKILL.md'}
    for d in skill_dirs
]

with open('$PACKAGE_JSON', 'w') as f:
    json.dump(pkg, f, indent=2)
    f.write('\n')

print(f'  Updated {len(skill_dirs)} chatSkills paths')
"
fi

echo ""
echo "Sync complete."
echo "  Root skills/             <- EDIT HERE (single source of truth)"
echo "  Plugin skills + scripts/ <- auto-generated (transformed)"
echo "  VS Code skills/          <- auto-generated (dir names = name: field)"

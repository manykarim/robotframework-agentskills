#!/usr/bin/env bash
# Usage: ./scripts/bump-version.sh <major|minor|patch>
# Bumps the CONTENT version (see RELEASING.md) everywhere it is recorded:
#   VERSION, .claude-plugin/marketplace.json (metadata + rf-agentskills entry),
#   plugins/rf-agentskills/.claude-plugin/plugin.json, vscode-extension/package.json
#   and metadata.version in every skills/*/SKILL.md (checked by validate-skills.py).
# Run scripts/sync-skills.sh afterwards to propagate the SKILL.md changes.
#
# REPO_ROOT can be overridden (used by tests to run against a scratch tree).
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
BUMP_TYPE="${1:-patch}"
VERSION_FILE="$REPO_ROOT/VERSION"

if [ ! -f "$VERSION_FILE" ]; then
    echo "ERROR: $VERSION_FILE not found" >&2
    exit 1
fi

CURRENT=$(tr -d '[:space:]' < "$VERSION_FILE")
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$BUMP_TYPE" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
    *)
        echo "Usage: $0 <major|minor|patch>" >&2
        exit 1
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
echo "$NEW_VERSION" > "$VERSION_FILE"

python3 - "$REPO_ROOT" "$NEW_VERSION" <<'PY'
import json
import re
import sys
from pathlib import Path

root, new = Path(sys.argv[1]), sys.argv[2]


def update_json(rel, mutate):
    path = root / rel
    if not path.is_file():
        print(f"  skip (missing): {rel}")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  {rel}")


def marketplace(data):
    if "version" in data.get("metadata", {}):
        data["metadata"]["version"] = new
    for plugin in data.get("plugins", []):
        if plugin.get("name") == "rf-agentskills" and "version" in plugin:
            plugin["version"] = new


def top_level(data):
    data["version"] = new


update_json(".claude-plugin/marketplace.json", marketplace)
update_json("plugins/rf-agentskills/.claude-plugin/plugin.json", top_level)
update_json("vscode-extension/package.json", top_level)

# metadata.version in each root SKILL.md frontmatter (the indented `version:`
# line of the metadata map, inside the leading --- block only).
pattern = re.compile(r"^(metadata:[ \t]*\n(?:[ \t]+[^\n]*\n)*?[ \t]+version:[ \t]*)[^\n]*$", re.M)
for skill_md in sorted(root.glob("skills/*/SKILL.md")):
    text = skill_md.read_text(encoding="utf-8")
    end = text.find("\n---", 3) if text.startswith("---\n") else -1
    new_fm, n = pattern.subn(lambda m: f'{m.group(1)}"{new}"', text[:end + 1], count=1) if end > 0 else ("", 0)
    if n:
        skill_md.write_text(new_fm + text[end + 1:], encoding="utf-8")
        print(f"  {skill_md.relative_to(root).as_posix()}")
    else:
        print(f"  WARNING: no metadata.version in {skill_md.relative_to(root).as_posix()}", file=sys.stderr)
PY

echo "Bumped content version: $CURRENT -> $NEW_VERSION"
echo ""
echo "Next steps:"
echo "  bash scripts/sync-skills.sh && python3 scripts/validate-skills.py --channel all"
echo "  git add -A && git commit -m 'release: v${NEW_VERSION}'"
echo "  git tag v${NEW_VERSION} && git push origin main --tags"

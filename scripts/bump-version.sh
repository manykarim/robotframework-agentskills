#!/usr/bin/env bash
# Usage: ./scripts/bump-version.sh <major|minor|patch>
# Updates VERSION file and marketplace.json, then creates a git tag.
set -euo pipefail

BUMP_TYPE="${1:-patch}"
VERSION_FILE="VERSION"
MARKETPLACE_FILE="marketplace.json"

if [ ! -f "$VERSION_FILE" ]; then
    echo "ERROR: $VERSION_FILE not found" >&2
    exit 1
fi

CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$BUMP_TYPE" in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo "Usage: $0 <major|minor|patch>" >&2
        exit 1
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

echo "$NEW_VERSION" > "$VERSION_FILE"

# Update marketplace.json
python3 -c "
import json
with open('$MARKETPLACE_FILE') as f:
    data = json.load(f)
data['version'] = '$NEW_VERSION'
with open('$MARKETPLACE_FILE', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"

echo "Bumped version: $CURRENT -> $NEW_VERSION"
echo ""
echo "Next steps:"
echo "  git add VERSION marketplace.json"
echo "  git commit -m 'release: v${NEW_VERSION}'"
echo "  git tag v${NEW_VERSION}"
echo "  git push origin main --tags"

# Shared helpers for agent check scripts.
#
# Each ``<agent>.sh`` sources this file and calls the helpers below.
# All helpers exit non-zero on first failure (set -e in caller).
#
# Helpers:
#   need_file <path> [<grep-pattern>]
#       file must exist; if pattern given, must contain at least one match
#   need_no_file <path>
#       file must NOT exist (used in --post-uninstall)
#   need_no_substitution <path>
#       file must not contain literal ${CLAUDE_PLUGIN_ROOT}
#   need_yaml_key <path> <jq-style-keypath>
#       e.g. need_yaml_key config.yaml extensions.rf-tools
#   need_json_key <path> <jq-keypath>
#       e.g. need_json_key mcp.json mcpServers.rf-tools
#   need_toml_key <path> <table-path>
#       e.g. need_toml_key config.toml mcp_servers.rf-tools
#   skip <reason>
#       prints reason to stderr and exits 0 (used when an introspection
#       command isn't available in this version of the agent)

set -euo pipefail

need_file () {
    local path="$1"; shift
    if [ ! -f "$path" ]; then
        printf '  [check] missing file: %s\n' "$path" >&2
        return 1
    fi
    while [ $# -gt 0 ]; do
        if ! grep -qE -- "$1" "$path"; then
            printf '  [check] %s : missing pattern %s\n' "$path" "$1" >&2
            return 1
        fi
        shift
    done
}

need_no_file () {
    local path="$1"
    if [ -f "$path" ]; then
        printf '  [check] uninstall left %s behind\n' "$path" >&2
        return 1
    fi
}

need_no_substitution () {
    local path="$1"
    if grep -qF '${CLAUDE_PLUGIN_ROOT}' "$path" 2>/dev/null; then
        printf '  [check] %s contains unsubstituted ${CLAUDE_PLUGIN_ROOT}\n' "$path" >&2
        return 1
    fi
}

need_yaml_key () {
    local path="$1" keypath="$2"
    python3 - "$path" "$keypath" <<'PY'
import sys, yaml, functools
path, keypath = sys.argv[1], sys.argv[2]
try:
    data = yaml.safe_load(open(path)) or {}
except Exception as e:
    sys.exit(f"  [check] failed to parse YAML {path}: {e}")
cur = data
for k in keypath.split('.'):
    if not isinstance(cur, dict) or k not in cur:
        sys.exit(f"  [check] {path} missing key {keypath}")
    cur = cur[k]
PY
}

need_json_key () {
    local path="$1" keypath="$2"
    if ! jq -e "$(printf '.%s' "$keypath")" "$path" >/dev/null 2>&1; then
        printf '  [check] %s missing key .%s\n' "$path" "$keypath" >&2
        return 1
    fi
}

need_toml_key () {
    local path="$1" keypath="$2"
    python3 - "$path" "$keypath" <<'PY'
import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib
path, keypath = sys.argv[1], sys.argv[2]
try:
    data = tomllib.loads(open(path).read())
except Exception as e:
    sys.exit(f"  [check] failed to parse TOML {path}: {e}")
cur = data
for k in keypath.split('.'):
    if not isinstance(cur, dict) or k not in cur:
        sys.exit(f"  [check] {path} missing key {keypath}")
    cur = cur[k]
PY
}

skip () {
    printf '  [check] skipped: %s\n' "$*" >&2
    exit 0
}

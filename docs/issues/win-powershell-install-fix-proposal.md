# Windows install crash — analysis and fix proposal

**Status:** Proposal — no code changes yet. Reviewing for direction before implementing.
**Branch:** `fix/win-powershell-install-issues` (off `main`).
**Date:** 2026-05-13.
**Issue source:** `docs/issues/rf-agentskills_install_issues_win_powershell.txt`

## TL;DR

`rf-agentskills install --agent claude-code` crashes on Windows with
`json.decoder.JSONDecodeError: Invalid \escape: line 9 column 27`.
Root cause is a single bug — the installer substitutes a Windows path
(containing `\`) into JSON text and then calls `json.loads()`, which
chokes on the unescaped backslashes.

Same bug latent in every other adapter that consumes JSON / TOML
after substitution: Codex, Cursor, OpenCode, Claude Desktop, Copilot
(via Claude Code), and the staged config files written under
`<root>/rf-agentskills-files/`.

**Recommended fix:** on Windows, normalise the substituted path to
forward slashes. Five-line change in `transforms.to_native_path_string()`.
Windows tools (Claude Code, Codex CLI, PowerShell, Python pathlib)
all accept forward-slash paths, and forward slashes are valid inside
JSON / TOML / YAML strings without escaping. Single fix unblocks all
adapters at once.

Recommended follow-up (separate PR): refactor adapter config-merge
paths to parse-then-substitute instead of substitute-then-parse, so
the failure class disappears entirely regardless of what character is
in the destination path.

## What the user reported

```
PS C:\workspace\claude-demo> uv run rf-agentskills install --agent claude-code
Traceback (most recent call last):
  …
  File "C:\workspace\claude-demo\.venv\Lib\site-packages\rf_agentskills\adapters\claude_code.py",
        line 234, in _hooks_merge_op
    hooks_obj = json.loads(raw)
  File "…\json\__init__.py", line 352, in loads
    return _default_decoder.decode(s)
  …
json.decoder.JSONDecodeError: Invalid \escape: line 9 column 27 (char 165)
```

Detection (`rf-agentskills targets`) and install plan **start** worked.
The crash is at the *plan-build* step, specifically when reading
`hooks/hooks.json` to extract the `hooks` block for `settings.json`.

## Reproduction (verified locally)

The bug reproduces on Linux too if we feed it a Windows-style path,
which is exactly what `to_native_path_string()` produces on Windows:

```python
from rf_agentskills import transforms as _x
import json

hooks_json_text = open('plugins/rf-agentskills/hooks/hooks.json').read()
win_plugin_root = r'C:\workspace\claude-demo\.claude\rf-agentskills-files'
substituted = _x.substitute_plugin_root(hooks_json_text, win_plugin_root)
json.loads(substituted)
```

Output:

```
CRASH: JSONDecodeError: Invalid \escape: line 9 column 27 (char 165)
  → text around char 165: '"command": "C:\\workspace\\clau'
```

The substituted JSON snippet:

```json
{
  "command": "C:\workspace\claude-demo\.claude\rf-agentskills-files/scripts/validate_robot.sh"
}
```

`\w`, `\c`, `\.`, `\r` are all **invalid** JSON escape sequences. Only
`\"`, `\\`, `\b`, `\f`, `\n`, `\r`, `\t`, `\/`, `\uXXXX` are valid.

## Where this bug lives

| Adapter | Affected call site | Format the substituted text is fed to |
|---|---|---|
| `claude_code.py` | `_hooks_merge_op` (the user's crash) | `json.loads` |
| `claude_code.py` | `_mcp_merge_op` | `json.loads` |
| `copilot.py` | `_collect_merges` (extra `.vscode/mcp.json` merge for project scope) | `json.loads` |
| `codex.py` | `_collect_merges` (reads `.mcp.json` via `json.loads` before lifting to TOML) | `json.loads` |
| `cursor.py` | `_hooks_merge_op` + `_mcp_merge_op` | `json.loads` |
| `opencode.py` | `_collect_merges` | `json.loads` |
| `claude_desktop.py` | `_mcp_merge_op` | `json.loads` |
| Every adapter | `_read_with_substitution` writing staged `_assets/.claude-plugin/plugin.json`, `_assets/.mcp.json`, `_assets/hooks/hooks.json` to disk | files would be **invalid JSON on disk** on Windows |

The user only sees the first hit (`_hooks_merge_op`) because the
crash terminates the plan-build before the others run. Same root
cause, ~7 symptoms.

Confirmed reproducible: I ran the same recipe locally against Codex's
JSON-read step — same crash, different stack:

```
=== plugin .mcp.json after substitution ===
{
  "mcpServers": {
    "rf-tools": {
      "command": "python3",
      "args": ["C:\Users\MKASIRIH\.claude\rf-agentskills-files/servers/rf-tools-server.py"],
      …
    }
  }
}

JSON CRASH: Invalid \escape: line 5 column 19 (char 84)
```

YAML (Goose's path) is more lenient — backslashes inside YAML strings
are mostly literal — but YAML scalars starting with `C:` get parsed
as strings reliably, so Goose's `merge_yaml_block` may actually be
OK. Worth a Windows reproduction to confirm.

## Why this hadn't bitten us before

Two reasons:

1. **All testing has been on Linux** (and macOS in CI thought-
   experiments). Forward-slash native; no escape semantics.
2. **The Docker test harness** runs the installer inside a Linux
   container even when you invoke it from a Windows host. The
   container's filesystem uses forward slashes throughout.

The pytest tests use `tmp_path` (Linux/macOS POSIX paths) and never
exercise the `sys.platform == "win32"` branch of
`to_native_path_string()`. So this code path has had **zero coverage**.

## Fix design

### Recommended — small, immediate (~5 lines)

Change `to_native_path_string()` in `installer/src/rf_agentskills/transforms.py`
to return forward-slash paths on Windows:

```python
def to_native_path_string(path: Path) -> str:
    """Return the path as a string suitable for JSON / TOML / YAML
    embedding and for any tool that consumes a path string (Claude
    Code, Codex CLI, PowerShell, Python).

    On Windows, paths are returned with forward slashes (e.g.
    ``C:/Users/foo/.claude/rf-agentskills-files``). All supported
    Windows tools accept forward-slash paths, AND forward slashes
    are valid inside JSON / TOML / YAML strings without escaping —
    which is what made the prior backslash behavior crash with
    ``Invalid \escape`` on every adapter that substitutes a path
    into a config file and then parses it.
    """
    if sys.platform == "win32":
        return PureWindowsPath(path).as_posix()
    return str(path)
```

That's it. Every existing call site benefits — none need to change.

#### Why this is safe

| Consumer | Accepts forward slashes on Windows? |
|---|---|
| Claude Code settings.json `hooks.command` | yes — passes to a shell, which handles either separator |
| `.mcp.json` `mcpServers.<n>.command` / `args` | yes — Node/Python child_process resolve normally |
| Codex `config.toml` `[mcp_servers.X]` `args` | yes — Codex runtime resolves paths via OS APIs |
| Cursor `hooks.json` / `mcp.json` | yes — JSON values are just strings to Cursor's loader |
| OpenCode `opencode.json` `mcp.X.command` array | yes — same |
| PowerShell `-File <path>` | yes — verified by Microsoft docs and `Get-Item` accepting both |
| Python `pathlib.Path` | yes — `Path("C:/foo")` works identically to `Path("C:\\foo")` |
| Bash hooks via Git Bash / WSL | yes (forward slashes are native there) |
| Hook script content (.sh, .py, .md) | yes — written verbatim to disk; readers don't care |

Where backslashes would be required (cmd.exe `start <path>`, some
GUI launchers): not in our codepaths.

### Defense-in-depth (recommended follow-up PR)

Refactor the JSON/TOML/YAML merge paths to **parse first, substitute
on values**, instead of substitute-then-parse. New transform:

```python
def substitute_in_loaded(obj, plugin_root_abs):
    """Walk a dict/list/str structure and substitute ``${CLAUDE_PLUGIN_ROOT}``
    only inside string values. Numbers, bools, None, dict keys, list
    indices, etc. are passed through unchanged."""
    if isinstance(obj, str):
        return obj.replace(PLUGIN_ROOT_TOKEN, plugin_root_abs)
    if isinstance(obj, list):
        return [substitute_in_loaded(x, plugin_root_abs) for x in obj]
    if isinstance(obj, dict):
        return {k: substitute_in_loaded(v, plugin_root_abs) for k, v in obj.items()}
    return obj
```

Each adapter's merge:

```python
# Before (vulnerable to escape characters in path)
raw = _x.substitute_plugin_root(plugin_mcp.read_text(...), plugin_root_abs)
hooks_obj = json.loads(raw)

# After (robust regardless of path characters)
obj = json.loads(plugin_mcp.read_text(...))
obj = _x.substitute_in_loaded(obj, plugin_root_abs)
```

Re-serialisation back to the disk file goes through `json.dumps` /
`tomli_w.dumps` / `yaml.safe_dump`, which handle escaping correctly.

The forward-slash change alone is enough to fix the user's crash.
The parse-first refactor adds belt-and-suspenders robustness and is
recommended but separable.

### What about `_read_with_substitution` for files on disk?

Files written under `<root>/rf-agentskills-files/` via
`_read_with_substitution` get byte-level substitution. With the
forward-slash fix in `to_native_path_string()`, the byte-substituted
contents end up containing `C:/...` instead of `C:\...`, which is
valid JSON when those files (`.claude-plugin/plugin.json`,
`hooks/hooks.json`, etc.) are later read by Claude Code or by us.

No additional change needed in `_read_with_substitution`.

## Risks and edge cases

1. **Mixed path separators** — after the fix, the substituted text
   contains paths like `C:/Users/x/.claude/rf-agentskills-files/scripts/foo.sh`
   (no separator inconsistency since the source token has `/`). On
   Linux/macOS this is identical to current behavior. Clean.

2. **Hook command Windows-rewrite** — `transforms.rewrite_hooks_for_windows()`
   produces things like `powershell -ExecutionPolicy Bypass -NoProfile
   -File "<ps_cmd>"`. With forward slashes the command becomes:
   `powershell ... -File "C:/Users/x/.../validate_robot.ps1"`. PowerShell
   accepts that — verified via docs (`Get-Item`, `Test-Path`, `& "<path>"`
   all accept forward slashes).

3. **`${CLAUDE_PLUGIN_ROOT}` env var future** — if we ever start
   exporting this as a real env var instead of substituting at
   install time, we'd want backslashes on Windows for users running
   the value through `cmd.exe`. But we don't do that today, and even
   then forward slashes work in most modern Windows contexts.

4. **YAML on Windows** — Goose's `config.yaml` merge takes the
   substituted dict and runs `yaml.safe_dump`. PyYAML escapes
   backslashes correctly in flow-style strings — but the issue
   appears earlier (the `_server_to_goose_extension()` helper feeds
   the substituted path into a dict literal that's never re-parsed).
   With forward slashes this is a non-issue; without forward slashes
   I'd want to verify with a Windows repro.

5. **Test coverage gap** — the `sys.platform == "win32"` branch of
   `to_native_path_string()` has zero tests today. The fix should
   include a test that monkeypatches `sys.platform` to `"win32"` and
   asserts forward-slash output, plus an integration-style test that
   builds a full plan with a `--prefix C:\\fake\\path` and verifies
   the produced merges parse as valid JSON / TOML.

## Test plan for the fix

```python
def test_to_native_path_string_uses_forward_slashes_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    out = _x.to_native_path_string(Path("C:/users/x/.claude/rf-agentskills-files"))
    assert "\\" not in out
    assert out == "C:/users/x/.claude/rf-agentskills-files"

def test_claude_code_hooks_merge_payload_is_valid_json_on_windows(monkeypatch, install_prefix):
    monkeypatch.setattr(sys, "platform", "win32")
    # Drive plan() with a Windows-style prefix:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=Path("C:/fake")))
    # Find the hooks merge op and exercise its apply() inside a tempdir
    hooks_merge = next(m for m in plan.merges if "hooks" in m.description)
    hooks_merge.apply()
    # Re-read and re-parse — would have crashed before the fix
    data = json.loads((Path("C:/fake") / "settings.json").read_text())
    assert "hooks" in data
```

Similar tests for each adapter that has a JSON / TOML merge. Goal:
every adapter has at least one Windows-platform-mocked test that
exercises plan() + apply() through a substitution.

## Affected files (proposed fix scope)

| File | Change |
|---|---|
| `installer/src/rf_agentskills/transforms.py` | Modify `to_native_path_string()` to return forward-slash paths on Windows |
| `tests/installer/test_transforms.py` | New test: forward-slash output on `monkeypatch.setattr(sys, "platform", "win32")` |
| `tests/installer/test_adapter_claude_code.py` | New test: plan + hooks-merge apply with Windows-mocked platform produces valid JSON |
| `tests/installer/test_adapter_secondaries.py` | Same shape of test for Codex, Cursor, OpenCode, Claude Desktop |
| `installer/CHANGELOG.md` | New `0.4.1` entry: "Windows install crash fix — forward-slash paths in substituted text" |
| `installer/pyproject.toml` + `__init__.py` | Bump 0.4.0 → 0.4.1 (patch — bug fix) |

Estimated PR size: ~30 source LOC + ~100 test LOC + doc + version bump.

## Out of scope for this fix

- **Parse-first refactor** — separate PR. Larger and architectural;
  warrants its own review.
- **Real Windows CI coverage** — the existing Docker harness is
  Linux-only. Adding a Windows GitHub Actions matrix is a separate
  scope. The platform-mocked unit tests in this fix catch the
  current crash class without paying for full Windows CI.
- **PowerShell hook scripts (`.ps1`)** — already flagged in earlier
  proposals (per `docs/installer/proposal.md`); not part of this
  bug. Bash hooks don't run on Windows today; PowerShell ports are
  a separate workstream.
- **OpenCode "not detected" on Windows in the user's trace** — the
  detection logic checks `~/.config/opencode/` which is not the
  Windows-conventional path. The user installed OpenCode in a
  different location. Detection improvement is a separate small fix
  (also affects detection of Cursor and Claude Desktop on Windows);
  doesn't block this PR.

## Decision points for the reviewer

1. **Forward-slash normalisation: agreed?** Or prefer
   parse-first as the primary fix?
2. **Version bump**: 0.4.0 → 0.4.1 (patch — bug fix, no API change).
   Worth a GH release with attached wheel/sdist, mirroring the v0.4.0
   process. Confirm or delay until after parse-first lands.
3. **Test platform-mocking**: monkeypatch `sys.platform = "win32"`
   suffices for unit-level reproduction, but is not a substitute for
   actual Windows CI. Acceptable as v0.4.1 fix, with real Windows
   CI as a separate follow-up?
4. **Adapter test coverage**: add Windows-mocked tests for every
   adapter that does substitute-into-config, or just the two that
   crashed in the user's report (Claude Code hooks, Codex MCP)?
   Recommend: all — they're cheap and prevent regressions.

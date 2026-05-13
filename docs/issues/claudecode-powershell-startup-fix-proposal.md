# ClaudeCode on Windows: SessionStart hook references missing `.ps1` files

**Status**: analysis / proposal, no changes implemented yet
**Reporter context**: `docs/issues/rf-agentskills_claudecode_powershell_error.txt`
**Affected release**: rf-agentskills **v0.4.1** (and v0.4.0; v0.3.0 didn't run on Windows either, but for a different reason — see v0.4.1 release notes)
**Severity**: high — every Windows ClaudeCode session shows a SessionStart error; three other hook events (PostToolUse, UserPromptSubmit, Stop) fail silently on every fire.

**Revision history**

| Rev | Note |
|---|---|
| 1 | Initial proposal: recommended converting `.sh` hooks to Python. |
| **2** | **Revised after reading [claudefa.st cross-platform-hooks guidance](https://claudefa.st/blog/tools/hooks/cross-platform-hooks) and running validation experiments. Primary recommendation switched to Node.js for alignment with community best practice; Python kept as a viable alternative for this specific package.** |

---

## 1. The symptom

After `pip install rf-agentskills==0.4.1` followed by `rf-agentskills install --agent claude-code` on a Windows / PowerShell host, ClaudeCode startup logs (from the user report):

```
SessionStart:startup hook error
Failed with non-blocking status code:
The argument 'C:/Users/MKASIRIH/.claude/rf-agentskills-files/scripts/check_rf_environment.ps1'
to the -File parameter does not exist. Provide the path to an existing …
```

This is the `powershell.exe -File <…>.ps1` invocation that v0.4.1's `rewrite_hooks_for_windows`
generates failing because the target file does not exist.

---

## 2. Reproduction

Driven purely from Linux (no Windows VM required) by exercising the same code
path the Windows install takes:

```python
from importlib.resources import files as pkg_files
from pathlib import Path
import json
from rf_agentskills import transforms

src = pkg_files('rf_agentskills') / '_assets' / 'hooks' / 'hooks.json'
raw = transforms.substitute_plugin_root(
    Path(str(src)).read_text(encoding='utf-8'),
    'C:/Users/MKASIRIH/.claude/rf-agentskills-files',
)
hooks_value = json.loads(raw)['hooks']
rewritten = transforms.rewrite_hooks_for_windows(hooks_value)
```

`rewritten` is exactly what v0.4.1 writes into `~/.claude/settings.json` on Windows.
Every hook command points at a `.ps1` file under
`C:/Users/.../rf-agentskills-files/scripts/`:

| Event              | Command (truncated)                                     | Backing file        |
|---|---|---|
| `PostToolUse`      | `powershell -File "…/scripts/validate_robot.ps1"`         | **MISSING**         |
| `UserPromptSubmit` | `powershell -File "…/scripts/maybe_inject_rf_context.ps1"`| **MISSING**         |
| `SessionStart`     | `powershell -File "…/scripts/check_rf_environment.ps1"`   | **MISSING** ← visible |
| `Stop`             | `powershell -File "…/scripts/maybe_remind_robot_tests.ps1"`| **MISSING**        |

Inspection of the package's `_assets/scripts/` directory (the wheel's actual
contents) confirms: **only `.sh` scripts ship; no `.ps1` files exist anywhere
in the package**.

The user sees the SessionStart error because it's the only one with synchronous,
visible feedback. The other three failures are silent — every Write/Edit, every
prompt submit, and every Stop event also triggers `powershell.exe` against a
nonexistent path. v0.4.1's Windows hooks are **wholly non-functional**.

---

## 3. Root cause

Two-half bug introduced in v0.4.1:

1. **The transform exists.** `transforms.rewrite_hooks_for_windows()` was added
   to swap `.sh` → `.ps1` in the hooks block when `sys.platform == 'win32'`
   (`installer/src/rf_agentskills/transforms.py:247-274`). Its docstring even
   admits the dependency:

   > The corresponding `.ps1` script is expected to ship in the same plugin
   > tree alongside its `.sh` sibling.

2. **The `.ps1` scripts were never written.** No `.ps1` files exist under
   `plugins/rf-agentskills/scripts/`, so the wheel's `_assets/scripts/`
   contains only `.sh` files. The transform creates dangling references.

In v0.4.0 and earlier the bug was masked by a separate v0.4.1-fixed crash
(the JSON-escape Windows-install crash) — installs never completed, so this
issue couldn't surface yet. v0.4.1 fixed the install crash, which uncovered
this latent bug.

---

## 4. What the four hook scripts actually do

(Read `plugins/rf-agentskills/scripts/*.sh` for the originals.)

| Script                            | Hook event            | Lines | What it does                                                                                                               |
|---|---|---|---|
| `check_rf_environment.sh`         | `SessionStart`        | ~100  | Probes `python3` + RF + libs; prints a diagnostic table to stderr. Always exits 0.                                         |
| `validate_robot.sh`               | `PostToolUse` (Write\|Edit) | ~90   | Extracts `file_path` from `TOOL_INPUT`; if `*.robot`/`*.resource`, runs `python -c "from robot.api import get_model; …"`.   |
| `maybe_inject_rf_context.sh`      | `UserPromptSubmit`    | ~85   | Reads event JSON on stdin; greps the prompt for RF signals; emits `additionalContext` JSON when matched.                   |
| `maybe_remind_robot_tests.sh`     | `Stop`                | ~70   | Reads event JSON on stdin; greps the session transcript for `.robot` / `.resource` writes; emits reminder JSON when found. |

Observation: **~50–80% of each script's logic is already a `python3 -c "..."`
heredoc inside the bash wrapper**. The bash layer is mostly stdin reading,
JSON parsing fallbacks (`jq` or `python3`), and regex matching with `grep -E`.

---

## 5. External guidance — claudefa.st cross-platform hooks blog

The post at <https://claudefa.st/blog/tools/hooks/cross-platform-hooks> gives
explicit recommendations for portable Claude Code hooks. Verbatim excerpts:

> **"Invoke Node.js directly in your Claude Code hooks config"** — *"This
> works on Windows, Linux, and macOS. Claude Code requires Node.js, so
> `node` is always available."*

> **"Python works for cross-platform hooks if your team has Python installed
> everywhere. Use `python3` (not `python`, which may not exist on some Linux
> distributions) in the `command` field. However, Node.js is the safer default
> since Claude Code guarantees its availability on every platform."**

Three rules to follow inside the hook file (whichever language):
- `os.homedir()` / `path.join(os.homedir(), …)` — never hardcode `$HOME` /
  `%USERPROFILE%`.
- `os.tmpdir()` — never hardcode `/tmp` or `$env:TEMP`.
- `path.join(…)` — never concatenate paths with `/` or `\`.

The post's debugging checklist orders failure modes: (1) hardcoded path
separators, (2) hardcoded env-var paths, (3) shell-specific commands
(`bash`, `cmd`, `powershell`, `sh`). The first two are about file paths
inside the script; the third is about the `command` field in `settings.json`
— "**Replace `bash`, `cmd`, `powershell`, `sh` with `node`**".

Our v0.4.1 implementation is a textbook violation of #3: we tried to use
`powershell -File <…>.ps1` instead of standardising on one runtime.

---

## 6. Experiments

All experiments run on Linux; cross-platform claims verified via the docs
and the fact that the patterns under test use no platform-specific shell
syntax or path separators.

### 6.1 Cold-start latency

Each hook fires a fresh interpreter, so per-invocation startup matters
(especially for `UserPromptSubmit` and `Stop`). Five runs each, sorted, on a
warm cache:

| Runtime              | min     | median  | max     |
|---|---|---|---|
| `node -e 1+1`        | 31.0 ms | 32.5 ms | 41.2 ms |
| `python3 -c pass`    | 27.7 ms | 32.0 ms | 32.7 ms |
| `bash -c true`       |  4.0 ms |  5.2 ms |  5.9 ms |

**Verdict**: Node and Python are within noise of each other (~30 ms). Both
are acceptable for hook latency. Bash is cheaper but we lose it on Windows
regardless. The choice between Node and Python is *not* driven by speed.

### 6.2 Node.js port of `maybe_inject_rf_context.sh`

Stand-up replacement in 40 lines (vs. 87 lines of bash with `jq` + `python3`
fallbacks):

```javascript
#!/usr/bin/env node
import { readFileSync } from "node:fs";

let raw;
try { raw = readFileSync(0, "utf-8"); } catch { process.exit(0); }
if (!raw) process.exit(0);

let event;
try { event = JSON.parse(raw); } catch { process.exit(0); }
const prompt = event.prompt ?? "";
if (!prompt) process.exit(0);

const RF_REGEX = /robot[ -]?framework|\.robot\b|\.resource\b|…/i;  // identical to bash's
if (!RF_REGEX.test(prompt)) process.exit(0);

process.stdout.write(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: "UserPromptSubmit",
    additionalContext: "Robot Framework context detected. …",
  },
}) + "\n");
```

Tested against four cases the bash version handles:
- prompt matches RF regex → emits envelope, exit 0 ✓
- prompt doesn't match → no output, exit 0 ✓
- empty stdin → no output, exit 0 ✓
- malformed JSON on stdin → no output, exit 0 ✓

**Verdict**: bash's regex syntax (`grep -E` with `\b` word boundaries and
`(a|b|c)` alternation) translates 1:1 to JavaScript regex. `readFileSync(0)`
+ `JSON.parse` collapses the bash `jq` / `python3` fallback chain into one
line. Cross-platform stdin / line-ending handling is automatic.

### 6.3 Node.js port of `validate_robot.sh`

The one hook with a *real* Python dependency — it calls
`from robot.api import get_model` to parse RF source. Two design choices for
Node:

1. Shell out to Python from the Node hook (`child_process.spawnSync`).
2. Skip the .mjs route for this hook and keep it as `.py`.

Option 1 prototyped and tested:

```javascript
const r = spawnSync(py, ["-c", PY_PARSER, filePath], { stdio: [...] });
if (r.error?.code === "ENOENT") continue;   // try next interpreter
process.exit(r.status ?? 0);
```

Tested cases:
- valid `.robot` file → "Robot Framework syntax OK" on stderr, exit 0 ✓
- non-RF file (e.g. `*.py`) → exit 0, no output ✓
- missing `TOOL_INPUT` → exit 0, no output ✓
- Python interpreter not found → exit 0, silent (fall-through) ✓
- robotframework not installed → "skipping syntax validation" on stderr,
  exit 0 (existing `try/except ImportError` survives) ✓

**Verdict**: works fine. Node handles the orchestration; Python does the
robot parsing. Same dependency surface as today (the existing bash version
also requires both bash *and* python3).

### 6.4 Path-separator handling

The package's own substitution already returns forward-slash paths on
Windows (v0.4.1 fix). Node accepts forward slashes in `readFile`, `existsSync`,
`spawnSync`, and `import` paths on Windows — no change needed there. The
`path.join()` discipline applies *only* to paths *constructed* inside the
hook script. None of our four hooks construct cross-platform paths
internally except `validate_robot` which reads a path verbatim from
`TOOL_INPUT.file_path` (already a fully-qualified absolute path the OS
gives us).

### 6.5 Node availability — caveat to the blog's claim

The blog states *"Claude Code requires Node.js, so node is always available."*
This was reliably true for the npm-installed Claude Code (`npm install -g
@anthropic-ai/claude-code`). On the local machine this proposal was drafted
on, `claude` is now a self-contained native binary (ELF) — Node is **not**
embedded into it. So the precise claim is:

- Users who installed via `npm` (still the majority on Windows and macOS)
  → have `node` on PATH.
- Users who installed via the new native installer **and** have not
  separately installed Node → may not have `node`.

For our package, this matters at *install* time, not at hook-fire time. The
installer can probe `shutil.which("node")` and:
- if present → register Node hooks;
- if absent and `python3`/`python` is present → fall back to Python hooks;
- if neither → skip hooks with a `post_install` note.

This is a one-time decision baked into `settings.json`; we don't switch
runtimes per fire.

---

## 7. Fix options (revised after experiments)

### Option A1 — convert hook scripts to **Node.js** (recommended)

Ship `*.mjs` files. Hook command on every OS:

```json
"command": "node \"${CLAUDE_PLUGIN_ROOT}/scripts/check_rf_environment.mjs\""
```

Delete `transforms.rewrite_hooks_for_windows()` and its caller — the substitute-only
path is enough for all platforms.

**Pros**
- Matches the [claudefa.st blog]'s explicit recommendation: `node`, not
  shell wrappers.
- Stdin/JSON handling collapses to two lines (`readFileSync(0)` + `JSON.parse`).
- bash regex → JS regex is 1:1 (verified in §6.2).
- One source of truth, no `.sh`/`.ps1` parity.
- `validate_robot.mjs` shells out to Python only when there's RF parsing to
  do — orthogonal to the hook fabric (§6.3).

**Cons / caveats**
- Adds Node as an installer-time dependency probe. Has to either be present
  on PATH or we fall back (see §6.5). For users who installed Claude Code
  via npm (the documented happy path), Node is already there.
- `validate_robot.mjs` still needs Python at runtime — same as today.

### Option A2 — convert hook scripts to **Python**

Ship `*.py` files. Hook command:

```json
"command": "python \"${CLAUDE_PLUGIN_ROOT}/scripts/check_rf_environment.py\""
```

(Or `python3` on POSIX; per blog, the bare `python` is unreliable on Linux.)

**Pros**
- Single runtime story across `rf-agentskills` (MCP server, skill scripts,
  hooks all in Python).
- The installer itself is Python — guaranteed available since
  `pip install rf-agentskills` succeeded.
- Can bake the absolute `sys.executable` of the installer's interpreter
  into the hook command at install time — eliminates the
  `python` vs `python3` vs `py` discovery problem.
- `validate_robot.py` can do `from robot.api import get_model` natively, no
  subprocess.

**Cons**
- Goes against the blog's explicit recommendation. Future contributors
  reading other Claude Code projects will see Node hooks everywhere.
- Baking `sys.executable` means hooks break if the user moves/upgrades the
  venv that did the install. Using bare `python3` works on POSIX but is
  unreliable on Windows (where `python3` may not exist; only `python` or
  `py` does).

### Option B — write `.ps1` ports

Ship parallel `validate_robot.ps1` etc. Keep `rewrite_hooks_for_windows`.
**Strictly worse than A1 / A2.** Two implementations to keep in sync; bash
regex → PowerShell `-match` is fiddly; `powershell.exe` ≠ `pwsh.exe`. Listed
only for completeness.

### Option C — skip hooks on Windows entirely (hotfix only)

In `ClaudeCodeAdapter`, drop the hooks merge when `sys.platform == 'win32'`.
Emit a `post_install` note saying hooks aren't wired on Windows yet.

- One-line patch; eliminates the user-visible crash in v0.4.2 in hours.
- Windows users lose RF context injection, env check, syntax validation,
  test reminder. The rest of the install (skills, agents, MCP server) still
  works.

### Option D — detect `bash.exe`; route through it; else skip

Probe `shutil.which("bash")` at install time; if present, register hooks as
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh"`; otherwise skip with a note.

- Zero porting effort; Git Bash / WSL users keep full functionality.
- Bifurcated behavior depending on PATH at install time; the reporter's
  stack trace shows PowerShell + uv with no Git Bash visible, so this
  option wouldn't have helped them. Listed only for completeness.

---

## 8. Recommended path (revised)

**Two-release plan**:

1. **v0.4.2 (hotfix, days)** — apply **Option C**: skip the hooks merge on
   Windows. Stops every Windows ClaudeCode session from logging a startup
   error. Document the gap in `post_install` notes and CHANGELOG.

2. **v0.5.0 (next minor, ~1 week)** — apply **Option A1 (Node.js)**:
   - Convert `check_rf_environment.sh`, `maybe_inject_rf_context.sh`,
     `maybe_remind_robot_tests.sh` to `.mjs` (pure Node; no Python needed).
   - Convert `validate_robot.sh` to `.mjs` that `spawnSync`s `python3`/`python`
     for the RF parser body.
   - Delete `transforms.rewrite_hooks_for_windows()` and its tests.
   - Update `plugins/rf-agentskills/hooks/hooks.json` to reference `.mjs`.
   - At install time, the adapter probes `shutil.which("node")`; if absent,
     skip hooks with a clear post_install note (Windows users who only have
     the native Claude Code installer + no separate Node install get the
     note; everyone else gets working hooks).
   - Lift the `pytest.mark.skipif(sys.platform == 'win32', …)` we added in
     v0.4.1 — port `tests/test_hook_scripts.py` to drive the `.mjs` scripts
     instead. The test pattern is identical: pipe JSON to stdin, assert on
     stdout + exit. Tests become **cross-platform** for free.

**Alternative: ship Option A1 as v0.4.2.** ~2x the diff of the pure hotfix
and an extra ~2 days of work. Windows users get a working install in one
release. Probably the right call if we're confident in the Node-on-PATH
assumption for our target users (npm-installed Claude Code is the canonical
flow; native installer is opt-in and recent).

**Why Node over Python (the change from rev 1)**

The blog post's argument that Claude Code itself ships Node is the
clinching point: Node is on PATH for the majority of Claude Code installs,
and the community is converging on Node hooks. Python is a viable fallback
for users who installed Claude Code natively and don't have Node — we
should probe and gracefully degrade rather than refuse to install.

**Why not Python as primary (alternative considered)**

Python is attractive *for this specific package* because `rf-agentskills`
already requires Python everywhere else (installer, MCP server, skill
scripts). But:
- The interpreter-name ambiguity (`python3` vs `python` vs `py`) is real on
  Windows; baking `sys.executable` is fragile to venv moves.
- Future maintainers will hit prior art in Node-hook patterns and ask why
  we're an outlier.
- The single-runtime argument is weaker than it looks: validate-robot still
  needs Python regardless of which language the *hook driver* is in.

---

## 9. Test plan

Whichever option lands:

- **Add a regression test** that asserts every command emitted in the
  Windows install's hooks block resolves to an existing file inside the
  package's `_assets/`. This test would have caught v0.4.1's broken
  `.sh→.ps1` rewrite immediately. Implementation: enumerate `plan.merges`
  for the hooks merge, extract each `"command"`, parse out the script path
  with a regex, check existence in `_assets/scripts/`.
- **Run on the Windows CI matrix** (added in v0.4.1) — the test must run on
  `windows-latest` for the file-existence check to actually exercise
  Windows path resolution.

For Option A1 (Node) specifically:
- Port `tests/test_hook_scripts.py` to `node` as the subprocess executable.
  The tests already pipe JSON to stdin and assert on stdout/exit, so the
  driver change is one line.
- The new tests run on every OS — drop the Windows skip from v0.4.1.
- New test: hook command shape — assert the install plan registers
  `node "<path>.mjs"`, not `bash <…>.sh` or `powershell -File <…>.ps1`.
- New test: graceful-degrade — when `shutil.which("node")` is monkeypatched
  to return None, the hooks merge is omitted and a note is added to
  `post_install` output.

---

## 10. Decision points for the implementer

1. **v0.4.2 = Option C alone, or Option A1 directly?** — depends on
   appetite for delay vs. completeness. Default to Option C for speed; A1
   directly is a 2-day stretch but ships full Windows support.
2. **Node-absent fallback strategy** — possible answers:
   - (a) Skip hooks with a note (proposed default).
   - (b) Fall back to Python hooks if Python is on PATH (doubles maintenance).
   - (c) Bundle Node binaries with the wheel (rejected: too heavy).
3. **Where to put per-OS hook command formatting** — proposing a tiny helper
   in `ClaudeCodeAdapter` (`_hook_command(script: str) -> str`) so both the
   hooks block and any future similar emitter share one source.
4. **Migration for existing users on v0.4.1 Windows installs** — they have
   the broken `.ps1` references in `~/.claude/settings.json`. Our
   `uninstall` cleans them up via the manifest. CHANGELOG should advise
   `rf-agentskills uninstall --agent claude-code` followed by `install`
   (or verify `install --force` cleanly overwrites the broken merge).
5. **MCP server (Python) vs hooks (Node)** — accept that the package will
   ship code in both languages going forward. Document in README. Could
   reconsider porting the MCP server to Node later but that's out of scope
   for this issue.

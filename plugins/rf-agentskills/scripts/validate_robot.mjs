#!/usr/bin/env node
// validate_robot.mjs — Validate Robot Framework .robot and .resource files.
//
// Called by the PostToolUse hook after Write or Edit operations. Reads the
// edited file_path from the TOOL_INPUT environment variable (Claude Code
// hook contract, see Anthropic docs).
//
// The actual parsing happens in Python via `robot.api.get_model`; this
// hook is a thin orchestrator. The interpreter is resolved from
// `python_runtime.json` next to this script (written by the installer
// from `sys.executable` at install time) so the hook targets the same
// venv / pipx / uv tool environment that has `robotframework`
// installed — not whatever generic `python3` happens to be on PATH.
// Falls back to `python3` then `python` on PATH if the recorded
// interpreter is unavailable.
//
// Exits 0 silently when:
//   - TOOL_INPUT is missing or unparsable
//   - the file isn't .robot / .resource
//   - the file no longer exists
//   - no Python interpreter is available
//   - robotframework isn't installed
// Exits 1 only when robotframework is installed AND get_model reports a
// real parse error.
import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadPythonInterpreters() {
  const candidates = [];
  try {
    const cfg = JSON.parse(
      readFileSync(join(HERE, "python_runtime.json"), "utf-8"),
    );
    if (typeof cfg.interpreter === "string" && cfg.interpreter) {
      candidates.push(cfg.interpreter);
    }
    for (const fb of cfg.fallbacks ?? []) {
      if (typeof fb === "string" && fb && !candidates.includes(fb)) {
        candidates.push(fb);
      }
    }
  } catch {
    // Config missing or unreadable — use PATH fallbacks only.
  }
  for (const fb of ["python3", "python"]) {
    if (!candidates.includes(fb)) candidates.push(fb);
  }
  return candidates;
}

const toolInput = process.env.TOOL_INPUT ?? "";
if (!toolInput) process.exit(0);

let filePath = "";
try {
  filePath = (JSON.parse(toolInput).file_path ?? "").toString();
} catch {
  process.exit(0);
}
if (!filePath) process.exit(0);

// Only validate .robot and .resource files.
if (!/\.(robot|resource)$/i.test(filePath)) process.exit(0);

// File may have been moved/deleted before the hook fired.
if (!existsSync(filePath)) process.exit(0);

// Inline Python parser — same logic as the original bash version's
// `python3 -c "..."` heredoc. Exits 0 on success / informational paths;
// exits 1 on a real RF parse error.
const PY_PARSER = `
import sys
try:
    from robot.api import get_model
except ImportError:
    print('Robot Framework not installed, skipping syntax validation.', file=sys.stderr)
    sys.exit(0)

try:
    model = get_model(sys.argv[1])
    sections = list(getattr(model, 'sections', []) or [])
    if not sections:
        print('WARNING: No recognized sections found '
              '(expected *** Settings ***, *** Test Cases ***, '
              '*** Keywords ***, or *** Variables ***)', file=sys.stderr)
    else:
        print(f'Robot Framework syntax OK: {sys.argv[1]}', file=sys.stderr)
    sys.exit(0)
except Exception as e:
    print(f'Robot Framework syntax error in {sys.argv[1]}: {e}', file=sys.stderr)
    sys.exit(1)
`;

for (const py of loadPythonInterpreters()) {
  const r = spawnSync(py, ["-c", PY_PARSER, filePath], {
    stdio: ["ignore", "inherit", "inherit"],
  });
  // ENOENT → interpreter not found on PATH (or the recorded absolute
  // path no longer exists); try the next candidate.
  if (r.error && r.error.code === "ENOENT") continue;
  // Anything else (spawn succeeded, even with nonzero exit) is authoritative.
  process.exit(r.status ?? 0);
}

// No Python interpreter available at all. Stay silent — the hook is
// non-blocking, and a stderr warning every save would be noisy.
process.exit(0);

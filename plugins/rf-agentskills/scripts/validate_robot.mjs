#!/usr/bin/env node
// validate_robot.mjs — Per-file static validation for Robot Framework
// .robot / .resource files.
//
// Runs from the PostToolUse hook after Write or Edit. Two tiers:
//
//   Tier 1 (structural errors): `robocop check --threshold E`. Reports
//     only error-severity findings (invalid FOR/IF/TRY syntax, bad
//     arguments, broken imports the linter can see, duplicates) and
//     suppresses the ~130 style rules that would otherwise fire on
//     every valid file. On a real error the hook exits 2 and writes the
//     diagnostic to stderr — the Claude Code PostToolUse contract feeds
//     stderr back to the agent on exit 2, so the agent can self-correct.
//     (Exit 1 is shown to the user only, which is why the previous
//     get_model-based check — which also never actually detected
//     anything — was invisible to the model.)
//
//   Tier 2 (formatting drift): `robocop format --check --diff`. Purely
//     informational. Surfaces the proposed reformat as additionalContext
//     (exit 0). Formatting alone NEVER triggers exit 2.
//
// Input contract: Claude Code delivers the PostToolUse event as JSON on
// stdin (matching the plugin's other hooks). For resilience we also
// accept the legacy `TOOL_INPUT` env var if stdin carries no usable
// payload.
//
// The interpreter is resolved from `python_runtime.json` next to this
// script (written by the installer from `sys.executable`) so robocop is
// invoked from the same venv / pipx / uv environment that has Robot
// Framework — not whatever generic `python3` is on PATH. Robocop is an
// OPTIONAL dependency: if no resolved interpreter has it installed the
// hook exits 0 silently (graceful degradation — never break a session).
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

// Resolve the edited file path from stdin JSON (preferred) or the
// legacy TOOL_INPUT env var. Returns "" when nothing usable is found.
function resolveFilePath() {
  let raw = "";
  try {
    raw = readFileSync(0, "utf-8");
  } catch {
    // No stdin available; fall through to env.
  }
  for (const source of [raw, process.env.TOOL_INPUT ?? ""]) {
    if (!source) continue;
    try {
      const obj = JSON.parse(source);
      // PostToolUse stdin shape: { tool_input: { file_path } }.
      // Legacy TOOL_INPUT shape: { file_path }.
      const fp = obj?.tool_input?.file_path ?? obj?.file_path ?? "";
      if (fp) return fp.toString();
    } catch {
      // Not JSON — try the next source.
    }
  }
  return "";
}

const filePath = resolveFilePath();
if (!filePath) process.exit(0);

// Only validate .robot and .resource files.
if (!/\.(robot|resource)$/i.test(filePath)) process.exit(0);

// File may have been moved/deleted before the hook fired.
if (!existsSync(filePath)) process.exit(0);

// Find the first interpreter that actually has robocop importable.
// Returns the interpreter string, or null if none / no interpreter.
function findRobocopInterpreter() {
  for (const py of loadPythonInterpreters()) {
    const probe = spawnSync(py, ["-c", "import robocop"], {
      stdio: ["ignore", "ignore", "ignore"],
    });
    if (probe.error && probe.error.code === "ENOENT") continue; // py missing
    if (probe.status === 0) return py; // py exists AND has robocop
    // py exists but robocop not installed there — keep looking in case a
    // fallback interpreter has it.
  }
  return null;
}

const py = findRobocopInterpreter();
// Robocop is optional. No interpreter has it → stay silent.
if (!py) process.exit(0);

// ── Tier 1: structural errors (error severity only) ─────────────────────────
const check = spawnSync(
  py,
  ["-m", "robocop", "check", "--threshold", "E", filePath],
  { encoding: "utf-8" },
);

// robocop exits non-zero when error-severity issues are found (and prints
// them to stdout). Surface them to the agent via stderr + exit 2 so it can
// self-correct. Guard on non-empty stdout so an unexpected robocop crash
// (which would also be non-zero) doesn't masquerade as a file error.
if (check.status !== 0 && (check.stdout ?? "").trim()) {
  process.stderr.write(
    `Robot Framework validation found errors in ${filePath}:\n` +
      check.stdout.trim() +
      "\n",
  );
  process.exit(2);
}

// ── Tier 2: formatting drift (informational only) ───────────────────────────
const fmt = spawnSync(
  py,
  ["-m", "robocop", "format", "--check", "--diff", "--no-overwrite", filePath],
  { encoding: "utf-8" },
);

// Non-zero here means "would reformat". Surface the diff as additionalContext
// (exit 0) — formatting is a suggestion, never a model-facing error.
if (fmt.status !== 0 && (fmt.stdout ?? "").trim()) {
  const payload = {
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext:
        `Robocop suggests formatting changes for ${filePath} ` +
        `(run \`robocop format\` to apply):\n` +
        fmt.stdout.trim(),
    },
  };
  process.stdout.write(JSON.stringify(payload) + "\n");
}

process.exit(0);

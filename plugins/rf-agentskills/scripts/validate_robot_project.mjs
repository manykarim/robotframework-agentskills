#!/usr/bin/env node
// validate_robot_project.mjs — Opt-in, end-of-task project-wide validation
// for Robot Framework suites. Runs from the Stop hook.
//
// This tier performs CROSS-FILE / semantic checks that only make sense
// once the whole project is on disk — running them per-save would
// false-alarm constantly (a keyword you just wrote looks "unused" until
// something calls it). One tool, one run:
//
//   `robotcode --format json analyze code --collect-unused` from the project
//   root. It reads robot.toml (paths, python-path, variables) and reports
//     - every error-severity diagnostic (unresolved keywords and variables,
//       failed imports, argument errors, model errors), and
//     - unused keywords and variables (KeywordNotUsed / VariableNotUsed).
//   The JSON is parsed; robotcode's bitmask exit code is not used.
//
// OPT-IN: the entire tier is gated behind the RF_AGENTSKILLS_PROJECT_VALIDATION
// env var (truthy = 1/true/yes/on). It is OFF by default because the analysis
// loads the project's libraries (to read their keywords) and scales with
// project size. When enabled and findings exist, the hook exits 2 with the
// diagnostic on stderr so the agent gets one more turn to fix before the turn
// ends.
//
// Graceful degradation: silent no-op (exit 0) when the flag is unset, robotcode
// isn't installed, the run times out (120 s) or its output is unparsable.
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { findRobotcode, projectRoot as projectRootOf, spawnOptions } from "./_python_env.mjs";

// Project-wide checks scale with project size: bounded, but more generous than
// the per-file check. A timeout skips the check silently.
const PROJECT_TIMEOUT_MS = 120000;
const MAX_LISTED = 20;
const UNUSED_CODES = new Set(["KeywordNotUsed", "VariableNotUsed"]);

// ── Gate: opt-in only ───────────────────────────────────────────────────────
function isTruthy(v) {
  return /^(1|true|yes|on)$/i.test((v ?? "").toString().trim());
}
if (!isTruthy(process.env.RF_AGENTSKILLS_PROJECT_VALIDATION)) process.exit(0);

// Read the Stop event once (stdin can only be consumed once). Break the
// Stop-hook loop: when firing as a continuation of a previous Stop block
// (`stop_hook_active`), exit 2 here would re-block on the same persistent
// finding forever — so no-op in that state.
let stopEvent = null;
try {
  stopEvent = JSON.parse(readFileSync(0, "utf-8"));
} catch {
  // No / unparsable stdin — proceed with process cwd.
}
if (stopEvent?.stop_hook_active) process.exit(0);

// Resolve the project root from the (already-parsed) Stop event JSON (cwd),
// falling back to the process cwd.
const projectRoot = projectRootOf(stopEvent);

const findings = [];

const rc = findRobotcode(projectRoot);
if (rc) {
  const r = spawnSync(
    rc.exe,
    ["--format", "json", "--no-color", "analyze", "code", "--collect-unused"],
    spawnOptions(PROJECT_TIMEOUT_MS, { encoding: "utf-8", cwd: projectRoot }),
  );
  let data = null;
  if (!r.error && r.status !== null) {
    try {
      data = JSON.parse(r.stdout || "");
    } catch {
      data = null; // unparsable: tool failure, not a finding
    }
  }
  const errors = [];
  const unused = [];
  for (const [file, list] of Object.entries(data?.diagnostics ?? {})) {
    for (const d of Array.isArray(list) ? list : []) {
      const code = String(d?.code ?? "");
      const line = `${file}:${Number(d?.range?.start?.line ?? 0) + 1}:${Number(d?.range?.start?.character ?? 0) + 1}: ` +
        `${code}: ${String(d?.message ?? "").trim()}`;
      if (UNUSED_CODES.has(code)) unused.push(line);
      else if (d?.severity === 1) errors.push(line);
    }
  }
  const listed = (items) =>
    items.slice(0, MAX_LISTED).join("\n  ") +
    (items.length > MAX_LISTED ? `\n  … ${items.length - MAX_LISTED} more omitted.` : "");
  if (errors.length) findings.push("Errors (robotcode analyze code):\n  " + listed(errors));
  if (unused.length) findings.push("Unused keywords and variables:\n  " + listed(unused));
}

// ── Report ──────────────────────────────────────────────────────────────────
if (findings.length) {
  process.stderr.write(
    "Robot Framework project validation found issues:\n\n" +
      findings.join("\n\n") +
      "\n",
  );
  process.exit(2);
}

process.exit(0);

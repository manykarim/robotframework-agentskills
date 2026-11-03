#!/usr/bin/env node
// validate_robot.mjs — Per-file static validation for Robot Framework
// .robot / .resource files.
//
// Runs from the PostToolUse hook after Write or Edit. Tiers:
//
//   Tier 1 (one Robocop pass, classified by rule ID): `robocop check --no-cache`
//     with the project's configured rule set and a pipe-separated issue format.
//     Every parsed finding is sorted into one class:
//       - error severity (E), not a DEPR rule -> real error. The hook exits 2
//         and writes the diagnostic to stderr (Claude Code and Codex feed it
//         back to the agent) and also prints {"decision":"block","reason":…}
//         on stdout, the only channel Copilot CLI passes to its model.
//         Same set as the former `--threshold E` run.
//       - DEPR03/04/07/08/09/10/11 -> hard deprecation (advisory warning)
//       - any other DEPR rule (DEPR05/06 …) -> modernization hint (advisory)
//       - everything else (style rules) -> dropped
//     Deprecations ONLY WARN: no DEPR finding ever causes exit 2. Findings on
//     lines the edit touched are listed individually (hard first, each with the
//     modern replacement), capped at 10 lines / 2,000 characters and not
//     repeated within one session; other deprecations are counted per rule.
//     RF_AGENTSKILLS_DEPRECATION_CHECK=off turns the deprecation output off;
//     any other value (including a legacy `block`) means `warn`.
//     No parsable line from a failing Robocop run = tool failure = silence.
//
//   Tier 2 (formatting drift): `robocop format --check --diff`. Informational
//     additionalContext only.
//
//   Tier 3 (opt-in, RF_AGENTSKILLS_FILE_DRYRUN=1): `robot --dryrun` on the
//     edited suite (.robot only, not __init__.robot). Advisory context only.
//
// Advisory output (tiers 1-3) is written only when no exit-2 diagnostic is.
// Every spawned process has a timeout (Robocop 10 s, dry run 20 s, probes
// 5 s); a timeout skips that tier silently. `--no-cache` keeps Robocop from
// leaving a .robocop_cache/ directory in the user's project.
//
// Input: the PostToolUse event JSON on stdin (legacy `TOOL_INPUT` env var as a
// fallback), in any agent's shape — see _hook_input.mjs (Claude Code, Copilot
// CLI, Cursor, VS Code, Codex). Non-edit tools exit silently; a patch that
// touches several .robot/.resource files is validated file by file. Interpreter: see _python_env.mjs (VIRTUAL_ENV -> <cwd>/.venv ->
// python_runtime.json -> python3/python); Robocop and Robot Framework are
// optional — without them the tier is a silent no-op.
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { fileURLToPath } from "node:url";
import { readHookInput } from "./_hook_input.mjs";
import { findInterpreterWith, projectRoot, spawnOptions } from "./_python_env.mjs";

const ROBOCOP_TIMEOUT_MS = 10000;
const DRYRUN_TIMEOUT_MS = 20000;
const MAX_LISTED = 10;
const MAX_CHARS = 2000;

// Hard deprecations: listed first, with the modern replacement.
const HARD_DEPRECATIONS = {
  DEPR03: "`WITH NAME` → use `AS`",
  DEPR04: "singular section header → use the plural header (`*** Test Cases ***`, `*** Keywords ***`)",
  DEPR07: "`Force Tags`/`Default Tags` → use `Test Tags` (and `[Tags]    -tag`)",
  DEPR08: "`Run Keyword If`/`Unless` → use `IF`/`ELSE`/`END`",
  DEPR09: "`Exit For Loop`/`Continue For Loop` → use `BREAK`/`CONTINUE`",
  DEPR10: "`Return From Keyword (If)` → use `RETURN` (inside `IF`)",
  DEPR11: "`[Return]` → use `RETURN`",
};
// Modernization hints (RF 7 `VAR`); Robocop already gates them by RF version.
const HINTS = {
  DEPR05: "`Set Test/Suite/Global Variable` → `VAR    ${name}    value    scope=TEST|SUITE|GLOBAL` (RF 7+)",
  DEPR06: "`Create List`/`Create Dictionary` → `VAR    @{list}` / `VAR    &{dict}` (RF 7+)",
};

const ISSUE_RE = /^([IWE])\|([A-Z]+\d+)\|(.+):(\d+):(\d+)\|(.*)$/;

function isTruthy(v) {
  return /^(1|true|yes|on)$/i.test((v ?? "").toString().trim());
}

const input = readHookInput();
const event = input.event;
const robotFiles = input.isEdit
  ? input.files.filter((f) => /\.(robot|resource)$/i.test(f) && existsSync(f))
  : [];
if (!robotFiles.length) process.exit(0);
if (robotFiles.length > 1) validateEach(robotFiles);
const filePath = robotFiles[0];

/** Report real errors: stderr + exit 2, plus the decision JSON for Copilot. */
function reportErrors(text) {
  const reason =
    "The edit was applied, but Robot Framework validation found errors. Fix them:\n" + text.trim();
  process.stdout.write(JSON.stringify({ decision: "block", reason }) + "\n");
  process.stderr.write(text.endsWith("\n") ? text : text + "\n");
  process.exit(2);
}

// One edit (an apply_patch) touched several files: validate each in a child run
// of this script, then report the merged result in the same exit-code contract.
function validateEach(files) {
  const self = fileURLToPath(import.meta.url);
  const errors = [];
  const contexts = [];
  for (const f of files) {
    const child = { ...event, tool_name: "Write", tool_input: { file_path: f } };
    delete child.tool_response;
    delete child.tool_result;
    const r = spawnSync(
      process.execPath,
      [self],
      spawnOptions(ROBOCOP_TIMEOUT_MS * 2 + DRYRUN_TIMEOUT_MS, {
        input: JSON.stringify(child), encoding: "utf-8", env: { ...process.env, TOOL_INPUT: "" },
      }),
    );
    if (r.status === 2) errors.push((r.stderr ?? "").trim());
    try {
      const ctx = JSON.parse(r.stdout || "null")?.hookSpecificOutput?.additionalContext;
      if (ctx) contexts.push(ctx);
    } catch {
      // no advisory output
    }
  }
  if (errors.length) reportErrors(errors.join("\n"));
  if (contexts.length) {
    const payload = { hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: contexts.join("\n\n") } };
    process.stdout.write(JSON.stringify(payload) + "\n");
  }
  process.exit(0);
}

const cwd = projectRoot(event);
let fileLines = [];
try {
  fileLines = readFileSync(filePath, "utf-8").split(/\r?\n/);
} catch {
  process.exit(0);
}

// ── Touched lines (design D4) ───────────────────────────────────────────────
// Returns a Set of 1-based line numbers, or null for "all lines touched".
function touchedLines() {
  const response = event?.tool_response;
  const patch = response && Array.isArray(response.structuredPatch) ? response.structuredPatch : null;
  // 1. structuredPatch: '+' lines of each hunk (Edit, Write update).
  if (patch && patch.length) {
    const set = new Set();
    for (const hunk of patch) {
      let line = Number(hunk?.newStart);
      if (!Number.isInteger(line) || !Array.isArray(hunk?.lines)) return null;
      for (const l of hunk.lines) {
        const s = String(l);
        if (s.startsWith("+")) {
          set.add(line);
          line += 1;
        } else if (s.startsWith("-")) {
          // removed line: no new-file line
        } else if (s.startsWith("\\")) {
          // "\ No newline at end of file"
        } else {
          line += 1;
        }
      }
    }
    return set;
  }
  const toolName = (event?.tool_name ?? "").toString();
  const newString = event?.tool_input?.new_string;
  // 2. Edit without a patch: the spans where new_string occurs now.
  if (/^(Edit|MultiEdit)$/.test(toolName) && typeof newString === "string" && newString.trim()) {
    const text = fileLines.join("\n");
    const set = new Set();
    let from = 0;
    for (;;) {
      const idx = text.indexOf(newString, from);
      if (idx < 0) break;
      const start = text.slice(0, idx).split("\n").length;
      const span = newString.split("\n").length;
      for (let i = 0; i < span; i++) set.add(start + i);
      from = idx + Math.max(newString.length, 1);
    }
    return set.size ? set : null;
  }
  // 3. Write (create, or no patch) and anything else: the whole file.
  return null;
}

// ── Per-session dedupe marker (design D5) ───────────────────────────────────
const sessionId = (event?.session_id ?? "").toString();
const markerPath = sessionId
  ? join(tmpdir(), `rf-agentskills-depr-${sessionId.replace(/[^A-Za-z0-9._-]/g, "_")}.json`)
  : "";

function loadSeen() {
  if (!markerPath) return new Set();
  try {
    const data = JSON.parse(readFileSync(markerPath, "utf-8"));
    return new Set(Array.isArray(data) ? data.map(String) : []);
  } catch {
    return new Set();
  }
}

function saveSeen(seen) {
  if (!markerPath) return;
  try {
    writeFileSync(markerPath, JSON.stringify([...seen].slice(-2000)));
  } catch {
    // Read-only temp dir etc. — only the dedupe is lost.
  }
}

function findingKey(f) {
  const text = (fileLines[f.line - 1] ?? "").trim();
  return createHash("sha1").update(`${filePath}\0${f.rule}\0${text}`).digest("hex");
}

// ── Tier 1: one Robocop pass ────────────────────────────────────────────────
function runRobocop(py) {
  const r = spawnSync(
    py,
    [
      "-m", "robocop", "check", "--no-cache",
      "-c", "print_issues.output_format=simple",
      "--issue-format", "{severity}|{rule_id}|{source}:{line}:{col}|{desc}",
      filePath,
    ],
    spawnOptions(ROBOCOP_TIMEOUT_MS, { encoding: "utf-8", cwd }),
  );
  if (r.error || r.status === null) return null; // timeout, overflow, crash
  const findings = [];
  for (const line of (r.stdout ?? "").split(/\r?\n/)) {
    const m = ISSUE_RE.exec(line.trim());
    if (m) {
      findings.push({
        severity: m[1], rule: m[2], line: Number(m[4]), col: Number(m[5]), desc: m[6], raw: line.trim(),
      });
    }
  }
  // A failing run that printed nothing parsable is a tool failure, not a finding.
  if (!findings.length && r.status !== 0) return null;
  return findings;
}

function deprecationText(deprFindings) {
  const touched = touchedLines();
  const seen = loadSeen();
  const listed = [];
  const counted = {};
  for (const f of deprFindings) {
    const isTouched = touched === null || touched.has(f.line);
    if (isTouched && !seen.has(findingKey(f))) listed.push(f);
    else counted[f.rule] = (counted[f.rule] ?? 0) + 1;
  }
  const rank = (f) => (f.rule in HARD_DEPRECATIONS ? 0 : 1);
  listed.sort((a, b) => rank(a) - rank(b) || a.line - b.line || a.col - b.col);
  if (!listed.length && !Object.keys(counted).length) return "";

  const name = basename(filePath);
  const header =
    `Deprecated Robot Framework syntax in ${filePath} (advisory, not blocking; ` +
    "modern forms: rf-language skill, references/migration.md):";
  const lines = [header];
  let used = header.length;
  let shown = 0;
  const emitted = [];
  for (const f of listed) {
    const hard = f.rule in HARD_DEPRECATIONS;
    const replacement = HARD_DEPRECATIONS[f.rule] ?? HINTS[f.rule] ?? f.desc;
    const line = `  ${hard ? "WARN" : "HINT"} ${f.rule} ${name}:${f.line} — ${replacement}`;
    if (shown >= MAX_LISTED || used + line.length + 1 > MAX_CHARS - 260) break;
    lines.push(line);
    used += line.length + 1;
    emitted.push(f);
    shown += 1;
  }
  const omitted = listed.length - shown;
  if (omitted > 0) lines.push(`  … ${omitted} more deprecation finding(s) omitted.`);
  const counts = Object.entries(counted).sort(([a], [b]) => a.localeCompare(b));
  if (counts.length) {
    lines.push(
      "  Also in this file (lines not changed by this edit, or already reported this session): " +
        counts.map(([rule, n]) => `${rule} ×${n}`).join(", ") + ".",
    );
  }
  lines.push(
    "  Silence with RF_AGENTSKILLS_DEPRECATION_CHECK=off or by ignoring the rule in the Robocop config.",
  );
  for (const f of emitted) seen.add(findingKey(f));
  saveSeen(seen);
  let text = lines.join("\n");
  if (text.length > MAX_CHARS) text = text.slice(0, MAX_CHARS - 1) + "…";
  return text;
}

// ── Tier 3 (opt-in): per-file dry run ───────────────────────────────────────
function dryRunText() {
  if (!isTruthy(process.env.RF_AGENTSKILLS_FILE_DRYRUN)) return "";
  if (!/\.robot$/i.test(filePath) || /^__init__\.robot$/i.test(basename(filePath))) return "";
  const py = findInterpreterWith("robot", cwd);
  if (!py) return "";
  const r = spawnSync(
    py,
    ["-m", "robot", "--dryrun", "--output", "NONE", "--report", "NONE", "--log", "NONE",
      "--console", "dotted", filePath],
    spawnOptions(DRYRUN_TIMEOUT_MS, { encoding: "utf-8", cwd }),
  );
  if (r.error || r.status === null) return "";
  const out = `${r.stdout ?? ""}\n${r.stderr ?? ""}`.split(/\r?\n/);
  const items = [];
  for (let i = 0; i < out.length; i++) {
    const l = out[i];
    if (l.includes("[ ERROR ]") && !/contains no tests/i.test(l)) items.push(l.trim());
    else if (l.startsWith("FAIL: ")) {
      const msg = [];
      for (let j = i + 1; j < out.length && !/^[-=]{10,}/.test(out[j]); j++) {
        if (out[j].trim()) msg.push(out[j].trim());
      }
      items.push(`${l.slice(6).trim()}: ${msg.join(" ")}`);
    }
  }
  if (!items.length) return "";
  const shown = items.slice(0, MAX_LISTED).map((s) => `  ${s.length > 300 ? s.slice(0, 299) + "…" : s}`);
  if (items.length > MAX_LISTED) shown.push(`  … ${items.length - MAX_LISTED} more omitted.`);
  let text = `robot --dryrun of ${filePath} (advisory; a keyword you write next may still be missing):\n` +
    shown.join("\n");
  if (text.length > MAX_CHARS) text = text.slice(0, MAX_CHARS - 1) + "…";
  return text;
}

// ── Main ────────────────────────────────────────────────────────────────────
const advisory = [];
const robocopPy = findInterpreterWith("robocop", cwd);
if (robocopPy) {
  const findings = runRobocop(robocopPy);
  if (findings) {
    const errors = findings.filter((f) => f.severity === "E" && !f.rule.startsWith("DEPR"));
    if (errors.length) {
      reportErrors(
        `Robot Framework validation found errors in ${filePath}:\n` +
          errors.map((f) => `${filePath}:${f.line}:${f.col} [E] ${f.rule} ${f.desc}`).join("\n"),
      );
    }
    const mode = (process.env.RF_AGENTSKILLS_DEPRECATION_CHECK ?? "").trim().toLowerCase();
    if (mode !== "off") {
      const text = deprecationText(findings.filter((f) => f.rule.startsWith("DEPR")));
      if (text) advisory.push(text);
    }

    // ── Tier 2: formatting drift (informational only) ──
    const fmt = spawnSync(
      robocopPy,
      ["-m", "robocop", "format", "--no-cache", "--check", "--diff", "--no-overwrite", filePath],
      spawnOptions(ROBOCOP_TIMEOUT_MS, { encoding: "utf-8", cwd }),
    );
    if (!fmt.error && fmt.status !== 0 && fmt.status !== null && (fmt.stdout ?? "").trim()) {
      let diff = fmt.stdout.trim();
      if (diff.length > MAX_CHARS) diff = diff.slice(0, MAX_CHARS - 1) + "…";
      advisory.push(
        `Robocop suggests formatting changes for ${filePath} (run \`robocop format\` to apply):\n` + diff,
      );
    }
  }
}

const dry = dryRunText();
if (dry) advisory.push(dry);

if (advisory.length) {
  const payload = {
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: advisory.join("\n\n"),
    },
  };
  process.stdout.write(JSON.stringify(payload) + "\n");
}
process.exit(0);

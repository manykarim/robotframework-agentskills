#!/usr/bin/env node
// validate_robot.mjs — Per-file static validation for Robot Framework
// .robot / .resource files.
//
// Runs from the PostToolUse hook after Write or Edit. Tiers:
//
//   Tier 0 (errors): `robotcode --format json analyze code <file>` from the
//     project root, so robot.toml, profiles, python-path and the installed
//     libraries apply. Error-severity diagnostics are classified by code:
//       - KeywordNotFound / VariableNotFound -> unresolved name: advisory on
//         edit (the agent may be about to write it in another file); the file
//         is recorded as pending and blocks at Stop if still unresolved.
//       - any other error (ModelError, argument DataError, failed import, …)
//         -> blocking error. The hook exits 2 and writes the diagnostic to
//         stderr (Claude Code and Codex feed it back to the agent) and also
//         prints {"decision":"block","reason":…} on stdout, the only channel
//         Copilot CLI passes to its model.
//     Warnings, infos and hints are dropped; each list shows at most 5
//     diagnostics. With RF_AGENTSKILLS_STOP_RECHECK=1 (set by
//     report_pending_errors.mjs) unresolved names block too and the advisory
//     tiers are skipped. No robotcode, a timeout (20 s) or unparsable output =
//     silence: a tool failure is never a finding.
//
//   Tier 1 (deprecations, one Robocop pass classified by rule ID):
//     `robocop check --no-cache` with the project's configured rule set and a
//     pipe-separated issue format. Error findings are left to tier 0:
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
// Advisory output (tiers 0-3) is written only when no exit-2 diagnostic is.
// A file with blocking errors or unresolved names is also recorded per session
// (_pending_errors.mjs) and cleared by its next clean run; report_pending_errors.mjs
// re-checks the recorded files at Stop. Every spawned process has a timeout
// (robotcode 20 s, Robocop 10 s, dry run 20 s, probes 5 s); a timeout skips
// that tier silently. `--no-cache` keeps Robocop from leaving a .robocop_cache/
// directory; robotcode keeps its normal .robotcode_cache/ (the warm cache makes
// the check take about a second).
//
// Input: the PostToolUse event JSON on stdin (legacy `TOOL_INPUT` env var as a
// fallback), in any agent's shape — see _hook_input.mjs (Claude Code, Copilot
// CLI, Cursor, VS Code, Codex). Non-edit tools exit silently; a patch that
// touches several .robot/.resource files is validated file by file. Tools: see
// _python_env.mjs (VIRTUAL_ENV -> <cwd>/.venv -> python_runtime.json -> PATH);
// robotcode, Robocop and Robot Framework are each optional — a missing tool
// makes its tier a silent no-op.
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { tmpdir } from "node:os";
import { basename, dirname, join, relative, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { readHookInput } from "./_hook_input.mjs";
import { recordResult } from "./_pending_errors.mjs";
import { findInterpreterWith, findRobotcode, projectRoot, spawnOptions } from "./_python_env.mjs";

// Child processes still running; killed when the hook exits early.
const running = new Set();
const ANALYZE_TIMEOUT_MS = 20000;
const ROBOCOP_TIMEOUT_MS = 10000;
const DRYRUN_TIMEOUT_MS = 20000;
const MAX_LISTED = 10;
const MAX_DIAGNOSTICS = 5;
const MAX_CHARS = 2000;
// Diagnostics that may resolve once the agent writes the next file.
const UNRESOLVED_CODES = new Set(["KeywordNotFound", "VariableNotFound"]);
const STOP_RECHECK = /^(1|true|yes|on)$/i.test((process.env.RF_AGENTSKILLS_STOP_RECHECK ?? "").trim());

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
  for (const child of running) child.kill("SIGKILL");
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
      spawnOptions(ANALYZE_TIMEOUT_MS + ROBOCOP_TIMEOUT_MS * 2 + DRYRUN_TIMEOUT_MS, {
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

// The robotcode and Robocop runs are independent, so they run in parallel; the
// hook then takes about as long as the slowest of them.
function spawnAsync(cmd, args, defaultTimeoutMs, runDir = cwd) {
  const opts = spawnOptions(defaultTimeoutMs);
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(cmd, args, { cwd: runDir, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
    } catch (error) {
      resolve({ error, status: null, stdout: "" });
      return;
    }
    running.add(child);
    let stdout = "";
    let done = false;
    const finish = (res) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      running.delete(child);
      resolve(res);
    };
    const timer = setTimeout(() => {
      child.kill(opts.killSignal);
      finish({ error: new Error("timeout"), status: null, stdout });
    }, opts.timeout);
    child.stdout.setEncoding("utf-8");
    child.stdout.on("data", (chunk) => {
      if (stdout.length < opts.maxBuffer) stdout += chunk;
    });
    child.stderr.resume();
    child.on("error", (error) => finish({ error, status: null, stdout }));
    child.on("close", (status) => finish({ error: null, status, stdout }));
  });
}

function exitNow(code) {
  for (const child of running) child.kill("SIGKILL");
  process.exit(code);
}

// ── Tier 0: robotcode analyze code ──────────────────────────────────────────
// Returns {blocking, unresolved} (lists of {line, col, code, message}) or null
// when robotcode is missing, timed out or printed nothing parsable.
function startAnalyze() {
  const rc = findRobotcode(cwd);
  if (!rc) return Promise.resolve(null);
  // robotcode only analyzes files under the root it finds from its working
  // directory; a file outside the event's project is analyzed from its folder.
  const rel = relative(cwd, filePath);
  const runDir = rel && !rel.startsWith("..") && !isAbsolute(rel) ? cwd : dirname(filePath);
  return spawnAsync(rc.exe, ["--format", "json", "--no-color", "analyze", "code", filePath], ANALYZE_TIMEOUT_MS, runDir);
}

function parseAnalyze(r) {
  if (!r || r.error || r.status === null) return null;
  let data;
  try {
    data = JSON.parse(r.stdout || "");
  } catch {
    return null;
  }
  const byFile = data && typeof data.diagnostics === "object" && data.diagnostics ? data.diagnostics : null;
  if (!byFile) return null;
  if (data.summary && data.summary.files === 0) return null; // nothing analyzed: no result
  const blocking = [];
  const unresolved = [];
  for (const list of Object.values(byFile)) {
    for (const d of Array.isArray(list) ? list : []) {
      if (d?.severity !== 1) continue; // LSP severity 1 = error
      const item = {
        line: Number(d.range?.start?.line ?? 0) + 1,
        col: Number(d.range?.start?.character ?? 0) + 1,
        code: String(d.code ?? "Error"),
        message: String(d.message ?? "").trim(),
      };
      (UNRESOLVED_CODES.has(item.code) ? unresolved : blocking).push(item);
    }
  }
  const order = (a, b) => a.line - b.line || a.col - b.col;
  return { blocking: blocking.sort(order), unresolved: unresolved.sort(order) };
}

function diagnosticLines(items) {
  const lines = items
    .slice(0, MAX_DIAGNOSTICS)
    .map((d) => `${filePath}:${d.line}:${d.col}: [ERROR] ${d.code}: ${d.message}`);
  if (items.length > MAX_DIAGNOSTICS) lines.push(`… ${items.length - MAX_DIAGNOSTICS} more omitted.`);
  return lines.join("\n");
}

// ── Tier 1: one Robocop pass ────────────────────────────────────────────────
function startRobocop(py) {
  return spawnAsync(
    py,
    [
      "-m", "robocop", "check", "--no-cache",
      "-c", "print_issues.output_format=simple",
      "--issue-format", "{severity}|{rule_id}|{source}:{line}:{col}|{desc}",
      filePath,
    ],
    ROBOCOP_TIMEOUT_MS,
  );
}

function parseRobocop(r) {
  if (!r || r.error || r.status === null) return null; // timeout, overflow, crash
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
const robocopPy = STOP_RECHECK ? null : findInterpreterWith("robocop", cwd);
const analyzeRun = startAnalyze();
const robocopRun = robocopPy ? startRobocop(robocopPy) : Promise.resolve(null);
const formatRun = robocopPy
  ? spawnAsync(robocopPy, ["-m", "robocop", "format", "--no-cache", "--check", "--diff", "--no-overwrite", filePath],
    ROBOCOP_TIMEOUT_MS)
  : Promise.resolve(null);
const analysis = parseAnalyze(await analyzeRun);
if (analysis) {
  const { blocking, unresolved } = analysis;
  // Remember the result for the Stop-time re-check (report_pending_errors.mjs).
  recordResult(sessionId, filePath, blocking.length + unresolved.length > 0);
  const blockingNow = STOP_RECHECK ? [...blocking, ...unresolved] : blocking;
  if (blockingNow.length) {
    reportErrors(`Robot Framework validation found errors in ${filePath}:\n` + diagnosticLines(blockingNow));
  }
  if (unresolved.length) {
    advisory.push(
      `robotcode cannot resolve these names in ${filePath} yet (advisory; define or import them before you ` +
        "finish, the check blocks at the end of the turn otherwise):\n" + diagnosticLines(unresolved),
    );
  }
}
if (STOP_RECHECK) exitNow(0);

if (robocopPy) {
  const findings = parseRobocop(await robocopRun);
  if (findings) {
    const mode = (process.env.RF_AGENTSKILLS_DEPRECATION_CHECK ?? "").trim().toLowerCase();
    if (mode !== "off") {
      const text = deprecationText(findings.filter((f) => f.rule.startsWith("DEPR")));
      if (text) advisory.push(text);
    }

    // ── Tier 2: formatting drift (informational only) ──
    const fmt = await formatRun;
    if (fmt && !fmt.error && fmt.status !== 0 && fmt.status !== null && (fmt.stdout ?? "").trim()) {
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

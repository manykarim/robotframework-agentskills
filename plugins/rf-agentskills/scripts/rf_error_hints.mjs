#!/usr/bin/env node
// rf_error_hints.mjs — PostToolUse hook (matcher: Bash).
//
// Scans a Bash command's output for Robot Framework error messages and, the
// first time each kind of error appears in a session, injects one short hint:
// which rf-agentskills skill to load and the concrete fix. Agents reliably read
// the error they just caused; that is where the pointer to the skill helps.
//
// Schema:
//   stdin  — Claude Code PostToolUse event JSON for the Bash tool
//            (tool_response.stdout / .stderr, or a plain string).
//   stdout — Either empty or one JSON object:
//            {"hookSpecificOutput": {"hookEventName": "PostToolUse",
//             "additionalContext": "..."}}.
//   exit   — Always 0. The hook never blocks.
import { readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const MAX_SCAN = 20000; // characters of output scanned
const MAX_HINT = 400; // characters per hint
const MAX_NAME = 80; // characters of an offending name quoted in a hint

// kind, pattern (first group = offending name, if any), hint builder
const SIGNATURES = [
  {
    kind: "no-keyword",
    re: /No keyword with name '([^']*)' found/,
    hint: (name) =>
      `Robot Framework found no keyword '${name}'. If the call carries values inside the name ` +
      "(e.g. 'Select team Los Angeles Lakers'), define an embedded-argument keyword such as " +
      "`Select team ${city} ${team:\\S+}`; the text between arguments is literal, not a regex. " +
      "Load the rf-language skill. For library keywords, check the exact name with rf-libdoc.",
  },
  {
    kind: "multiple-keywords",
    re: /Multiple keywords with name '([^']*)' found/,
    hint: (name) =>
      `Keyword '${name}' is defined more than once. Call it qualified (resource.Keyword) or set ` +
      "`Set Library Search Order`, or rename one. See the rf-language skill.",
  },
  {
    kind: "argument-syntax",
    re: /Invalid argument syntax '([^']*)'/,
    hint: (name) =>
      `Invalid argument syntax '${name}'. Typed user-keyword arguments are written \`\${count: int}\` ` +
      "and need RF 7.3+; `${count}: int` is invalid. See the rf-language skill.",
  },
  {
    kind: "variable",
    re: /Resolving variable '([^']*)' failed/,
    hint: (name) =>
      `Variable '${name}' could not be resolved. Check its scope (VAR scope=TEST|SUITE|GLOBAL), ` +
      "the import order of resource/variable files, and `$var` vs `${var}` in expressions. " +
      "See the rf-language skill.",
  },
  {
    kind: "library-import",
    re: /Importing library '([^']*)' failed/,
    hint: (name) =>
      `Library '${name}' could not be imported. Install it into the project environment ` +
      "(e.g. `uv add <package>`) and run robot from that environment. See the rf-setup skill.",
  },
];

function outputText(response) {
  if (response == null) return "";
  if (typeof response === "string") return response;
  const parts = [];
  for (const key of ["stdout", "stderr", "output", "content"]) {
    const v = response[key];
    if (typeof v === "string") parts.push(v);
  }
  return parts.join("\n");
}

function main() {
  let raw = "";
  try { raw = readFileSync(0, "utf-8"); } catch { return; }
  if (!raw) return;
  let event;
  try { event = JSON.parse(raw); } catch { return; }
  if (!event || typeof event !== "object") return;

  const text = outputText(event.tool_response).slice(0, MAX_SCAN);
  if (!text) return;

  const sessionId = (event.session_id ?? "").toString();
  const marker = sessionId
    ? join(tmpdir(), `rf-agentskills-hints-${sessionId.replace(/[^A-Za-z0-9._-]/g, "_")}.json`)
    : "";
  let seen = new Set();
  if (marker) {
    try { seen = new Set(JSON.parse(readFileSync(marker, "utf-8")).map(String)); } catch { /* none yet */ }
  }

  const hints = [];
  for (const sig of SIGNATURES) {
    if (seen.has(sig.kind)) continue;
    const m = sig.re.exec(text);
    if (!m) continue;
    const name = (m[1] ?? "").slice(0, MAX_NAME);
    hints.push(sig.hint(name).slice(0, MAX_HINT));
    seen.add(sig.kind);
  }
  if (!hints.length) return;

  if (marker) {
    try { writeFileSync(marker, JSON.stringify([...seen])); } catch { /* dedupe lost only */ }
  }
  const payload = {
    hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: hints.join("\n\n") },
  };
  process.stdout.write(JSON.stringify(payload) + "\n");
}

try { main(); } catch { /* never block */ }
process.exit(0);

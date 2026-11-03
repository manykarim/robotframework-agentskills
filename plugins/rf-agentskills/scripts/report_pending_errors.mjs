#!/usr/bin/env node
// report_pending_errors.mjs — Stop hook: re-validate the .robot/.resource
// files whose PostToolUse validation failed this session and, if they still
// fail, block the stop so the agent gets one more turn to fix them.
//
// Needed for VS Code's Local agent mode, which does not wait for PostToolUse
// hooks before the next model request (the error only reaches the user as a
// banner). Agents that do deliver PostToolUse feedback normally fix the file
// first, which clears its entry, so this hook stays silent there.
//
// Output contract (same as validate_robot.mjs): stderr diagnostic + exit 2
// (Claude Code, Codex and VS Code Local continue with stderr as the reason),
// plus {"decision":"block","reason":…} on stdout for Copilot.
//
// Loop safety: no-op when stop_hook_active is set, and a file is reported at
// most once per content version (its sha1 is remembered), so an unfixable
// file can't block every later turn.
import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { contentHash, loadPending, savePending } from "./_pending_errors.mjs";
import { spawnOptions } from "./_python_env.mjs";

let event = null;
try {
  event = JSON.parse(readFileSync(0, "utf-8"));
} catch {
  process.exit(0);
}
if (!event || event.stop_hook_active) process.exit(0);
const sessionId = (event.session_id ?? "").toString();
if (!sessionId) process.exit(0);

const VALIDATOR = join(dirname(fileURLToPath(import.meta.url)), "validate_robot.mjs");
const errors = [];
const stillPending = Object.entries(loadPending(sessionId));
if (!stillPending.length) process.exit(0);

for (const [file, info] of stillPending) {
  if (!existsSync(file)) continue;
  const hash = contentHash(file);
  if (hash && info?.reported === hash) continue; // already reported this version
  const child = { ...event, hook_event_name: "PostToolUse", tool_name: "Write", tool_input: { file_path: file } };
  const r = spawnSync(
    process.execPath,
    [VALIDATOR],
    spawnOptions(45000, { input: JSON.stringify(child), encoding: "utf-8", env: { ...process.env, TOOL_INPUT: "" } }),
  );
  if (r.status === 2 && (r.stderr ?? "").trim()) errors.push({ file, hash, text: r.stderr.trim() });
}

// The validator child runs updated the state (cleared fixed files); reload,
// drop deleted files and remember what we report now.
const state = loadPending(sessionId);
for (const file of Object.keys(state)) if (!existsSync(file)) delete state[file];
for (const e of errors) state[e.file] = { reported: e.hash };
savePending(sessionId, state);

if (!errors.length) process.exit(0);
const text = errors.map((e) => e.text).join("\n");
const reason =
  "Robot Framework validation still reports errors in files you edited. Fix them before finishing:\n" + text;
process.stdout.write(JSON.stringify({ decision: "block", reason }) + "\n");
process.stderr.write(reason + "\n");
process.exit(2);

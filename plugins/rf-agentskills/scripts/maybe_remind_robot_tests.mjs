#!/usr/bin/env node
// maybe_remind_robot_tests.mjs — Conditional Stop hook.
//
// Reads the Claude Code Stop event JSON on stdin, inspects the session
// transcript for any tool result that wrote a .robot or .resource file,
// and only emits an additionalContext reminder ("run robot, inspect
// report.html") when at least one such file was touched. Sessions that
// produced only non-RF artifacts get no injection.
//
// Cross-platform port of maybe_remind_robot_tests.sh. Reads the
// transcript via streaming-ish chunking so very long sessions don't
// blow up memory.
//
// Schema:
//   stdin  — Claude Code Stop event JSON. Includes transcript_path.
//   stdout — Either empty (no reminder) or one JSON object with
//            hookSpecificOutput.additionalContext.
//   exit   — Always 0.
import { readFileSync, existsSync, statSync, openSync, readSync, closeSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

let raw = "";
try { raw = readFileSync(0, "utf-8"); } catch { process.exit(0); }
if (!raw) process.exit(0);

let event;
try { event = JSON.parse(raw); } catch { process.exit(0); }

// Break the Stop-hook loop. Claude Code sets `stop_hook_active` when this
// Stop fires as a continuation of a previous Stop-hook block; emitting any
// model-facing output here would re-invoke the model and loop until the
// block cap. Always no-op in that state.
if (event?.stop_hook_active) process.exit(0);

const transcript = (event?.transcript_path ?? "").toString();
if (!transcript || !existsSync(transcript)) process.exit(0);

// Fire the reminder at most once per session. Without this, every later turn
// that touched a .robot file re-emits it (the noise the loop amplified). The
// marker is a tiny file in the OS temp dir keyed by session_id; all I/O is
// best-effort and must never break the (non-blocking) hook.
const sessionId = (event?.session_id ?? "").toString();
let marker = "";
if (sessionId) {
  const safe = sessionId.replace(/[^A-Za-z0-9._-]/g, "_");
  marker = join(tmpdir(), `rf-agentskills-reminded-${safe}`);
  try {
    if (existsSync(marker)) process.exit(0);
  } catch {
    // Can't stat the marker — fall through and emit (guard above prevents loops).
  }
}

// Pattern: `"file_path"  :  "...path.robot"` (or .resource). Matches the
// `grep -E` regex from the bash original. Whitespace optional between
// quotes and colon.
const FILE_PATH_RE = /"file_path"\s*:\s*"[^"]*\.(?:robot|resource)"/i;

function transcriptMentionsRfFile(path) {
  // The transcript is a JSONL file that can be tens of MB on long
  // sessions. Read in 64 KB chunks rather than slurping it all.
  const size = (() => { try { return statSync(path).size; } catch { return 0; } })();
  if (!size) return false;
  const BUF = Buffer.alloc(65536);
  const fd = openSync(path, "r");
  let pos = 0;
  let carry = "";
  try {
    while (pos < size) {
      const n = readSync(fd, BUF, 0, BUF.length, pos);
      if (n <= 0) break;
      // Stitch the boundary with the previous chunk so we don't miss a
      // match split across the seam.
      const chunk = carry + BUF.slice(0, n).toString("utf-8");
      if (FILE_PATH_RE.test(chunk)) return true;
      // Keep the last ~256 bytes as carry to bridge boundary matches.
      carry = chunk.length > 256 ? chunk.slice(-256) : chunk;
      pos += n;
    }
  } finally {
    try { closeSync(fd); } catch {}
  }
  return false;
}

if (!transcriptMentionsRfFile(transcript)) process.exit(0);

const payload = {
  hookSpecificOutput: {
    hookEventName: "Stop",
    additionalContext: [
      "Robot Framework artifacts detected this session. Recommended next steps:",
      "\n  1. Run the suite: robot --outputdir results tests/",
      "\n  2. Programmatic inspection: python \"${CLAUDE_PLUGIN_ROOT}/scripts/rf_results.py\" ",
      "--output results/output.xml --sections summary,errors --pretty",
      "\n  3. Open results/report.html for the rendered report.",
    ].join(""),
  },
};

// Record that this session has been reminded (best-effort).
if (marker) {
  try { writeFileSync(marker, ""); } catch { /* ignore — never break the hook */ }
}

process.stdout.write(JSON.stringify(payload) + "\n");
process.exit(0);

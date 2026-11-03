// _pending_errors.mjs — per-session record of .robot/.resource files whose
// last PostToolUse validation found real errors.
//
// Why: VS Code's Local agent mode (1.142) sends the next model request
// without waiting for PostToolUse hooks, so the validation error never
// reaches the model. Stop hooks ARE awaited, so validate_robot.mjs records
// failing files here and report_pending_errors.mjs re-checks them at Stop.
// In agents where PostToolUse feedback works, the fixing edit clears the
// entry again and the Stop hook stays silent.
//
// State: { "<abs path>": { reported: "<sha1 of content when last reported at Stop>" | null } }
// in the OS temp dir, keyed by session_id. All I/O is best-effort.
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { tmpdir } from "node:os";
import { join } from "node:path";

export function pendingPath(sessionId) {
  const sid = (sessionId ?? "").toString();
  if (!sid) return "";
  return join(tmpdir(), `rf-agentskills-pending-${sid.replace(/[^A-Za-z0-9._-]/g, "_")}.json`);
}

export function loadPending(sessionId) {
  const p = pendingPath(sessionId);
  if (!p) return {};
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    return data && typeof data === "object" && !Array.isArray(data) ? data : {};
  } catch {
    return {};
  }
}

export function savePending(sessionId, state) {
  const p = pendingPath(sessionId);
  if (!p) return;
  try {
    writeFileSync(p, JSON.stringify(state));
  } catch {
    // Read-only temp dir: only the Stop-time re-check is lost.
  }
}

/** Record (failed=true) or clear (failed=false) one file's validation result. */
export function recordResult(sessionId, file, failed) {
  if (!pendingPath(sessionId)) return;
  const state = loadPending(sessionId);
  if (failed) {
    if (!(file in state)) state[file] = { reported: null };
  } else if (file in state) {
    delete state[file];
  } else {
    return;
  }
  savePending(sessionId, state);
}

export function contentHash(file) {
  try {
    return createHash("sha1").update(readFileSync(file)).digest("hex");
  } catch {
    return "";
  }
}

// _hook_input.mjs — one reader for every agent's hook input.
//
// The plugin's Claude-format hooks.json runs in Claude Code, Copilot CLI,
// VS Code, Codex and Cursor. Each sends the same event names but its own tool
// names and input shapes (observed 2026-10-08):
//
//   Claude Code / Copilot CLI  tool_name Write|Edit|MultiEdit, tool_input.file_path
//   Cursor (converted hooks)   tool_name Write|Shell, file_path or tool_input.file_path
//   VS Code                    create_file / replace_string_in_file: tool_input.filePath
//                              multi_replace_string_in_file: tool_input.replacements[].filePath
//                              apply_patch: tool_input.input (patch text); run_in_terminal
//   Codex                      apply_patch: tool_input.command (patch text); Bash
//
// VS Code ignores matchers in Claude-format hooks and runs every command for
// every tool, so callers must check `isEdit` / `isShell` and exit quietly.
import { readFileSync } from "node:fs";
import { isAbsolute, resolve } from "node:path";

const EDIT_TOOLS =
  /^(write|edit|multiedit|apply_patch|create_file|replace_string_in_file|multi_replace_string_in_file|insert_edit_into_file|edit_file|edit_notebook_file|create)$/i;
const SHELL_TOOLS = /^(bash|shell|run_in_terminal|powershell|exec_command|local_shell)$/i;
const PATCH_FILE_RE = /^\*\*\* (?:Add File|Update File|Move to): (.+)$/;

function parseJson(text) {
  if (typeof text !== "string" || !text.trim()) return null;
  try {
    const obj = JSON.parse(text);
    return obj && typeof obj === "object" ? obj : null;
  } catch {
    return null;
  }
}

/** Paths of every file an `apply_patch` envelope adds, updates or moves to. */
export function patchFiles(patch) {
  if (typeof patch !== "string" || !patch.includes("*** ")) return [];
  const files = [];
  for (const line of patch.split(/\r?\n/)) {
    const m = PATCH_FILE_RE.exec(line.trim());
    if (m) files.push(m[1].trim());
  }
  return files;
}

function patchText(toolInput) {
  if (typeof toolInput === "string") return toolInput;
  for (const key of ["input", "command", "patch"]) {
    const v = toolInput?.[key];
    if (typeof v === "string" && /\*\*\* (Begin Patch|Add File:|Update File:)/.test(v)) return v;
  }
  return "";
}

/**
 * Normalize one hook event.
 * @returns {{event: object|null, tool: string, isEdit: boolean, isShell: boolean,
 *            files: string[], command: string, cwd: string}}
 */
export function normalizeHookInput(event) {
  const empty = { event: null, tool: "", isEdit: false, isShell: false, files: [], command: "", cwd: process.cwd() };
  if (!event || typeof event !== "object") return empty;
  const tool = String(event.tool_name ?? event.toolName ?? "");
  let toolInput = event.tool_input ?? event.toolArgs ?? {};
  if (typeof toolInput === "string") toolInput = parseJson(toolInput) ?? toolInput;
  const cwd = String(event.cwd || process.cwd());

  const raw = [];
  const patch = patchText(toolInput);
  raw.push(...patchFiles(patch));
  if (toolInput && typeof toolInput === "object") {
    for (const key of ["file_path", "filePath"]) {
      if (typeof toolInput[key] === "string") raw.push(toolInput[key]);
    }
    if (Array.isArray(toolInput.replacements)) {
      for (const r of toolInput.replacements) if (typeof r?.filePath === "string") raw.push(r.filePath);
    }
  }
  if (typeof event.file_path === "string") raw.push(event.file_path);

  const files = [...new Set(raw.filter(Boolean).map((f) => (isAbsolute(f) ? f : resolve(cwd, f))))];
  // No tool name (legacy TOOL_INPUT, Cursor afterFileEdit): a file path means an edit.
  const isEdit = tool ? EDIT_TOOLS.test(tool) : files.length > 0;
  const isShell = SHELL_TOOLS.test(tool);
  const command = isShell && !patch && typeof toolInput?.command === "string" ? toolInput.command : "";
  return { event, tool, isEdit, isShell, files: isEdit ? files : [], command, cwd };
}

/** Read the hook event from stdin (legacy `TOOL_INPUT` env var as a fallback). */
export function readHookInput() {
  let stdin = "";
  try {
    stdin = readFileSync(0, "utf-8");
  } catch {
    // no stdin
  }
  for (const source of [stdin, process.env.TOOL_INPUT ?? ""]) {
    const obj = parseJson(source);
    if (obj) return normalizeHookInput(obj);
  }
  return normalizeHookInput(null);
}

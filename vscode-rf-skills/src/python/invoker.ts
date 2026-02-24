import * as vscode from "vscode";
import { execFile, spawn } from "child_process";
import * as path from "path";

/** Result returned by every Python script invocation. */
export interface InvokeResult {
  data?: unknown;
  error?: string;
}

const TIMEOUT_MS = 30_000;
const MAX_BUFFER = 10 * 1024 * 1024; // 10 MB

/**
 * Resolve the scripts directory that ships alongside the extension.
 *
 * In development the layout is:
 *   <extensionPath>/scripts/<scriptName>
 *
 * The Python scripts bundled with the extension live there, but the caller
 * may also pass an absolute path.
 */
function resolveScriptPath(
  context: vscode.ExtensionContext,
  scriptName: string
): string {
  if (path.isAbsolute(scriptName)) {
    return scriptName;
  }
  return path.join(context.extensionPath, "scripts", scriptName);
}

/**
 * Return an ordered list of Python commands to try.
 *
 * Priority:
 *   1. The value configured in `rfSkills.pythonPath`
 *   2. `uv run python3`  (for projects that use `uv`)
 *   3. `python3`
 *   4. `python`
 */
export function pythonCandidates(config: vscode.WorkspaceConfiguration): string[][] {
  const configured = config.get<string>("pythonPath", "").trim();

  const candidates: string[][] = [];

  if (configured) {
    // If the user wrote something like "uv run python3" we need to split it.
    candidates.push(configured.split(/\s+/));
  }

  candidates.push(["uv", "run", "python3"]);
  candidates.push(["python3"]);
  candidates.push(["python"]);

  return candidates;
}

/**
 * Attempt to find a working Python by trying each candidate in order.
 * Returns the first candidate whose `--version` succeeds.
 */
async function resolvePython(
  config: vscode.WorkspaceConfiguration
): Promise<string[]> {
  const candidates = pythonCandidates(config);

  for (const parts of candidates) {
    const ok = await new Promise<boolean>((resolve) => {
      const [cmd, ...rest] = parts;
      execFile(
        cmd,
        [...rest, "--version"],
        { timeout: 5_000 },
        (err) => resolve(!err)
      );
    });
    if (ok) {
      return parts;
    }
  }

  throw new Error(
    "No working Python interpreter found. " +
      "Set rfSkills.pythonPath in settings or ensure python3 is on PATH."
  );
}

/**
 * Invoke a bundled Python script with CLI arguments (no stdin).
 *
 * stdout is expected to be JSON.  If it cannot be parsed the raw text is
 * returned inside the `error` field.
 */
export async function invokePythonScript(
  context: vscode.ExtensionContext,
  scriptName: string,
  args: string[],
  stdinData?: string
): Promise<InvokeResult> {
  const config = vscode.workspace.getConfiguration("rfSkills");
  let pythonParts: string[];

  try {
    pythonParts = await resolvePython(config);
  } catch (err: unknown) {
    return { error: err instanceof Error ? err.message : String(err) };
  }

  const scriptPath = resolveScriptPath(context, scriptName);
  const cwd =
    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();

  if (stdinData !== undefined) {
    return invokeWithStdin(pythonParts, scriptPath, args, stdinData, cwd);
  }

  return invokeWithExecFile(pythonParts, scriptPath, args, cwd);
}

// ------------------------------------------------------------------
// Internal helpers
// ------------------------------------------------------------------

function invokeWithExecFile(
  pythonParts: string[],
  scriptPath: string,
  args: string[],
  cwd: string
): Promise<InvokeResult> {
  return new Promise((resolve) => {
    const [cmd, ...prefix] = pythonParts;
    const fullArgs = [...prefix, scriptPath, ...args];

    execFile(
      cmd,
      fullArgs,
      { timeout: TIMEOUT_MS, maxBuffer: MAX_BUFFER, cwd },
      (err, stdout, stderr) => {
        if (err) {
          const msg = stderr?.trim() || err.message;
          resolve({ error: `Python error: ${msg}` });
          return;
        }
        resolve(parseJsonOutput(stdout));
      }
    );
  });
}

function invokeWithStdin(
  pythonParts: string[],
  scriptPath: string,
  args: string[],
  stdinData: string,
  cwd: string
): Promise<InvokeResult> {
  return new Promise((resolve) => {
    const [cmd, ...prefix] = pythonParts;
    const fullArgs = [...prefix, scriptPath, ...args];

    const proc = spawn(cmd, fullArgs, {
      cwd,
      stdio: ["pipe", "pipe", "pipe"],
      timeout: TIMEOUT_MS,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
      if (stdout.length > MAX_BUFFER) {
        proc.kill();
      }
    });

    proc.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    proc.on("error", (err) => {
      resolve({ error: `Failed to start Python: ${err.message}` });
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        const msg = stderr.trim() || `Process exited with code ${code}`;
        resolve({ error: `Python error: ${msg}` });
        return;
      }
      resolve(parseJsonOutput(stdout));
    });

    proc.stdin.write(stdinData);
    proc.stdin.end();
  });
}

function parseJsonOutput(raw: string): InvokeResult {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { data: null };
  }
  try {
    return { data: JSON.parse(trimmed) };
  } catch {
    return { error: `Unexpected output (not JSON): ${trimmed.slice(0, 500)}` };
  }
}

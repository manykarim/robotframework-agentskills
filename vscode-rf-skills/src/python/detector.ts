import * as vscode from "vscode";
import { execFile } from "child_process";
import { pythonCandidates } from "./invoker.js";

/** Full picture of the local Python / Robot Framework environment. */
export interface PythonEnvironment {
  pythonPath: string;
  pythonVersion: string;
  rfVersion?: string;
  installedLibraries: InstalledLibrary[];
}

export interface InstalledLibrary {
  name: string;
  importName: string;
  installed: boolean;
}

/**
 * Libraries that are commonly used with Robot Framework.
 * `importName` is what you would pass to `import <name>` in Python.
 */
const KNOWN_LIBRARIES: ReadonlyArray<{ name: string; importName: string }> = [
  { name: "Browser", importName: "Browser" },
  { name: "SeleniumLibrary", importName: "SeleniumLibrary" },
  { name: "AppiumLibrary", importName: "AppiumLibrary" },
  { name: "RequestsLibrary", importName: "RequestsLibrary" },
  { name: "RESTinstance", importName: "REST" },
  { name: "DatabaseLibrary", importName: "DatabaseLibrary" },
  { name: "SSHLibrary", importName: "SSHLibrary" },
  { name: "FTPLibrary", importName: "FtpLibrary" },
  { name: "ExcelLibrary", importName: "ExcelLibrary" },
  { name: "RPA.Browser.Selenium", importName: "RPA.Browser.Selenium" },
  { name: "Pabot", importName: "pabot" },
];

// Session-scoped cache so we only probe once per activation.
let cachedEnvironment: PythonEnvironment | undefined;

/**
 * Return the Python command string (might be multi-part, e.g. "uv run python3").
 * Preference: config > python3 > python.
 */
export function getPythonPath(
  config: vscode.WorkspaceConfiguration
): string {
  const explicit = config.get<string>("pythonPath", "").trim();
  if (explicit) {
    return explicit;
  }
  return "python3";
}

/**
 * Detect everything about the local Python / RF setup.
 *
 * Results are cached for the lifetime of the extension host so we do not
 * repeatedly shell out.  Call `clearEnvironmentCache()` to reset.
 */
export async function detectPythonEnvironment(): Promise<PythonEnvironment> {
  if (cachedEnvironment) {
    return cachedEnvironment;
  }

  const config = vscode.workspace.getConfiguration("rfSkills");
  const pythonParts = await findWorkingPython(config);
  const pythonCmd = pythonParts.join(" ");

  const pythonVersion = await runPython(
    pythonParts,
    ["--version"]
  ).then(
    (out) => out.replace(/^Python\s*/i, "").trim(),
    () => "unknown"
  );

  const rfVersion = await runPython(pythonParts, [
    "-c",
    "import robot; print(robot.version.VERSION)",
  ]).then(
    (out) => out.trim() || undefined,
    () => undefined
  );

  const installedLibraries = await detectLibraries(pythonParts);

  cachedEnvironment = {
    pythonPath: pythonCmd,
    pythonVersion,
    rfVersion,
    installedLibraries,
  };

  return cachedEnvironment;
}

/** Clear the cached environment so the next call re-probes the system. */
export function clearEnvironmentCache(): void {
  cachedEnvironment = undefined;
}

// ------------------------------------------------------------------
// Internal helpers
// ------------------------------------------------------------------

async function findWorkingPython(
  config: vscode.WorkspaceConfiguration
): Promise<string[]> {
  const candidates = pythonCandidates(config);

  for (const parts of candidates) {
    const ok = await runPython(parts, ["--version"]).then(
      () => true,
      () => false
    );
    if (ok) {
      return parts;
    }
  }

  throw new Error(
    "No Python interpreter found. Install Python 3 or set rfSkills.pythonPath."
  );
}

async function detectLibraries(
  pythonParts: string[]
): Promise<InstalledLibrary[]> {
  // Build a single Python snippet that probes every library at once.
  const checks = KNOWN_LIBRARIES.map(
    (lib) =>
      `try:\n    __import__("${lib.importName.split(".")[0]}")\n    print("${lib.name}=1")\nexcept ImportError:\n    print("${lib.name}=0")`
  ).join("\n");

  let output: string;
  try {
    output = await runPython(pythonParts, ["-c", checks]);
  } catch {
    // If we cannot run the check, mark all as unknown / not installed.
    return KNOWN_LIBRARIES.map((lib) => ({
      name: lib.name,
      importName: lib.importName,
      installed: false,
    }));
  }

  const lookup = new Map<string, boolean>();
  for (const line of output.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const [name, flag] = trimmed.split("=");
    if (name) {
      lookup.set(name, flag === "1");
    }
  }

  return KNOWN_LIBRARIES.map((lib) => ({
    name: lib.name,
    importName: lib.importName,
    installed: lookup.get(lib.name) ?? false,
  }));
}

function runPython(parts: string[], args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const [cmd, ...prefix] = parts;
    execFile(
      cmd,
      [...prefix, ...args],
      { timeout: 10_000 },
      (err, stdout, stderr) => {
        if (err) {
          reject(new Error(stderr?.trim() || err.message));
          return;
        }
        resolve(stdout);
      }
    );
  });
}

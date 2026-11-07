// _python_env.mjs — shared Python interpreter resolution for the hook scripts.
//
// Not a hook itself (the leading underscore marks a helper). Imported by
// validate_robot.mjs, validate_robot_project.mjs and check_rf_environment.mjs.
// findRobotcode() resolves the `robotcode` executable the same way: robotcode has
// no `python -m robotcode` entry point, so the executable next to each
// interpreter (bin/robotcode, Scripts\robotcode.exe) is used.
//
// Resolution order (first interpreter that can import the needed module wins):
//   1. the active virtual environment ($VIRTUAL_ENV)
//   2. the project's .venv under the event's working directory
//      (POSIX: .venv/bin/python, Windows: .venv\Scripts\python.exe)
//   3. the installer-recorded interpreter (python_runtime.json next to this file,
//      plus its fallbacks)
//   4. python3 / python on PATH
//
// The project environment wins so that Robocop and `robot` see the project's
// Robot Framework version. A package manager (`uv run`, `poetry run`) is never
// started: it can create environments, sync dependencies or reach the network.
//
// Every probe has a timeout (5 s by default). RF_AGENTSKILLS_HOOK_TIMEOUT_MS is a
// test-only override that caps every hook timeout (probes, Robocop, dry run).
import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { basename, dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const IS_WIN = process.platform === "win32";

export const PROBE_TIMEOUT_MS = 5000;

// Timeout for a spawned process: the given default, capped by the test-only
// override when it is a positive integer.
export function timeoutMs(defaultMs) {
  const raw = (process.env.RF_AGENTSKILLS_HOOK_TIMEOUT_MS ?? "").trim();
  const n = /^\d+$/.test(raw) ? Number(raw) : 0;
  return n > 0 ? Math.min(n, defaultMs) : defaultMs;
}

// Options shared by every spawnSync in the hooks: bounded time and output.
export function spawnOptions(defaultTimeoutMs, extra = {}) {
  return {
    timeout: timeoutMs(defaultTimeoutMs),
    killSignal: "SIGKILL",
    maxBuffer: 1024 * 1024,
    windowsHide: true,
    ...extra,
  };
}

function venvPython(root) {
  return IS_WIN
    ? join(root, "Scripts", "python.exe")
    : join(root, "bin", "python");
}

function installerInterpreters() {
  const out = [];
  try {
    const cfg = JSON.parse(readFileSync(join(HERE, "python_runtime.json"), "utf-8"));
    if (typeof cfg.interpreter === "string" && cfg.interpreter) out.push(cfg.interpreter);
    for (const fb of cfg.fallbacks ?? []) {
      if (typeof fb === "string" && fb) out.push(fb);
    }
  } catch {
    // Config missing or unreadable (plugin checkout) — PATH fallbacks only.
  }
  return out;
}

// Ordered, de-duplicated interpreter candidates for a project directory.
export function pythonCandidates(cwd) {
  const candidates = [];
  const add = (py) => {
    if (py && !candidates.includes(py)) candidates.push(py);
  };
  const venv = (process.env.VIRTUAL_ENV ?? "").trim();
  if (venv) {
    const py = venvPython(venv);
    if (existsSync(py)) add(py);
  }
  const root = cwd || process.cwd();
  const projectPy = venvPython(join(root, ".venv"));
  if (existsSync(projectPy)) add(projectPy);
  for (const py of installerInterpreters()) add(py);
  add("python3");
  add("python");
  return candidates;
}

function scriptsExe(binDir, name) {
  return join(binDir, IS_WIN ? `${name}.exe` : name);
}

// Ordered, de-duplicated `robotcode` executable candidates for a project
// directory, in the same order as pythonCandidates(): the active venv, the
// project's .venv, the installer interpreter's directory, then PATH.
export function robotcodeCandidates(cwd) {
  const out = [];
  const add = (exe) => {
    if (exe && !out.includes(exe)) out.push(exe);
  };
  const venv = (process.env.VIRTUAL_ENV ?? "").trim();
  if (venv) {
    const exe = scriptsExe(join(venv, IS_WIN ? "Scripts" : "bin"), "robotcode");
    if (existsSync(exe)) add(exe);
  }
  const root = cwd || process.cwd();
  const projectExe = scriptsExe(join(root, ".venv", IS_WIN ? "Scripts" : "bin"), "robotcode");
  if (existsSync(projectExe)) add(projectExe);
  for (const py of installerInterpreters()) {
    if (basename(py) === py) continue; // bare command name: covered by PATH below
    const exe = scriptsExe(dirname(py), "robotcode");
    if (existsSync(exe)) add(exe);
  }
  add("robotcode");
  return out;
}

// First robotcode candidate that answers `--version`, as {exe, version}
// ("2.8.0"), or null. Paths that exist are trusted without a probe unless the
// version is wanted; the bare PATH name is always probed.
export function findRobotcode(cwd, { withVersion = false } = {}) {
  for (const exe of robotcodeCandidates(cwd)) {
    if (!withVersion && exe !== "robotcode") return { exe, version: null };
    const r = spawnSync(exe, ["--version"], {
      ...spawnOptions(PROBE_TIMEOUT_MS),
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "ignore"],
    });
    if (r.error || r.status !== 0) continue;
    const m = /(\d+\.\d+(?:\.\d+)?)/.exec(r.stdout ?? "");
    return { exe, version: m ? m[1] : null };
  }
  return null;
}

// True when `version` ("2.8.0") is at least `min` ("2.8").
export function versionAtLeast(version, min) {
  const a = String(version ?? "").split(".").map(Number);
  const b = String(min).split(".").map(Number);
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const x = a[i] || 0;
    const y = b[i] || 0;
    if (x !== y) return x > y;
  }
  return true;
}

// The event's working directory (falls back to the process cwd).
export function projectRoot(event) {
  const cwd = event && typeof event.cwd === "string" ? event.cwd : "";
  if (cwd && existsSync(cwd)) return cwd;
  return process.cwd();
}

// First candidate for which `import <module>` succeeds, or null.
export function findInterpreterWith(moduleName, cwd) {
  for (const py of pythonCandidates(cwd)) {
    const probe = spawnSync(py, ["-c", `import ${moduleName}`], {
      ...spawnOptions(PROBE_TIMEOUT_MS),
      stdio: ["ignore", "ignore", "ignore"],
    });
    if (probe.error) continue; // missing interpreter, timeout, …
    if (probe.status === 0) return py;
  }
  return null;
}

// First candidate that exists at all (`--version` answers), or null.
export function firstPython(cwd) {
  for (const py of pythonCandidates(cwd)) {
    const r = spawnSync(py, ["--version"], {
      ...spawnOptions(PROBE_TIMEOUT_MS),
      stdio: "ignore",
    });
    if (!r.error) return py;
  }
  return null;
}

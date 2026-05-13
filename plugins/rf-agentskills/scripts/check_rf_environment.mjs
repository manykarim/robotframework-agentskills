#!/usr/bin/env node
// check_rf_environment.mjs — Check Robot Framework environment at session start.
//
// Called by the SessionStart hook to verify that the RF toolchain is
// available. Outputs a diagnostic summary to stderr so Claude sees the
// environment state. Always exits 0 (informational only — never blocks
// session start).
//
// Cross-platform port of check_rf_environment.sh.
//
// Python interpreter resolution: prefers the install-time interpreter
// recorded in `python_runtime.json` (next to this script, written by the
// rf-agentskills installer from `sys.executable`). This is essential for
// pipx / uv tool install / venv setups where the interpreter that has
// `robotframework` installed is NOT the `python` on PATH. Falls back to
// `python3` then `python` if the recorded interpreter is unavailable.
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadPythonInterpreters() {
  const candidates = [];
  try {
    const cfg = JSON.parse(
      readFileSync(join(HERE, "python_runtime.json"), "utf-8"),
    );
    if (typeof cfg.interpreter === "string" && cfg.interpreter) {
      candidates.push(cfg.interpreter);
    }
    for (const fb of cfg.fallbacks ?? []) {
      if (typeof fb === "string" && fb && !candidates.includes(fb)) {
        candidates.push(fb);
      }
    }
  } catch {
    // Config missing — use PATH fallbacks only.
  }
  for (const fb of ["python3", "python"]) {
    if (!candidates.includes(fb)) candidates.push(fb);
  }
  return candidates;
}

const found = [];
const missing = [];

function commandExists(cmd) {
  // `where` on Windows, `command -v` on POSIX. `spawnSync` with shell:true
  // is portable enough for a pure existence probe.
  const probe = process.platform === "win32"
    ? spawnSync("where", [cmd], { stdio: "ignore" })
    : spawnSync("sh", ["-c", `command -v ${cmd}`], { stdio: "ignore" });
  return probe.status === 0;
}

// Resolve which Python invocation to use. Try (in order): the
// install-time interpreter from python_runtime.json, then `python3`,
// then `python` on PATH. The recorded interpreter wins when present
// because it's the one with `robotframework` installed (pipx / uv tool
// install / venv all keep `robot` in their own Python, not on PATH).
function pickPython() {
  for (const py of loadPythonInterpreters()) {
    // For absolute paths, a probe with `--version` is the cheapest
    // existence check that works on Windows too (no `where` needed).
    const r = spawnSync(py, ["--version"], { stdio: "ignore" });
    if (!r.error || r.error.code !== "ENOENT") return py;
  }
  return null;
}

function pythonImportExists(py, importName) {
  if (!py) return false;
  const r = spawnSync(py, ["-c", `import ${importName}`], { stdio: "ignore" });
  return r.status === 0;
}

function check(category, ok, label) {
  (ok ? found : missing).push(label);
  return ok;
}

process.stderr.write("=== Robot Framework Environment Check ===\n");

const py = pickPython();

process.stderr.write("\nCore:\n");
check("core", py !== null, "python3");
const rfOk = pythonImportExists(py, "robot");
check("core", rfOk, "robotframework");
let rfVersion = "not installed";
if (rfOk) {
  const r = spawnSync(py, ["-c", "import robot; print(robot.version.VERSION)"], {
    encoding: "utf-8",
  });
  if (r.status === 0) rfVersion = (r.stdout ?? "").trim() || rfVersion;
}
process.stderr.write(`  Robot Framework version: ${rfVersion}\n`);

process.stderr.write("\nWeb Testing:\n");
check("web", pythonImportExists(py, "Browser"),
  "robotframework-browser (Browser Library)");
check("web", pythonImportExists(py, "SeleniumLibrary"),
  "robotframework-seleniumlibrary");
if (pythonImportExists(py, "Browser") && commandExists("npx")) {
  process.stderr.write(
    "  Browser Library: installed (run 'rfbrowser init' if not initialized)\n",
  );
}

process.stderr.write("\nAPI Testing:\n");
check("api", pythonImportExists(py, "RequestsLibrary"),
  "robotframework-requests");
check("api", pythonImportExists(py, "REST"), "RESTinstance");

process.stderr.write("\nMobile Testing:\n");
check("mobile", pythonImportExists(py, "AppiumLibrary"),
  "robotframework-appiumlibrary");
check("mobile", commandExists("appium"), "appium");

process.stderr.write("\n--- Summary ---\n");
if (found.length) {
  process.stderr.write(`Available: ${found.join(", ")}\n`);
}
if (missing.length) {
  process.stderr.write(`Not installed: ${missing.join(", ")}\n`);
  process.stderr.write("\nInstall missing packages as needed:\n");
  process.stderr.write("  pip install robotframework                    # Core (required)\n");
  process.stderr.write("  pip install robotframework-browser && rfbrowser init  # Web (Playwright)\n");
  process.stderr.write("  pip install robotframework-seleniumlibrary    # Web (Selenium)\n");
  process.stderr.write("  pip install robotframework-requests           # API\n");
  process.stderr.write("  pip install RESTinstance                      # API (alternative)\n");
  process.stderr.write("  pip install robotframework-appiumlibrary      # Mobile\n");
} else {
  process.stderr.write("All checked packages are installed.\n");
}
process.stderr.write("=== End Environment Check ===\n");

process.exit(0);

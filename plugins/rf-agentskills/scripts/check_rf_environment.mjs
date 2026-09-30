#!/usr/bin/env node
// check_rf_environment.mjs — Check the Robot Framework environment at session start.
//
// Called by the SessionStart hook. Writes a diagnostic summary to stderr so the
// agent sees the environment state. Always exits 0 (informational only — never
// blocks session start).
//
// Interpreter resolution is shared with the validation hooks (_python_env.mjs):
// VIRTUAL_ENV -> <cwd>/.venv -> python_runtime.json -> python3/python. The
// SessionStart event's `cwd` selects the project (process cwd when it has none);
// a missing, empty or malformed event produces no output. Install advice follows the rf-setup skill (project environment,
// `uv add …`); it never recommends `pip install` or `rfbrowser init`.
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import {
  PROBE_TIMEOUT_MS,
  findInterpreterWith,
  firstPython,
  projectRoot,
  spawnOptions,
} from "./_python_env.mjs";

// Missing, empty or malformed event -> no output (the hook never blocks).
let event = null;
try {
  event = JSON.parse(readFileSync(0, "utf-8"));
} catch {
  process.exit(0);
}
if (!event || typeof event !== "object" || Array.isArray(event)) process.exit(0);
const cwd = projectRoot(event);

const found = [];
const missing = [];

function commandExists(cmd) {
  const probe = process.platform === "win32"
    ? spawnSync("where", [cmd], { ...spawnOptions(PROBE_TIMEOUT_MS), stdio: "ignore" })
    : spawnSync("sh", ["-c", `command -v ${cmd}`], { ...spawnOptions(PROBE_TIMEOUT_MS), stdio: "ignore" });
  return probe.status === 0;
}

function pythonImportExists(py, importName) {
  if (!py) return false;
  const r = spawnSync(py, ["-c", `import ${importName}`], {
    ...spawnOptions(PROBE_TIMEOUT_MS),
    stdio: "ignore",
  });
  return r.status === 0;
}

function check(ok, label) {
  (ok ? found : missing).push(label);
  return ok;
}

process.stderr.write("=== Robot Framework Environment Check ===\n");

// Prefer the interpreter that has Robot Framework; else the first one that runs.
const py = findInterpreterWith("robot", cwd) ?? firstPython(cwd);

process.stderr.write("\nCore:\n");
check(py !== null, "python3");
const rfOk = pythonImportExists(py, "robot");
check(rfOk, "robotframework");
let rfVersion = "not installed";
if (rfOk) {
  const r = spawnSync(py, ["-c", "import robot; print(robot.version.VERSION)"], {
    ...spawnOptions(PROBE_TIMEOUT_MS),
    encoding: "utf-8",
  });
  if (r.status === 0) rfVersion = (r.stdout ?? "").trim() || rfVersion;
}
process.stderr.write(`  Robot Framework version: ${rfVersion}\n`);
if (py) process.stderr.write(`  Interpreter: ${py}\n`);

process.stderr.write("\nLinting:\n");
const robocopOk = check(pythonImportExists(py, "robocop") ||
  findInterpreterWith("robocop", cwd) !== null, "robotframework-robocop");
process.stderr.write(
  robocopOk
    ? "  Robocop: available (invalid and deprecated syntax is checked on every .robot/.resource edit)\n"
    : "  Robocop: not installed — syntax and deprecation checks on edit are disabled " +
        "(uv add --dev robotframework-robocop; see the rf-setup skill)\n",
);

process.stderr.write("\nWeb Testing:\n");
check(pythonImportExists(py, "Browser"), "robotframework-browser (Browser Library)");
check(pythonImportExists(py, "SeleniumLibrary"), "robotframework-seleniumlibrary");

process.stderr.write("\nAPI Testing:\n");
check(pythonImportExists(py, "RequestsLibrary"), "robotframework-requests");
check(pythonImportExists(py, "REST"), "RESTinstance");

process.stderr.write("\nMobile Testing:\n");
check(pythonImportExists(py, "AppiumLibrary"), "robotframework-appiumlibrary");
check(commandExists("appium"), "appium");

process.stderr.write("\n--- Summary ---\n");
if (found.length) {
  process.stderr.write(`Available: ${found.join(", ")}\n`);
}
if (missing.length) {
  process.stderr.write(`Not installed: ${missing.join(", ")}\n`);
  process.stderr.write(
    "\nInstall only what the project needs, into the project environment. " +
      "See the rf-setup skill for the full steps (uv, venv, poetry; Browser needs Node.js):\n",
  );
  process.stderr.write("  uv add robotframework                        # core\n");
  process.stderr.write("  uv add --dev robotframework-robocop          # lint + checks on edit\n");
  process.stderr.write("  uv add robotframework-requests               # API (default)\n");
  process.stderr.write("  uv add \"robotframework-browser[bb]\"          # web (default; see rf-setup)\n");
} else {
  process.stderr.write("All checked packages are installed.\n");
}
process.stderr.write("=== End Environment Check ===\n");

process.exit(0);

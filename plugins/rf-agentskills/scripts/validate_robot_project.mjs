#!/usr/bin/env node
// validate_robot_project.mjs — Opt-in, end-of-task project-wide validation
// for Robot Framework suites. Runs from the Stop hook.
//
// This tier performs CROSS-FILE / semantic checks that only make sense
// once the whole project is on disk — running them per-save would
// false-alarm constantly (a keyword you just wrote looks "unused" until
// something calls it; a call into a not-yet-written resource looks
// "undefined"). Two checks:
//
//   1. `robot --dryrun` over the project — resolves imports and keyword
//      references without executing keyword bodies. Catches undefined
//      keywords, argument errors, and broken imports. IMPORTANT: dryrun's
//      exit code does NOT reflect import errors when the broken import is
//      never used by an executed keyword — those surface only as
//      `[ ERROR ]` console lines. So we inspect BOTH the exit code and
//      the output for `[ ERROR ]`.
//
//   2. `robotframework-find-unused` — dead-code analysis (unused
//      keywords) across the project.
//
// OPT-IN: the entire tier is gated behind the RF_AGENTSKILLS_PROJECT_VALIDATION
// env var (truthy = 1/true/yes). It is OFF by default because `--dryrun`
// imports libraries (runs their import-time code — could open a browser,
// connect to a DB) and both checks scale with project size. When enabled
// and findings exist, the hook exits 2 with the diagnostic on stderr so
// the agent gets one more turn to fix before the turn ends.
//
// Graceful degradation: silent no-op (exit 0) when the flag is unset, no
// interpreter is available, or the required tool isn't installed.
import { readFileSync, mkdtempSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { tmpdir } from "node:os";

const HERE = dirname(fileURLToPath(import.meta.url));

// ── Gate: opt-in only ───────────────────────────────────────────────────────
function isTruthy(v) {
  return /^(1|true|yes|on)$/i.test((v ?? "").toString().trim());
}
if (!isTruthy(process.env.RF_AGENTSKILLS_PROJECT_VALIDATION)) process.exit(0);

// Read the Stop event once (stdin can only be consumed once). Break the
// Stop-hook loop: when firing as a continuation of a previous Stop block
// (`stop_hook_active`), exit 2 here would re-block on the same persistent
// finding forever — so no-op in that state.
let stopEvent = null;
try {
  stopEvent = JSON.parse(readFileSync(0, "utf-8"));
} catch {
  // No / unparsable stdin — proceed with process cwd.
}
if (stopEvent?.stop_hook_active) process.exit(0);

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
    // Config missing — PATH fallbacks only.
  }
  for (const fb of ["python3", "python"]) {
    if (!candidates.includes(fb)) candidates.push(fb);
  }
  return candidates;
}

// Resolve the project root from the (already-parsed) Stop event JSON (cwd),
// falling back to the process cwd.
function resolveProjectRoot() {
  if (stopEvent?.cwd) return stopEvent.cwd.toString();
  return process.cwd();
}

// Find the first interpreter for which `import <module>` succeeds.
function findInterpreterWith(moduleName) {
  for (const py of loadPythonInterpreters()) {
    const probe = spawnSync(py, ["-c", `import ${moduleName}`], {
      stdio: ["ignore", "ignore", "ignore"],
    });
    if (probe.error && probe.error.code === "ENOENT") continue;
    if (probe.status === 0) return py;
  }
  return null;
}

const projectRoot = resolveProjectRoot();
const findings = [];

// ── Check 1: robot --dryrun ─────────────────────────────────────────────────
const robotPy = findInterpreterWith("robot");
if (robotPy) {
  let outDir;
  try {
    outDir = mkdtempSync(join(tmpdir(), "rf-dryrun-"));
  } catch {
    outDir = tmpdir();
  }
  const dry = spawnSync(
    robotPy,
    [
      "-m",
      "robot",
      "--dryrun",
      "--output",
      "NONE",
      "--report",
      "NONE",
      "--log",
      "NONE",
      "-d",
      outDir,
      projectRoot,
    ],
    { encoding: "utf-8" },
  );
  const combined = `${dry.stdout ?? ""}\n${dry.stderr ?? ""}`;
  // Import/parse problems surface as [ ERROR ] lines regardless of exit code.
  const errorLines = combined
    .split(/\r?\n/)
    .filter((l) => l.includes("[ ERROR ]"))
    // Ignore the "no tests" case — an empty/utility project isn't a failure.
    .filter((l) => !/contains no tests/i.test(l));
  if (errorLines.length) {
    findings.push("Dry-run import/parse errors:\n  " + errorLines.join("\n  "));
  }
  // A non-zero exit with no [ ERROR ] line means keyword-resolution failures
  // (undefined keyword, argument errors). Surface the FAIL summary lines.
  if (dry.status !== 0 && !errorLines.length) {
    const failLines = combined
      .split(/\r?\n/)
      .filter((l) => /no keyword with name|FAIL|multiple errors/i.test(l))
      .slice(0, 20);
    if (failLines.length) {
      findings.push(
        "Dry-run keyword/argument errors:\n  " + failLines.join("\n  "),
      );
    }
  }
}

// ── Check 2: find-unused (unused keywords) ──────────────────────────────────
const unusedPy = findInterpreterWith("robotframework_find_unused");
if (unusedPy) {
  const unused = spawnSync(
    unusedPy,
    ["-m", "robotframework_find_unused", "keywords", projectRoot],
    { encoding: "utf-8" },
  );
  const out = `${unused.stdout ?? ""}\n${unused.stderr ?? ""}`;
  // The tool prints "Found N unused keywords:" followed by one per line.
  if (/found\s+\d+\s+unused keyword/i.test(out)) {
    const idx = out.toLowerCase().indexOf("found");
    findings.push("Unused keywords:\n  " + out.slice(idx).trim());
  }
}

// ── Report ──────────────────────────────────────────────────────────────────
if (findings.length) {
  process.stderr.write(
    "Robot Framework project validation found issues:\n\n" +
      findings.join("\n\n") +
      "\n",
  );
  process.exit(2);
}

process.exit(0);

#!/usr/bin/env node
// maybe_inject_rf_context.mjs — Conditional UserPromptSubmit hook.
//
// Reads the Claude Code UserPromptSubmit event JSON on stdin, inspects
// the user's prompt for Robot Framework signals, and only emits an
// additionalContext injection when at least one signal is present.
// The injection is a short routing text (<= 450 characters): which skill
// to load for which kind of work, keyword lookup via rf-libdoc /
// `robotcode libdoc`, and a one-line RF 7 syntax reminder.
//
// Schema:
//   stdin  — Claude Code UserPromptSubmit event JSON.
//   stdout — Either empty (no injection) or one JSON object of the form
//            {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
//             "additionalContext": "..."}}.
//   exit   — Always 0. The hook is non-blocking by design.
import { readFileSync } from "node:fs";

let raw = "";
try { raw = readFileSync(0, "utf-8"); } catch { process.exit(0); }
if (!raw) process.exit(0);

let event;
try { event = JSON.parse(raw); } catch { process.exit(0); }
const prompt = (event?.prompt ?? "").toString();
if (!prompt) process.exit(0);

// Robot Framework signal regex (case-insensitive). Conservative on
// purpose — better to under-inject than over-inject. Categories covered:
//   - Direct RF mentions: "robot framework", "robot-framework"
//   - File extensions: .robot, .resource
//   - Library names: SeleniumLibrary, Browser Library, AppiumLibrary,
//     RequestsLibrary, RESTinstance, PlatynUI
//   - rf-agentskills skill ids (one identifier in every channel): rf-libdoc,
//     rf-results, rf-robotcode, rf-setup, rf-language, rf-python-library, rf-browser, rf-selenium, rf-appium,
//     rf-requests, rf-restinstance, rf-platynui (the pre-2.0 short plugin id
//     "libdoc" is still caught by the generic \blibdoc\b tooling term)
//   - rf-agentskills subagent ids: rf-test-architect, rf-debug-expert,
//     rf-keyword-consultant, rf-migration-guide
//   - Tooling: libdoc, robotidy, robocop, rfbrowser, robotcode,
//     robot-debug, robot.toml
//   - Python library API: @keyword, robot.api.deco, ROBOT_LIBRARY_SCOPE (and
//     other ROBOT_LIBRARY_* / ROBOT_LISTENER_* settings), "contains no keywords",
//     "robot listener" / "listener API" (bare "listener" is too generic)
//   - RF section headers pasted into the prompt: *** Settings ***, *** Variables ***,
//     *** Test Cases ***, *** Tasks ***, *** Keywords ***, *** Comments ***
//     (singular legacy spellings included)
// Things NOT matched: bare "test" (too noisy), bare "RF" (ambiguous).
const RF_REGEX = /robot[ -]?framework|\.robot\b|\.resource\b|\b(selenium|browser|appium|requests)library\b|\brestinstance\b|\b(selenium|browser|appium|requests) library\b|\bplatynui\b|\blibdoc\b|\b(robotidy|robocop|rfbrowser|robotcode)\b|\brobot-debug\b|\brobot\.toml\b|@keyword\b|\brobot\.api\.deco\b|\bROBOT_(LIBRARY|LISTENER)_[A-Z_]+|contains no keywords|\brobot( framework)? listeners?\b|\blistener api\b|\brf-(libdoc|results|robotcode|setup|language|python-library|browser|selenium|appium|requests|restinstance|platynui)\b|\brf-(test-architect|debug-expert|keyword-consultant|migration-guide)\b|\*\*\*\s*(settings?|variables?|test cases?|tasks?|keywords?|comments?)\s*\*\*\*/i;

if (!RF_REGEX.test(prompt)) process.exit(0);

// Routing text (<= 450 characters, ~80 tokens). Skill descriptions are already in
// the agent's context and subagents are listed by the Task tool; what the model
// lacks is which skill to load when. Names only shipped skills (tests check it).
const CONTEXT = [
  "Robot Framework context detected. Load the matching rf-agentskills skill before writing RF: ",
  "tests, suites, keywords, resources, variables -> rf-language; ",
  "Python libraries/listeners -> rf-python-library; ",
  "library usage -> rf-<library> (defaults: rf-browser web, rf-requests API); installs -> rf-setup. ",
  "Check keyword names/arguments with rf-libdoc or `robotcode libdoc` (rf-robotcode), not memory. ",
  "Write RF 7 syntax: RETURN, VAR, IF, Test Tags.",
].join("");

const payload = {
  hookSpecificOutput: {
    hookEventName: "UserPromptSubmit",
    additionalContext: CONTEXT,
  },
};

process.stdout.write(JSON.stringify(payload) + "\n");
process.exit(0);

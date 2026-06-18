#!/usr/bin/env node
// maybe_inject_rf_context.mjs — Conditional UserPromptSubmit hook.
//
// Reads the Claude Code UserPromptSubmit event JSON on stdin, inspects
// the user's prompt for Robot Framework signals, and only emits an
// additionalContext injection when at least one signal is present.
//
// Cross-platform port of maybe_inject_rf_context.sh. The regex below is
// the exact same expression the bash version compiled with `grep -iE`;
// JS regex syntax accepts it unchanged (alternation, `\b` word
// boundaries, character classes).
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
//   - rf-agentskills skill ids: libdoc-search, libdoc-explain,
//     keyword-builder, testcase-builder, resource-architect, rf-results
//   - rf-agentskills subagent ids: rf-test-architect, rf-debug-expert,
//     rf-keyword-consultant, rf-migration-guide
//   - Tooling: libdoc, robotidy, robocop, rfbrowser
// Things NOT matched: bare "test" (too noisy), bare "RF" (ambiguous).
const RF_REGEX = /robot[ -]?framework|\.robot\b|\.resource\b|\b(selenium|browser|appium|requests)library\b|\brestinstance\b|\b(selenium|browser|appium|requests) library\b|\bplatynui\b|\blibdoc\b|\b(robotidy|robocop|rfbrowser)\b|\b(keyword|testcase|resource)[ -]builder\b|\b(libdoc-search|libdoc-explain|keyword-builder|testcase-builder|resource-architect|rf-results)\b|\brf-(test-architect|debug-expert|keyword-consultant|migration-guide)\b/i;

if (!RF_REGEX.test(prompt)) process.exit(0);

const payload = {
  hookSpecificOutput: {
    hookEventName: "UserPromptSubmit",
    additionalContext: [
      "Robot Framework context detected. Available rf-agentskills ",
      "(load the relevant SKILL.md when needed):",
      "\n  - Library references: browser, selenium, appium, requests, restinstance",
      "\n  - Script-based tools: keyword-builder, testcase-builder, resource-architect, ",
      "libdoc-search, libdoc-explain, results",
      "\n  - Subagents: rf-test-architect, rf-debug-expert, rf-keyword-consultant, rf-migration-guide",
      "\nPrefer libdoc-search / libdoc-explain over guessing keyword signatures from memory.",
    ].join(""),
  },
};

process.stdout.write(JSON.stringify(payload) + "\n");
process.exit(0);

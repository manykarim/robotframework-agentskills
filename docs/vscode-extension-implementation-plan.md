# VS Code Extension Implementation Plan: Robot Framework Skills

## Executive Summary

This plan describes building a **complementary** VS Code extension that packages the 11 Robot Framework agent skills as VS Code features — snippets, commands, tree views, webviews, and code actions. The extension is designed to work **alongside RobotCode** (the dominant RF extension with 309K+ installs) rather than compete with it, filling gaps in curated snippets, scaffolding, offline keyword reference, migration guidance, and test result analysis.

**Extension name**: `robotframework-skills`
**Display name**: `Robot Framework Skills`
**Publisher**: `manykarim`
**Distribution**: VS Code Marketplace + Open VSX Registry

---

## 1. Competitive Landscape & Positioning

### Existing RF Extensions

| Extension | Installs | Strengths | Gaps |
|-----------|----------|-----------|------|
| **RobotCode** (d-biehl.robotcode) | 309K | LSP, completions, diagnostics, debugging, test runner, formatting | No curated snippets, no scaffolding, no offline keyword reference, no migration tools |
| **robotframework-lsp** (Robocorp) | Legacy | LSP, IntelliJ support | Less active, community shifted to RobotCode |
| **RF Intellisense** | Legacy | Early keyword completion | Unmaintained |

### Our Unique Value (Gap-Filling)

1. **Pre-built snippet libraries**: 40+ snippets for Browser, Selenium, Appium, Requests, RESTinstance — available without installing Python libraries
2. **Interactive code generators**: Commands invoking our Python scripts to generate keywords, test cases, and resource structures
3. **Offline keyword database**: Static keyword index embedded in the extension, enabling search without a Python environment
4. **Domain-specific reference panels**: TreeView/Webview showing library-specific locator syntax, assertion patterns, troubleshooting
5. **Migration guidance**: Code actions to modernize RF5/6 syntax to RF7+ and migrate between libraries
6. **Test result analysis**: Webview dashboard for output.xml analysis with failure diagnosis

### Positioning Statement

> "Works alongside RobotCode to provide curated snippets, keyword references, code generators, and migration tools for Robot Framework testing libraries."

---

## 2. Technical Architecture

### 2.1 Project Structure

```
vscode-rf-skills/
├── .vscode/
│   ├── launch.json              # Extension Host debug config
│   ├── tasks.json               # Build tasks
│   └── settings.json            # Editor settings
├── src/
│   ├── extension.ts             # Entry point (activate/deactivate)
│   ├── commands/
│   │   ├── searchKeyword.ts     # Keyword search command
│   │   ├── generateKeyword.ts   # Keyword builder command
│   │   ├── generateTestCase.ts  # Test case builder command
│   │   ├── scaffoldProject.ts   # Resource architect command
│   │   └── analyzeResults.ts    # Results analysis command
│   ├── providers/
│   │   ├── codeActions.ts       # Migration code actions
│   │   ├── codeLens.ts          # Run/Debug code lenses
│   │   ├── hover.ts             # Keyword hover documentation
│   │   └── completion.ts        # Snippet-based completions
│   ├── views/
│   │   ├── keywordBrowser.ts    # Keyword reference tree view
│   │   ├── testExplorer.ts      # Test results tree view
│   │   └── projectStructure.ts  # RF project tree view
│   ├── webviews/
│   │   ├── resultsDashboard.ts  # Test results webview
│   │   ├── keywordViewer.ts     # Keyword documentation webview
│   │   └── migrationReport.ts   # Migration analysis webview
│   ├── python/
│   │   ├── invoker.ts           # Python script invocation bridge
│   │   └── detector.ts          # Python/RF environment detection
│   ├── data/
│   │   ├── keywordIndex.ts      # Static keyword database
│   │   └── snippetData.ts       # Snippet definitions as data
│   └── test/
│       ├── extension.test.ts    # Integration tests
│       ├── invoker.test.ts      # Python bridge unit tests
│       └── providers.test.ts    # Provider unit tests
├── snippets/
│   ├── browser.json             # Browser Library snippets
│   ├── selenium.json            # SeleniumLibrary snippets
│   ├── appium.json              # AppiumLibrary snippets
│   ├── requests.json            # RequestsLibrary snippets
│   ├── restinstance.json        # RESTinstance snippets
│   ├── builtin.json             # BuiltIn library snippets
│   └── structure.json           # RF structural snippets
├── data/
│   └── keyword-index.json       # Pre-built keyword database from libdoc
├── media/
│   ├── icon.png                 # Extension icon (128x128)
│   ├── icon.svg                 # SVG for activity bar
│   └── webview/
│       ├── results.css          # Webview styles
│       └── results.js           # Webview client script
├── scripts/                     # Python scripts (copied from plugin)
│   ├── keyword_builder.py
│   ├── testcase_builder.py
│   ├── resource_architect.py
│   ├── rf_libdoc.py
│   └── rf_results.py
├── package.json                 # Extension manifest
├── tsconfig.json                # TypeScript config
├── esbuild.js                   # Build script
├── .vscodeignore                # VSIX exclude patterns
├── .vscode-test.mjs             # Test runner config
├── eslint.config.mjs            # Linting
├── CHANGELOG.md                 # Marketplace changelog
└── README.md                    # Marketplace page content
```

### 2.2 Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | TypeScript | VS Code standard, type safety |
| Bundler | esbuild | 14ms builds vs 50s webpack, recommended by VS Code team |
| Test runner | @vscode/test-electron + mocha | Official VS Code test framework |
| Python invocation | `child_process.execFile` via `uv run` | Validated in experiments, JSON protocol |
| Webview framework | Vanilla HTML/CSS/JS | Simplicity, no build pipeline for webviews |
| Minimum VS Code | ^1.90.0 | Broad compatibility while using modern APIs |
| Node.js target | ES2022 / CommonJS | VS Code extension host requirements |

### 2.3 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     VS Code Extension Host                   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Commands     │  │  Providers   │  │  Views            │  │
│  │  (palette)    │  │  (inline)    │  │  (sidebar/panel)  │  │
│  │              │  │              │  │                   │  │
│  │  searchKW    │  │  codeAction  │  │  keywordBrowser   │  │
│  │  generateKW  │  │  codeLens    │  │  testExplorer     │  │
│  │  generateTC  │  │  hover       │  │  projectStructure │  │
│  │  scaffold    │  │  completion  │  │                   │  │
│  │  analyze     │  │              │  │                   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                 │                    │              │
│         ▼                 ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Python Script Invoker                       │ │
│  │  uv run python3 <script> --args   (child_process)       │ │
│  │  JSON stdin → JSON stdout protocol                       │ │
│  └──────────┬──────────────────────────────┬───────────────┘ │
│             │                              │                  │
│  ┌──────────▼──────────┐  ┌───────────────▼───────────────┐ │
│  │ Static Keyword Index │  │ Webview Panels                │ │
│  │ (embedded JSON)      │  │ (results, docs, migration)    │ │
│  │ No Python required   │  │ HTML/CSS/JS + message passing │ │
│  └─────────────────────┘  └───────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Snippet Contributions (declarative, no code)            │ │
│  │  7 JSON files × 40+ snippets total                       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  RobotCode LSP   │  (separate extension)
                    │  Diagnostics     │  Coexists, no conflict
                    │  Completions     │
                    │  Debugging       │
                    └─────────────────┘
```

### 2.4 Python Script Invocation Bridge

The validated pattern from experiments:

```typescript
// src/python/invoker.ts
import { execFile, spawn } from 'child_process';
import * as vscode from 'vscode';

export async function invokePythonScript(
    context: vscode.ExtensionContext,
    scriptName: string,
    args: string[],
    stdinData?: string
): Promise<{ data?: unknown; error?: string }> {
    const scriptPath = context.asAbsolutePath(`scripts/${scriptName}`);
    const pythonPath = vscode.workspace
        .getConfiguration('rfSkills')
        .get<string>('pythonPath', 'python3');

    return new Promise((resolve) => {
        const proc = stdinData
            ? spawn(pythonPath, [scriptPath, ...args], {
                  timeout: 30000,
              })
            : null;

        if (!stdinData) {
            execFile(
                pythonPath,
                [scriptPath, ...args],
                { maxBuffer: 10 * 1024 * 1024, timeout: 30000 },
                (error, stdout, stderr) => {
                    if (error) {
                        try {
                            resolve({ error: JSON.parse(stderr).error });
                        } catch {
                            resolve({ error: stderr || error.message });
                        }
                        return;
                    }
                    try {
                        resolve({ data: JSON.parse(stdout) });
                    } catch {
                        resolve({ error: `Invalid JSON: ${stdout}` });
                    }
                }
            );
            return;
        }

        // stdin-based invocation for scripts that read from stdin
        let stdout = '';
        let stderr = '';
        proc!.stdout!.on('data', (d) => (stdout += d));
        proc!.stderr!.on('data', (d) => (stderr += d));
        proc!.on('close', (code) => {
            if (code !== 0) {
                try {
                    resolve({ error: JSON.parse(stderr).error });
                } catch {
                    resolve({ error: stderr });
                }
                return;
            }
            try {
                resolve({ data: JSON.parse(stdout) });
            } catch {
                resolve({ error: `Invalid JSON: ${stdout}` });
            }
        });
        proc!.stdin!.write(stdinData);
        proc!.stdin!.end();
    });
}
```

**Environment detection** (validated):
- `uv run python3` — preferred, handles virtualenvs
- Fallback: `python3` directly
- Detect robotframework: `python3 -c "import robot; print(robot.version.VERSION)"`
- Graceful degradation: scripts with ImportError handling already return JSON errors

### 2.5 Activation Strategy

```json
{
  "activationEvents": [
    "workspaceContains:**/*.robot",
    "workspaceContains:**/*.resource"
  ]
}
```

Commands and language contributions auto-activate since VS Code 1.74.0.

---

## 3. Feature Implementation Plan

### Phase 1: Snippets + Basic Commands (MVP)

**Goal**: Deliver immediate value with zero Python dependency. Ship to Marketplace.

#### 3.1 Snippet Contributions (Declarative)

Convert SKILL.md patterns into VS Code snippet JSON files:

| File | Source Skill | Snippet Count | Examples |
|------|-------------|---------------|----------|
| `browser.json` | browser | ~10 | `rf-browser-setup`, `rf-browser-click`, `rf-browser-fill`, `rf-browser-login`, `rf-browser-upload` |
| `selenium.json` | selenium | ~9 | `rf-selenium-setup`, `rf-selenium-open`, `rf-selenium-click`, `rf-selenium-wait`, `rf-selenium-login` |
| `appium.json` | appium | ~6 | `rf-appium-android`, `rf-appium-ios`, `rf-appium-swipe`, `rf-appium-context` |
| `requests.json` | requests | ~6 | `rf-requests-get`, `rf-requests-post-json`, `rf-requests-crud`, `rf-requests-bearer` |
| `restinstance.json` | restinstance | ~5 | `rf-rest-get-assert`, `rf-rest-crud`, `rf-rest-schema` |
| `builtin.json` | (general) | ~5 | `rf-for-loop`, `rf-if-else`, `rf-try-except`, `rf-var-scope` |
| `structure.json` | builders | ~5 | `rf-test-keyword-driven`, `rf-test-template`, `rf-keyword-simple`, `rf-suite-structure`, `rf-settings` |

**Total**: ~46 snippets

Snippet format example:
```json
{
  "Browser Library Setup": {
    "prefix": "rf-browser-setup",
    "scope": "robotframework",
    "body": [
      "*** Settings ***",
      "Library    Browser    auto_closing_level=KEEP",
      "",
      "*** Test Cases ***",
      "${1:Test Name}",
      "    New Browser    chromium    headless=${2|true,false|}",
      "    New Context",
      "    New Page    ${3:https://example.com}",
      "    $0"
    ],
    "description": "Browser Library test setup with Browser, Context, and Page"
  }
}
```

#### 3.2 Basic Commands (TypeScript)

| Command | UI | Python Required | Description |
|---------|-----|-----------------|-------------|
| `rfSkills.searchKeyword` | QuickPick input → results list | Yes (rf_libdoc.py) | Search keywords across libraries |
| `rfSkills.generateKeyword` | QuickPick form | Yes (keyword_builder.py) | Generate user keyword from input |
| `rfSkills.generateTestCase` | QuickPick form | Yes (testcase_builder.py) | Generate test case from input |
| `rfSkills.scaffoldProject` | Multi-step QuickPick | Yes (resource_architect.py) | Scaffold RF project structure |
| `rfSkills.analyzeResults` | File picker → webview | Yes (rf_results.py) | Analyze output.xml in dashboard |
| `rfSkills.checkEnvironment` | Notification | Yes | Show RF version, installed libraries |

#### 3.3 Settings

```json
{
  "rfSkills.pythonPath": {
    "type": "string",
    "default": "python3",
    "description": "Path to Python interpreter"
  },
  "rfSkills.snippets.browser": {
    "type": "boolean",
    "default": true,
    "description": "Enable Browser Library snippets"
  },
  "rfSkills.snippets.selenium": {
    "type": "boolean",
    "default": true,
    "description": "Enable SeleniumLibrary snippets"
  },
  "rfSkills.snippets.appium": {
    "type": "boolean",
    "default": true,
    "description": "Enable AppiumLibrary snippets"
  },
  "rfSkills.snippets.requests": {
    "type": "boolean",
    "default": true,
    "description": "Enable RequestsLibrary snippets"
  },
  "rfSkills.snippets.restinstance": {
    "type": "boolean",
    "default": true,
    "description": "Enable RESTinstance snippets"
  },
  "rfSkills.results.autoOpen": {
    "type": "boolean",
    "default": true,
    "description": "Auto-open results dashboard after test run"
  },
  "rfSkills.results.outputPath": {
    "type": "string",
    "default": "results/output.xml",
    "description": "Default output.xml location"
  }
}
```

### Phase 2: Tree Views + Webviews

#### 3.4 Keyword Browser Tree View

Sidebar panel in the Activity Bar showing keyword reference:

```
RF SKILLS
├── Browser Library
│   ├── Navigation
│   │   ├── New Browser (browser, headless, ...)
│   │   ├── New Context (viewport, locale, ...)
│   │   └── New Page (url)
│   ├── Input
│   │   ├── Click (selector, button, ...)
│   │   ├── Fill Text (selector, txt, ...)
│   │   └── Type Text (selector, txt, ...)
│   └── Assertions
│       ├── Get Text (selector, ==, assertion_...)
│       └── Get Element Count (selector, ==, ...)
├── SeleniumLibrary
│   └── ...
├── RequestsLibrary
│   └── ...
└── [Search Keywords...]
```

**Data source**: Pre-built `data/keyword-index.json` (static, embedded) with fallback to live `rf_libdoc.py` queries when Python is available.

**Tree node actions**:
- Click → Show keyword documentation in hover/webview
- Double-click → Insert keyword call at cursor position
- Context menu → "Copy keyword name", "Open in libdoc"

#### 3.5 Test Results Dashboard Webview

Rich HTML panel showing output.xml analysis:

```
┌─────────────────────────────────────────────────────┐
│  RF Test Results    output.xml (2026-02-24 14:30)   │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 15 PASS  │  │  3 FAIL  │  │  1 SKIP  │          │
│  │ (79%)    │  │ (16%)    │  │ (5%)     │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                      │
│  Failed Tests:                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │ ✗ Order Tests > Cancel Order                  │   │
│  │   Error: Element not found: id=cancel-btn     │   │
│  │   Duration: 4.5s                              │   │
│  │   [Go to Source] [Show Full Log]              │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Slowest Tests:                                      │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░ Cancel Order (4.5s)             │
│  ▓▓▓▓▓▓▓▓▓▓░░░░░░ Login Flow (3.2s)               │
│  ▓▓▓▓▓░░░░░░░░░░░ Search Items (1.8s)              │
└─────────────────────────────────────────────────────┘
```

**Communication**: Extension ↔ Webview via `postMessage`/`onDidReceiveMessage`.

#### 3.6 Keyword Documentation Webview

Shown when clicking a keyword in the tree or using "Explain Keyword" command:

- Keyword name, library, version
- Full documentation (rendered from RF doc format)
- Argument table with types, defaults, required/optional
- Usage examples from SKILL.md patterns
- Related keywords

### Phase 3: Code Actions + Advanced Features

#### 3.7 Migration Code Actions (Lightbulb Menu)

| Trigger Pattern | Code Action | Category |
|-----------------|-------------|----------|
| `[Return]` setting | "Convert to RETURN (RF7+)" | Refactor |
| `Run Keyword If` | "Convert to IF/END block (RF7+)" | Refactor |
| `Run Keyword Unless` | "Convert to IF NOT/END (RF7+)" | Refactor |
| `:FOR` loop | "Convert to FOR loop (RF7+)" | Refactor |
| `Set Test Variable` | "Convert to VAR scope=TEST (RF7+)" | Refactor |
| `Set Suite Variable` | "Convert to VAR scope=SUITE (RF7+)" | Refactor |
| `Set Global Variable` | "Convert to VAR scope=GLOBAL (RF7+)" | Refactor |
| `Sleep` keyword | "Replace with proper wait keyword" | QuickFix |
| Selected test body lines | "Extract to user keyword" | Refactor |
| `Open Browser` + `Go To` | "Migrate to Browser Library" | Refactor |

#### 3.8 Code Lenses

| Location | Text | Action |
|----------|------|--------|
| Above `*** Test Cases ***` | "Run Suite (N tests)" | Execute `robot` on file |
| Above each test case | "Run \| Debug \| Last: PASS 1.2s" | Run single test |
| Above user keyword | "Used by N tests" | Find all references |
| Above Library import | "v18.9.1 — 245 keywords" | Open keyword browser filtered |

#### 3.9 File Watchers

| Pattern | Action |
|---------|--------|
| `**/*.robot`, `**/*.resource` on save | Run diagnostics if RobotCode not installed |
| `**/output.xml` created/modified | Auto-refresh test explorer, update status bar |

#### 3.10 Status Bar Items

| Position | Content | Click Action |
|----------|---------|--------------|
| Left | `RF 7.1` | Show environment details |
| Right | `Tests: 15/18 PASS` | Open results dashboard |

### Phase 4: Walkthrough + Polish

#### 3.11 Getting Started Walkthrough

Interactive onboarding for RF newcomers:

1. "Install Robot Framework" — check Python, pip install
2. "Create Your First Test" — use testcase-builder command
3. "Choose a Testing Library" — compare Browser vs Selenium vs Requests
4. "Run and Analyze Tests" — execute and view results
5. "Explore Keyword Reference" — open keyword browser tree

---

## 4. Package.json Manifest

```json
{
  "name": "robotframework-skills",
  "displayName": "Robot Framework Skills",
  "description": "Curated snippets, keyword references, code generators, and migration tools for Robot Framework testing libraries. Works alongside RobotCode.",
  "version": "0.1.0",
  "publisher": "manykarim",
  "license": "Apache-2.0",
  "icon": "media/icon.png",
  "repository": {
    "type": "git",
    "url": "https://github.com/manykarim/robotframework-agentskills"
  },
  "engines": {
    "vscode": "^1.90.0"
  },
  "categories": ["Snippets", "Testing", "Other"],
  "keywords": [
    "robotframework", "robot framework", "testing", "automation",
    "browser library", "selenium", "appium", "requests", "playwright",
    "snippets", "test automation", "api testing", "mobile testing"
  ],
  "activationEvents": [
    "workspaceContains:**/*.robot",
    "workspaceContains:**/*.resource"
  ],
  "main": "./dist/extension.js",
  "contributes": {
    "snippets": [
      { "language": "robotframework", "path": "./snippets/browser.json" },
      { "language": "robotframework", "path": "./snippets/selenium.json" },
      { "language": "robotframework", "path": "./snippets/appium.json" },
      { "language": "robotframework", "path": "./snippets/requests.json" },
      { "language": "robotframework", "path": "./snippets/restinstance.json" },
      { "language": "robotframework", "path": "./snippets/builtin.json" },
      { "language": "robotframework", "path": "./snippets/structure.json" }
    ],
    "commands": [
      { "command": "rfSkills.searchKeyword", "title": "Search Keywords", "category": "RF Skills" },
      { "command": "rfSkills.explainKeyword", "title": "Explain Keyword at Cursor", "category": "RF Skills" },
      { "command": "rfSkills.generateKeyword", "title": "Generate User Keyword", "category": "RF Skills" },
      { "command": "rfSkills.generateTestCase", "title": "Generate Test Case", "category": "RF Skills" },
      { "command": "rfSkills.scaffoldProject", "title": "Scaffold RF Project", "category": "RF Skills" },
      { "command": "rfSkills.analyzeResults", "title": "Analyze Test Results", "category": "RF Skills" },
      { "command": "rfSkills.checkEnvironment", "title": "Check RF Environment", "category": "RF Skills" },
      { "command": "rfSkills.modernizeSyntax", "title": "Modernize RF Syntax (RF7+)", "category": "RF Skills" }
    ],
    "viewsContainers": {
      "activitybar": [{
        "id": "rf-skills",
        "title": "RF Skills",
        "icon": "media/icon.svg"
      }]
    },
    "views": {
      "rf-skills": [
        { "id": "rfSkills.keywordBrowser", "name": "Keyword Reference" },
        { "id": "rfSkills.testResults", "name": "Test Results" }
      ]
    },
    "menus": {
      "editor/context": [
        {
          "when": "resourceLangId == robotframework",
          "command": "rfSkills.explainKeyword",
          "group": "navigation"
        }
      ]
    },
    "walkthroughs": [{
      "id": "rfSkills.gettingStarted",
      "title": "Get Started with Robot Framework",
      "description": "Learn to write tests with curated skill references",
      "steps": [
        {
          "id": "checkEnvironment",
          "title": "Check Your Environment",
          "description": "Verify Python and Robot Framework are installed",
          "media": { "markdown": "media/walkthrough/check-environment.md" },
          "completionEvents": ["onCommand:rfSkills.checkEnvironment"]
        },
        {
          "id": "createTest",
          "title": "Create Your First Test",
          "description": "Generate a test case using the built-in scaffolder",
          "media": { "markdown": "media/walkthrough/create-test.md" },
          "completionEvents": ["onCommand:rfSkills.generateTestCase"]
        },
        {
          "id": "exploreSnippets",
          "title": "Explore Library Snippets",
          "description": "Type 'rf-' in a .robot file to see available snippets",
          "media": { "markdown": "media/walkthrough/explore-snippets.md" }
        },
        {
          "id": "browseKeywords",
          "title": "Browse Keyword Reference",
          "description": "Open the sidebar to explore keywords by library",
          "media": { "markdown": "media/walkthrough/browse-keywords.md" },
          "completionEvents": ["onView:rfSkills.keywordBrowser"]
        }
      ]
    }],
    "configuration": {
      "title": "Robot Framework Skills",
      "properties": {
        "rfSkills.pythonPath": {
          "type": "string",
          "default": "python3",
          "description": "Path to Python interpreter for RF tools"
        },
        "rfSkills.results.outputPath": {
          "type": "string",
          "default": "results/output.xml",
          "description": "Default output.xml location"
        },
        "rfSkills.results.autoOpen": {
          "type": "boolean",
          "default": true,
          "description": "Auto-open results dashboard after test run"
        }
      }
    }
  },
  "scripts": {
    "compile": "npm run check-types && node esbuild.js",
    "check-types": "tsc --noEmit",
    "watch": "npm-run-all -p watch:*",
    "watch:esbuild": "node esbuild.js --watch",
    "watch:tsc": "tsc --noEmit --watch --project tsconfig.json",
    "vscode:prepublish": "npm run package",
    "package": "npm run check-types && node esbuild.js --production",
    "test": "vscode-test",
    "lint": "eslint src"
  },
  "devDependencies": {
    "@types/mocha": "^10.0.6",
    "@types/node": "^20.0.0",
    "@types/vscode": "^1.90.0",
    "@vscode/test-cli": "^0.0.10",
    "@vscode/test-electron": "^2.4.0",
    "@vscode/vsce": "^3.0.0",
    "esbuild": "^0.27.0",
    "eslint": "^9.0.0",
    "npm-run-all": "^4.1.5",
    "typescript": "^5.5.0"
  }
}
```

---

## 5. Skill-to-Feature Mapping Matrix

| Source Artifact | Snippets | Commands | Code Actions | Tree View | Webview | Code Lens | Status Bar |
|----------------|----------|----------|-------------|-----------|---------|-----------|------------|
| browser skill | 10 | — | Sleep warn | Keyword ref | Keyword docs | — | Lib version |
| selenium skill | 9 | — | Sleep warn, timeout | Keyword ref | Keyword docs | — | Lib version |
| appium skill | 6 | — | Removed KW error | Keyword ref | Keyword docs | — | Lib version |
| requests skill | 6 | — | SSL verify warn | Keyword ref | Keyword docs | — | Lib version |
| restinstance skill | 5 | — | — | Keyword ref | Keyword docs | — | Lib version |
| libdoc-search | — | searchKeyword | Find keyword | Keyword browser | — | Library info | — |
| libdoc-explain | — | explainKeyword | Show docs | Detail panel | Keyword viewer | — | — |
| results | — | analyzeResults | — | Test explorer | Dashboard | Run/Debug | Pass/fail count |
| keyword-builder | 2 | generateKeyword | Extract to KW | — | — | — | — |
| testcase-builder | 2 | generateTestCase | — | — | — | — | — |
| resource-architect | 1 | scaffoldProject | — | Project tree | Preview | — | — |
| rf-test-architect | 1 | planSuite | Add docs | — | — | — | — |
| rf-debug-expert | — | diagnose | Replace Sleep | — | Diagnosis | — | — |
| rf-migration-guide | — | modernize | 9 syntax fixes | — | Migration rpt | — | — |
| rf-keyword-consultant | — | findKeyword | — | — | Comparison | — | — |

---

## 6. Implementation Phases & Timeline

### Phase 1: MVP — Snippets + Commands (Week 1-2)

| Task | Effort | Details |
|------|--------|---------|
| Scaffold extension project | 0.5d | package.json, tsconfig, esbuild, .vscodeignore |
| Create 7 snippet JSON files | 1d | Convert SKILL.md patterns → VS Code snippets |
| Build Python invoker bridge | 0.5d | src/python/invoker.ts + detector.ts |
| Implement searchKeyword command | 0.5d | QuickPick → rf_libdoc.py → results list |
| Implement generateKeyword command | 0.5d | QuickPick form → keyword_builder.py → insert |
| Implement generateTestCase command | 0.5d | QuickPick form → testcase_builder.py → insert |
| Implement scaffoldProject command | 0.5d | Multi-step QuickPick → resource_architect.py |
| Implement analyzeResults command | 1d | File picker → rf_results.py → basic webview |
| Implement checkEnvironment command | 0.5d | Detect Python/RF/libraries → notification |
| Write tests | 1d | Unit tests for invoker, integration tests for commands |
| Create extension icon + README | 0.5d | Marketplace presentation |
| **Publish to Marketplace** | 0.5d | Create publisher, vsce publish |
| **Total Phase 1** | **~7d** | |

### Phase 2: Tree Views + Webviews (Week 3-4)

| Task | Effort | Details |
|------|--------|---------|
| Build static keyword index | 1d | Generate keyword-index.json from libdoc output |
| Implement Keyword Browser tree | 1.5d | TreeDataProvider, search, click-to-insert |
| Implement Results Dashboard webview | 2d | HTML/CSS/JS, summary cards, failure list, timing |
| Implement Keyword Viewer webview | 1d | Documentation rendering, argument table |
| Implement test results tree | 1d | Parse output.xml, pass/fail icons, click-to-navigate |
| File watchers (output.xml) | 0.5d | Auto-refresh trees on file change |
| Status bar items | 0.5d | RF version, test results count |
| Tests + polish | 1d | Integration tests, bug fixes |
| **Total Phase 2** | **~8.5d** | |

### Phase 3: Code Actions + Code Lenses (Week 5-6)

| Task | Effort | Details |
|------|--------|---------|
| Migration code actions (9 patterns) | 2d | CodeActionProvider, regex pattern matching |
| Code lenses (Run/Debug/References) | 1.5d | CodeLensProvider, test execution integration |
| Hover provider (keyword docs) | 1d | HoverProvider backed by keyword index |
| Completion provider (snippet-enhanced) | 1d | CompletionItemProvider for argument completions |
| Migration report webview | 1d | Scan workspace, generate report |
| Tests + polish | 1d | |
| **Total Phase 3** | **~7.5d** | |

### Phase 4: Walkthrough + Polish (Week 7)

| Task | Effort | Details |
|------|--------|---------|
| Getting Started walkthrough | 1d | 4 steps with markdown content |
| Open VSX Registry publishing | 0.5d | Cross-publish to open-vsx.org |
| CI/CD pipeline | 1d | GitHub Actions for build, test, publish |
| Documentation + CHANGELOG | 0.5d | |
| **Total Phase 4** | **~3d** | |

**Total estimated effort: ~26 working days (5-7 weeks)**

---

## 7. Publishing & Distribution

### VS Code Marketplace

1. Create Azure DevOps PAT (scope: Marketplace → Manage)
2. Register publisher `manykarim` at marketplace.visualstudio.com/manage
3. Package: `npx vsce package`
4. Publish: `npx vsce publish`
5. Pre-release channel: `npx vsce publish --pre-release`

### Open VSX Registry

1. Register via GitHub OAuth at open-vsx.org
2. Create access token
3. `npx ovsx create-namespace manykarim --pat <token>`
4. `npx ovsx publish robotframework-skills-0.1.0.vsix --pat <token>`

### CI/CD (GitHub Actions)

```yaml
# .github/workflows/vscode-extension.yml
name: VS Code Extension CI
on:
  push:
    branches: [main]
    paths: ['vscode-rf-skills/**']
  pull_request:
    paths: ['vscode-rf-skills/**']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
        working-directory: vscode-rf-skills
      - run: npm run lint
        working-directory: vscode-rf-skills
      - run: npm run check-types
        working-directory: vscode-rf-skills
      - run: npm run package
        working-directory: vscode-rf-skills
      - run: npx vsce package
        working-directory: vscode-rf-skills

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
        working-directory: vscode-rf-skills
      - run: xvfb-run -a npm test
        working-directory: vscode-rf-skills

  publish:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    needs: [build, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
        working-directory: vscode-rf-skills
      - run: npx vsce publish -p ${{ secrets.VSCE_PAT }}
        working-directory: vscode-rf-skills
      - run: npx ovsx publish -p ${{ secrets.OVSX_PAT }}
        working-directory: vscode-rf-skills
```

---

## 8. Monorepo Strategy

The VS Code extension lives in the **same repository** as the Claude Code plugin:

```
robotframework-agentskills/
├── .claude-plugin/              # Claude Code marketplace
├── plugins/rf-agentskills/      # Claude Code plugin
├── skills/                      # Original standalone skills
├── vscode-rf-skills/            # VS Code extension (NEW)
│   ├── src/
│   ├── snippets/
│   ├── scripts/                 # Symlinks or copies of Python scripts
│   ├── data/
│   ├── media/
│   ├── package.json
│   └── ...
├── scripts/                     # Shared validation scripts
├── tests/                       # Shared tests
└── .github/workflows/
    ├── ci.yml                   # Claude plugin CI
    └── vscode-extension.yml     # VS Code extension CI
```

**Script sharing**: The 5 Python scripts are shared between the Claude plugin and VS Code extension. Options:
1. **Copy**: Duplicate scripts into `vscode-rf-skills/scripts/` (simplest, no cross-dependency)
2. **Symlink**: Link to `plugins/rf-agentskills/scripts/` (works locally, breaks in VSIX)
3. **Build step**: Copy scripts during `vscode:prepublish` (best of both worlds)

**Recommendation**: Option 3 — add a copy step to the build pipeline.

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| RobotCode conflicts (duplicate completions) | Medium | Use distinct trigger prefixes (`rf-*`), document as complementary |
| Python not available in user environment | Low | Snippets/tree view work without Python; graceful degradation for commands |
| `robotframework` language ID not registered | Low | Check if RobotCode is installed; register our own if not |
| Keyword index goes stale vs library updates | Low | Regenerate periodically; allow live rf_libdoc.py fallback |
| `uv` not available in user environment | Medium | Fallback chain: `uv run python3` → `python3` → `python` |
| Webview security (XSS in keyword docs) | Medium | Sanitize all HTML content; use CSP in webviews |
| Large output.xml files (100MB+) | Low | Stream parsing; limit displayed results; show progress |

---

## 10. Success Metrics

| Metric | Target (6 months) |
|--------|-------------------|
| Marketplace installs | 1,000+ |
| Marketplace rating | 4.0+ stars |
| Snippet usage (telemetry) | Track most-used snippets to prioritize |
| Command usage | Track which commands are most popular |
| GitHub stars | 50+ |
| Open issues resolved | <10 open bugs at any time |

---

## 11. Toolchain Summary (Validated)

| Component | Tool | Version | Status |
|-----------|------|---------|--------|
| Runtime | Node.js | 24.13.0 | Validated |
| Package manager | npm | 11.6.2 | Validated |
| Bundler | esbuild | 0.27.x | Validated (14ms builds) |
| Packager | @vscode/vsce | 3.7.1 | Validated (valid .vsix) |
| Python runner | uv | 0.9.26 | Validated |
| Python | python3 | 3.12.1 | Validated |
| Robot Framework | robotframework | 7.4.1 | Validated |
| Test framework | @vscode/test-electron | 2.4.x | Available |

---

## 12. Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Compete vs complement RobotCode | **Complement** | RobotCode has 309K installs, strong LSP; we fill different gaps |
| Own LSP vs no LSP | **No LSP** | Avoid conflicts with RobotCode; use providers for targeted features |
| Monorepo vs separate repo | **Monorepo** | Share Python scripts, unified CI, single source of truth |
| Webview framework | **Vanilla HTML/CSS/JS** | No build pipeline for webviews, simplicity |
| Snippet trigger prefix | **`rf-`** | Short, memorable, no conflict with RobotCode |
| Bundler | **esbuild** | 14ms vs 50s webpack, VS Code team recommended |
| Minimum VS Code version | **^1.90.0** | Modern API access, broad compatibility |
| Python invocation | **child_process via uv/python3** | Validated, simple, handles JSON protocol |
| Distribution | **Marketplace + Open VSX** | Maximum reach (VS Code + VSCodium/Theia/etc.) |
| Extension name | **robotframework-skills** | Clear, descriptive, matches the project |

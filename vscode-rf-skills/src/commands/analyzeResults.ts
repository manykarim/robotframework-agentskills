import * as vscode from "vscode";
import { invokePythonScript } from "../python/invoker.js";

/** Top-level shape returned by rf_results.py --sections all. */
interface ResultsData {
  meta: { outputs: string[]; merged: boolean };
  summary?: {
    totals: { passed: number; failed: number; skipped: number; total: number };
    suite_count: number;
    test_count: number;
    overall_status: string;
  };
  details?: {
    suites: Array<{
      name: string;
      status: string;
      totals: { passed: number; failed: number; skipped: number; total: number };
      tests: Array<{ name: string; status: string; elapsed_ms: number }>;
    }>;
    failed_tests: Array<{
      name: string;
      suite: string;
      message: string;
      keyword_path: string | null;
    }>;
    tags: Array<{
      name: string;
      totals: { passed: number; failed: number; skipped: number; total: number };
    }>;
  };
  errors?: {
    execution_errors: Array<{ level: string; message: string }>;
    failed_test_messages: Array<{
      test: string;
      suite: string;
      message: string;
      keyword_path: string | null;
    }>;
    keyword_errors: Array<{
      keyword: string;
      test: string;
      suite: string;
      message: string;
      elapsed_ms: number;
    }>;
  };
  timing?: {
    totals: { elapsed_ms: number };
    slowest_tests: Array<{
      name: string;
      suite: string;
      elapsed_ms: number;
    }>;
  };
}

export function registerAnalyzeResults(
  context: vscode.ExtensionContext
): void {
  const disposable = vscode.commands.registerCommand(
    "rfSkills.analyzeResults",
    async () => {
      // File picker filtered to XML.
      const uris = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectMany: false,
        filters: { "Robot Output": ["xml"] },
        title: "Select output.xml",
        defaultUri: defaultOutputUri(),
      });

      if (!uris || uris.length === 0) {
        return;
      }

      const outputPath = uris[0].fsPath;

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Analyzing test results...",
          cancellable: false,
        },
        async () => {
          const result = await invokePythonScript(
            context,
            "rf_results.py",
            [
              "--output",
              outputPath,
              "--sections",
              "all",
              "--pretty",
              "--include-keyword-timing",
            ]
          );

          if (result.error) {
            vscode.window.showErrorMessage(
              `Results analysis failed: ${result.error}`
            );
            return;
          }

          const data = result.data as ResultsData | undefined;
          if (!data) {
            vscode.window.showWarningMessage("No results data returned.");
            return;
          }

          showResultsDashboard(context, data, outputPath);
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function defaultOutputUri(): vscode.Uri | undefined {
  const config = vscode.workspace.getConfiguration("rfSkills");
  const relPath = config.get<string>("results.outputPath", "results/output.xml");
  const root = vscode.workspace.workspaceFolders?.[0]?.uri;
  if (root) {
    return vscode.Uri.joinPath(root, relPath);
  }
  return undefined;
}

function showResultsDashboard(
  context: vscode.ExtensionContext,
  data: ResultsData,
  filePath: string
): void {
  const panel = vscode.window.createWebviewPanel(
    "rfResults",
    "RF Test Results",
    vscode.ViewColumn.One,
    { enableScripts: true }
  );

  panel.webview.html = buildDashboardHtml(data, filePath);

  // Handle "go to source" messages from the webview.
  panel.webview.onDidReceiveMessage(
    async (msg: { command: string; suite?: string; test?: string }) => {
      if (msg.command === "goToSource" && msg.suite && msg.test) {
        await navigateToTest(msg.suite, msg.test);
      }
    },
    undefined,
    context.subscriptions
  );
}

async function navigateToTest(
  suiteName: string,
  testName: string
): Promise<void> {
  // Attempt to find the test file based on suite name.
  // Robot Framework suite names are typically derived from file names.
  const suitePart = suiteName.split(".").pop() ?? suiteName;
  const pattern = `**/${suitePart.replace(/\s+/g, "_")}.robot`;
  const files = await vscode.workspace.findFiles(pattern, null, 5);

  if (files.length === 0) {
    vscode.window.showWarningMessage(
      `Could not find source file for suite "${suiteName}".`
    );
    return;
  }

  const doc = await vscode.workspace.openTextDocument(files[0]);
  const editor = await vscode.window.showTextDocument(doc);

  // Try to jump to the test name line.
  const text = doc.getText();
  const idx = text.indexOf(testName);
  if (idx >= 0) {
    const pos = doc.positionAt(idx);
    editor.revealRange(
      new vscode.Range(pos, pos),
      vscode.TextEditorRevealType.InCenter
    );
    editor.selection = new vscode.Selection(pos, pos);
  }
}

// ------------------------------------------------------------------
// HTML generation
// ------------------------------------------------------------------

function buildDashboardHtml(data: ResultsData, filePath: string): string {
  const summary = data.summary;
  const details = data.details;
  const timing = data.timing;

  const passRate =
    summary && summary.totals.total > 0
      ? ((summary.totals.passed / summary.totals.total) * 100).toFixed(1)
      : "0";

  const failedTests = details?.failed_tests ?? [];

  const slowestTests = timing?.slowest_tests?.slice(0, 10) ?? [];

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>RF Test Results</title>
  <style>
    :root {
      --pass: #22c55e; --fail: #ef4444; --skip: #eab308;
      --bg: var(--vscode-editor-background, #1e1e1e);
      --fg: var(--vscode-editor-foreground, #d4d4d4);
      --card-bg: var(--vscode-editorWidget-background, #252526);
      --border: var(--vscode-editorWidget-border, #3c3c3c);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: var(--vscode-font-family, sans-serif); background: var(--bg); color: var(--fg); padding: 16px; }
    h1 { font-size: 1.3em; margin-bottom: 4px; }
    .subtitle { font-size: 0.85em; opacity: 0.7; margin-bottom: 16px; word-break: break-all; }
    .cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
    .card { flex: 1 1 140px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 14px; text-align: center; }
    .card .value { font-size: 2em; font-weight: bold; }
    .card .label { font-size: 0.8em; opacity: 0.7; margin-top: 4px; }
    .pass .value { color: var(--pass); }
    .fail .value { color: var(--fail); }
    .skip .value { color: var(--skip); }
    .rate .value { color: ${Number(passRate) >= 80 ? "var(--pass)" : "var(--fail)"}; }
    h2 { font-size: 1.1em; margin: 16px 0 8px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
    th, td { padding: 6px 10px; border: 1px solid var(--border); text-align: left; font-size: 0.85em; }
    th { background: var(--card-bg); }
    .link { color: #58a6ff; cursor: pointer; text-decoration: underline; }
    .bar-container { display: flex; height: 14px; border-radius: 3px; overflow: hidden; margin-bottom: 16px; }
    .bar-pass { background: var(--pass); }
    .bar-fail { background: var(--fail); }
    .bar-skip { background: var(--skip); }
    .timing-bar { background: var(--card-bg); border: 1px solid var(--border); border-radius: 3px; height: 18px; margin: 2px 0; }
    .timing-fill { background: #58a6ff; height: 100%; border-radius: 3px; }
  </style>
</head>
<body>
  <h1>Test Results Dashboard</h1>
  <p class="subtitle">${escapeHtml(filePath)}</p>

  ${summary ? renderSummaryCards(summary, passRate) : ""}
  ${summary ? renderPassBar(summary) : ""}
  ${failedTests.length > 0 ? renderFailures(failedTests) : ""}
  ${slowestTests.length > 0 ? renderTiming(slowestTests) : ""}
  ${details?.suites ? renderSuites(details.suites) : ""}

  <script>
    const vscode = acquireVsCodeApi();
    document.querySelectorAll('[data-goto]').forEach(el => {
      el.addEventListener('click', () => {
        const [suite, test] = el.dataset.goto.split('||');
        vscode.postMessage({ command: 'goToSource', suite, test });
      });
    });
  </script>
</body>
</html>`;
}

function renderSummaryCards(
  summary: NonNullable<ResultsData["summary"]>,
  passRate: string
): string {
  return `<div class="cards">
    <div class="card pass"><div class="value">${summary.totals.passed}</div><div class="label">Passed</div></div>
    <div class="card fail"><div class="value">${summary.totals.failed}</div><div class="label">Failed</div></div>
    <div class="card skip"><div class="value">${summary.totals.skipped}</div><div class="label">Skipped</div></div>
    <div class="card rate"><div class="value">${passRate}%</div><div class="label">Pass Rate</div></div>
  </div>`;
}

function renderPassBar(
  summary: NonNullable<ResultsData["summary"]>
): string {
  const t = summary.totals;
  if (t.total === 0) {
    return "";
  }
  const pPct = ((t.passed / t.total) * 100).toFixed(1);
  const fPct = ((t.failed / t.total) * 100).toFixed(1);
  const sPct = ((t.skipped / t.total) * 100).toFixed(1);
  return `<div class="bar-container">
    <div class="bar-pass" style="width:${pPct}%" title="Passed ${t.passed}"></div>
    <div class="bar-fail" style="width:${fPct}%" title="Failed ${t.failed}"></div>
    <div class="bar-skip" style="width:${sPct}%" title="Skipped ${t.skipped}"></div>
  </div>`;
}

function renderFailures(
  failures: NonNullable<ResultsData["details"]>["failed_tests"]
): string {
  const rows = failures
    .map(
      (f) =>
        `<tr>
      <td><span class="link" data-goto="${escapeAttr(f.suite)}||${escapeAttr(f.name)}">${escapeHtml(f.name)}</span></td>
      <td>${escapeHtml(f.suite)}</td>
      <td>${escapeHtml(f.message ?? "")}</td>
    </tr>`
    )
    .join("\n");

  return `<h2>Failures (${failures.length})</h2>
  <table>
    <tr><th>Test</th><th>Suite</th><th>Message</th></tr>
    ${rows}
  </table>`;
}

function renderTiming(
  tests: NonNullable<ResultsData["timing"]>["slowest_tests"]
): string {
  const maxMs = Math.max(...tests.map((t) => t.elapsed_ms), 1);
  const rows = tests
    .map(
      (t) =>
        `<tr>
      <td>${escapeHtml(t.name)}</td>
      <td>${escapeHtml(t.suite)}</td>
      <td>${(t.elapsed_ms / 1000).toFixed(2)}s</td>
      <td style="width:40%"><div class="timing-bar"><div class="timing-fill" style="width:${((t.elapsed_ms / maxMs) * 100).toFixed(1)}%"></div></div></td>
    </tr>`
    )
    .join("\n");

  return `<h2>Slowest Tests</h2>
  <table>
    <tr><th>Test</th><th>Suite</th><th>Duration</th><th>Relative</th></tr>
    ${rows}
  </table>`;
}

function renderSuites(
  suites: NonNullable<ResultsData["details"]>["suites"]
): string {
  if (suites.length === 0) {
    return "";
  }
  const rows = suites
    .map(
      (s) =>
        `<tr>
      <td>${escapeHtml(s.name)}</td>
      <td style="color:${s.status === "PASS" ? "var(--pass)" : "var(--fail)"}">${escapeHtml(s.status)}</td>
      <td>${s.totals.passed}</td><td>${s.totals.failed}</td><td>${s.totals.skipped}</td>
    </tr>`
    )
    .join("\n");

  return `<h2>Suites</h2>
  <table>
    <tr><th>Suite</th><th>Status</th><th>Pass</th><th>Fail</th><th>Skip</th></tr>
    ${rows}
  </table>`;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(text: string): string {
  return escapeHtml(text).replace(/'/g, "&#39;");
}

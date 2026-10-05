import * as vscode from 'vscode';
import type { ResultsSummary, TestResult, SuiteResult } from '../views/testExplorer.js';

// -- Panel Singleton ---------------------------------------------------------

let currentPanel: vscode.WebviewPanel | undefined;

// -- Public API --------------------------------------------------------------

/**
 * Creates (or reveals) the Test Results Dashboard webview panel.
 */
export function createResultsDashboard(
    context: vscode.ExtensionContext,
    resultsData: ResultsSummary,
): vscode.WebviewPanel {
    if (currentPanel) {
        currentPanel.reveal(vscode.ViewColumn.One);
        currentPanel.webview.html = buildHtml(currentPanel.webview, resultsData);
        return currentPanel;
    }

    const panel = vscode.window.createWebviewPanel(
        'rfSkills.resultsDashboard',
        'RF Test Results',
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [],
        },
    );

    currentPanel = panel;

    panel.webview.html = buildHtml(panel.webview, resultsData);

    // Handle messages from the webview
    panel.webview.onDidReceiveMessage(
        async (message: { command: string; filePath?: string; line?: number }) => {
            if (message.command === 'openFile' && message.filePath) {
                await vscode.commands.executeCommand(
                    'rfSkills.goToTestSource',
                    message.filePath,
                    message.line,
                );
            }
        },
        undefined,
        context.subscriptions,
    );

    panel.onDidDispose(() => {
        currentPanel = undefined;
    });

    return panel;
}

// -- HTML Builder ------------------------------------------------------------

function buildHtml(webview: vscode.Webview, data: ResultsSummary): string {
    const nonce = getNonce();
    const passPercent = data.total > 0 ? ((data.passed / data.total) * 100).toFixed(1) : '0';
    const failPercent = data.total > 0 ? ((data.failed / data.total) * 100).toFixed(1) : '0';
    const skipPercent = data.total > 0 ? ((data.skipped / data.total) * 100).toFixed(1) : '0';

    const failedTests = collectFailedTests(data.suites);
    const slowestTests = collectAllTests(data.suites)
        .sort((a, b) => b.duration - a.duration)
        .slice(0, 10);
    const maxDuration = slowestTests.length > 0 ? slowestTests[0].duration : 1;
    const tagStats = collectTagStats(data.suites);

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
    <title>RF Test Results</title>
    <style nonce="${nonce}">
        ${getStyles()}
    </style>
</head>
<body>
    <h1>Test Results Dashboard</h1>
    <p class="timestamp">Generated: ${escapeHtml(data.generated)} | Duration: ${formatDuration(data.duration)}</p>

    <!-- Summary Cards -->
    <div class="cards">
        <div class="card total">
            <div class="card-value">${data.total}</div>
            <div class="card-label">Total</div>
        </div>
        <div class="card passed">
            <div class="card-value">${data.passed}</div>
            <div class="card-label">Passed (${passPercent}%)</div>
        </div>
        <div class="card failed">
            <div class="card-value">${data.failed}</div>
            <div class="card-label">Failed (${failPercent}%)</div>
        </div>
        <div class="card skipped">
            <div class="card-value">${data.skipped}</div>
            <div class="card-label">Skipped (${skipPercent}%)</div>
        </div>
    </div>

    <!-- Failed Tests Table -->
    ${failedTests.length > 0 ? `
    <h2>Failed Tests</h2>
    <table class="results-table">
        <thead>
            <tr>
                <th>Test Name</th>
                <th>Suite</th>
                <th>Error Message</th>
                <th>Duration</th>
                <th>Source</th>
            </tr>
        </thead>
        <tbody>
            ${failedTests.map(({ test, suiteName }) => `
            <tr class="fail-row">
                <td class="test-name">${escapeHtml(test.name)}</td>
                <td>${escapeHtml(suiteName)}</td>
                <td class="error-msg">${escapeHtml(truncate(test.message, 120))}</td>
                <td class="duration">${formatDuration(test.duration)}</td>
                <td>${test.sourcePath
                    ? `<a href="#" class="source-link" data-path="${escapeHtml(test.sourcePath)}" data-line="${test.sourceLine ?? 1}">Go to Source</a>`
                    : '-'
                }</td>
            </tr>`).join('')}
        </tbody>
    </table>` : '<h2>All Tests Passed</h2><p class="all-pass-msg">No failures to report.</p>'}

    <!-- Timing Chart -->
    ${slowestTests.length > 0 ? `
    <h2>Slowest Tests</h2>
    <div class="timing-chart">
        ${slowestTests.map(test => {
            const widthPct = maxDuration > 0 ? ((test.duration / maxDuration) * 100).toFixed(1) : '0';
            const barClass = test.status === 'FAIL' ? 'bar-fail' : test.status === 'SKIP' ? 'bar-skip' : 'bar-pass';
            return `
        <div class="timing-row">
            <div class="timing-label">${escapeHtml(truncate(test.name, 40))}</div>
            <div class="timing-bar-container">
                <div class="timing-bar ${barClass}" style="width: ${widthPct}%"></div>
            </div>
            <div class="timing-value">${formatDuration(test.duration)}</div>
        </div>`;
        }).join('')}
    </div>` : ''}

    <!-- Tag Statistics -->
    ${tagStats.length > 0 ? `
    <h2>Tag Statistics</h2>
    <table class="results-table tag-table">
        <thead>
            <tr>
                <th>Tag</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            ${tagStats.map(ts => `
            <tr>
                <td>${escapeHtml(ts.tag)}</td>
                <td class="pass-count">${ts.passed}</td>
                <td class="fail-count">${ts.failed}</td>
                <td>${ts.passed + ts.failed}</td>
            </tr>`).join('')}
        </tbody>
    </table>` : ''}

    <script nonce="${nonce}">
        (function() {
            const vscode = acquireVsCodeApi();

            document.addEventListener('click', function(e) {
                const link = e.target.closest('.source-link');
                if (link) {
                    e.preventDefault();
                    vscode.postMessage({
                        command: 'openFile',
                        filePath: link.dataset.path,
                        line: parseInt(link.dataset.line, 10) || 1
                    });
                }
            });
        })();
    </script>
</body>
</html>`;
}

// -- Data Helpers ------------------------------------------------------------

interface FailedTestEntry {
    test: TestResult;
    suiteName: string;
}

function collectFailedTests(suites: SuiteResult[]): FailedTestEntry[] {
    const results: FailedTestEntry[] = [];
    for (const suite of suites) {
        for (const test of suite.tests) {
            if (test.status === 'FAIL') {
                results.push({ test, suiteName: suite.name });
            }
        }
        results.push(...collectFailedTests(suite.suites));
    }
    return results;
}

function collectAllTests(suites: SuiteResult[]): TestResult[] {
    const results: TestResult[] = [];
    for (const suite of suites) {
        results.push(...suite.tests);
        results.push(...collectAllTests(suite.suites));
    }
    return results;
}

interface TagStat {
    tag: string;
    passed: number;
    failed: number;
}

function collectTagStats(suites: SuiteResult[]): TagStat[] {
    const map = new Map<string, { passed: number; failed: number }>();

    const allTests = collectAllTests(suites);
    for (const test of allTests) {
        for (const tag of test.tags) {
            if (!map.has(tag)) {
                map.set(tag, { passed: 0, failed: 0 });
            }
            const entry = map.get(tag)!;
            if (test.status === 'PASS') {
                entry.passed++;
            } else if (test.status === 'FAIL') {
                entry.failed++;
            }
        }
    }

    return Array.from(map.entries())
        .map(([tag, counts]) => ({ tag, ...counts }))
        .sort((a, b) => a.tag.localeCompare(b.tag));
}

// -- Style Helpers -----------------------------------------------------------

function getStyles(): string {
    return `
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            padding: 20px;
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            line-height: 1.5;
        }
        h1 {
            font-size: 1.5em;
            margin-bottom: 4px;
            color: var(--vscode-foreground);
        }
        h2 {
            font-size: 1.15em;
            margin: 24px 0 12px;
            color: var(--vscode-foreground);
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 4px;
        }
        .timestamp {
            color: var(--vscode-descriptionForeground);
            font-size: 0.9em;
            margin-bottom: 16px;
        }

        /* Summary Cards */
        .cards {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 8px;
        }
        .card {
            flex: 1;
            min-width: 120px;
            padding: 16px;
            border-radius: 6px;
            text-align: center;
            background: var(--vscode-editorWidget-background);
            border: 1px solid var(--vscode-panel-border);
        }
        .card-value {
            font-size: 2em;
            font-weight: bold;
            line-height: 1.2;
        }
        .card-label {
            font-size: 0.85em;
            color: var(--vscode-descriptionForeground);
            margin-top: 4px;
        }
        .card.total .card-value { color: var(--vscode-foreground); }
        .card.passed .card-value { color: var(--vscode-testing-iconPassed); }
        .card.failed .card-value { color: var(--vscode-testing-iconFailed); }
        .card.skipped .card-value { color: var(--vscode-testing-iconSkipped); }

        /* Tables */
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
        }
        .results-table th,
        .results-table td {
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .results-table th {
            background: var(--vscode-editorWidget-background);
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        .results-table .test-name { font-weight: 500; }
        .results-table .error-msg {
            color: var(--vscode-testing-iconFailed);
            font-size: 0.9em;
            max-width: 400px;
            word-break: break-word;
        }
        .results-table .duration {
            white-space: nowrap;
            color: var(--vscode-descriptionForeground);
        }
        .source-link {
            color: var(--vscode-textLink-foreground);
            text-decoration: none;
            cursor: pointer;
            white-space: nowrap;
        }
        .source-link:hover {
            text-decoration: underline;
            color: var(--vscode-textLink-activeForeground);
        }
        .all-pass-msg {
            color: var(--vscode-testing-iconPassed);
            font-weight: 500;
        }
        .pass-count { color: var(--vscode-testing-iconPassed); }
        .fail-count { color: var(--vscode-testing-iconFailed); }

        /* Timing Chart */
        .timing-chart { margin-bottom: 8px; }
        .timing-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }
        .timing-label {
            width: 260px;
            min-width: 160px;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
            font-size: 0.9em;
        }
        .timing-bar-container {
            flex: 1;
            height: 18px;
            background: var(--vscode-editorWidget-background);
            border-radius: 3px;
            overflow: hidden;
        }
        .timing-bar {
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        .bar-pass { background: var(--vscode-testing-iconPassed); opacity: 0.8; }
        .bar-fail { background: var(--vscode-testing-iconFailed); opacity: 0.8; }
        .bar-skip { background: var(--vscode-testing-iconSkipped); opacity: 0.8; }
        .timing-value {
            width: 60px;
            text-align: right;
            font-size: 0.85em;
            color: var(--vscode-descriptionForeground);
            white-space: nowrap;
        }
    `;
}

// -- Utility -----------------------------------------------------------------

function getNonce(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < 32; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatDuration(seconds: number): string {
    if (seconds < 1) {
        return `${Math.round(seconds * 1000)}ms`;
    }
    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    }
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs.toFixed(0)}s`;
}

function truncate(text: string, maxLen: number): string {
    if (!text) {
        return '';
    }
    const firstLine = text.split('\n')[0];
    if (firstLine.length <= maxLen) {
        return firstLine;
    }
    return firstLine.substring(0, maxLen - 3) + '...';
}

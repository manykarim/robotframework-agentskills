import * as vscode from 'vscode';

// -- Data Types --------------------------------------------------------------

export interface MigrationFinding {
    filePath: string;
    line: number;
    patternType: string;           // e.g. "deprecated-keyword", "old-syntax", "removed-setting"
    description: string;
    before: string;                // the original code
    after: string;                 // the suggested replacement
    severity: 'error' | 'warning' | 'info';
    fixed?: boolean;
}

export interface MigrationReportData {
    findings: MigrationFinding[];
    totalFiles: number;
    estimatedEffort: string;       // e.g. "30 minutes", "2 hours"
}

// -- Panel Singleton ---------------------------------------------------------

let currentPanel: vscode.WebviewPanel | undefined;

// -- Public API --------------------------------------------------------------

/**
 * Shows the migration report as a rich webview panel.
 */
export function showMigrationReport(
    context: vscode.ExtensionContext,
    data: MigrationReportData,
): vscode.WebviewPanel {
    if (currentPanel) {
        currentPanel.reveal(vscode.ViewColumn.One);
        currentPanel.webview.html = buildHtml(currentPanel.webview, data);
        return currentPanel;
    }

    const panel = vscode.window.createWebviewPanel(
        'rfSkills.migrationReport',
        'RF Migration Report',
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [],
        },
    );

    currentPanel = panel;

    panel.webview.html = buildHtml(panel.webview, data);

    // Handle messages from the webview
    panel.webview.onDidReceiveMessage(
        async (message: {
            command: string;
            filePath?: string;
            line?: number;
            findingIndex?: number;
            findings?: number[];
        }) => {
            switch (message.command) {
                case 'openFile':
                    if (message.filePath) {
                        await vscode.commands.executeCommand(
                            'rfSkills.goToTestSource',
                            message.filePath,
                            message.line,
                        );
                    }
                    break;

                case 'applyFix':
                    if (message.findingIndex !== undefined) {
                        await vscode.commands.executeCommand(
                            'rfSkills.applyMigrationFix',
                            data.findings[message.findingIndex],
                        );
                        // Mark as fixed and refresh
                        data.findings[message.findingIndex].fixed = true;
                        panel.webview.html = buildHtml(panel.webview, data);
                    }
                    break;

                case 'applyAllForFile':
                    if (message.findings) {
                        for (const idx of message.findings) {
                            if (!data.findings[idx].fixed) {
                                await vscode.commands.executeCommand(
                                    'rfSkills.applyMigrationFix',
                                    data.findings[idx],
                                );
                                data.findings[idx].fixed = true;
                            }
                        }
                        panel.webview.html = buildHtml(panel.webview, data);
                    }
                    break;
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

function buildHtml(_webview: vscode.Webview, data: MigrationReportData): string {
    const nonce = getNonce();

    const totalFindings = data.findings.length;
    const fixedCount = data.findings.filter(f => f.fixed).length;
    const remainingCount = totalFindings - fixedCount;

    const errorCount = data.findings.filter(f => f.severity === 'error' && !f.fixed).length;
    const warningCount = data.findings.filter(f => f.severity === 'warning' && !f.fixed).length;
    const infoCount = data.findings.filter(f => f.severity === 'info' && !f.fixed).length;

    // Group findings by file
    const fileGroups = groupByFile(data.findings);

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
    <title>Migration Report</title>
    <style nonce="${nonce}">
        ${getStyles()}
    </style>
</head>
<body>
    <h1>Migration Report</h1>

    <!-- Summary -->
    <div class="summary">
        <div class="summary-stat">
            <span class="stat-value">${totalFindings}</span>
            <span class="stat-label">Total Findings</span>
        </div>
        <div class="summary-stat">
            <span class="stat-value fixed-value">${fixedCount}</span>
            <span class="stat-label">Fixed</span>
        </div>
        <div class="summary-stat">
            <span class="stat-value remaining-value">${remainingCount}</span>
            <span class="stat-label">Remaining</span>
        </div>
        <div class="summary-stat">
            <span class="stat-value">${data.totalFiles}</span>
            <span class="stat-label">Files</span>
        </div>
        <div class="summary-stat">
            <span class="stat-value">${escapeHtml(data.estimatedEffort)}</span>
            <span class="stat-label">Estimated Effort</span>
        </div>
    </div>

    <!-- Progress Bar -->
    <div class="progress-container">
        <div class="progress-bar" style="width: ${totalFindings > 0 ? ((fixedCount / totalFindings) * 100).toFixed(1) : 0}%"></div>
    </div>
    <p class="progress-text">${fixedCount}/${totalFindings} findings resolved</p>

    <!-- Severity Summary -->
    <div class="severity-badges">
        ${errorCount > 0 ? `<span class="severity-badge severity-error">${errorCount} errors</span>` : ''}
        ${warningCount > 0 ? `<span class="severity-badge severity-warning">${warningCount} warnings</span>` : ''}
        ${infoCount > 0 ? `<span class="severity-badge severity-info">${infoCount} info</span>` : ''}
        ${remainingCount === 0 && totalFindings > 0 ? '<span class="severity-badge severity-done">All fixed!</span>' : ''}
    </div>

    <!-- File-by-file findings -->
    ${Array.from(fileGroups.entries()).map(([filePath, indices]) => {
        const fileFindings = indices.map(i => data.findings[i]);
        const fileFixed = fileFindings.filter(f => f.fixed).length;
        const allFixed = fileFixed === fileFindings.length;
        return `
    <div class="file-group ${allFixed ? 'file-done' : ''}">
        <div class="file-header">
            <span class="file-path">${escapeHtml(filePath)}</span>
            <span class="file-count">${fileFixed}/${fileFindings.length}</span>
            ${!allFixed ? `<button class="apply-all-btn" data-findings="${escapeHtml(JSON.stringify(indices))}">Apply All</button>` : '<span class="done-label">Done</span>'}
        </div>
        ${indices.map(idx => {
            const finding = data.findings[idx];
            return `
        <div class="finding ${finding.fixed ? 'finding-fixed' : ''} finding-${finding.severity}">
            <div class="finding-header">
                <span class="finding-type">${escapeHtml(finding.patternType)}</span>
                <span class="finding-line">Line ${finding.line}</span>
                <span class="finding-severity severity-${finding.severity}">${finding.severity}</span>
                ${finding.fixed ? '<span class="fixed-label">Fixed</span>' : ''}
            </div>
            <p class="finding-desc">${escapeHtml(finding.description)}</p>
            <div class="diff-view">
                <div class="diff-before">
                    <span class="diff-label">Before:</span>
                    <code>${escapeHtml(finding.before)}</code>
                </div>
                <div class="diff-after">
                    <span class="diff-label">After:</span>
                    <code>${escapeHtml(finding.after)}</code>
                </div>
            </div>
            <div class="finding-actions">
                <a href="#" class="source-link" data-path="${escapeHtml(finding.filePath)}" data-line="${finding.line}">Go to Source</a>
                ${!finding.fixed ? `<button class="fix-btn" data-index="${idx}">Apply Fix</button>` : ''}
            </div>
        </div>`;
        }).join('')}
    </div>`;
    }).join('')}

    <script nonce="${nonce}">
        (function() {
            const vscode = acquireVsCodeApi();

            document.addEventListener('click', function(e) {
                const target = e.target;

                // "Go to Source" links
                const link = target.closest('.source-link');
                if (link) {
                    e.preventDefault();
                    vscode.postMessage({
                        command: 'openFile',
                        filePath: link.dataset.path,
                        line: parseInt(link.dataset.line, 10) || 1
                    });
                    return;
                }

                // "Apply Fix" button
                const fixBtn = target.closest('.fix-btn');
                if (fixBtn) {
                    e.preventDefault();
                    vscode.postMessage({
                        command: 'applyFix',
                        findingIndex: parseInt(fixBtn.dataset.index, 10)
                    });
                    return;
                }

                // "Apply All" button for a file
                const applyAllBtn = target.closest('.apply-all-btn');
                if (applyAllBtn) {
                    e.preventDefault();
                    const findings = JSON.parse(applyAllBtn.dataset.findings);
                    vscode.postMessage({
                        command: 'applyAllForFile',
                        findings: findings
                    });
                    return;
                }
            });
        })();
    </script>
</body>
</html>`;
}

// -- Data Helpers ------------------------------------------------------------

function groupByFile(findings: MigrationFinding[]): Map<string, number[]> {
    const map = new Map<string, number[]>();
    for (let i = 0; i < findings.length; i++) {
        const fp = findings[i].filePath;
        if (!map.has(fp)) {
            map.set(fp, []);
        }
        map.get(fp)!.push(i);
    }
    return map;
}

// -- Styles ------------------------------------------------------------------

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
            margin-bottom: 16px;
        }

        /* Summary */
        .summary {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        .summary-stat {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 12px 20px;
            background: var(--vscode-editorWidget-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 6px;
            min-width: 100px;
        }
        .stat-value {
            font-size: 1.6em;
            font-weight: bold;
        }
        .stat-label {
            font-size: 0.8em;
            color: var(--vscode-descriptionForeground);
        }
        .fixed-value { color: var(--vscode-testing-iconPassed); }
        .remaining-value { color: var(--vscode-testing-iconFailed); }

        /* Progress */
        .progress-container {
            height: 8px;
            background: var(--vscode-editorWidget-background);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 4px;
        }
        .progress-bar {
            height: 100%;
            background: var(--vscode-testing-iconPassed);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .progress-text {
            font-size: 0.85em;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 12px;
        }

        /* Severity */
        .severity-badges {
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
        }
        .severity-badge {
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 0.8em;
            font-weight: 500;
        }
        .severity-error {
            background: var(--vscode-testing-iconFailed);
            color: var(--vscode-editor-background);
        }
        .severity-warning {
            background: var(--vscode-testing-iconSkipped);
            color: var(--vscode-editor-background);
        }
        .severity-info {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
        }
        .severity-done {
            background: var(--vscode-testing-iconPassed);
            color: var(--vscode-editor-background);
        }

        /* File Groups */
        .file-group {
            margin-bottom: 20px;
            border: 1px solid var(--vscode-panel-border);
            border-radius: 6px;
            overflow: hidden;
        }
        .file-group.file-done {
            opacity: 0.7;
        }
        .file-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            background: var(--vscode-editorWidget-background);
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .file-path {
            flex: 1;
            font-weight: 500;
            font-family: var(--vscode-editor-font-family);
            font-size: 0.9em;
        }
        .file-count {
            color: var(--vscode-descriptionForeground);
            font-size: 0.85em;
        }
        .done-label {
            color: var(--vscode-testing-iconPassed);
            font-size: 0.85em;
            font-weight: 500;
        }

        /* Findings */
        .finding {
            padding: 10px 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .finding:last-child { border-bottom: none; }
        .finding-fixed {
            opacity: 0.5;
        }
        .finding-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }
        .finding-type {
            font-weight: 500;
            font-size: 0.9em;
        }
        .finding-line {
            color: var(--vscode-descriptionForeground);
            font-size: 0.8em;
        }
        .finding-severity {
            font-size: 0.75em;
            padding: 1px 6px;
            border-radius: 8px;
        }
        .fixed-label {
            font-size: 0.75em;
            padding: 1px 6px;
            border-radius: 8px;
            background: var(--vscode-testing-iconPassed);
            color: var(--vscode-editor-background);
        }
        .finding-desc {
            font-size: 0.9em;
            margin-bottom: 8px;
            color: var(--vscode-descriptionForeground);
        }

        /* Diff View */
        .diff-view {
            margin-bottom: 8px;
            font-family: var(--vscode-editor-font-family);
            font-size: 0.85em;
        }
        .diff-before, .diff-after {
            padding: 4px 8px;
            border-radius: 3px;
            margin-bottom: 4px;
            overflow-x: auto;
        }
        .diff-before {
            background: var(--vscode-diffEditor-removedLineBackground);
        }
        .diff-after {
            background: var(--vscode-diffEditor-insertedLineBackground);
        }
        .diff-label {
            font-weight: 600;
            font-size: 0.8em;
            margin-right: 6px;
            color: var(--vscode-descriptionForeground);
        }
        .diff-before code, .diff-after code {
            white-space: pre;
        }

        /* Actions */
        .finding-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .source-link {
            color: var(--vscode-textLink-foreground);
            text-decoration: none;
            cursor: pointer;
            font-size: 0.85em;
        }
        .source-link:hover {
            text-decoration: underline;
        }
        .fix-btn, .apply-all-btn {
            padding: 3px 10px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 0.8em;
        }
        .fix-btn:hover, .apply-all-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        .apply-all-btn {
            font-size: 0.8em;
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

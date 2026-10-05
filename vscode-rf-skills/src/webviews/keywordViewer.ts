import * as vscode from 'vscode';
import type { Keyword, Library } from '../data/keywordIndex.js';

// -- Panel Singleton ---------------------------------------------------------

let currentPanel: vscode.WebviewPanel | undefined;

// -- Public API --------------------------------------------------------------

export interface KeywordViewData {
    keyword: Keyword;
    library?: Library;
    relatedKeywords?: Keyword[];
}

/**
 * Creates or reuses a webview panel to show keyword documentation.
 */
export function showKeywordDocumentation(
    context: vscode.ExtensionContext,
    data: KeywordViewData,
): vscode.WebviewPanel {
    if (currentPanel) {
        currentPanel.reveal(vscode.ViewColumn.Beside);
        currentPanel.title = `RF: ${data.keyword.name}`;
        currentPanel.webview.html = buildHtml(currentPanel.webview, data);
        return currentPanel;
    }

    const panel = vscode.window.createWebviewPanel(
        'rfSkills.keywordViewer',
        `RF: ${data.keyword.name}`,
        vscode.ViewColumn.Beside,
        {
            enableScripts: true,
            retainContextWhenHidden: false,
            localResourceRoots: [],
        },
    );

    currentPanel = panel;

    panel.webview.html = buildHtml(panel.webview, data);

    // Handle messages from the webview
    panel.webview.onDidReceiveMessage(
        async (message: { command: string; keywordName?: string }) => {
            if (message.command === 'insertKeyword' && message.keywordName) {
                const editor = vscode.window.activeTextEditor;
                if (editor) {
                    await editor.edit(editBuilder => {
                        editBuilder.insert(editor.selection.active, message.keywordName!);
                    });
                }
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

function buildHtml(_webview: vscode.Webview, data: KeywordViewData): string {
    const nonce = getNonce();
    const kw = data.keyword;
    const lib = data.library;

    const hasArgs = kw.args.length > 0;
    const related = data.relatedKeywords ?? [];

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
    <title>${escapeHtml(kw.name)}</title>
    <style nonce="${nonce}">
        ${getStyles()}
    </style>
</head>
<body>
    <div class="header">
        <h1>${escapeHtml(kw.name)}</h1>
        ${lib ? `<span class="library-badge">${escapeHtml(lib.name)} ${escapeHtml(lib.version)}</span>` : ''}
        ${kw.deprecated ? '<span class="deprecated-badge">DEPRECATED</span>' : ''}
    </div>

    <p class="short-doc">${escapeHtml(kw.shortDoc)}</p>

    ${kw.tags.length > 0 ? `
    <div class="tags">
        ${kw.tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
    </div>` : ''}

    <!-- Arguments Table -->
    ${hasArgs ? `
    <h2>Arguments</h2>
    <table class="args-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Default</th>
                <th>Required</th>
            </tr>
        </thead>
        <tbody>
            ${kw.args.map(arg => `
            <tr>
                <td class="arg-name">${escapeHtml(arg.name)}</td>
                <td class="arg-type">${escapeHtml(arg.type ?? '-')}</td>
                <td class="arg-default">${arg.default !== undefined && arg.default !== '' ? `<code>${escapeHtml(arg.default)}</code>` : '-'}</td>
                <td class="arg-required">${arg.required === false ? 'No' : 'Yes'}</td>
            </tr>`).join('')}
        </tbody>
    </table>` : '<p class="no-args">This keyword takes no arguments.</p>'}

    <!-- Full Documentation -->
    <h2>Documentation</h2>
    <div class="doc-content">
        ${formatDoc(kw.doc || kw.shortDoc)}
    </div>

    <!-- Usage Example -->
    <h2>Usage</h2>
    <div class="usage-example">
        <pre><code>${buildUsageExample(kw)}</code></pre>
        <button class="insert-btn" id="insertBtn" title="Insert at cursor">Insert at Cursor</button>
    </div>

    <!-- Related Keywords -->
    ${related.length > 0 ? `
    <h2>Related Keywords</h2>
    <ul class="related-list">
        ${related.map(rk => `
        <li>
            <span class="related-name">${escapeHtml(rk.name)}</span>
            <span class="related-doc">${escapeHtml(truncate(rk.shortDoc, 80))}</span>
        </li>`).join('')}
    </ul>` : ''}

    <script nonce="${nonce}">
        (function() {
            const vscode = acquireVsCodeApi();

            document.getElementById('insertBtn').addEventListener('click', function() {
                vscode.postMessage({
                    command: 'insertKeyword',
                    keywordName: ${JSON.stringify(buildInsertText(kw))}
                });
            });
        })();
    </script>
</body>
</html>`;
}

// -- Helpers -----------------------------------------------------------------

function buildUsageExample(kw: Keyword): string {
    const parts = [kw.name];
    for (const arg of kw.args) {
        if (arg.default !== undefined && arg.default !== '') {
            parts.push(`${arg.name}=${arg.default}`);
        } else {
            parts.push(`\${${arg.name}}`);
        }
    }
    return escapeHtml(parts.join('    '));
}

function buildInsertText(kw: Keyword): string {
    const parts = [kw.name];
    for (const arg of kw.args) {
        if (arg.default !== undefined && arg.default !== '') {
            parts.push(`${arg.name}=${arg.default}`);
        } else {
            parts.push(`\${${arg.name}}`);
        }
    }
    return parts.join('    ');
}

function formatDoc(doc: string): string {
    // Convert simple markdown-like patterns to HTML
    const lines = doc.split('\n');
    const htmlLines: string[] = [];

    for (const line of lines) {
        if (line.startsWith('```')) {
            // Toggle code block (simplified handling)
            htmlLines.push(line === '```' ? '</pre>' : '<pre><code>');
        } else if (line.startsWith('- ') || line.startsWith('* ')) {
            htmlLines.push(`<li>${escapeHtml(line.substring(2))}</li>`);
        } else if (line.trim() === '') {
            htmlLines.push('<br>');
        } else {
            htmlLines.push(`<p>${escapeHtml(line)}</p>`);
        }
    }

    return htmlLines.join('\n');
}

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
        .header {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 8px;
        }
        h1 {
            font-size: 1.5em;
            color: var(--vscode-foreground);
        }
        h2 {
            font-size: 1.1em;
            margin: 20px 0 8px;
            color: var(--vscode-foreground);
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 4px;
        }
        .library-badge {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }
        .deprecated-badge {
            background: var(--vscode-testing-iconFailed);
            color: var(--vscode-editor-background);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .short-doc {
            font-size: 1.05em;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 8px;
        }
        .tags {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 8px;
        }
        .tag {
            background: var(--vscode-editorWidget-background);
            border: 1px solid var(--vscode-panel-border);
            padding: 1px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            color: var(--vscode-descriptionForeground);
        }

        /* Arguments Table */
        .args-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
        }
        .args-table th,
        .args-table td {
            padding: 6px 10px;
            text-align: left;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .args-table th {
            background: var(--vscode-editorWidget-background);
            font-weight: 600;
        }
        .arg-name { font-weight: 500; }
        .arg-type { color: var(--vscode-symbolIcon-typeParameterForeground); font-style: italic; }
        .arg-default code {
            background: var(--vscode-textCodeBlock-background);
            padding: 1px 4px;
            border-radius: 3px;
            font-family: var(--vscode-editor-font-family);
            font-size: 0.9em;
        }
        .arg-required { text-align: center; }
        .no-args {
            color: var(--vscode-descriptionForeground);
            font-style: italic;
        }

        /* Documentation */
        .doc-content {
            padding: 8px 0;
        }
        .doc-content p {
            margin-bottom: 4px;
        }
        .doc-content pre {
            background: var(--vscode-textCodeBlock-background);
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            margin: 8px 0;
        }
        .doc-content code {
            font-family: var(--vscode-editor-font-family);
            font-size: 0.9em;
        }
        .doc-content li {
            margin-left: 20px;
            margin-bottom: 2px;
        }

        /* Usage Example */
        .usage-example {
            position: relative;
        }
        .usage-example pre {
            background: var(--vscode-textCodeBlock-background);
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
        }
        .usage-example code {
            font-family: var(--vscode-editor-font-family);
            font-size: 0.9em;
        }
        .insert-btn {
            margin-top: 8px;
            padding: 4px 12px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 0.85em;
        }
        .insert-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }

        /* Related Keywords */
        .related-list {
            list-style: none;
        }
        .related-list li {
            padding: 4px 0;
            border-bottom: 1px solid var(--vscode-panel-border);
            display: flex;
            gap: 12px;
        }
        .related-name {
            font-weight: 500;
            min-width: 160px;
        }
        .related-doc {
            color: var(--vscode-descriptionForeground);
            font-size: 0.9em;
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

function truncate(text: string, maxLen: number): string {
    if (!text) {
        return '';
    }
    if (text.length <= maxLen) {
        return text;
    }
    return text.substring(0, maxLen - 3) + '...';
}

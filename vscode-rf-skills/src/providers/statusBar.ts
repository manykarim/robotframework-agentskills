import * as vscode from 'vscode';
import { detectPythonEnvironment } from '../python/detector.js';

/**
 * Creates and manages status bar items for:
 * 1. RF Environment (left side) - shows RF/Python version
 * 2. Test Results (right side) - shows pass/fail counts from output.xml
 */
export function createStatusBarItems(context: vscode.ExtensionContext): void {
    createRfEnvironmentItem(context);
    createTestResultsItem(context);
}

// -- RF Environment Status Bar Item -------------------------------------------

function createRfEnvironmentItem(context: vscode.ExtensionContext): void {
    const item = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Left,
        100,
    );
    item.text = '$(beaker) RF ?';
    item.tooltip = 'Robot Framework - detecting environment...';
    item.command = 'rfSkills.checkEnvironment';
    item.show();
    context.subscriptions.push(item);

    // Detect environment on activation
    updateRfEnvironment(item);

    // Re-detect when configuration changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('rfSkills.pythonPath')) {
                updateRfEnvironment(item);
            }
        }),
    );
}

async function updateRfEnvironment(item: vscode.StatusBarItem): Promise<void> {
    try {
        const env = await detectPythonEnvironment();

        if (env.rfVersion) {
            item.text = `$(beaker) RF ${env.rfVersion}`;
            item.tooltip = `Robot Framework ${env.rfVersion} | Python ${env.pythonVersion}`;
            item.backgroundColor = undefined;
        } else {
            item.text = '$(beaker) RF ?';
            item.tooltip = `Python ${env.pythonVersion} | Robot Framework not found`;
            item.backgroundColor = new vscode.ThemeColor(
                'statusBarItem.warningBackground',
            );
        }
    } catch {
        item.text = '$(beaker) RF ?';
        item.tooltip = 'Robot Framework - environment detection failed';
        item.backgroundColor = new vscode.ThemeColor(
            'statusBarItem.errorBackground',
        );
    }
}

// -- Test Results Status Bar Item ---------------------------------------------

function createTestResultsItem(context: vscode.ExtensionContext): void {
    const item = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        50,
    );
    item.command = 'rfSkills.analyzeResults';
    item.hide(); // hidden until output.xml is found
    context.subscriptions.push(item);

    // Watch for output.xml changes
    const watcher = vscode.workspace.createFileSystemWatcher('**/output.xml');

    watcher.onDidCreate((uri) => {
        updateTestResults(item, uri);
    });
    watcher.onDidChange((uri) => {
        updateTestResults(item, uri);
    });
    watcher.onDidDelete(() => {
        item.hide();
    });

    context.subscriptions.push(watcher);

    // Check if output.xml already exists at startup
    findExistingOutputXml().then((uri) => {
        if (uri) {
            updateTestResults(item, uri);
        }
    });
}

async function findExistingOutputXml(): Promise<vscode.Uri | undefined> {
    const files = await vscode.workspace.findFiles('**/output.xml', '**/node_modules/**', 1);
    return files[0];
}

async function updateTestResults(
    item: vscode.StatusBarItem,
    uri: vscode.Uri,
): Promise<void> {
    try {
        const content = await vscode.workspace.fs.readFile(uri);
        const text = Buffer.from(content).toString('utf-8');

        const counts = parseOutputXmlCounts(text);
        if (!counts) {
            item.hide();
            return;
        }

        const { pass, fail, skip } = counts;
        const total = pass + fail + skip;

        if (fail > 0) {
            item.text = `$(testing-error-icon) Tests: FAIL ${fail}/${total}`;
            item.tooltip = `${pass} passed, ${fail} failed, ${skip} skipped`;
            item.backgroundColor = new vscode.ThemeColor(
                'statusBarItem.errorBackground',
            );
        } else if (skip > 0) {
            item.text = `$(testing-skipped-icon) Tests: ${pass}/${total} PASS (${skip} skipped)`;
            item.tooltip = `${pass} passed, ${skip} skipped`;
            item.backgroundColor = new vscode.ThemeColor(
                'statusBarItem.warningBackground',
            );
        } else {
            item.text = `$(testing-passed-icon) Tests: ${pass}/${total} PASS`;
            item.tooltip = `All ${total} tests passed`;
            item.backgroundColor = undefined;
        }

        item.show();
    } catch {
        item.hide();
    }
}

/**
 * Quick XML parser for Robot Framework output.xml stat element.
 * Looks for the `<stat pass="N" fail="N" skip="N">` element in the
 * total statistics section.
 */
function parseOutputXmlCounts(
    xml: string,
): { pass: number; fail: number; skip: number } | null {
    // RF output.xml contains <stat pass="N" fail="N" skip="N">Total</stat>
    // within <statistics><total>...</total></statistics>
    const totalMatch = xml.match(
        /<statistics>[\s\S]*?<total>[\s\S]*?<stat\s+([^>]*)>Total<\/stat>/i,
    );
    if (!totalMatch) {
        return null;
    }

    const attrs = totalMatch[1];

    const passMatch = attrs.match(/pass="(\d+)"/);
    const failMatch = attrs.match(/fail="(\d+)"/);
    const skipMatch = attrs.match(/skip="(\d+)"/);

    return {
        pass: passMatch ? parseInt(passMatch[1], 10) : 0,
        fail: failMatch ? parseInt(failMatch[1], 10) : 0,
        skip: skipMatch ? parseInt(skipMatch[1], 10) : 0,
    };
}

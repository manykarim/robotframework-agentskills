import * as vscode from 'vscode';
import * as path from 'path';
import { exec } from 'child_process';

// -- Data Types --------------------------------------------------------------

export interface TestResult {
    name: string;
    status: 'PASS' | 'FAIL' | 'SKIP';
    duration: number;          // seconds
    message: string;           // error message for failures
    sourcePath?: string;       // path to .robot file
    sourceLine?: number;       // line number in source
    tags: string[];
}

export interface SuiteResult {
    name: string;
    status: 'PASS' | 'FAIL';
    tests: TestResult[];
    suites: SuiteResult[];     // nested suites
    duration: number;
    sourcePath?: string;
}

export interface ResultsSummary {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    duration: number;
    generated: string;         // ISO timestamp
    suites: SuiteResult[];
}

// -- Tree Item Types ---------------------------------------------------------

type TestTreeItemKind = 'suite' | 'test';

export class TestTreeItem extends vscode.TreeItem {
    constructor(
        public readonly kind: TestTreeItemKind,
        label: string,
        collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly suiteData?: SuiteResult,
        public readonly testData?: TestResult,
    ) {
        super(label, collapsibleState);

        switch (kind) {
            case 'suite': {
                const suite = suiteData!;
                this.contextValue = 'rfTestSuite';
                this.iconPath = suite.status === 'PASS'
                    ? new vscode.ThemeIcon('pass', new vscode.ThemeColor('testing.iconPassed'))
                    : new vscode.ThemeIcon('error', new vscode.ThemeColor('testing.iconFailed'));
                this.description = formatDuration(suite.duration);
                this.tooltip = `${suite.name} - ${suite.status} (${formatDuration(suite.duration)})`;
                break;
            }

            case 'test': {
                const test = testData!;
                this.contextValue = 'rfTestCase';
                this.description = formatDuration(test.duration);

                switch (test.status) {
                    case 'PASS':
                        this.iconPath = new vscode.ThemeIcon('pass', new vscode.ThemeColor('testing.iconPassed'));
                        this.tooltip = `PASS (${formatDuration(test.duration)})`;
                        break;
                    case 'FAIL':
                        this.iconPath = new vscode.ThemeIcon('error', new vscode.ThemeColor('testing.iconFailed'));
                        this.tooltip = new vscode.MarkdownString(
                            `**FAIL** (${formatDuration(test.duration)})\n\n${test.message}`,
                        );
                        // Show error message as description for failed tests
                        this.description = `${formatDuration(test.duration)} - ${truncate(test.message, 60)}`;
                        break;
                    case 'SKIP':
                        this.iconPath = new vscode.ThemeIcon('debug-step-over', new vscode.ThemeColor('testing.iconSkipped'));
                        this.tooltip = `SKIP: ${test.message || 'Skipped'}`;
                        break;
                }

                // Navigate to source on click
                if (test.sourcePath) {
                    this.command = {
                        command: 'rfSkills.goToTestSource',
                        title: 'Go to Test Source',
                        arguments: [test.sourcePath, test.sourceLine],
                    };
                }
                break;
            }
        }
    }
}

// -- Utilities ---------------------------------------------------------------

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
    // Take only the first line
    const firstLine = text.split('\n')[0];
    if (firstLine.length <= maxLen) {
        return firstLine;
    }
    return firstLine.substring(0, maxLen - 3) + '...';
}

// -- Python Invoker ----------------------------------------------------------

/**
 * Invoke rf_results.py to parse an output.xml file and return structured data.
 * The Python script is expected to be in the plugin's scripts directory.
 */
async function parseOutputXml(
    pythonPath: string,
    scriptPath: string,
    outputXmlPath: string,
): Promise<ResultsSummary | null> {
    return new Promise((resolve) => {
        const cmd = `"${pythonPath}" "${scriptPath}" "${outputXmlPath}"`;
        exec(cmd, { maxBuffer: 10 * 1024 * 1024 }, (error, stdout, _stderr) => {
            if (error) {
                resolve(null);
                return;
            }
            try {
                const data = JSON.parse(stdout) as ResultsSummary;
                resolve(data);
            } catch {
                resolve(null);
            }
        });
    });
}

// -- Tree Data Provider ------------------------------------------------------

export class TestResultsProvider implements vscode.TreeDataProvider<TestTreeItem> {
    private readonly _onDidChangeTreeData = new vscode.EventEmitter<TestTreeItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private summary: ResultsSummary | null = null;
    private context: vscode.ExtensionContext | null = null;
    private fileWatcher: vscode.FileSystemWatcher | null = null;

    /** Call once during activation to bind the extension context. */
    initialize(context: vscode.ExtensionContext): void {
        this.context = context;
        this.setupFileWatcher(context);
    }

    /** Load results from a specific output.xml path. */
    async loadResults(outputXmlPath: string): Promise<void> {
        if (!this.context) {
            return;
        }

        const config = vscode.workspace.getConfiguration('rfSkills');
        const pythonPath = config.get<string>('pythonPath', 'python3');

        // Look for rf_results.py in the extension's scripts directory
        const scriptPath = path.join(this.context.extensionPath, 'scripts', 'rf_results.py');

        const data = await parseOutputXml(pythonPath, scriptPath, outputXmlPath);
        if (data) {
            this.summary = data;
            this._onDidChangeTreeData.fire();
        } else {
            vscode.window.showWarningMessage(
                `RF Skills: Could not parse ${path.basename(outputXmlPath)}. ` +
                'Ensure rf_results.py is available and output.xml is valid.',
            );
        }
    }

    /** Set results from already-parsed data (used by dashboard). */
    setResults(summary: ResultsSummary): void {
        this.summary = summary;
        this._onDidChangeTreeData.fire();
    }

    /** Get the current summary, if available. */
    getSummary(): ResultsSummary | null {
        return this.summary;
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: TestTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: TestTreeItem): TestTreeItem[] {
        if (!this.summary) {
            const placeholder = new vscode.TreeItem(
                'No test results loaded',
                vscode.TreeItemCollapsibleState.None,
            );
            placeholder.iconPath = new vscode.ThemeIcon('info');
            placeholder.description = 'Run tests or open output.xml';
            return [placeholder as unknown as TestTreeItem];
        }

        // Root level: top-level suites
        if (!element) {
            return this.summary.suites.map(suite => this.suiteToTreeItem(suite));
        }

        // Suite level: nested suites + tests
        if (element.kind === 'suite' && element.suiteData) {
            const children: TestTreeItem[] = [];

            // Nested suites first
            for (const childSuite of element.suiteData.suites) {
                children.push(this.suiteToTreeItem(childSuite));
            }

            // Then tests
            for (const test of element.suiteData.tests) {
                children.push(
                    new TestTreeItem(
                        'test',
                        test.name,
                        vscode.TreeItemCollapsibleState.None,
                        undefined,
                        test,
                    ),
                );
            }

            return children;
        }

        return [];
    }

    private suiteToTreeItem(suite: SuiteResult): TestTreeItem {
        const hasChildren = suite.suites.length > 0 || suite.tests.length > 0;
        return new TestTreeItem(
            'suite',
            suite.name,
            hasChildren
                ? vscode.TreeItemCollapsibleState.Expanded
                : vscode.TreeItemCollapsibleState.None,
            suite,
        );
    }

    private setupFileWatcher(context: vscode.ExtensionContext): void {
        // Watch for output.xml changes
        this.fileWatcher = vscode.workspace.createFileSystemWatcher('**/output.xml');

        this.fileWatcher.onDidChange(uri => {
            this.loadResults(uri.fsPath);
        });

        this.fileWatcher.onDidCreate(uri => {
            this.loadResults(uri.fsPath);
        });

        context.subscriptions.push(this.fileWatcher);
    }

    dispose(): void {
        this.fileWatcher?.dispose();
    }
}

// -- Command Registration Helpers -------------------------------------------

/**
 * Registers all commands related to the test results tree view.
 * Call once during extension activation.
 */
export function registerTestExplorerCommands(
    context: vscode.ExtensionContext,
    provider: TestResultsProvider,
): void {
    // Refresh results
    context.subscriptions.push(
        vscode.commands.registerCommand('rfSkills.refreshResults', () => {
            provider.refresh();
        }),
    );

    // Load results from file picker
    context.subscriptions.push(
        vscode.commands.registerCommand('rfSkills.loadResults', async () => {
            const uris = await vscode.window.showOpenDialog({
                canSelectMany: false,
                filters: { 'XML files': ['xml'] },
                openLabel: 'Load output.xml',
            });
            if (uris && uris.length > 0) {
                await provider.loadResults(uris[0].fsPath);
            }
        }),
    );

    // Navigate to test source
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'rfSkills.goToTestSource',
            async (filePath: string, line?: number) => {
                try {
                    const uri = vscode.Uri.file(filePath);
                    const doc = await vscode.workspace.openTextDocument(uri);
                    const lineNum = (line ?? 1) - 1;
                    const pos = new vscode.Position(Math.max(0, lineNum), 0);
                    await vscode.window.showTextDocument(doc, {
                        selection: new vscode.Range(pos, pos),
                    });
                } catch {
                    vscode.window.showWarningMessage(
                        `RF Skills: Could not open source file: ${filePath}`,
                    );
                }
            },
        ),
    );
}

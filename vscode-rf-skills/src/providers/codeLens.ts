import * as vscode from 'vscode';

const TEST_CASES_HEADER = /^\*{3}\s*Test\s*Cases?\s*\*{3}/i;
const KEYWORDS_HEADER = /^\*{3}\s*Keywords?\s*\*{3}/i;
const SECTION_HEADER = /^\*{3}\s*\w+/;

/**
 * Provides code lenses for running individual tests, full suites,
 * and displaying counts of tests/keywords in each section.
 */
export class RFCodeLensProvider implements vscode.CodeLensProvider {
    private readonly _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
    readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

    refresh(): void {
        this._onDidChangeCodeLenses.fire();
    }

    provideCodeLenses(
        document: vscode.TextDocument,
        _token: vscode.CancellationToken,
    ): vscode.CodeLens[] {
        const lenses: vscode.CodeLens[] = [];
        const lineCount = document.lineCount;

        let inTestCases = false;
        let inKeywords = false;
        let testCasesHeaderLine = -1;
        let keywordsHeaderLine = -1;
        let testCount = 0;
        let keywordCount = 0;
        const testNames: Array<{ name: string; line: number }> = [];
        const keywordNames: Array<{ name: string; line: number }> = [];

        for (let i = 0; i < lineCount; i++) {
            const lineText = document.lineAt(i).text;

            if (TEST_CASES_HEADER.test(lineText)) {
                inTestCases = true;
                inKeywords = false;
                testCasesHeaderLine = i;
                continue;
            }

            if (KEYWORDS_HEADER.test(lineText)) {
                inKeywords = true;
                inTestCases = false;
                keywordsHeaderLine = i;
                continue;
            }

            if (SECTION_HEADER.test(lineText)) {
                inTestCases = false;
                inKeywords = false;
                continue;
            }

            const trimmed = lineText.trimEnd();
            if (trimmed === '') {
                continue;
            }

            // A non-indented, non-comment line inside a section is a name
            const isName =
                trimmed.length > 0 &&
                !lineText.startsWith(' ') &&
                !lineText.startsWith('\t') &&
                !lineText.startsWith('#');

            if (!isName) {
                continue;
            }

            if (inTestCases) {
                testCount++;
                testNames.push({ name: trimmed, line: i });
            } else if (inKeywords) {
                keywordCount++;
                keywordNames.push({ name: trimmed, line: i });
            }
        }

        // -- Test Cases section header lenses --
        if (testCasesHeaderLine >= 0) {
            const headerRange = new vscode.Range(testCasesHeaderLine, 0, testCasesHeaderLine, 0);

            lenses.push(
                new vscode.CodeLens(headerRange, {
                    title: '$(play) Run Suite',
                    command: 'rfSkills.runSuite',
                    arguments: [document.uri],
                    tooltip: 'Run all tests in this file',
                }),
            );

            lenses.push(
                new vscode.CodeLens(headerRange, {
                    title: `${testCount} test${testCount !== 1 ? 's' : ''}`,
                    command: '',
                    tooltip: `${testCount} test case${testCount !== 1 ? 's' : ''} in this suite`,
                }),
            );
        }

        // -- Individual test case lenses --
        for (const test of testNames) {
            const testRange = new vscode.Range(test.line, 0, test.line, 0);

            lenses.push(
                new vscode.CodeLens(testRange, {
                    title: '$(play) Run',
                    command: 'rfSkills.runTest',
                    arguments: [document.uri, test.name],
                    tooltip: `Run "${test.name}"`,
                }),
            );

            lenses.push(
                new vscode.CodeLens(testRange, {
                    title: '$(debug-alt) Debug',
                    command: 'rfSkills.debugTest',
                    arguments: [document.uri, test.name],
                    tooltip: `Debug "${test.name}"`,
                }),
            );
        }

        // -- Keywords section header lenses --
        if (keywordsHeaderLine >= 0) {
            const headerRange = new vscode.Range(keywordsHeaderLine, 0, keywordsHeaderLine, 0);

            lenses.push(
                new vscode.CodeLens(headerRange, {
                    title: `${keywordCount} keyword${keywordCount !== 1 ? 's' : ''}`,
                    command: '',
                    tooltip: `${keywordCount} keyword${keywordCount !== 1 ? 's' : ''} in this file`,
                }),
            );
        }

        return lenses;
    }
}

/**
 * Registers the code lens provider and associated run/debug commands.
 */
export function registerCodeLens(context: vscode.ExtensionContext): void {
    const selector: vscode.DocumentSelector = { language: 'robotframework', scheme: 'file' };
    const provider = new RFCodeLensProvider();

    context.subscriptions.push(
        vscode.languages.registerCodeLensProvider(selector, provider),
    );

    // -- Run Suite command --
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'rfSkills.runSuite',
            async (fileUri?: vscode.Uri) => {
                const uri = fileUri ?? vscode.window.activeTextEditor?.document.uri;
                if (!uri) {
                    vscode.window.showWarningMessage('RF Skills: No Robot Framework file is open.');
                    return;
                }
                const task = createRobotTask('Run Suite', ['--loglevel', 'INFO', uri.fsPath]);
                await vscode.tasks.executeTask(task);
            },
        ),
    );

    // -- Run Test command --
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'rfSkills.runTest',
            async (fileUri?: vscode.Uri, testName?: string) => {
                const uri = fileUri ?? vscode.window.activeTextEditor?.document.uri;
                if (!uri || !testName) {
                    vscode.window.showWarningMessage('RF Skills: Cannot determine test to run.');
                    return;
                }
                const task = createRobotTask(`Run: ${testName}`, [
                    '--test', testName,
                    '--loglevel', 'INFO',
                    uri.fsPath,
                ]);
                await vscode.tasks.executeTask(task);
            },
        ),
    );

    // -- Debug Test command --
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'rfSkills.debugTest',
            async (fileUri?: vscode.Uri, testName?: string) => {
                const uri = fileUri ?? vscode.window.activeTextEditor?.document.uri;
                if (!uri || !testName) {
                    vscode.window.showWarningMessage('RF Skills: Cannot determine test to debug.');
                    return;
                }
                // Debug uses the same robot invocation but with --listener for debug support.
                // For now, run with verbose logging as a starting point.
                const task = createRobotTask(`Debug: ${testName}`, [
                    '--test', testName,
                    '--loglevel', 'DEBUG',
                    '--listener', 'RobotFramework:DEBUG',
                    uri.fsPath,
                ]);
                await vscode.tasks.executeTask(task);
            },
        ),
    );

    // Refresh lenses when config changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('rfSkills')) {
                provider.refresh();
            }
        }),
    );
}

/**
 * Creates a VS Code ShellExecution task for running robot.
 */
function createRobotTask(name: string, args: string[]): vscode.Task {
    const taskDefinition: vscode.TaskDefinition = { type: 'rfSkills' };
    const execution = new vscode.ShellExecution('robot', args);
    const task = new vscode.Task(
        taskDefinition,
        vscode.TaskScope.Workspace,
        name,
        'RF Skills',
        execution,
    );
    task.group = vscode.TaskGroup.Test;
    task.presentationOptions = {
        reveal: vscode.TaskRevealKind.Always,
        panel: vscode.TaskPanelKind.Shared,
        clear: true,
    };
    return task;
}

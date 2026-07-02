import * as vscode from 'vscode';
import { loadKeywordIndex } from './data/keywordIndex.js';
import { registerCodeActions } from './providers/codeActions.js';
import { registerCodeLens } from './providers/codeLens.js';
import { registerHover } from './providers/hover.js';
import { registerCompletion } from './providers/completion.js';
import { registerDiagnostics } from './providers/diagnostics.js';
import { createStatusBarItems } from './providers/statusBar.js';

// -- Command implementations (Python-backed) --------------------------------
import { registerSearchKeyword } from './commands/searchKeyword.js';
import { registerExplainKeyword } from './commands/explainKeyword.js';
import { registerGenerateKeyword } from './commands/generateKeyword.js';
import { registerGenerateTestCase } from './commands/generateTestCase.js';
import { registerScaffoldProject } from './commands/scaffoldProject.js';
import { registerAnalyzeResults } from './commands/analyzeResults.js';
import { registerCheckEnvironment } from './commands/checkEnvironment.js';
import { registerModernizeSyntax } from './commands/modernizeSyntax.js';

// -- Tree View Providers (full implementations) ------------------------------
import {
    KeywordBrowserProvider,
    registerKeywordBrowserCommands,
} from './views/keywordBrowser.js';
import {
    TestResultsProvider,
    registerTestExplorerCommands,
} from './views/testExplorer.js';

// -- File Watchers -----------------------------------------------------------

function createFileWatchers(context: vscode.ExtensionContext): void {
    // Watch .robot and .resource files
    const robotWatcher = vscode.workspace.createFileSystemWatcher('**/*.{robot,resource}');
    robotWatcher.onDidChange((_uri) => {
        // Placeholder: trigger diagnostics refresh when RobotCode is not installed.
    });
    context.subscriptions.push(robotWatcher);

    // Watch output.xml for test result updates
    const outputXmlWatcher = vscode.workspace.createFileSystemWatcher('**/output.xml');
    outputXmlWatcher.onDidChange((_uri) => {
        // Placeholder: refresh test results tree + status bar.
    });
    outputXmlWatcher.onDidCreate((_uri) => {
        // Placeholder: auto-open results dashboard if configured.
    });
    context.subscriptions.push(outputXmlWatcher);
}

// -- Activation & Deactivation -----------------------------------------------

export function activate(context: vscode.ExtensionContext): void {
    const outputChannel = vscode.window.createOutputChannel('RF Skills');
    outputChannel.appendLine('Robot Framework Skills extension is activating...');

    // Load keyword index for hover, completion, and other providers
    const keywordIndex = loadKeywordIndex(context);

    // Register commands (each module registers its own command and pushes to subscriptions)
    registerSearchKeyword(context);
    registerExplainKeyword(context);
    registerGenerateKeyword(context);
    registerGenerateTestCase(context);
    registerScaffoldProject(context);
    registerAnalyzeResults(context);
    registerCheckEnvironment(context);
    registerModernizeSyntax(context);

    // Register tree view providers (full implementations from views/)
    const keywordBrowserProvider = new KeywordBrowserProvider();
    keywordBrowserProvider.initialize(context);
    vscode.window.registerTreeDataProvider('rfSkills.keywordBrowser', keywordBrowserProvider);
    registerKeywordBrowserCommands(context, keywordBrowserProvider);

    const testResultsProvider = new TestResultsProvider();
    testResultsProvider.initialize(context);
    vscode.window.registerTreeDataProvider('rfSkills.testResults', testResultsProvider);
    registerTestExplorerCommands(context, testResultsProvider);

    // Register inline editor providers (from src/providers/)
    registerCodeActions(context);
    registerCodeLens(context);
    registerHover(context, keywordIndex);
    registerCompletion(context, keywordIndex);
    registerDiagnostics(context);

    // Create status bar items
    createStatusBarItems(context);

    // Set up file watchers
    createFileWatchers(context);

    // Run a lightweight environment check on activation (non-blocking).
    // We import the detector directly rather than triggering the full
    // user-facing command so that we can log silently.
    import('./python/detector.js').then(({ detectPythonEnvironment }) =>
        detectPythonEnvironment().then((env) => {
            if (env.rfVersion) {
                outputChannel.appendLine(`Detected RF ${env.rfVersion} (Python ${env.pythonVersion}).`);
            } else {
                outputChannel.appendLine('Robot Framework not detected. Some features will be limited.');
            }
        })
    ).catch(() => {
        // Silently ignore errors during initial environment probe.
    });

    outputChannel.appendLine('Robot Framework Skills extension activated successfully.');
}

export function deactivate(): void {
    // Clean-up handled by disposables in context.subscriptions.
}

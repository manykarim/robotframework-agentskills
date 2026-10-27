import * as vscode from 'vscode';

/**
 * Diagnostic patterns for deprecated Robot Framework syntax.
 * Each entry maps a regex to a severity and message.
 */
interface DiagnosticPattern {
    regex: RegExp;
    severity: vscode.DiagnosticSeverity;
    message: string;
    code: string;
}

const DIAGNOSTIC_PATTERNS: DiagnosticPattern[] = [
    {
        regex: /^\s*\[Return\]\s+/i,
        severity: vscode.DiagnosticSeverity.Warning,
        message: 'Use RETURN statement (RF7+)',
        code: 'rf-deprecated-return',
    },
    {
        regex: /^\s*Run Keyword If\s+/,
        severity: vscode.DiagnosticSeverity.Information,
        message: 'Consider using IF/END block (RF7+)',
        code: 'rf-deprecated-run-keyword-if',
    },
    {
        regex: /^\s*Run Keyword Unless\s+/,
        severity: vscode.DiagnosticSeverity.Information,
        message: 'Consider using IF NOT/END block (RF7+)',
        code: 'rf-deprecated-run-keyword-unless',
    },
    {
        regex: /^\s*:FOR\s+/i,
        severity: vscode.DiagnosticSeverity.Warning,
        message: 'Use FOR without colon prefix (RF7+)',
        code: 'rf-deprecated-colon-for',
    },
    {
        regex: /^\s*Set (Test|Suite|Global) Variable\s+/,
        severity: vscode.DiagnosticSeverity.Information,
        message: 'Consider using VAR with scope (RF7+)',
        code: 'rf-deprecated-set-variable',
    },
    {
        regex: /^\s*Sleep\s+/,
        severity: vscode.DiagnosticSeverity.Hint,
        message: 'Consider using a wait keyword instead of Sleep',
        code: 'rf-sleep-usage',
    },
];

/** File extensions that should be diagnosed. */
const RF_EXTENSIONS = new Set(['.robot', '.resource']);

/**
 * Manages diagnostics for deprecated Robot Framework syntax patterns.
 * Scans files on open and save, providing warnings/hints for patterns
 * that have modern RF7+ replacements.
 */
export class RFDiagnosticsManager {
    private readonly collection: vscode.DiagnosticCollection;
    private readonly disposables: vscode.Disposable[] = [];

    constructor() {
        this.collection = vscode.languages.createDiagnosticCollection('rfSkills');
    }

    /**
     * Activates the diagnostics manager by subscribing to document events.
     */
    activate(context: vscode.ExtensionContext): void {
        // Scan on open
        this.disposables.push(
            vscode.workspace.onDidOpenTextDocument((doc) => {
                this.updateDiagnostics(doc);
            }),
        );

        // Scan on save
        this.disposables.push(
            vscode.workspace.onDidSaveTextDocument((doc) => {
                this.updateDiagnostics(doc);
            }),
        );

        // Clear when document is closed
        this.disposables.push(
            vscode.workspace.onDidCloseTextDocument((doc) => {
                this.collection.delete(doc.uri);
            }),
        );

        // Scan on configuration change (re-run if enabled/disabled)
        this.disposables.push(
            vscode.workspace.onDidChangeConfiguration((e) => {
                if (e.affectsConfiguration('rfSkills.diagnostics.enabled')) {
                    this.refreshAll();
                }
            }),
        );

        // Register disposables
        context.subscriptions.push(this.collection);
        for (const d of this.disposables) {
            context.subscriptions.push(d);
        }

        // Scan all currently open RF documents
        for (const doc of vscode.workspace.textDocuments) {
            this.updateDiagnostics(doc);
        }
    }

    /**
     * Force a refresh of diagnostics for all open documents.
     */
    refreshAll(): void {
        this.collection.clear();
        for (const doc of vscode.workspace.textDocuments) {
            this.updateDiagnostics(doc);
        }
    }

    /**
     * Scans a single document and updates its diagnostic entries.
     */
    private updateDiagnostics(document: vscode.TextDocument): void {
        if (!this.isRobotFile(document)) {
            return;
        }

        const config = vscode.workspace.getConfiguration('rfSkills');
        const enabled = config.get<boolean>('diagnostics.enabled', true);
        if (!enabled) {
            this.collection.delete(document.uri);
            return;
        }

        const diagnostics: vscode.Diagnostic[] = [];

        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i);
            const lineText = line.text;

            for (const pattern of DIAGNOSTIC_PATTERNS) {
                const match = pattern.regex.exec(lineText);
                if (match) {
                    // Highlight from the start of the matched keyword to end of line
                    const matchStart = lineText.search(/\S/); // first non-whitespace
                    const range = new vscode.Range(
                        i,
                        matchStart >= 0 ? matchStart : 0,
                        i,
                        lineText.length,
                    );

                    const diagnostic = new vscode.Diagnostic(
                        range,
                        pattern.message,
                        pattern.severity,
                    );
                    diagnostic.code = {
                        value: pattern.code,
                        target: vscode.Uri.parse(
                            'https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html',
                        ),
                    };
                    diagnostic.source = 'RF Skills';
                    diagnostics.push(diagnostic);
                }
            }
        }

        this.collection.set(document.uri, diagnostics);
    }

    /**
     * Checks whether a document is a Robot Framework file.
     */
    private isRobotFile(document: vscode.TextDocument): boolean {
        if (document.languageId === 'robotframework') {
            return true;
        }
        // Fallback: check file extension
        const ext = document.uri.fsPath.substring(
            document.uri.fsPath.lastIndexOf('.'),
        );
        return RF_EXTENSIONS.has(ext.toLowerCase());
    }
}

/**
 * Creates, activates, and returns the diagnostics manager.
 */
export function registerDiagnostics(context: vscode.ExtensionContext): RFDiagnosticsManager {
    const manager = new RFDiagnosticsManager();
    manager.activate(context);
    return manager;
}

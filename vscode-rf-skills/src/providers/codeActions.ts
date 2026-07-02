import * as vscode from 'vscode';

/**
 * Provides code actions for migrating deprecated Robot Framework syntax
 * to modern RF7+ equivalents (RETURN, IF/END, FOR, VAR).
 */
export class RFCodeActionProvider implements vscode.CodeActionProvider {
    static readonly providedCodeActionKinds = [
        vscode.CodeActionKind.QuickFix,
        vscode.CodeActionKind.RefactorRewrite,
    ];

    provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        _context: vscode.CodeActionContext,
        _token: vscode.CancellationToken,
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        // Process each line in the range (or selection)
        const startLine = range.start.line;
        const endLine = range.end.line;

        for (let lineNum = startLine; lineNum <= endLine; lineNum++) {
            const line = document.lineAt(lineNum);
            const lineText = line.text;

            actions.push(
                ...this.checkReturnStatement(document, line, lineText),
                ...this.checkRunKeywordIf(document, line, lineText),
                ...this.checkRunKeywordUnless(document, line, lineText),
                ...this.checkColonFor(document, line, lineText),
                ...this.checkSetVariable(document, line, lineText),
                ...this.checkSleep(document, line, lineText),
            );
        }

        // Check for missing [Documentation] across the entire visible range
        actions.push(...this.checkMissingDocumentation(document, range));

        return actions;
    }

    // -- Pattern 1: [Return] -> RETURN -------------------------------------------

    private checkReturnStatement(
        document: vscode.TextDocument,
        line: vscode.TextLine,
        lineText: string,
    ): vscode.CodeAction[] {
        const match = lineText.match(/^(\s*)\[Return\]\s+(.*)/i);
        if (!match) {
            return [];
        }

        const indent = match[1];
        const value = match[2];
        const action = new vscode.CodeAction(
            'Migrate to RETURN statement (RF7+)',
            vscode.CodeActionKind.RefactorRewrite,
        );
        action.edit = new vscode.WorkspaceEdit();
        action.edit.replace(
            document.uri,
            line.range,
            `${indent}RETURN    ${value}`,
        );
        action.isPreferred = true;
        return [action];
    }

    // -- Pattern 2: Run Keyword If -> IF/END -------------------------------------

    private checkRunKeywordIf(
        document: vscode.TextDocument,
        line: vscode.TextLine,
        lineText: string,
    ): vscode.CodeAction[] {
        const match = lineText.match(/^(\s*)Run Keyword If\s+(.+?)\s{2,}(\S+.*)/);
        if (!match) {
            return [];
        }

        const indent = match[1];
        const condition = match[2];
        const keywordAndArgs = match[3];
        const action = new vscode.CodeAction(
            'Migrate to IF/END block (RF7+)',
            vscode.CodeActionKind.RefactorRewrite,
        );
        action.edit = new vscode.WorkspaceEdit();
        const replacement = [
            `${indent}IF    ${condition}`,
            `${indent}    ${keywordAndArgs}`,
            `${indent}END`,
        ].join('\n');
        action.edit.replace(document.uri, line.range, replacement);
        action.isPreferred = true;
        return [action];
    }

    // -- Pattern 3: Run Keyword Unless -> IF NOT/END -----------------------------

    private checkRunKeywordUnless(
        document: vscode.TextDocument,
        line: vscode.TextLine,
        lineText: string,
    ): vscode.CodeAction[] {
        const match = lineText.match(/^(\s*)Run Keyword Unless\s+(.+?)\s{2,}(\S+.*)/);
        if (!match) {
            return [];
        }

        const indent = match[1];
        const condition = match[2];
        const keywordAndArgs = match[3];
        const action = new vscode.CodeAction(
            'Migrate to IF NOT/END block (RF7+)',
            vscode.CodeActionKind.RefactorRewrite,
        );
        action.edit = new vscode.WorkspaceEdit();
        const replacement = [
            `${indent}IF    not ${condition}`,
            `${indent}    ${keywordAndArgs}`,
            `${indent}END`,
        ].join('\n');
        action.edit.replace(document.uri, line.range, replacement);
        action.isPreferred = true;
        return [action];
    }

    // -- Pattern 4: :FOR -> FOR --------------------------------------------------

    private checkColonFor(
        document: vscode.TextDocument,
        line: vscode.TextLine,
        lineText: string,
    ): vscode.CodeAction[] {
        const match = lineText.match(/^(\s*):FOR\s+(.*)/i);
        if (!match) {
            return [];
        }

        const indent = match[1];
        const rest = match[2];
        const action = new vscode.CodeAction(
            'Remove colon prefix from FOR (RF7+)',
            vscode.CodeActionKind.RefactorRewrite,
        );
        action.edit = new vscode.WorkspaceEdit();
        action.edit.replace(
            document.uri,
            line.range,
            `${indent}FOR    ${rest}`,
        );
        action.isPreferred = true;
        return [action];
    }

    // -- Pattern 5: Set Test/Suite/Global Variable -> VAR with scope -------------

    private checkSetVariable(
        document: vscode.TextDocument,
        line: vscode.TextLine,
        lineText: string,
    ): vscode.CodeAction[] {
        const match = lineText.match(
            /^(\s*)Set (Test|Suite|Global) Variable\s+(\$\{[^}]+\})\s+(.*)/,
        );
        if (!match) {
            return [];
        }

        const indent = match[1];
        const scope = match[2].toUpperCase();
        const varName = match[3];
        const value = match[4];
        const action = new vscode.CodeAction(
            `Migrate to VAR with scope=${scope} (RF7+)`,
            vscode.CodeActionKind.RefactorRewrite,
        );
        action.edit = new vscode.WorkspaceEdit();
        action.edit.replace(
            document.uri,
            line.range,
            `${indent}VAR    ${varName}    ${value}    scope=${scope}`,
        );
        action.isPreferred = true;
        return [action];
    }

    // -- Pattern 6: Sleep -> Warning with suggestion -----------------------------

    private checkSleep(
        document: vscode.TextDocument,
        line: vscode.TextLine,
        lineText: string,
    ): vscode.CodeAction[] {
        const match = lineText.match(/^(\s*)Sleep\s+(.*)/);
        if (!match) {
            return [];
        }

        const indent = match[1];
        const action = new vscode.CodeAction(
            'Replace with Wait Until Keyword Succeeds',
            vscode.CodeActionKind.QuickFix,
        );
        action.edit = new vscode.WorkspaceEdit();
        action.edit.replace(
            document.uri,
            line.range,
            `${indent}Wait Until Keyword Succeeds    3x    1s    Log    Replace this with actual keyword`,
        );
        action.diagnostics = [
            new vscode.Diagnostic(
                line.range,
                'Consider using a wait keyword instead of Sleep',
                vscode.DiagnosticSeverity.Hint,
            ),
        ];
        return [action];
    }

    // -- Pattern 7: Missing [Documentation] --------------------------------------

    private checkMissingDocumentation(
        document: vscode.TextDocument,
        range: vscode.Range,
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];
        const text = document.getText();
        const lines = text.split('\n');

        // Find test case and keyword block boundaries
        const blocks = this.findBlocks(lines);

        for (const block of blocks) {
            // Only offer the action if the block header is within the requested range
            if (block.nameLineNum < range.start.line || block.nameLineNum > range.end.line) {
                continue;
            }

            if (!block.hasDocumentation) {
                const action = new vscode.CodeAction(
                    `Add [Documentation] to "${block.name}"`,
                    vscode.CodeActionKind.RefactorRewrite,
                );
                action.edit = new vscode.WorkspaceEdit();
                const insertPosition = new vscode.Position(block.nameLineNum + 1, 0);
                action.edit.insert(
                    document.uri,
                    insertPosition,
                    '    [Documentation]    TODO: Add documentation\n',
                );
                actions.push(action);
            }
        }

        return actions;
    }

    private findBlocks(
        lines: string[],
    ): Array<{ name: string; nameLineNum: number; hasDocumentation: boolean }> {
        const blocks: Array<{ name: string; nameLineNum: number; hasDocumentation: boolean }> = [];
        let inTestCases = false;
        let inKeywords = false;

        const testCasesHeader = /^\*{3}\s*Test\s*Cases?\s*\*{3}/i;
        const keywordsHeader = /^\*{3}\s*Keywords?\s*\*{3}/i;
        const sectionHeader = /^\*{3}\s*\w+/;

        let currentBlockName: string | null = null;
        let currentBlockLine = -1;
        let currentHasDoc = false;

        const flushBlock = (): void => {
            if (currentBlockName !== null) {
                blocks.push({
                    name: currentBlockName,
                    nameLineNum: currentBlockLine,
                    hasDocumentation: currentHasDoc,
                });
            }
            currentBlockName = null;
            currentBlockLine = -1;
            currentHasDoc = false;
        };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            if (testCasesHeader.test(line)) {
                flushBlock();
                inTestCases = true;
                inKeywords = false;
                continue;
            }
            if (keywordsHeader.test(line)) {
                flushBlock();
                inKeywords = true;
                inTestCases = false;
                continue;
            }
            if (sectionHeader.test(line)) {
                flushBlock();
                inTestCases = false;
                inKeywords = false;
                continue;
            }

            if (!inTestCases && !inKeywords) {
                continue;
            }

            const trimmed = line.trimEnd();
            if (trimmed === '') {
                continue;
            }

            // Non-indented, non-empty line is a test case or keyword name
            if (trimmed.length > 0 && !line.startsWith(' ') && !line.startsWith('\t') && !line.startsWith('#')) {
                flushBlock();
                currentBlockName = trimmed;
                currentBlockLine = i;
                currentHasDoc = false;
                continue;
            }

            // Indented line inside a block: check for [Documentation]
            if (currentBlockName !== null && /^\s+\[Documentation\]/i.test(line)) {
                currentHasDoc = true;
            }
        }

        flushBlock();
        return blocks;
    }
}

/**
 * Registers the RF code action provider and returns the disposable.
 */
export function registerCodeActions(context: vscode.ExtensionContext): void {
    const selector: vscode.DocumentSelector = { language: 'robotframework', scheme: 'file' };
    context.subscriptions.push(
        vscode.languages.registerCodeActionsProvider(
            selector,
            new RFCodeActionProvider(),
            { providedCodeActionKinds: RFCodeActionProvider.providedCodeActionKinds },
        ),
    );
}

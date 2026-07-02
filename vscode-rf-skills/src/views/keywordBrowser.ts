import * as vscode from 'vscode';
import {
    loadKeywordIndex,
    reloadKeywordIndex,
    searchKeywords,
    formatArgSignature,
    type KeywordIndex,
    type Library,
    type Category,
    type Keyword,
} from '../data/keywordIndex.js';

// -- Tree Item Types ---------------------------------------------------------

type KeywordTreeItemKind = 'library' | 'category' | 'keyword';

export class KeywordTreeItem extends vscode.TreeItem {
    constructor(
        public readonly kind: KeywordTreeItemKind,
        label: string,
        collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly libraryData?: Library,
        public readonly categoryData?: Category,
        public readonly keywordData?: Keyword,
    ) {
        super(label, collapsibleState);

        switch (kind) {
            case 'library':
                this.iconPath = new vscode.ThemeIcon('library');
                this.contextValue = 'rfKeywordLibrary';
                this.tooltip = `${label} (${libraryData?.version ?? ''})`;
                break;

            case 'category':
                this.iconPath = new vscode.ThemeIcon('symbol-class');
                this.contextValue = 'rfKeywordCategory';
                this.tooltip = `${label} (${categoryData?.keywords.length ?? 0} keywords)`;
                break;

            case 'keyword': {
                this.iconPath = new vscode.ThemeIcon('symbol-method');
                this.contextValue = 'rfKeyword';
                const kw = keywordData!;
                const sig = formatArgSignature(kw);
                this.description = sig ? `(${sig})` : '';
                this.tooltip = new vscode.MarkdownString(
                    `**${kw.name}**${sig ? `  \n\`${sig}\`` : ''}\n\n${kw.shortDoc}`,
                );
                // Single-click shows documentation in output channel
                this.command = {
                    command: 'rfSkills.showKeywordDoc',
                    title: 'Show Keyword Documentation',
                    arguments: [kw, libraryData],
                };
                break;
            }
        }
    }
}

// -- Tree Data Provider ------------------------------------------------------

export class KeywordBrowserProvider implements vscode.TreeDataProvider<KeywordTreeItem> {
    private readonly _onDidChangeTreeData = new vscode.EventEmitter<KeywordTreeItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private index: KeywordIndex | null = null;
    private filterQuery = '';
    private context: vscode.ExtensionContext | null = null;

    /** Call once during activation to bind the extension context. */
    initialize(context: vscode.ExtensionContext): void {
        this.context = context;
        this.index = loadKeywordIndex(context);
    }

    refresh(): void {
        if (this.context) {
            this.index = reloadKeywordIndex(this.context);
        }
        this._onDidChangeTreeData.fire();
    }

    /** Apply a text filter. Pass empty string to clear. */
    setFilter(query: string): void {
        this.filterQuery = query;
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: KeywordTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: KeywordTreeItem): KeywordTreeItem[] {
        if (!this.index) {
            return [];
        }

        // If a filter is active, show flat search results
        if (this.filterQuery && !element) {
            return this.getFilteredResults();
        }

        // Root level: libraries
        if (!element) {
            return this.index.libraries.map(
                lib =>
                    new KeywordTreeItem(
                        'library',
                        lib.name,
                        vscode.TreeItemCollapsibleState.Collapsed,
                        lib,
                    ),
            );
        }

        // Library level: categories
        if (element.kind === 'library' && element.libraryData) {
            return element.libraryData.categories.map(
                cat =>
                    new KeywordTreeItem(
                        'category',
                        cat.name,
                        vscode.TreeItemCollapsibleState.Collapsed,
                        element.libraryData,
                        cat,
                    ),
            );
        }

        // Category level: keywords
        if (element.kind === 'category' && element.categoryData) {
            return element.categoryData.keywords.map(
                kw =>
                    new KeywordTreeItem(
                        'keyword',
                        kw.name,
                        vscode.TreeItemCollapsibleState.None,
                        element.libraryData,
                        element.categoryData,
                        kw,
                    ),
            );
        }

        return [];
    }

    private getFilteredResults(): KeywordTreeItem[] {
        if (!this.index) {
            return [];
        }

        const results = searchKeywords(this.index, this.filterQuery);
        return results.map(
            r =>
                new KeywordTreeItem(
                    'keyword',
                    `${r.keyword.name}  [${r.library.name}]`,
                    vscode.TreeItemCollapsibleState.None,
                    r.library,
                    r.category,
                    r.keyword,
                ),
        );
    }
}

// -- Command Registration Helpers -------------------------------------------

/**
 * Registers all commands related to the keyword browser tree view.
 * Call once during extension activation.
 */
export function registerKeywordBrowserCommands(
    context: vscode.ExtensionContext,
    provider: KeywordBrowserProvider,
): void {
    // Refresh tree
    context.subscriptions.push(
        vscode.commands.registerCommand('rfSkills.refreshKeywords', () => {
            provider.refresh();
        }),
    );

    // Filter/search keywords
    context.subscriptions.push(
        vscode.commands.registerCommand('rfSkills.filterKeywords', async () => {
            const query = await vscode.window.showInputBox({
                placeHolder: 'Type to filter keywords (e.g. "click", "browser", "api")...',
                prompt: 'Search keyword names, descriptions, and tags',
            });
            if (query !== undefined) {
                provider.setFilter(query);
            }
        }),
    );

    // Clear filter
    context.subscriptions.push(
        vscode.commands.registerCommand('rfSkills.clearKeywordFilter', () => {
            provider.setFilter('');
        }),
    );

    // Show keyword documentation (single click handler)
    const outputChannel = vscode.window.createOutputChannel('RF Keyword Docs');
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'rfSkills.showKeywordDoc',
            (keyword: Keyword, library?: Library) => {
                outputChannel.clear();
                outputChannel.appendLine(`=== ${keyword.name} ===`);
                if (library) {
                    outputChannel.appendLine(`Library: ${library.name} ${library.version}`);
                }
                outputChannel.appendLine('');

                if (keyword.args.length > 0) {
                    outputChannel.appendLine('Arguments:');
                    for (const arg of keyword.args) {
                        const req = arg.required === false ? '(optional)' : '';
                        const def = arg.default ? ` = ${arg.default}` : '';
                        const typ = arg.type ? ` [${arg.type}]` : '';
                        outputChannel.appendLine(`  ${arg.name}${typ}${def} ${req}`);
                    }
                    outputChannel.appendLine('');
                }

                outputChannel.appendLine(keyword.doc || keyword.shortDoc);

                if (keyword.tags.length > 0) {
                    outputChannel.appendLine('');
                    outputChannel.appendLine(`Tags: ${keyword.tags.join(', ')}`);
                }

                if (keyword.deprecated) {
                    outputChannel.appendLine('');
                    outputChannel.appendLine('WARNING: This keyword is deprecated.');
                }

                outputChannel.show(true);
            },
        ),
    );

    // Insert keyword call at cursor (double-click / explicit command)
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'rfSkills.insertKeyword',
            (item: KeywordTreeItem) => {
                const editor = vscode.window.activeTextEditor;
                if (!editor || !item.keywordData) {
                    return;
                }

                const kw = item.keywordData;
                const args = kw.args
                    .map(arg => {
                        if (arg.default) {
                            return `${arg.name}=${arg.default}`;
                        }
                        return `\${${arg.name}}`;
                    })
                    .join('    ');

                const text = args ? `${kw.name}    ${args}` : kw.name;

                editor.edit(editBuilder => {
                    editBuilder.insert(editor.selection.active, text);
                });
            },
        ),
    );
}

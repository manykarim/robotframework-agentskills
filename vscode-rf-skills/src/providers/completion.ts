import * as vscode from 'vscode';
import type { KeywordIndex, Keyword, Library, Category } from '../data/keywordIndex.js';

const TEST_CASES_HEADER = /^\*{3}\s*Test\s*Cases?\s*\*{3}/i;
const KEYWORDS_HEADER = /^\*{3}\s*Keywords?\s*\*{3}/i;
const SETTINGS_HEADER = /^\*{3}\s*Settings?\s*\*{3}/i;
const SECTION_HEADER = /^\*{3}\s*\w+/;

/**
 * Well-known Robot Framework library names offered when the user types
 * after `Library    ` in a Settings section.
 */
const KNOWN_LIBRARIES = [
    { name: 'Browser', description: 'Playwright-based browser automation' },
    { name: 'SeleniumLibrary', description: 'Selenium-based browser automation' },
    { name: 'AppiumLibrary', description: 'Mobile testing with Appium' },
    { name: 'RequestsLibrary', description: 'HTTP API testing with Requests' },
    { name: 'REST', description: 'RESTful API testing (RESTinstance)' },
    { name: 'BuiltIn', description: 'Robot Framework built-in keywords' },
    { name: 'Collections', description: 'List and dictionary operations' },
    { name: 'String', description: 'String manipulation keywords' },
    { name: 'OperatingSystem', description: 'OS-level file and process keywords' },
    { name: 'Process', description: 'Process execution and management' },
];

/**
 * Provides completions for keyword names, library imports, and
 * keyword argument placeholders in Robot Framework files.
 */
export class RFCompletionProvider implements vscode.CompletionItemProvider {
    /** Flat list of all keywords with their library info */
    private entries: Array<{
        keyword: Keyword;
        library: Library;
        category: Category;
    }> = [];

    /** Lowercase keyword name -> entry for argument lookup */
    private byName = new Map<string, { keyword: Keyword; library: Library }>();

    constructor(index: KeywordIndex) {
        this.buildEntries(index);
    }

    updateIndex(index: KeywordIndex): void {
        this.entries = [];
        this.byName.clear();
        this.buildEntries(index);
    }

    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        _token: vscode.CancellationToken,
        _context: vscode.CompletionContext,
    ): vscode.CompletionItem[] | undefined {
        const lineText = document.lineAt(position.line).text;
        const section = this.currentSection(document, position.line);

        // -- Library name completion in Settings section --
        if (section === 'settings') {
            return this.libraryCompletions(lineText, position);
        }

        // -- Keyword body completions (test cases / keywords sections) --
        if (section === 'testcases' || section === 'keywords') {
            // Only complete on indented lines
            if (!lineText.startsWith(' ') && !lineText.startsWith('\t')) {
                return undefined;
            }

            const trimmed = lineText.substring(0, position.character).trimStart();

            // Check if cursor is past a keyword name (argument position)
            const argCompletions = this.argumentCompletions(trimmed, position);
            if (argCompletions && argCompletions.length > 0) {
                return argCompletions;
            }

            // Otherwise, offer keyword name completions
            return this.keywordCompletions(trimmed);
        }

        return undefined;
    }

    // -- Keyword name completions ------------------------------------------------

    private keywordCompletions(prefix: string): vscode.CompletionItem[] {
        const lowerPrefix = prefix.toLowerCase();

        return this.entries
            .filter((e) => e.keyword.name.toLowerCase().startsWith(lowerPrefix))
            .slice(0, 50) // limit for performance
            .map((e) => {
                const item = new vscode.CompletionItem(
                    e.keyword.name,
                    vscode.CompletionItemKind.Function,
                );
                item.detail = e.library.name;
                item.documentation = new vscode.MarkdownString(e.keyword.shortDoc);

                // Build snippet with argument placeholders
                const snippetParts = [e.keyword.name];
                let tabStop = 1;
                for (const arg of e.keyword.args) {
                    if (arg.required !== false || arg.default === undefined || arg.default === '') {
                        const placeholder = arg.default && arg.default !== '' ? arg.default : arg.name;
                        snippetParts.push(`\${${tabStop}:${placeholder}}`);
                        tabStop++;
                    }
                }
                item.insertText = new vscode.SnippetString(
                    snippetParts.join('    '),
                );

                // Sort: exact prefix match first
                const isExact = e.keyword.name.toLowerCase().startsWith(lowerPrefix);
                item.sortText = isExact ? `0_${e.keyword.name}` : `1_${e.keyword.name}`;

                if (e.keyword.deprecated) {
                    item.tags = [vscode.CompletionItemTag.Deprecated];
                }

                return item;
            });
    }

    // -- Argument completions (after a known keyword) ----------------------------

    private argumentCompletions(
        linePrefix: string,
        position: vscode.Position,
    ): vscode.CompletionItem[] | undefined {
        // Split line on 2+ spaces to find the keyword portion
        const parts = linePrefix.split(/\s{2,}/);
        if (parts.length < 2) {
            return undefined;
        }

        const keywordName = parts[0].trim();
        const entry = this.byName.get(keywordName.toLowerCase());
        if (!entry) {
            return undefined;
        }

        // Determine which argument index we are at (parts.length - 1 gives arg position)
        const argIndex = parts.length - 2; // -1 for keyword, -1 for 0-based

        return entry.keyword.args.map((arg, i) => {
            const item = new vscode.CompletionItem(
                arg.name,
                vscode.CompletionItemKind.Variable,
            );
            item.detail = `Argument ${i + 1} of ${entry.keyword.name}`;
            const docParts: string[] = [];
            if (arg.type) {
                docParts.push(`Type: \`${arg.type}\``);
            }
            if (arg.default !== undefined && arg.default !== '') {
                docParts.push(`Default: \`${arg.default}\``);
            }
            if (arg.required) {
                docParts.push('**Required**');
            }
            item.documentation = new vscode.MarkdownString(docParts.join(' | '));
            item.sortText = String(i).padStart(3, '0');

            // Highlight the current positional arg
            if (i === argIndex) {
                item.preselect = true;
            }

            return item;
        });
    }

    // -- Library name completions in Settings ------------------------------------

    private libraryCompletions(
        lineText: string,
        position: vscode.Position,
    ): vscode.CompletionItem[] | undefined {
        // Check if line matches `Library    <cursor>`
        const match = lineText.match(/^(\s*)Library\s{2,}/i);
        if (!match) {
            return undefined;
        }

        // Only complete if cursor is past the "Library    " prefix
        const prefixEnd = match[0].length;
        if (position.character < prefixEnd) {
            return undefined;
        }

        const typed = lineText.substring(prefixEnd, position.character).trim().toLowerCase();

        return KNOWN_LIBRARIES
            .filter((lib) => lib.name.toLowerCase().startsWith(typed))
            .map((lib) => {
                const item = new vscode.CompletionItem(
                    lib.name,
                    vscode.CompletionItemKind.Module,
                );
                item.detail = lib.description;
                item.documentation = new vscode.MarkdownString(
                    `Import the **${lib.name}** library.`,
                );
                return item;
            });
    }

    // -- Section detection -------------------------------------------------------

    private currentSection(
        document: vscode.TextDocument,
        lineNum: number,
    ): 'settings' | 'testcases' | 'keywords' | 'other' {
        for (let i = lineNum; i >= 0; i--) {
            const text = document.lineAt(i).text;
            if (SECTION_HEADER.test(text)) {
                if (SETTINGS_HEADER.test(text)) {
                    return 'settings';
                }
                if (TEST_CASES_HEADER.test(text)) {
                    return 'testcases';
                }
                if (KEYWORDS_HEADER.test(text)) {
                    return 'keywords';
                }
                return 'other';
            }
        }
        return 'other';
    }

    // -- Index building ----------------------------------------------------------

    private buildEntries(index: KeywordIndex): void {
        for (const library of index.libraries) {
            for (const category of library.categories) {
                for (const keyword of category.keywords) {
                    this.entries.push({ keyword, library, category });
                    this.byName.set(keyword.name.toLowerCase(), { keyword, library });
                }
            }
        }
    }
}

/**
 * Registers the completion provider.
 */
export function registerCompletion(
    context: vscode.ExtensionContext,
    index: KeywordIndex,
): RFCompletionProvider {
    const selector: vscode.DocumentSelector = { language: 'robotframework', scheme: 'file' };
    const provider = new RFCompletionProvider(index);

    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            selector,
            provider,
            ' ', // trigger on space (for keyword arguments)
        ),
    );

    return provider;
}

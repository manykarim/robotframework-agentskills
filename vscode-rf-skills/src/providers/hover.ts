import * as vscode from 'vscode';
import type { KeywordIndex, Keyword, Library, Category } from '../data/keywordIndex.js';

const SECTION_HEADER = /^\*{3}\s*\w+/;
const TEST_CASES_HEADER = /^\*{3}\s*Test\s*Cases?\s*\*{3}/i;
const KEYWORDS_HEADER = /^\*{3}\s*Keywords?\s*\*{3}/i;
const SETTINGS_HEADER = /^\*{3}\s*Settings?\s*\*{3}/i;

/**
 * Provides hover documentation for Robot Framework keywords
 * by looking them up in the static keyword index.
 */
export class RFHoverProvider implements vscode.HoverProvider {
    /** Flat lookup: lowercase keyword name -> { keyword, library, category } */
    private readonly lookup = new Map<
        string,
        { keyword: Keyword; library: Library; category: Category }
    >();

    constructor(index: KeywordIndex) {
        this.buildLookup(index);
    }

    /**
     * Rebuild the flat lookup when the index is reloaded.
     */
    updateIndex(index: KeywordIndex): void {
        this.lookup.clear();
        this.buildLookup(index);
    }

    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        _token: vscode.CancellationToken,
    ): vscode.ProviderResult<vscode.Hover> {
        // Only provide hovers inside Test Cases or Keywords body lines
        if (!this.isInsideBody(document, position.line)) {
            return null;
        }

        const lineText = document.lineAt(position.line).text;

        // Body lines are indented; extract the keyword name
        // RF separates keyword from arguments with 2+ spaces or tab
        const trimmedLine = lineText.replace(/^\s+/, '');
        if (trimmedLine === '' || trimmedLine.startsWith('#') || trimmedLine.startsWith('[')) {
            return null;
        }

        // Split on 2+ spaces or tab to separate keyword from arguments
        const parts = trimmedLine.split(/\s{2,}|\t/);
        const keywordName = parts[0].trim();
        if (!keywordName) {
            return null;
        }

        // Check if the cursor is within the keyword name portion of the line
        const keywordStart = lineText.indexOf(keywordName);
        const keywordEnd = keywordStart + keywordName.length;
        if (position.character < keywordStart || position.character > keywordEnd) {
            return null;
        }

        const entry = this.lookup.get(keywordName.toLowerCase());
        if (!entry) {
            return null;
        }

        const { keyword, library } = entry;
        const md = this.buildMarkdown(keyword, library);
        const hoverRange = new vscode.Range(
            position.line,
            keywordStart,
            position.line,
            keywordEnd,
        );

        return new vscode.Hover(md, hoverRange);
    }

    // -- Private helpers ---------------------------------------------------------

    private buildLookup(index: KeywordIndex): void {
        for (const library of index.libraries) {
            for (const category of library.categories) {
                for (const keyword of category.keywords) {
                    this.lookup.set(keyword.name.toLowerCase(), {
                        keyword,
                        library,
                        category,
                    });
                }
            }
        }
    }

    private buildMarkdown(keyword: Keyword, library: Library): vscode.MarkdownString {
        const md = new vscode.MarkdownString();
        md.isTrusted = true;
        md.supportHtml = true;

        // Keyword name (bold) and library (italic)
        md.appendMarkdown(`**${keyword.name}**\n\n`);
        md.appendMarkdown(`*${library.name}*\n\n`);

        // Arguments table
        if (keyword.args.length > 0) {
            md.appendMarkdown('| Argument | Type | Default |\n');
            md.appendMarkdown('|----------|------|---------|\n');
            for (const arg of keyword.args) {
                const type = arg.type ?? '';
                const def = arg.default !== undefined && arg.default !== '' ? arg.default : '';
                const required = arg.required ? ' **(required)**' : '';
                md.appendMarkdown(`| \`${arg.name}\`${required} | ${type} | ${def} |\n`);
            }
            md.appendMarkdown('\n');
        }

        // Short documentation
        if (keyword.shortDoc) {
            md.appendMarkdown(`${keyword.shortDoc}\n\n`);
        }

        // Tags
        if (keyword.tags.length > 0) {
            md.appendMarkdown(`Tags: ${keyword.tags.map(t => `\`${t}\``).join(', ')}\n\n`);
        }

        // Deprecation warning
        if (keyword.deprecated) {
            md.appendMarkdown('**Deprecated**\n\n');
        }

        // Full docs link via command URI
        const encodedName = encodeURIComponent(keyword.name);
        const commandUri = `command:rfSkills.explainKeyword?${encodeURIComponent(JSON.stringify(encodedName))}`;
        md.appendMarkdown(`[Full docs](${commandUri})`);

        return md;
    }

    /**
     * Determines whether a given line number is inside a Test Cases or Keywords
     * body section (i.e., an indented line under one of those headers).
     */
    private isInsideBody(document: vscode.TextDocument, lineNum: number): boolean {
        const lineText = document.lineAt(lineNum).text;

        // Must be indented to be a body line
        if (lineText.length > 0 && !lineText.startsWith(' ') && !lineText.startsWith('\t')) {
            return false;
        }

        // Walk backward to find the current section
        for (let i = lineNum; i >= 0; i--) {
            const text = document.lineAt(i).text;
            if (SECTION_HEADER.test(text)) {
                return TEST_CASES_HEADER.test(text) ||
                       KEYWORDS_HEADER.test(text);
            }
        }

        return false;
    }
}

/**
 * Registers the hover provider and returns the disposable.
 */
export function registerHover(
    context: vscode.ExtensionContext,
    index: KeywordIndex,
): RFHoverProvider {
    const selector: vscode.DocumentSelector = { language: 'robotframework', scheme: 'file' };
    const provider = new RFHoverProvider(index);

    context.subscriptions.push(
        vscode.languages.registerHoverProvider(selector, provider),
    );

    return provider;
}

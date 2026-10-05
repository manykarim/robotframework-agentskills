import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

// -- Types -------------------------------------------------------------------

export interface KeywordArg {
    name: string;
    type?: string;
    default?: string;
    required?: boolean;
}

export interface Keyword {
    name: string;
    args: KeywordArg[];
    shortDoc: string;
    doc: string;
    tags: string[];
    deprecated: boolean;
}

export interface Category {
    name: string;
    keywords: Keyword[];
}

export interface Library {
    name: string;
    version: string;
    categories: Category[];
}

export interface KeywordIndex {
    libraries: Library[];
}

// -- Cache -------------------------------------------------------------------

let cachedIndex: KeywordIndex | null = null;

// -- Loader ------------------------------------------------------------------

/**
 * Loads the keyword index from the bundled JSON file.
 * Results are cached so the file is read at most once per session.
 */
export function loadKeywordIndex(context: vscode.ExtensionContext): KeywordIndex {
    if (cachedIndex) {
        return cachedIndex;
    }

    const jsonPath = path.join(context.extensionPath, 'data', 'keyword-index.json');

    if (!fs.existsSync(jsonPath)) {
        vscode.window.showWarningMessage(
            'RF Skills: keyword-index.json not found. Keyword browser will be empty.',
        );
        cachedIndex = { libraries: [] };
        return cachedIndex;
    }

    try {
        const raw = fs.readFileSync(jsonPath, 'utf-8');
        cachedIndex = JSON.parse(raw) as KeywordIndex;
        return cachedIndex;
    } catch (err) {
        vscode.window.showErrorMessage(
            `RF Skills: Failed to parse keyword-index.json: ${err instanceof Error ? err.message : String(err)}`,
        );
        cachedIndex = { libraries: [] };
        return cachedIndex;
    }
}

/**
 * Force-reload the keyword index from disk (clears cache).
 */
export function reloadKeywordIndex(context: vscode.ExtensionContext): KeywordIndex {
    cachedIndex = null;
    return loadKeywordIndex(context);
}

// -- Search ------------------------------------------------------------------

export interface SearchResult {
    library: Library;
    category: Category;
    keyword: Keyword;
}

/**
 * Search keywords by a query string. Matches against keyword name,
 * short doc, tags, and library name. Case-insensitive.
 */
export function searchKeywords(
    index: KeywordIndex,
    query: string,
): SearchResult[] {
    const lowerQuery = query.toLowerCase().trim();
    if (!lowerQuery) {
        return [];
    }

    const results: SearchResult[] = [];

    for (const library of index.libraries) {
        const libraryNameLower = library.name.toLowerCase();

        for (const category of library.categories) {
            for (const keyword of category.keywords) {
                const nameMatch = keyword.name.toLowerCase().includes(lowerQuery);
                const docMatch = keyword.shortDoc.toLowerCase().includes(lowerQuery);
                const tagMatch = keyword.tags.some(t => t.toLowerCase().includes(lowerQuery));
                const libMatch = libraryNameLower.includes(lowerQuery);

                if (nameMatch || docMatch || tagMatch || libMatch) {
                    results.push({ library, category, keyword });
                }
            }
        }
    }

    // Sort: exact name prefix matches first, then alphabetical
    results.sort((a, b) => {
        const aPrefix = a.keyword.name.toLowerCase().startsWith(lowerQuery) ? 0 : 1;
        const bPrefix = b.keyword.name.toLowerCase().startsWith(lowerQuery) ? 0 : 1;
        if (aPrefix !== bPrefix) {
            return aPrefix - bPrefix;
        }
        return a.keyword.name.localeCompare(b.keyword.name);
    });

    return results;
}

/**
 * Builds a human-readable argument signature string for a keyword.
 * Example: "browser=chromium, headless=true"
 */
export function formatArgSignature(keyword: Keyword): string {
    if (keyword.args.length === 0) {
        return '';
    }

    return keyword.args
        .map(arg => {
            let s = arg.name;
            if (arg.default !== undefined && arg.default !== '') {
                s += `=${arg.default}`;
            }
            return s;
        })
        .join(', ');
}

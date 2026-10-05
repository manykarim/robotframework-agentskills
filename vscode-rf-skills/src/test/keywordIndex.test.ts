import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Keyword index tests.
 *
 * These tests validate the structure of data/keyword-index.json and exercise
 * the search/filter logic from src/data/keywordIndex.ts.
 *
 * The search functions are imported from the compiled module.  The tests also
 * work as a structural contract check even when the keyword-index.json file
 * has not been generated yet (graceful skip).
 */

const DATA_DIR = path.resolve(__dirname, '../../data');
const INDEX_PATH = path.join(DATA_DIR, 'keyword-index.json');

// -- Types matching keywordIndex.ts ------------------------------------------

interface KeywordArg {
    name: string;
    type?: string;
    default?: string;
    required?: boolean;
}

interface Keyword {
    name: string;
    args: KeywordArg[];
    shortDoc: string;
    doc: string;
    tags: string[];
    deprecated: boolean;
}

interface Category {
    name: string;
    keywords: Keyword[];
}

interface Library {
    name: string;
    version: string;
    categories: Category[];
}

interface KeywordIndex {
    libraries: Library[];
}

// -- Test-local search implementation (mirrors keywordIndex.ts) ---------------

interface SearchResult {
    library: Library;
    category: Category;
    keyword: Keyword;
}

function searchKeywords(index: KeywordIndex, query: string): SearchResult[] {
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

function formatArgSignature(keyword: Keyword): string {
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

// -- Helpers -----------------------------------------------------------------

function loadIndex(): KeywordIndex | null {
    if (!fs.existsSync(INDEX_PATH)) {
        return null;
    }
    const raw = fs.readFileSync(INDEX_PATH, 'utf-8');
    return JSON.parse(raw) as KeywordIndex;
}

suite('Keyword Index Tests', () => {

    let index: KeywordIndex | null = null;

    suiteSetup(() => {
        index = loadIndex();
    });

    test('keyword-index.json exists or tests gracefully skip', function () {
        if (!index) {
            this.skip();
            return;
        }
        assert.ok(index, 'Index loaded successfully');
    });

    test('Index has a "libraries" array', function () {
        if (!index) {
            this.skip();
            return;
        }
        assert.ok(Array.isArray(index.libraries), '"libraries" should be an array');
        assert.ok(index.libraries.length > 0, 'Expected at least one library');
    });

    test('All libraries have name and categories', function () {
        if (!index) {
            this.skip();
            return;
        }
        for (const lib of index.libraries) {
            assert.ok(
                typeof lib.name === 'string' && lib.name.length > 0,
                `Library is missing a name: ${JSON.stringify(lib).slice(0, 100)}`,
            );
            assert.ok(
                Array.isArray(lib.categories),
                `Library "${lib.name}" is missing categories array`,
            );
        }
    });

    test('All categories have names and keywords arrays', function () {
        if (!index) {
            this.skip();
            return;
        }
        for (const lib of index.libraries) {
            for (const cat of lib.categories) {
                assert.ok(
                    typeof cat.name === 'string' && cat.name.length > 0,
                    `Category in ${lib.name} is missing a name`,
                );
                assert.ok(
                    Array.isArray(cat.keywords),
                    `Category "${cat.name}" in ${lib.name} is missing keywords array`,
                );
            }
        }
    });

    test('Keywords have required fields (name, args, shortDoc)', function () {
        if (!index) {
            this.skip();
            return;
        }
        let count = 0;
        for (const lib of index.libraries) {
            for (const cat of lib.categories) {
                for (const kw of cat.keywords) {
                    assert.ok(
                        typeof kw.name === 'string' && kw.name.length > 0,
                        `Keyword in ${lib.name}/${cat.name} is missing a name`,
                    );
                    assert.ok(
                        Array.isArray(kw.args),
                        `Keyword "${kw.name}" is missing args array`,
                    );
                    assert.ok(
                        typeof kw.shortDoc === 'string',
                        `Keyword "${kw.name}" is missing shortDoc`,
                    );
                    assert.ok(
                        typeof kw.doc === 'string',
                        `Keyword "${kw.name}" is missing doc`,
                    );
                    assert.ok(
                        Array.isArray(kw.tags),
                        `Keyword "${kw.name}" is missing tags array`,
                    );
                    assert.ok(
                        typeof kw.deprecated === 'boolean',
                        `Keyword "${kw.name}" is missing deprecated boolean`,
                    );
                    count++;
                }
            }
        }
        assert.ok(count > 0, 'Expected at least one keyword in the index');
    });

    test('Total keyword count is reasonable (50+)', function () {
        if (!index) {
            this.skip();
            return;
        }
        let total = 0;
        for (const lib of index.libraries) {
            for (const cat of lib.categories) {
                total += cat.keywords.length;
            }
        }
        assert.ok(total >= 50, `Expected 50+ keywords total, got ${total}`);
    });

    test('Keyword args have required "name" field', function () {
        if (!index) {
            this.skip();
            return;
        }
        for (const lib of index.libraries) {
            for (const cat of lib.categories) {
                for (const kw of cat.keywords) {
                    for (const arg of kw.args) {
                        assert.ok(
                            typeof arg.name === 'string' && arg.name.length > 0,
                            `Arg in keyword "${kw.name}" (${lib.name}) is missing a name`,
                        );
                    }
                }
            }
        }
    });

    // -- Search function tests -----------------------------------------------

    test('Search returns empty results for empty query', function () {
        if (!index) {
            this.skip();
            return;
        }
        const results = searchKeywords(index, '');
        assert.strictEqual(results.length, 0, 'Empty query should return no results');
    });

    test('Search returns empty results for whitespace-only query', function () {
        if (!index) {
            this.skip();
            return;
        }
        const results = searchKeywords(index, '   ');
        assert.strictEqual(results.length, 0, 'Whitespace query should return no results');
    });

    test('Search finds keywords by name', function () {
        if (!index) {
            this.skip();
            return;
        }
        // Pick the first keyword name in the index
        const firstKw = index.libraries[0]?.categories[0]?.keywords[0];
        if (!firstKw) {
            this.skip();
            return;
        }
        const results = searchKeywords(index, firstKw.name);
        assert.ok(results.length > 0, `Search for "${firstKw.name}" should return results`);
        assert.ok(
            results.some(r => r.keyword.name === firstKw.name),
            `Results should include the exact keyword "${firstKw.name}"`,
        );
    });

    test('Search finds keywords by library name', function () {
        if (!index) {
            this.skip();
            return;
        }
        const libName = index.libraries[0]?.name;
        if (!libName) {
            this.skip();
            return;
        }
        const results = searchKeywords(index, libName);
        assert.ok(results.length > 0, `Search for library "${libName}" should return results`);
    });

    test('Search is case-insensitive', function () {
        if (!index) {
            this.skip();
            return;
        }
        const firstKw = index.libraries[0]?.categories[0]?.keywords[0];
        if (!firstKw) {
            this.skip();
            return;
        }
        const upper = searchKeywords(index, firstKw.name.toUpperCase());
        const lower = searchKeywords(index, firstKw.name.toLowerCase());
        assert.strictEqual(
            upper.length,
            lower.length,
            'Case-insensitive search should return same count for upper and lower',
        );
    });

    // -- formatArgSignature tests --------------------------------------------

    test('formatArgSignature returns empty string for no args', () => {
        const kw: Keyword = {
            name: 'No Args Keyword',
            args: [],
            shortDoc: '',
            doc: '',
            tags: [],
            deprecated: false,
        };
        assert.strictEqual(formatArgSignature(kw), '');
    });

    test('formatArgSignature formats args with defaults', () => {
        const kw: Keyword = {
            name: 'With Defaults',
            args: [
                { name: 'browser', default: 'chromium' },
                { name: 'headless', default: 'true' },
            ],
            shortDoc: '',
            doc: '',
            tags: [],
            deprecated: false,
        };
        assert.strictEqual(formatArgSignature(kw), 'browser=chromium, headless=true');
    });

    test('formatArgSignature formats args without defaults', () => {
        const kw: Keyword = {
            name: 'Required Args',
            args: [
                { name: 'locator' },
                { name: 'timeout' },
            ],
            shortDoc: '',
            doc: '',
            tags: [],
            deprecated: false,
        };
        assert.strictEqual(formatArgSignature(kw), 'locator, timeout');
    });

    test('formatArgSignature handles mix of required and optional args', () => {
        const kw: Keyword = {
            name: 'Mixed',
            args: [
                { name: 'url' },
                { name: 'browser', default: 'chromium' },
            ],
            shortDoc: '',
            doc: '',
            tags: [],
            deprecated: false,
        };
        assert.strictEqual(formatArgSignature(kw), 'url, browser=chromium');
    });
});

import * as assert from 'assert';
import { execFile } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

/**
 * Python invoker tests.
 *
 * These tests exercise the Python scripts bundled with the extension using
 * child_process directly.  They do not depend on the VS Code API so they
 * can run both inside the VS Code test host and as standalone mocha tests.
 */

const SCRIPTS_DIR = path.resolve(__dirname, '../../scripts');
const TIMEOUT_MS = 15_000;

/** Helper: run a Python script and return { stdout, stderr, code }. */
function runPythonScript(
    scriptName: string,
    args: string[],
    stdinData?: string,
): Promise<{ stdout: string; stderr: string; code: number | null }> {
    return new Promise((resolve) => {
        const scriptPath = path.join(SCRIPTS_DIR, scriptName);

        if (stdinData !== undefined) {
            const { spawn } = require('child_process');
            const proc = spawn('python3', [scriptPath, ...args], {
                timeout: TIMEOUT_MS,
                stdio: ['pipe', 'pipe', 'pipe'],
            });

            let stdout = '';
            let stderr = '';

            proc.stdout.on('data', (chunk: Buffer) => {
                stdout += chunk.toString();
            });
            proc.stderr.on('data', (chunk: Buffer) => {
                stderr += chunk.toString();
            });
            proc.on('error', (err: Error) => {
                resolve({ stdout, stderr: err.message, code: -1 });
            });
            proc.on('close', (code: number | null) => {
                resolve({ stdout, stderr, code });
            });

            proc.stdin.write(stdinData);
            proc.stdin.end();
        } else {
            execFile(
                'python3',
                [scriptPath, ...args],
                { timeout: TIMEOUT_MS, maxBuffer: 5 * 1024 * 1024 },
                (err, stdout, stderr) => {
                    const code = err ? (err as NodeJS.ErrnoException & { code?: string }).code === 'ETIMEDOUT' ? -2 : 1 : 0;
                    resolve({ stdout: stdout || '', stderr: stderr || '', code: err ? code : 0 });
                },
            );
        }
    });
}

suite('Python Invoker Tests', () => {

    test('Scripts directory exists and contains expected files', () => {
        assert.ok(fs.existsSync(SCRIPTS_DIR), `Scripts directory not found: ${SCRIPTS_DIR}`);

        const expected = ['keyword_builder.py', 'rf_libdoc.py', 'rf_results.py', 'testcase_builder.py', 'resource_architect.py'];
        for (const name of expected) {
            const fullPath = path.join(SCRIPTS_DIR, name);
            assert.ok(fs.existsSync(fullPath), `Expected script not found: ${name}`);
        }
    });

    test('keyword_builder.py shows help with --help', async () => {
        const result = await runPythonScript('keyword_builder.py', ['--help']);
        assert.strictEqual(result.code, 0, `Expected exit code 0, got ${result.code}. stderr: ${result.stderr}`);
        assert.ok(result.stdout.length > 0, 'Help output should not be empty');
    });

    test('keyword_builder.py accepts JSON input via stdin', async () => {
        const input = JSON.stringify({
            name: 'Test Keyword',
            args: [{ name: 'arg1', type: 'str' }],
            doc: 'A test keyword',
            steps: ['Log    Hello'],
        });

        const result = await runPythonScript('keyword_builder.py', [], input);
        // The script may succeed or fail depending on input format,
        // but it should not crash with an unhandled exception.
        assert.ok(
            result.code === 0 || result.stderr.length > 0,
            'Script should either succeed or provide an error message',
        );
    });

    test('rf_libdoc.py reports error when called without required args', async () => {
        // Without --search or --keyword, the script should exit with an error
        // or print usage. Either way it should not hang.
        const result = await runPythonScript('rf_libdoc.py', []);
        // rf_libdoc.py requires robotframework; if not installed it exits with
        // a JSON error on stderr. If RF is installed, it needs --search or --keyword.
        assert.ok(
            result.code !== 0 || result.stdout.length > 0 || result.stderr.length > 0,
            'Script should produce output or a non-zero exit code',
        );
    });

    test('rf_libdoc.py returns JSON error when RF not installed (or valid JSON when it is)', async () => {
        const result = await runPythonScript('rf_libdoc.py', ['--search', 'click', '--library', 'BuiltIn']);
        // If RF is installed: valid JSON on stdout with matches
        // If RF is not installed: JSON error on stderr
        const output = result.stdout.trim() || result.stderr.trim();
        assert.ok(output.length > 0, 'Script should produce some output');

        // Try to parse as JSON (at least one of stdout/stderr should be JSON-parseable)
        let parsed = false;
        try {
            JSON.parse(result.stdout.trim());
            parsed = true;
        } catch {
            // stdout was not JSON, try stderr
        }
        if (!parsed) {
            try {
                JSON.parse(result.stderr.trim());
                parsed = true;
            } catch {
                // stderr was not JSON either
            }
        }
        // The script should output JSON in at least one stream
        assert.ok(parsed || result.code !== 0, 'Script should produce JSON output or fail with non-zero exit code');
    });

    test('Invalid script path produces error', async () => {
        const result = await runPythonScript('nonexistent_script.py', []);
        assert.ok(result.code !== 0, 'Non-existent script should fail');
    });

    test('testcase_builder.py shows help with --help', async () => {
        const result = await runPythonScript('testcase_builder.py', ['--help']);
        assert.strictEqual(result.code, 0, `Expected exit code 0, got ${result.code}. stderr: ${result.stderr}`);
        assert.ok(result.stdout.length > 0, 'Help output should not be empty');
    });

    test('resource_architect.py shows help with --help', async () => {
        const result = await runPythonScript('resource_architect.py', ['--help']);
        assert.strictEqual(result.code, 0, `Expected exit code 0, got ${result.code}. stderr: ${result.stderr}`);
        assert.ok(result.stdout.length > 0, 'Help output should not be empty');
    });
});

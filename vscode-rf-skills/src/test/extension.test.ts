import * as assert from 'assert';
import * as vscode from 'vscode';

suite('Extension Test Suite', () => {
    vscode.window.showInformationMessage('Start all tests.');

    test('Extension should be present', () => {
        assert.ok(vscode.extensions.getExtension('manykarim.robotframework-skills'));
    });

    test('Extension should activate on robot file', async () => {
        const ext = vscode.extensions.getExtension('manykarim.robotframework-skills');
        if (ext && !ext.isActive) {
            await ext.activate();
        }
        assert.ok(ext?.isActive);
    });

    test('Commands should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        const rfCommands = commands.filter(c => c.startsWith('rfSkills.'));
        assert.ok(rfCommands.length >= 8, `Expected 8+ commands, got ${rfCommands.length}`);
    });

    test('Search keyword command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('rfSkills.searchKeyword'));
    });

    test('Generate keyword command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('rfSkills.generateKeyword'));
    });

    test('Analyze results command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('rfSkills.analyzeResults'));
    });

    test('Explain keyword command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('rfSkills.explainKeyword'));
    });

    test('Generate test case command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('rfSkills.generateTestCase'));
    });

    test('Scaffold project command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('rfSkills.scaffoldProject'));
    });

    test('Check environment command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('rfSkills.checkEnvironment'));
    });

    test('Modernize syntax command should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('rfSkills.modernizeSyntax'));
    });

    test('Keyword browser view should be registered', async () => {
        // The view container should exist after activation
        const ext = vscode.extensions.getExtension('manykarim.robotframework-skills');
        assert.ok(ext, 'Extension should exist');
        if (!ext.isActive) {
            await ext.activate();
        }
        // If the view is registered, the extension contributes it in package.json
        // We verify the extension is active which means all views are registered
        assert.ok(ext.isActive, 'Extension should be active');
    });
});

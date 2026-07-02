import * as vscode from "vscode";
import {
  detectPythonEnvironment,
  clearEnvironmentCache,
} from "../python/detector.js";

export function registerCheckEnvironment(
  context: vscode.ExtensionContext
): void {
  const disposable = vscode.commands.registerCommand(
    "rfSkills.checkEnvironment",
    async () => {
      // Always re-probe so the user gets fresh results.
      clearEnvironmentCache();

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Detecting RF environment...",
          cancellable: false,
        },
        async () => {
          try {
            const env = await detectPythonEnvironment();

            const channel = vscode.window.createOutputChannel(
              "RF Environment",
              { log: true }
            );

            channel.appendLine("=== Robot Framework Environment ===");
            channel.appendLine("");
            channel.appendLine(`Python:     ${env.pythonPath}`);
            channel.appendLine(`Version:    ${env.pythonVersion}`);
            channel.appendLine(
              `RF Version: ${env.rfVersion ?? "NOT INSTALLED"}`
            );
            channel.appendLine("");

            const installed = env.installedLibraries.filter((l) => l.installed);
            const missing = env.installedLibraries.filter((l) => !l.installed);

            if (installed.length > 0) {
              channel.appendLine("Installed libraries:");
              for (const lib of installed) {
                channel.appendLine(`  [ok] ${lib.name}`);
              }
            }
            if (missing.length > 0) {
              channel.appendLine("");
              channel.appendLine("Not installed:");
              for (const lib of missing) {
                channel.appendLine(`  [ ] ${lib.name}`);
              }
            }

            channel.show(true);

            if (!env.rfVersion) {
              const choice = await vscode.window.showWarningMessage(
                "Robot Framework is not installed. Install it?",
                "Install with pip",
                "Dismiss"
              );
              if (choice === "Install with pip") {
                const terminal = vscode.window.createTerminal(
                  "Install Robot Framework"
                );
                terminal.show();
                terminal.sendText(
                  `${env.pythonPath} -m pip install robotframework`
                );
              }
            } else {
              vscode.window.showInformationMessage(
                `RF ${env.rfVersion} detected with Python ${env.pythonVersion}. ` +
                  `${installed.length} libraries found.`
              );
            }
          } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err);
            vscode.window.showErrorMessage(
              `Environment check failed: ${msg}`
            );
          }
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

import * as vscode from "vscode";
import { invokePythonScript } from "../python/invoker.js";

/** Shape returned by resource_architect.py. */
interface ScaffoldResult {
  directories: string[];
  files: Array<{ path: string; content: string }>;
  warnings: string[];
  suggestions: string[];
  meta: {
    resource_dir: string;
    resource_naming: string;
  };
}

/** Domains the user can pick from. */
const DOMAIN_OPTIONS: readonly string[] = [
  "web",
  "api",
  "mobile",
  "desktop",
  "database",
  "ssh",
];

/** Library choices keyed by domain. */
const LIBRARIES_BY_DOMAIN: Record<string, string[]> = {
  web: ["Browser", "SeleniumLibrary"],
  api: ["RequestsLibrary", "REST"],
  mobile: ["AppiumLibrary"],
  desktop: ["AutoItLibrary", "SikuliLibrary"],
  database: ["DatabaseLibrary"],
  ssh: ["SSHLibrary"],
};

const VARIABLE_FORMATS: readonly string[] = [
  "resource",
  "yaml",
  "python",
];

export function registerScaffoldProject(
  context: vscode.ExtensionContext
): void {
  const disposable = vscode.commands.registerCommand(
    "rfSkills.scaffoldProject",
    async () => {
      // Step 1: Project name.
      const projectName = await vscode.window.showInputBox({
        title: "RF Skills: Scaffold Project (1/5)",
        prompt: "Project name (used as directory name)",
        placeHolder: "e.g. my-rf-project",
        validateInput: (v) =>
          v.trim() ? null : "Project name is required",
      });
      if (!projectName) {
        return;
      }

      // Step 2: Domains (multi-select).
      const domainPicks = await vscode.window.showQuickPick(
        DOMAIN_OPTIONS.map((d) => ({
          label: d,
          picked: d === "web",
        })),
        {
          title: "RF Skills: Scaffold Project (2/5)",
          placeHolder: "Select testing domains",
          canPickMany: true,
        }
      );
      if (!domainPicks || domainPicks.length === 0) {
        return;
      }
      const domains = domainPicks.map((d) => d.label);

      // Step 3: Libraries (auto-suggested from domains, user can add more).
      const suggestedLibraries = new Set<string>();
      for (const domain of domains) {
        for (const lib of LIBRARIES_BY_DOMAIN[domain] ?? []) {
          suggestedLibraries.add(lib);
        }
      }

      const libraryInput = await vscode.window.showInputBox({
        title: "RF Skills: Scaffold Project (3/5)",
        prompt:
          "Libraries (comma-separated). Pre-filled from domains, edit as needed",
        value: Array.from(suggestedLibraries).join(", "),
      });
      if (libraryInput === undefined) {
        return;
      }
      const libraries = libraryInput
        .split(",")
        .map((l) => l.trim())
        .filter(Boolean);

      // Step 4: Environments.
      const envInput = await vscode.window.showInputBox({
        title: "RF Skills: Scaffold Project (4/5)",
        prompt: "Environments (comma-separated, optional)",
        placeHolder: "e.g. dev, staging, production",
      });
      if (envInput === undefined) {
        return;
      }
      const environments = envInput
        .split(",")
        .map((e) => e.trim())
        .filter(Boolean);

      // Step 5: Variable format.
      const varFormat = await vscode.window.showQuickPick(
        VARIABLE_FORMATS as unknown as string[],
        {
          title: "RF Skills: Scaffold Project (5/5)",
          placeHolder: "Variable file format",
        }
      );
      if (!varFormat) {
        return;
      }

      // Determine output root.
      const workspaceRoot =
        vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (!workspaceRoot) {
        vscode.window.showErrorMessage(
          "Open a workspace folder before scaffolding a project."
        );
        return;
      }

      const projectRoot = `${workspaceRoot}/${projectName.trim()}`;

      const stdinData = JSON.stringify({
        project_root: projectRoot,
        domains,
        libraries,
        environments,
        variables_format: varFormat,
      });

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Scaffolding project...",
          cancellable: false,
        },
        async () => {
          const result = await invokePythonScript(
            context,
            "resource_architect.py",
            ["--write"],
            stdinData
          );

          if (result.error) {
            vscode.window.showErrorMessage(
              `Scaffold failed: ${result.error}`
            );
            return;
          }

          const data = result.data as ScaffoldResult | undefined;
          if (!data) {
            vscode.window.showWarningMessage("No scaffold output received.");
            return;
          }

          for (const w of data.warnings) {
            vscode.window.showWarningMessage(`Scaffold: ${w}`);
          }
          for (const s of data.suggestions) {
            vscode.window.showInformationMessage(`Suggestion: ${s}`);
          }

          await showCreatedFiles(data);
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

async function showCreatedFiles(data: ScaffoldResult): Promise<void> {
  const filePaths = data.files.map((f) => f.path);

  if (filePaths.length === 0) {
    vscode.window.showInformationMessage("No files were created.");
    return;
  }

  // Build a tree summary.
  const treeLines = [
    `Created ${filePaths.length} file(s) in ${data.directories.length} directory(ies):`,
    "",
  ];
  for (const dir of data.directories) {
    treeLines.push(`  [dir]  ${dir}`);
  }
  for (const filePath of filePaths) {
    treeLines.push(`  [file] ${filePath}`);
  }

  const channel = vscode.window.createOutputChannel("RF Project Scaffold");
  for (const line of treeLines) {
    channel.appendLine(line);
  }
  channel.show(true);

  // Offer to open the first created file.
  if (filePaths.length > 0) {
    const choice = await vscode.window.showInformationMessage(
      `Scaffolded ${filePaths.length} file(s). Open first file?`,
      "Open",
      "Dismiss"
    );
    if (choice === "Open") {
      try {
        const doc = await vscode.workspace.openTextDocument(
          vscode.Uri.file(filePaths[0])
        );
        await vscode.window.showTextDocument(doc);
      } catch {
        vscode.window.showWarningMessage(
          `Could not open ${filePaths[0]}.`
        );
      }
    }
  }
}

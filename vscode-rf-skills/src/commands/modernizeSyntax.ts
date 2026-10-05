import * as vscode from "vscode";

// ------------------------------------------------------------------
// Deprecated patterns and their RF7+ replacements
// ------------------------------------------------------------------

interface DeprecatedPattern {
  /** Human-readable label shown in the QuickPick. */
  label: string;
  /** Regex that matches the deprecated syntax.  Must have capture groups
   *  needed by the `replacement` callback. */
  regex: RegExp;
  /** Build the replacement text from the regex match.  Receives the full
   *  match array.  Must return the replacement string. */
  replacement: (match: RegExpMatchArray) => string;
}

const PATTERNS: readonly DeprecatedPattern[] = [
  {
    label: "[Return] -> RETURN",
    // Matches:  "    [Return]    value"  (RF setting syntax)
    regex: /^(\s*)\[Return\](\s{2,}|\t)(.*)$/gim,
    replacement: (m) => `${m[1]}RETURN${m[2]}${m[3]}`,
  },
  {
    label: "Run Keyword If -> IF/ELSE",
    // Matches: "    Run Keyword If    cond    keyword    args..."
    regex:
      /^(\s*)Run Keyword If(\s{2,}|\t)(.+?)(\s{2,}|\t)(\S.*)$/gim,
    replacement: (m) => {
      const indent = m[1];
      const condition = m[3].trim();
      const body = m[5].trim();
      return [
        `${indent}IF    ${condition}`,
        `${indent}    ${body}`,
        `${indent}END`,
      ].join("\n");
    },
  },
  {
    label: "Run Keyword Unless -> IF NOT",
    regex:
      /^(\s*)Run Keyword Unless(\s{2,}|\t)(.+?)(\s{2,}|\t)(\S.*)$/gim,
    replacement: (m) => {
      const indent = m[1];
      const condition = m[3].trim();
      const body = m[5].trim();
      return [
        `${indent}IF    not (${condition})`,
        `${indent}    ${body}`,
        `${indent}END`,
      ].join("\n");
    },
  },
  {
    label: ":FOR -> FOR/END",
    // Old-style FOR:  ":FOR  ${item}  IN  @{list}"
    regex:
      /^(\s*):FOR(\s{2,}|\t)(.+?)(\s{2,}|\t)(IN(?:\s+RANGE)?)(\s{2,}|\t)(.*)$/gim,
    replacement: (m) => {
      const indent = m[1];
      const loopVar = m[3].trim();
      const inKeyword = m[5].trim();
      const values = m[7].trim();
      return `${indent}FOR    ${loopVar}    ${inKeyword}    ${values}`;
    },
  },
  {
    label: "Set Test Variable -> VAR (test scope)",
    regex:
      /^(\s*)Set Test Variable(\s{2,}|\t)(\$\{[^}]+\})(\s{2,}|\t)(.*)$/gim,
    replacement: (m) => {
      const indent = m[1];
      const varName = m[3].trim();
      const value = m[5].trim();
      return `${indent}VAR    ${varName}    ${value}    scope=TEST`;
    },
  },
  {
    label: "Set Suite Variable -> VAR (suite scope)",
    regex:
      /^(\s*)Set Suite Variable(\s{2,}|\t)(\$\{[^}]+\})(\s{2,}|\t)(.*)$/gim,
    replacement: (m) => {
      const indent = m[1];
      const varName = m[3].trim();
      const value = m[5].trim();
      return `${indent}VAR    ${varName}    ${value}    scope=SUITE`;
    },
  },
  {
    label: "Set Global Variable -> VAR (global scope)",
    regex:
      /^(\s*)Set Global Variable(\s{2,}|\t)(\$\{[^}]+\})(\s{2,}|\t)(.*)$/gim,
    replacement: (m) => {
      const indent = m[1];
      const varName = m[3].trim();
      const value = m[5].trim();
      return `${indent}VAR    ${varName}    ${value}    scope=GLOBAL`;
    },
  },
];

// ------------------------------------------------------------------
// Registration
// ------------------------------------------------------------------

export function registerModernizeSyntax(
  context: vscode.ExtensionContext
): void {
  const disposable = vscode.commands.registerCommand(
    "rfSkills.modernizeSyntax",
    async () => {
      // Decide scope: current file or entire workspace.
      const scope = await vscode.window.showQuickPick(
        [
          {
            label: "Current File",
            description: "Scan the active editor only",
            value: "file" as const,
          },
          {
            label: "Workspace",
            description: "Scan all .robot and .resource files",
            value: "workspace" as const,
          },
        ],
        { title: "Modernize RF Syntax: Select scope" }
      );
      if (!scope) {
        return;
      }

      const fileUris =
        scope.value === "file"
          ? getActiveFileUri()
          : await getWorkspaceRobotFiles();

      if (fileUris.length === 0) {
        vscode.window.showInformationMessage(
          "No .robot / .resource files to scan."
        );
        return;
      }

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Scanning for deprecated patterns...",
          cancellable: false,
        },
        async () => {
          const findings = await scanFiles(fileUris);

          if (findings.length === 0) {
            vscode.window.showInformationMessage(
              "No deprecated patterns found. Code is already modern."
            );
            return;
          }

          await presentFindings(findings);
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

interface PatternFinding {
  pattern: DeprecatedPattern;
  occurrences: Array<{
    uri: vscode.Uri;
    line: number;
    matchText: string;
    replacement: string;
  }>;
}

// ------------------------------------------------------------------
// Core logic
// ------------------------------------------------------------------

function getActiveFileUri(): vscode.Uri[] {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return [];
  }
  const ext = editor.document.fileName;
  if (ext.endsWith(".robot") || ext.endsWith(".resource")) {
    return [editor.document.uri];
  }
  return [];
}

async function getWorkspaceRobotFiles(): Promise<vscode.Uri[]> {
  return vscode.workspace.findFiles(
    "**/*.{robot,resource}",
    "**/node_modules/**",
    500
  );
}

async function scanFiles(uris: vscode.Uri[]): Promise<PatternFinding[]> {
  const findingsMap = new Map<string, PatternFinding>();

  for (const p of PATTERNS) {
    findingsMap.set(p.label, { pattern: p, occurrences: [] });
  }

  for (const uri of uris) {
    let doc: vscode.TextDocument;
    try {
      doc = await vscode.workspace.openTextDocument(uri);
    } catch {
      continue;
    }
    const text = doc.getText();

    for (const p of PATTERNS) {
      // Reset lastIndex for global regex.
      const regex = new RegExp(p.regex.source, p.regex.flags);
      let match: RegExpExecArray | null;
      while ((match = regex.exec(text)) !== null) {
        const pos = doc.positionAt(match.index);
        const finding = findingsMap.get(p.label)!;
        finding.occurrences.push({
          uri,
          line: pos.line,
          matchText: match[0],
          replacement: p.replacement(match),
        });
      }
    }
  }

  return Array.from(findingsMap.values()).filter(
    (f) => f.occurrences.length > 0
  );
}

async function presentFindings(
  findings: PatternFinding[]
): Promise<void> {
  interface FindingItem extends vscode.QuickPickItem {
    finding: PatternFinding;
  }

  const items: FindingItem[] = findings.map((f) => ({
    label: f.pattern.label,
    description: `${f.occurrences.length} occurrence(s)`,
    picked: true,
    finding: f,
  }));

  const picked = await vscode.window.showQuickPick(items, {
    title: "Select patterns to modernize",
    placeHolder: "Uncheck patterns you want to skip",
    canPickMany: true,
  });

  if (!picked || picked.length === 0) {
    return;
  }

  const edit = new vscode.WorkspaceEdit();
  let totalReplacements = 0;

  for (const item of picked) {
    for (const occ of item.finding.occurrences) {
      const doc = await vscode.workspace.openTextDocument(occ.uri);
      const lineText = doc.lineAt(occ.line).text;
      const lineRange = doc.lineAt(occ.line).range;

      // For multi-line replacements (like IF/ELSE), we replace the entire
      // matched line.  The match might span only part of the line if there
      // is content after, but our regexes are anchored to full lines so
      // lineText should contain the match.
      if (lineText.includes(occ.matchText.split("\n")[0])) {
        edit.replace(occ.uri, lineRange, occ.replacement);
        totalReplacements++;
      }
    }
  }

  if (totalReplacements === 0) {
    vscode.window.showInformationMessage("No replacements made.");
    return;
  }

  const success = await vscode.workspace.applyEdit(edit);
  if (success) {
    vscode.window.showInformationMessage(
      `Modernized ${totalReplacements} occurrence(s) across ${picked.length} pattern(s).`
    );
  } else {
    vscode.window.showErrorMessage(
      "Failed to apply some modernization edits."
    );
  }
}

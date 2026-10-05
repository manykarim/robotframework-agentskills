import * as vscode from "vscode";
import { invokePythonScript } from "../python/invoker.js";

/** Shape returned by keyword_builder.py. */
interface KeywordBuilderResult {
  artifact: string;
  warnings: string[];
  suggestions: string[];
  meta: Record<string, unknown>;
}

export function registerGenerateKeyword(
  context: vscode.ExtensionContext
): void {
  const disposable = vscode.commands.registerCommand(
    "rfSkills.generateKeyword",
    async () => {
      // Step 1: Keyword name.
      const keywordName = await vscode.window.showInputBox({
        title: "RF Skills: Generate User Keyword (1/4)",
        prompt: "Keyword name (Title Case recommended)",
        placeHolder: "e.g. Login With Valid Credentials",
        validateInput: (value) =>
          value.trim() ? null : "Keyword name is required",
      });
      if (!keywordName) {
        return;
      }

      // Step 2: Arguments (comma-separated).
      const argsRaw = await vscode.window.showInputBox({
        title: "RF Skills: Generate User Keyword (2/4)",
        prompt:
          "Arguments (comma-separated). Use name=default for optional args",
        placeHolder:
          "e.g. username, password, timeout=10s",
      });
      if (argsRaw === undefined) {
        return; // cancelled
      }

      // Step 3: Steps (multiline).
      const stepsRaw = await vscode.window.showInputBox({
        title: "RF Skills: Generate User Keyword (3/4)",
        prompt:
          "Steps — one per line, use semicolons to separate lines. " +
          "Format: keyword    arg1    arg2 (4-space separator)",
        placeHolder:
          "e.g. Input Text    id=username    ${username} ; Click Button    id=login",
      });
      if (stepsRaw === undefined) {
        return;
      }

      // Step 4: Tags.
      const tagsRaw = await vscode.window.showInputBox({
        title: "RF Skills: Generate User Keyword (4/4)",
        prompt: "Tags (comma-separated, optional)",
        placeHolder: "e.g. login, smoke",
      });
      if (tagsRaw === undefined) {
        return;
      }

      const stdinData = buildStdinJson(
        keywordName,
        argsRaw,
        stepsRaw,
        tagsRaw
      );

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Generating keyword...",
          cancellable: false,
        },
        async () => {
          const result = await invokePythonScript(
            context,
            "keyword_builder.py",
            [],
            stdinData
          );

          if (result.error) {
            vscode.window.showErrorMessage(
              `Keyword generation failed: ${result.error}`
            );
            return;
          }

          const data = result.data as KeywordBuilderResult | undefined;
          if (!data?.artifact) {
            vscode.window.showWarningMessage(
              "No keyword code was generated."
            );
            return;
          }

          showWarningsAndSuggestions(data);
          await insertArtifact(data.artifact);
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function buildStdinJson(
  keywordName: string,
  argsRaw: string,
  stepsRaw: string,
  tagsRaw: string
): string {
  const args = parseArguments(argsRaw);
  const steps = parseSteps(stepsRaw);
  const tags = parseTags(tagsRaw);

  const payload: Record<string, unknown> = {
    keyword_name: keywordName.trim(),
    arguments: args,
    steps,
    tags,
  };

  return JSON.stringify(payload);
}

/**
 * Parse comma-separated argument definitions into the format expected by
 * keyword_builder.py:
 *   [ { name: "username" }, { name: "timeout", default: "10s" } ]
 */
function parseArguments(
  raw: string
): Array<{ name: string; default?: string }> {
  if (!raw.trim()) {
    return [];
  }
  return raw.split(",").map((part) => {
    const trimmed = part.trim();
    if (trimmed.includes("=")) {
      const [name, ...rest] = trimmed.split("=");
      return { name: name.trim(), default: rest.join("=").trim() };
    }
    return { name: trimmed };
  });
}

/**
 * Parse steps entered as semicolon-separated lines.
 * Each step can be either:
 *   - A raw line: "Log    Hello"
 *   - keyword + args separated by 4 spaces
 */
function parseSteps(
  raw: string
): Array<{ keyword?: string; args?: string[]; line?: string }> {
  if (!raw.trim()) {
    return [];
  }
  return raw.split(";").map((part) => {
    const trimmed = part.trim();
    // Split on 4-space separator.
    const cells = trimmed.split(/\s{4,}/);
    if (cells.length > 1) {
      const [keyword, ...args] = cells;
      return { keyword: keyword.trim(), args: args.map((a) => a.trim()) };
    }
    // Single token -- treat as a raw line.
    return { line: trimmed };
  });
}

function parseTags(raw: string): string[] {
  if (!raw.trim()) {
    return [];
  }
  return raw
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

function showWarningsAndSuggestions(data: KeywordBuilderResult): void {
  for (const w of data.warnings) {
    vscode.window.showWarningMessage(`Keyword builder: ${w}`);
  }
  for (const s of data.suggestions) {
    vscode.window.showInformationMessage(`Suggestion: ${s}`);
  }
}

/**
 * Insert generated Robot Framework code into the active editor.
 *
 * If the file contains a `*** Keywords ***` section the code is appended at
 * the end of that section.  Otherwise it is inserted at the cursor or at the
 * end of the file.
 */
async function insertArtifact(artifact: string): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    // No active editor -- open in a new untitled document.
    const doc = await vscode.workspace.openTextDocument({
      language: "robotframework",
      content: `*** Keywords ***\n${artifact}\n`,
    });
    await vscode.window.showTextDocument(doc);
    return;
  }

  const document = editor.document;
  const text = document.getText();

  // Try to find the Keywords section.
  const keywordsSectionRegex = /^\*\*\*\s*Keywords?\s*\*\*\*/im;
  const nextSectionRegex = /^\*\*\*\s*.+\s*\*\*\*/gim;

  const kwMatch = keywordsSectionRegex.exec(text);

  let insertPosition: vscode.Position;

  if (kwMatch) {
    // Find the next section header after Keywords.
    nextSectionRegex.lastIndex = kwMatch.index + kwMatch[0].length;
    const nextMatch = nextSectionRegex.exec(text);

    if (nextMatch) {
      // Insert before the next section, with a blank line.
      const pos = document.positionAt(nextMatch.index);
      insertPosition = new vscode.Position(pos.line, 0);
    } else {
      // No next section -- append at end of file.
      insertPosition = new vscode.Position(document.lineCount, 0);
    }
  } else {
    // No Keywords section -- insert at cursor.
    insertPosition = editor.selection.active;
  }

  const snippet = `\n${artifact}\n`;

  await editor.edit((editBuilder) => {
    editBuilder.insert(insertPosition, snippet);
  });

  // Reveal the inserted text.
  const revealPos = new vscode.Position(
    insertPosition.line + 1,
    0
  );
  editor.revealRange(
    new vscode.Range(revealPos, revealPos),
    vscode.TextEditorRevealType.InCenter
  );
}

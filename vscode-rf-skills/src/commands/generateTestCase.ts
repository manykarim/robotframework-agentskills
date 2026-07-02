import * as vscode from "vscode";
import { invokePythonScript } from "../python/invoker.js";

/** Shape returned by testcase_builder.py. */
interface TestCaseBuilderResult {
  artifact: string;
  warnings: string[];
  suggestions: string[];
}

type TestType = "keyword-driven" | "template";

export function registerGenerateTestCase(
  context: vscode.ExtensionContext
): void {
  const disposable = vscode.commands.registerCommand(
    "rfSkills.generateTestCase",
    async () => {
      // Step 1: Test name.
      const testName = await vscode.window.showInputBox({
        title: "RF Skills: Generate Test Case (1/4)",
        prompt: "Test case name",
        placeHolder: "e.g. User Can Log In With Valid Credentials",
        validateInput: (v) =>
          v.trim() ? null : "Test name is required",
      });
      if (!testName) {
        return;
      }

      // Step 2: Test type.
      const typeChoice = await vscode.window.showQuickPick(
        [
          {
            label: "Keyword-Driven",
            description: "Sequential keyword steps",
            value: "keyword-driven" as TestType,
          },
          {
            label: "Template",
            description: "Data-driven with [Template]",
            value: "template" as TestType,
          },
        ],
        { title: "RF Skills: Generate Test Case (2/4)" }
      );
      if (!typeChoice) {
        return;
      }

      let stdinData: string;

      if (typeChoice.value === "template") {
        stdinData = await gatherTemplateInput(testName);
      } else {
        stdinData = await gatherKeywordDrivenInput(testName);
      }

      // Empty string means the user cancelled.
      if (!stdinData) {
        return;
      }

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Generating test case...",
          cancellable: false,
        },
        async () => {
          const result = await invokePythonScript(
            context,
            "testcase_builder.py",
            ["--allow-control"],
            stdinData
          );

          if (result.error) {
            vscode.window.showErrorMessage(
              `Test generation failed: ${result.error}`
            );
            return;
          }

          const data = result.data as TestCaseBuilderResult | undefined;
          if (!data?.artifact) {
            vscode.window.showWarningMessage(
              "No test case code was generated."
            );
            return;
          }

          for (const w of data.warnings) {
            vscode.window.showWarningMessage(`Test builder: ${w}`);
          }
          for (const s of data.suggestions) {
            vscode.window.showInformationMessage(`Suggestion: ${s}`);
          }

          await insertTestCase(data.artifact);
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

// ------------------------------------------------------------------
// Input gathering
// ------------------------------------------------------------------

async function gatherKeywordDrivenInput(testName: string): Promise<string> {
  // Step 3: Steps.
  const stepsRaw = await vscode.window.showInputBox({
    title: "RF Skills: Generate Test Case (3/4)",
    prompt:
      "Steps (semicolon-separated). " +
      "Format: keyword    arg1    arg2 (4-space separator)",
    placeHolder:
      "e.g. Open Browser    https://example.com    chrome ; " +
      "Input Text    id=user    admin ; Click Button    id=login",
  });
  if (stepsRaw === undefined) {
    return "";
  }

  // Step 4: Tags.
  const tagsRaw = await vscode.window.showInputBox({
    title: "RF Skills: Generate Test Case (4/4)",
    prompt: "Tags (comma-separated, optional)",
    placeHolder: "e.g. smoke, login",
  });
  if (tagsRaw === undefined) {
    return "";
  }

  const steps = parseSteps(stepsRaw);
  const tags = parseCsv(tagsRaw);

  return JSON.stringify({
    tests: [
      {
        name: testName.trim(),
        steps,
        tags,
      },
    ],
  });
}

async function gatherTemplateInput(testName: string): Promise<string> {
  // Step 3: Template keyword.
  const templateKeyword = await vscode.window.showInputBox({
    title: "RF Skills: Generate Test Case (3/4)",
    prompt: "Template keyword name",
    placeHolder: "e.g. Login Should Succeed",
    validateInput: (v) =>
      v.trim() ? null : "Template keyword is required",
  });
  if (!templateKeyword) {
    return "";
  }

  // Step 4: Data rows + tags.
  const dataRaw = await vscode.window.showInputBox({
    title: "RF Skills: Generate Test Case (4/4)",
    prompt:
      "Data rows (semicolons separate rows, 4-space separates columns). " +
      "Optionally append |tags:smoke,regression at end.",
    placeHolder:
      "e.g. admin    secret ; user    pass123 |tags:smoke",
  });
  if (dataRaw === undefined) {
    return "";
  }

  let dataSection = dataRaw;
  let tags: string[] = [];
  const tagSplit = dataRaw.split("|tags:");
  if (tagSplit.length > 1) {
    dataSection = tagSplit[0];
    tags = parseCsv(tagSplit[1]);
  }

  const dataRows = dataSection
    .split(";")
    .map((row) =>
      row
        .trim()
        .split(/\s{4,}/)
        .map((c) => c.trim())
    )
    .filter((row) => row.some(Boolean));

  return JSON.stringify({
    tests: [
      {
        name: testName.trim(),
        template: templateKeyword.trim(),
        data_rows: dataRows,
        tags,
      },
    ],
  });
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function parseSteps(
  raw: string
): Array<{ keyword?: string; args?: string[]; line?: string }> {
  if (!raw.trim()) {
    return [];
  }
  return raw.split(";").map((part) => {
    const trimmed = part.trim();
    const cells = trimmed.split(/\s{4,}/);
    if (cells.length > 1) {
      const [keyword, ...args] = cells;
      return { keyword: keyword.trim(), args: args.map((a) => a.trim()) };
    }
    return { line: trimmed };
  });
}

function parseCsv(raw: string): string[] {
  if (!raw.trim()) {
    return [];
  }
  return raw
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

/**
 * Insert generated test case text into the active editor or a new document.
 *
 * If the active file has a `*** Test Cases ***` section the artifact is
 * appended at the end of that section.  Otherwise it opens a new document.
 */
async function insertTestCase(artifact: string): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    const doc = await vscode.workspace.openTextDocument({
      language: "robotframework",
      content: `*** Test Cases ***\n${artifact}\n`,
    });
    await vscode.window.showTextDocument(doc);
    return;
  }

  const document = editor.document;
  const text = document.getText();

  const tcSectionRegex = /^\*\*\*\s*Test\s*Cases?\s*\*\*\*/im;
  const nextSectionRegex = /^\*\*\*\s*.+\s*\*\*\*/gim;
  const tcMatch = tcSectionRegex.exec(text);

  let insertPosition: vscode.Position;

  if (tcMatch) {
    nextSectionRegex.lastIndex = tcMatch.index + tcMatch[0].length;
    const nextMatch = nextSectionRegex.exec(text);

    if (nextMatch) {
      const pos = document.positionAt(nextMatch.index);
      insertPosition = new vscode.Position(pos.line, 0);
    } else {
      insertPosition = new vscode.Position(document.lineCount, 0);
    }
  } else {
    insertPosition = editor.selection.active;
  }

  const snippet = `\n${artifact}\n`;

  await editor.edit((editBuilder) => {
    editBuilder.insert(insertPosition, snippet);
  });

  const revealPos = new vscode.Position(insertPosition.line + 1, 0);
  editor.revealRange(
    new vscode.Range(revealPos, revealPos),
    vscode.TextEditorRevealType.InCenter
  );
}

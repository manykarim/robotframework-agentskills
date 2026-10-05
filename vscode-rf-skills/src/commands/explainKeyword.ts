import * as vscode from "vscode";
import { invokePythonScript } from "../python/invoker.js";

/** A single keyword match from rf_libdoc.py --keyword. */
interface KeywordDetail {
  library: {
    name: string;
    type: string;
    version: string;
    doc: string;
    source: string | null;
  };
  keyword: {
    name: string;
    args: string[];
    doc: string;
    short_doc: string;
    tags: string[];
    deprecated: boolean;
    source: string | null;
    lineno: number | null;
    private: boolean;
  };
  usage: {
    raw: string[];
    required: string[];
    optional: string[];
    varargs: string[];
    kwargs: string[];
    defaults: Record<string, string>;
  };
}

interface LibdocKeywordResult {
  keyword_matches?: KeywordDetail[];
  matches?: Array<{
    keyword: { name: string; short_doc: string };
    library: { name: string };
    score: number;
  }>;
  hint?: string;
  errors?: Array<{ source: string; error: string }>;
}

/** Libraries to search when explaining a keyword at cursor. */
const DEFAULT_LIBRARIES: readonly string[] = [
  "BuiltIn",
  "Browser",
  "SeleniumLibrary",
  "AppiumLibrary",
  "RequestsLibrary",
  "REST",
  "Collections",
  "String",
  "OperatingSystem",
  "Process",
  "XML",
  "DateTime",
];

export function registerExplainKeyword(
  context: vscode.ExtensionContext
): void {
  const disposable = vscode.commands.registerCommand(
    "rfSkills.explainKeyword",
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("No active editor.");
        return;
      }

      const keywordName = getKeywordAtCursor(editor);
      if (!keywordName) {
        vscode.window.showWarningMessage(
          "Could not detect a keyword name at the cursor position."
        );
        return;
      }

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: `Looking up "${keywordName}"...`,
          cancellable: false,
        },
        async () => {
          const args = buildArgs(keywordName);
          const result = await invokePythonScript(
            context,
            "rf_libdoc.py",
            args
          );

          if (result.error) {
            vscode.window.showErrorMessage(
              `Keyword lookup failed: ${result.error}`
            );
            return;
          }

          const data = result.data as LibdocKeywordResult | undefined;
          if (!data) {
            vscode.window.showWarningMessage("No data returned.");
            return;
          }

          if (data.keyword_matches && data.keyword_matches.length > 0) {
            showKeywordPanel(data.keyword_matches[0]);
            return;
          }

          // Fallback: fuzzy matches.
          if (data.matches && data.matches.length > 0) {
            const items = data.matches.map((m) => ({
              label: m.keyword.name,
              description: `[${m.library.name}]`,
              detail: m.keyword.short_doc,
            }));
            vscode.window.showQuickPick(items, {
              title: `No exact match for "${keywordName}". Did you mean...`,
              placeHolder: "Select a keyword",
            });
            return;
          }

          vscode.window.showInformationMessage(
            data.hint ?? `No documentation found for "${keywordName}".`
          );
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

/**
 * Extract the keyword name under the cursor.
 *
 * In Robot Framework test files the body lines are indented with spaces and
 * the keyword is the first non-setting token on the line.  We grab the full
 * content of the line, strip leading whitespace, and then take everything
 * before the first four-space separator (which delimits arguments).
 *
 * If the cursor is on a blank or comment line, fall back to the word range.
 */
function getKeywordAtCursor(editor: vscode.TextEditor): string | undefined {
  const position = editor.selection.active;
  const line = editor.document.lineAt(position.line).text;
  const trimmed = line.trim();

  if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("***")) {
    return undefined;
  }

  // Skip Robot Framework settings like [Documentation], [Tags], etc.
  if (/^\[.+\]/.test(trimmed)) {
    return undefined;
  }

  // The keyword name is the first cell.  Cells are separated by 2+ spaces
  // or a tab character.  We also strip any variable assignment prefix like
  // ${var}=  or  @{list}=
  let cell = trimmed.split(/\s{2,}|\t/)[0];

  // Strip assignment prefix: ${var}=, @{list}=, &{dict}=
  cell = cell.replace(/^[$@&%]\{[^}]*\}\s*=?\s*/, "").trim();

  if (!cell) {
    // Fall back to word under cursor.
    const range = editor.document.getWordRangeAtPosition(position);
    return range ? editor.document.getText(range) : undefined;
  }

  return cell;
}

function buildArgs(keywordName: string): string[] {
  const args: string[] = ["--keyword", keywordName, "--pretty"];
  for (const lib of DEFAULT_LIBRARIES) {
    args.push("--library", lib);
  }
  return args;
}

function showKeywordPanel(detail: KeywordDetail): void {
  const kw = detail.keyword;
  const lib = detail.library;
  const usage = detail.usage;

  const channel = vscode.window.createOutputChannel("RF Keyword Docs", {
    log: true,
  });

  channel.appendLine(`=== ${kw.name} ===`);
  channel.appendLine(`Library:    ${lib.name} (${lib.type})`);
  if (lib.version) {
    channel.appendLine(`Version:    ${lib.version}`);
  }
  channel.appendLine("");

  // Argument table
  channel.appendLine("--- Arguments ---");
  if (usage.required.length > 0) {
    channel.appendLine(`  Required: ${usage.required.join(", ")}`);
  }
  if (usage.optional.length > 0) {
    const optWithDefaults = usage.optional.map((name) => {
      const def = usage.defaults[name];
      return def !== undefined ? `${name}=${def}` : name;
    });
    channel.appendLine(`  Optional: ${optWithDefaults.join(", ")}`);
  }
  if (usage.varargs.length > 0) {
    channel.appendLine(`  Varargs:  *${usage.varargs.join(", *")}`);
  }
  if (usage.kwargs.length > 0) {
    channel.appendLine(`  Kwargs:   **${usage.kwargs.join(", **")}`);
  }
  if (
    usage.required.length === 0 &&
    usage.optional.length === 0 &&
    usage.varargs.length === 0 &&
    usage.kwargs.length === 0
  ) {
    channel.appendLine("  (no arguments)");
  }
  channel.appendLine("");

  if (kw.tags.length > 0) {
    channel.appendLine(`Tags: ${kw.tags.join(", ")}`);
  }
  if (kw.deprecated) {
    channel.appendLine("** DEPRECATED **");
  }
  if (kw.source) {
    const loc = kw.lineno ? `${kw.source}:${kw.lineno}` : kw.source;
    channel.appendLine(`Source: ${loc}`);
  }
  channel.appendLine("");

  channel.appendLine("--- Documentation ---");
  channel.appendLine(kw.doc || "(no documentation)");
  channel.show(true);
}

import * as vscode from "vscode";
import { invokePythonScript } from "../python/invoker.js";

/** Libraries available for keyword search. */
const LIBRARY_OPTIONS: readonly string[] = [
  "All",
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

/** Shape of a single match returned by rf_libdoc.py --search. */
interface KeywordMatch {
  library: { name: string; type: string };
  keyword: {
    name: string;
    args: string[];
    doc: string;
    short_doc: string;
    tags: string[];
    deprecated: boolean;
    source: string | null;
    lineno: number | null;
  };
  score: number;
  reasons: string[];
}

/** Top-level JSON returned by rf_libdoc.py. */
interface LibdocSearchResult {
  libraries?: Array<{ name: string }>;
  matches?: KeywordMatch[];
  hint?: string;
  errors?: Array<{ source: string; error: string }>;
}

export function registerSearchKeyword(
  context: vscode.ExtensionContext
): void {
  const disposable = vscode.commands.registerCommand(
    "rfSkills.searchKeyword",
    async () => {
      // Step 1: Get search query.
      const query = await vscode.window.showInputBox({
        title: "RF Skills: Search Keywords",
        prompt: "Enter a keyword name or description to search for",
        placeHolder: "e.g. click element, wait until, open browser",
      });
      if (!query) {
        return;
      }

      // Step 2: Pick library.
      const library = await vscode.window.showQuickPick(
        LIBRARY_OPTIONS as unknown as string[],
        {
          title: "Search in which library?",
          placeHolder: "Select a library or All",
        }
      );
      if (!library) {
        return;
      }

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Searching keywords...",
          cancellable: false,
        },
        async () => {
          const args = buildArgs(query, library);
          const result = await invokePythonScript(
            context,
            "rf_libdoc.py",
            args
          );

          if (result.error) {
            vscode.window.showErrorMessage(
              `Keyword search failed: ${result.error}`
            );
            return;
          }

          const data = result.data as LibdocSearchResult | undefined;
          if (!data) {
            vscode.window.showWarningMessage(
              "No data returned from keyword search."
            );
            return;
          }

          if (data.errors && data.errors.length > 0) {
            const libs = data.errors.map((e) => e.source).join(", ");
            vscode.window.showWarningMessage(
              `Could not load: ${libs}. Is Robot Framework installed?`
            );
          }

          const matches = data.matches ?? [];
          if (matches.length === 0) {
            vscode.window.showInformationMessage(
              data.hint ?? "No matching keywords found."
            );
            return;
          }

          await showMatchPicker(context, matches);
        }
      );
    }
  );

  context.subscriptions.push(disposable);
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function buildArgs(query: string, library: string): string[] {
  const args: string[] = ["--search", query, "--pretty"];
  if (library === "All") {
    for (const lib of LIBRARY_OPTIONS) {
      if (lib !== "All") {
        args.push("--library", lib);
      }
    }
  } else {
    args.push("--library", library);
  }
  return args;
}

async function showMatchPicker(
  _context: vscode.ExtensionContext,
  matches: KeywordMatch[]
): Promise<void> {
  interface MatchItem extends vscode.QuickPickItem {
    match: KeywordMatch;
  }

  const items: MatchItem[] = matches.map((m) => ({
    label: m.keyword.name,
    description: `[${m.library.name}]  score: ${m.score}`,
    detail: m.keyword.short_doc || undefined,
    match: m,
  }));

  const picked = await vscode.window.showQuickPick(items, {
    title: "Keyword Search Results",
    placeHolder: "Select a keyword to view full documentation",
    matchOnDescription: true,
    matchOnDetail: true,
  });

  if (!picked) {
    return;
  }

  showKeywordDocumentation(picked.match);
}

function showKeywordDocumentation(match: KeywordMatch): void {
  const kw = match.keyword;
  const lib = match.library;

  const argsStr =
    kw.args.length > 0 ? kw.args.join("    ") : "(no arguments)";

  const tagsStr =
    kw.tags.length > 0 ? kw.tags.join(", ") : "none";

  const channel = vscode.window.createOutputChannel("RF Keyword Docs", {
    log: true,
  });

  channel.appendLine(`=== ${kw.name} ===`);
  channel.appendLine(`Library:    ${lib.name}`);
  channel.appendLine(`Arguments:  ${argsStr}`);
  channel.appendLine(`Tags:       ${tagsStr}`);
  channel.appendLine(`Deprecated: ${kw.deprecated ? "Yes" : "No"}`);
  if (kw.source) {
    const loc = kw.lineno ? `${kw.source}:${kw.lineno}` : kw.source;
    channel.appendLine(`Source:     ${loc}`);
  }
  channel.appendLine("");
  channel.appendLine("--- Documentation ---");
  channel.appendLine(kw.doc || "(no documentation)");
  channel.show(true);
}

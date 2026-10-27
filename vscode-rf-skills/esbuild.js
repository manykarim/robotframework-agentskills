const esbuild = require("esbuild");
const path = require("path");
const fs = require("fs");

const production = process.argv.includes("--production");
const watch = process.argv.includes("--watch");

/**
 * Plugin that forwards esbuild problems to the VS Code problem matcher.
 * @type {import('esbuild').Plugin}
 */
const esbuildProblemMatcherPlugin = {
  name: "esbuild-problem-matcher",
  setup(build) {
    build.onStart(() => {
      console.log("[watch] build started");
    });
    build.onEnd((result) => {
      for (const { text, location } of result.errors) {
        console.error(
          `> ${location.file}:${location.line}:${location.column}: error: ${text}`
        );
      }
      console.log("[watch] build finished");
    });
  },
};

/** Discover all test entry points in src/test/. */
function getTestEntryPoints() {
  const testDir = path.join(__dirname, "src", "test");
  if (!fs.existsSync(testDir)) {
    return [];
  }
  return fs
    .readdirSync(testDir)
    .filter((f) => f.endsWith(".test.ts"))
    .map((f) => path.join("src", "test", f));
}

async function main() {
  // Build the extension bundle
  const extCtx = await esbuild.context({
    entryPoints: ["src/extension.ts"],
    bundle: true,
    format: "cjs",
    minify: production,
    sourcemap: !production,
    sourcesContent: false,
    platform: "node",
    outfile: "dist/extension.js",
    external: ["vscode"],
    logLevel: "silent",
    plugins: [esbuildProblemMatcherPlugin],
  });

  // Build test files (each as a separate bundle so the test runner can load them)
  const testEntryPoints = getTestEntryPoints();
  let testCtx = null;

  if (testEntryPoints.length > 0 && !production) {
    testCtx = await esbuild.context({
      entryPoints: testEntryPoints,
      bundle: true,
      format: "cjs",
      sourcemap: true,
      sourcesContent: false,
      platform: "node",
      outdir: "dist/test",
      external: ["vscode", "mocha", "assert"],
      logLevel: "silent",
      plugins: [esbuildProblemMatcherPlugin],
    });
  }

  if (watch) {
    await extCtx.watch();
    if (testCtx) {
      await testCtx.watch();
    }
  } else {
    await extCtx.rebuild();
    await extCtx.dispose();
    if (testCtx) {
      await testCtx.rebuild();
      await testCtx.dispose();
    }
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

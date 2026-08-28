#!/usr/bin/env node
/* Render TeX formulas from stdin JSON to self-contained MathJax SVG fragments.
 * Input:  [{"tex":"x^2", "display":true}, ...]
 * Output: ["<mjx-container ...>...</mjx-container>", ...]
 */
const fs = require("fs");
const os = require("os");
const path = require("path");

// The packaged skill does not carry node_modules. Resolve MathJax from a
// user-writable cache installed by scripts/ensure_mathjax.sh, then fall back
// to a development checkout's local node_modules.
const cacheHome = process.platform === "darwin"
  ? path.join(os.homedir(), ".cache")
  : (process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache"));
const mathRoot = process.env.KAMI_MATHJAX_ROOT || path.join(cacheHome, "kami", "mathjax");
const roots = [mathRoot, path.join(__dirname, "..")];
const load = (id) => require(require.resolve(id, { paths: roots }));

try {
  const { mathjax } = load("mathjax-full/js/mathjax.js");
  const { TeX } = load("mathjax-full/js/input/tex.js");
  const { SVG } = load("mathjax-full/js/output/svg.js");
  const { liteAdaptor } = load("mathjax-full/js/adaptors/liteAdaptor.js");
  const { RegisterHTMLHandler } = load("mathjax-full/js/handlers/html.js");
  const { AllPackages } = load("mathjax-full/js/input/tex/AllPackages.js");

  const formulas = JSON.parse(fs.readFileSync(0, "utf8"));
  const adaptor = liteAdaptor();
  RegisterHTMLHandler(adaptor);
  const tex = new TeX({ packages: AllPackages });
  // `none` keeps every SVG self-contained, avoiding cross-formula path IDs.
  const svg = new SVG({ fontCache: "none" });
  const doc = mathjax.document("", { InputJax: tex, OutputJax: svg });
  const rendered = formulas.map(({ tex: source, display }) => {
    const node = doc.convert(source, { display: Boolean(display) });
    return adaptor.outerHTML(node);
  });
  process.stdout.write(JSON.stringify(rendered));
} catch (err) {
  process.stderr.write(`MathJax render failed: ${err.stack || err.message}\n`);
  process.exit(1);
}

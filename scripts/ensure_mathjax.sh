#!/usr/bin/env bash
# Ensure strict TeX -> SVG rendering is available for Kami.
set -euo pipefail

if [ "$(uname -s)" = "Darwin" ]; then
  # shared.configure_weasyprint_runtime repurposes XDG_CACHE_HOME for fontconfig.
  # Keep MathJax in its own stable user cache instead.
  CACHE_HOME="$HOME/.cache"
else
  CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
fi
MATH_ROOT="${KAMI_MATHJAX_ROOT:-$CACHE_HOME/kami/mathjax}"

if node - "$MATH_ROOT" <<'NODE' >/dev/null 2>&1
const root = process.argv[2];
try {
  require.resolve("mathjax-full/package.json", { paths: [root] });
  process.exit(0);
} catch (_) {
  process.exit(1);
}
NODE
then
  echo "OK: MathJax available at $MATH_ROOT"
  exit 0
fi

echo "Installing MathJax for strict LaTeX SVG rendering at $MATH_ROOT"
npm install --no-save --prefix "$MATH_ROOT" mathjax-full@3
echo "OK: MathJax installed"

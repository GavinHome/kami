#!/usr/bin/env python3
"""Strict TeX -> MathJax SVG rendering for Kami HTML documents.

Source convention:
  <span class="latex-inline" data-latex="...">...</span>
  <div class="latex-display" data-latex="...">...</div>

`render_latex_in_html` replaces those placeholders with self-contained SVG
formula fragments. It fails rather than falling back to raw TeX or Unicode
pseudo-formulas when MathJax is unavailable or a formula is invalid.

CLI:
  python3 scripts/math_render.py --in-place filled.html
  python3 scripts/math_render.py --check filled.html
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
NODE_RENDERER = SCRIPT_DIR / "mathjax_svg.js"
PLACEHOLDER_RE = re.compile(
    r'<(?P<tag>span|div)\s+class="latex-(?P<mode>inline|display)"\s+'
    r'data-latex="(?P<tex>[^"]*)"\s*>.*?</(?P=tag)>',
    re.S,
)


def _render_svg(formulas: list[dict]) -> list[str]:
    if not NODE_RENDERER.exists():
        raise RuntimeError(f"MathJax renderer missing: {NODE_RENDERER}")
    result = subprocess.run(
        ["node", str(NODE_RENDERER)],
        input=json.dumps(formulas, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or "MathJax process failed"
        if "mathjax-full" in detail or "Cannot find module" in detail:
            detail = "MathJax is unavailable; run `bash scripts/ensure_mathjax.sh`.\n" + detail
        raise RuntimeError(detail)
    try:
        out = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid MathJax output: {exc}") from exc
    if len(out) != len(formulas):
        raise RuntimeError("MathJax returned a mismatched formula count")
    return out


def render_latex_in_html(raw: str) -> str:
    """Replace every LaTeX placeholder with a strict MathJax SVG fragment."""
    matches = list(PLACEHOLDER_RE.finditer(raw))
    if not matches:
        return raw
    formulas = [
        {"tex": html.unescape(m.group("tex")), "display": m.group("mode") == "display"}
        for m in matches
    ]
    svgs = iter(_render_svg(formulas))

    def replace(match: re.Match) -> str:
        svg = next(svgs)
        if match.group("mode") == "display":
            return (
                '<div class="latex-display-svg" '
                'style="display:block;text-align:center;margin:10pt 0;break-inside:avoid;">'
                + svg + "</div>"
            )
        return (
            '<span class="latex-inline-svg" '
            'style="display:inline-block;vertical-align:middle;white-space:nowrap;">'
            + svg + "</span>"
        )

    return PLACEHOLDER_RE.sub(replace, raw)


def check_latex_html(raw: str) -> list[str]:
    issues = []
    pending = len(PLACEHOLDER_RE.findall(raw))
    if pending:
        issues.append(f"{pending} unrendered LaTeX placeholder(s)")
    # Raw display delimiters are forbidden in a completed HTML delivery.
    if re.search(r"\\\[|\\\]", raw):
        issues.append("raw display TeX delimiter \\[...\\] remains")
    if re.search(r'class="latex-(?:inline|display)"', raw):
        issues.append("LaTeX placeholder class remains")
    return issues


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--in-place", type=Path)
    group.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    path = args.in_place or args.check
    if not path.exists():
        print(f"ERROR: {path} not found")
        return 1
    raw = path.read_text(encoding="utf-8")
    if args.in_place:
        try:
            rendered = render_latex_in_html(raw)
        except RuntimeError as exc:
            print(f"ERROR: strict LaTeX rendering failed: {exc}")
            return 1
        path.write_text(rendered, encoding="utf-8")
        print(f"OK: {path}: rendered {len(PLACEHOLDER_RE.findall(raw))} LaTeX formula(s) to SVG")
        return 0
    issues = check_latex_html(raw)
    if issues:
        print(f"ERROR: {path}: " + "; ".join(issues))
        return 1
    print(f"OK: {path}: no raw or unrendered LaTeX placeholder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

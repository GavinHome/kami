#!/usr/bin/env python3
"""Render Kami HTML and ensure its PDF has usable sidebar bookmarks.

Usage: python3 scripts/add_outline.py filled.html output.pdf

Newer WeasyPrint versions emit a full heading outline. This script preserves
that hierarchy. Older renderers emit none, so it falls back to chapter anchors
from <section class="chapter" id="..."> and their first <h1> title.
"""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import render_pdf  # noqa: E402


class ChapterParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chapters = []
        self.in_chapter = False
        self.current_id = None
        self.in_h1 = False
        self.buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "section" and "chapter" in (a.get("class") or "").split() and a.get("id"):
            self.in_chapter, self.current_id = True, a["id"]
        elif tag == "h1" and self.in_chapter and self.current_id:
            self.in_h1, self.buf = True, []

    def handle_endtag(self, tag):
        if tag == "h1" and self.in_h1:
            title = " ".join("".join(self.buf).split())
            if title:
                self.chapters.append((self.current_id, title))
            self.in_h1 = False
            self.in_chapter = False
            self.current_id = None
        elif tag == "section":
            self.in_chapter = False
            self.current_id = None

    def handle_data(self, data):
        if self.in_h1:
            self.buf.append(data)


def main(argv):
    if len(argv) != 2:
        print("Usage: add_outline.py filled.html output.pdf")
        return 2
    html_path, out_path = map(Path, argv)
    raw = html_path.read_text(encoding="utf-8")
    parser = ChapterParser()
    parser.feed(raw)
    pages = render_pdf(html_path, out_path)

    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(str(out_path))
    try:
        existing = reader.outline
    except Exception:
        existing = []
    if existing:
        print(f"OK: {out_path.name}: {pages} pages, renderer outline preserved")
        return 0

    from weasyprint import HTML
    document = HTML(filename=str(html_path)).render()
    anchor_page = {}
    for page_index, page in enumerate(document.pages):
        for anchor in getattr(page, "anchors", set()):
            anchor_page.setdefault(anchor, page_index)

    writer = PdfWriter()
    writer.append(reader)
    count = 0
    for anchor, title in parser.chapters:
        if anchor in anchor_page:
            writer.add_outline_item(title, anchor_page[anchor])
            count += 1
    with out_path.open("wb") as f:
        writer.write(f)
    print(f"OK: {out_path.name}: {pages} pages, fallback outline with {count} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

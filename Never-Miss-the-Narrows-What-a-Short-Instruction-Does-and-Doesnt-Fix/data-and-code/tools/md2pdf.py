#!/usr/bin/env python3
"""Render a Markdown document to PDF (python-markdown + headless Chromium). Usage: md2pdf.py in.md out.pdf"""
import sys
from pathlib import Path
import markdown
from playwright.sync_api import sync_playwright

CSS = """
@page { size: Letter; margin: 18mm 16mm; }
body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.42; color: #1a1a1a; }
h1 { font-size: 17pt; margin: 0 0 6pt; } h2 { font-size: 12.5pt; margin: 14pt 0 4pt; border-bottom: 1px solid #ddd; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 10pt 0 3pt; } p, li { margin: 3pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 8.8pt; page-break-inside: auto; }
tr { page-break-inside: avoid; } th, td { border: 1px solid #ccc; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #f2f2f2; } code { font-family: Menlo, Consolas, monospace; font-size: 8.6pt; background: #f5f5f5; padding: 0 2px; }
pre { background: #f5f5f5; padding: 6pt; white-space: pre-wrap; word-break: break-word; font-size: 8.4pt; }
"""


def main(src, dst):
    html = markdown.markdown(Path(src).read_text(encoding="utf-8"), extensions=["tables", "fenced_code", "sane_lists"])
    doc = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html}</body></html>"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(doc, wait_until="load")
        pg.pdf(path=dst, format="Letter", print_background=True,
               margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"},
               display_header_footer=True, header_template="<span></span>",
               footer_template="<div style='font-size:7pt;width:100%;text-align:center;color:#888'><span class='pageNumber'></span>/<span class='totalPages'></span></div>")
        b.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

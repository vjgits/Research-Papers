import sys; sys.path.insert(0, "tools")
from pathlib import Path
import markdown
from md2pdf import CSS
from playwright.sync_api import sync_playwright
root = Path.cwd()
src = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root/"docs/paper/PAPER_Never_Miss_the_Narrows_v4.md"; dst = src.with_suffix(".pdf")  # usage: python3 tools/render_paper.py docs/paper/<file>.md
md = src.read_text().replace("../../outputs/figures/", f"file://{root}/outputs/figures/")
html = markdown.markdown(md, extensions=["tables","fenced_code","sane_lists"])
css = CSS + "img{max-width:100%;display:block;margin:8pt auto 2pt;} em{color:#444} h1{font-size:18pt;line-height:1.2}"
tmp = src.parent/"_tmp.html"
tmp.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{html}</body></html>")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.goto(f"file://{tmp}", wait_until="load")
    pg.pdf(path=str(dst), format="Letter", print_background=True,
        margin={"top":"16mm","bottom":"16mm","left":"16mm","right":"16mm"}, display_header_footer=True,
        header_template="<span></span>",
        footer_template="<div style='font-size:7pt;width:100%;text-align:center;color:#888'><span class='pageNumber'></span>/<span class='totalPages'></span></div>")
    b.close()
tmp.unlink()

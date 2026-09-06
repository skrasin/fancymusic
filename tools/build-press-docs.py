#!/usr/bin/env python3
"""Собирает DOCX и PDF пресс-релиза из одного исходника Markdown.

    python3 tools/build-press-docs.py <slug>

Читает  projects/<slug>/output/press-release.md
Пишет   projects/<slug>/output/press-release.docx
        projects/<slug>/output/press-release.pdf
и кладёт копии рядом со страницей релиза, в docs/releases/<slug>/,
чтобы кнопки скачивания на странице работали.

Оба файла собираются из одного Markdown, поэтому содержание совпадает,
а оформление у каждого своё — по возможностям формата.

DOCX — python-docx. Bebas и Inter в документ не вкладываются, у получателя
их нет: заголовки идут Arial Narrow (ближайший узкий гротеск, есть и в Word,
и в LibreOffice), текст — Arial. Фирменные цвета сохраняются.

PDF — печать через Chromium, а не конвертация DOCX: в этой системе
LibreOffice стоит без Writer и документы не открывает. Заодно PDF получается
с настоящими Bebas и Inter, потому что браузер грузит веб-шрифты бренда.
"""
import re
import shutil
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor, Cm

ROOT = Path(__file__).resolve().parent.parent
INK = RGBColor(0x2E, 0x2E, 0x2E)
RED = RGBColor(0xFF, 0x26, 0x26)
GREY = RGBColor(0x6F, 0x6F, 0x6F)
DISPLAY_FONT = "Arial Narrow"
TEXT_FONT = "Arial"


def style_run(run, *, font=TEXT_FONT, size=11, color=INK, bold=False, caps=False):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.all_caps = caps
    return run


def inline(paragraph, text, **kw):
    """Разбирает **полужирный** и остальное кладёт обычным начертанием."""
    for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not chunk:
            continue
        style_run(paragraph.add_run(chunk), bold=(i % 2 == 1) or kw.pop("bold", False), **kw)


def build_docx(md: str, dst: Path) -> None:
    doc = Document()
    section = doc.sections[0]
    section.left_margin = section.right_margin = Cm(2.5)
    section.top_margin = section.bottom_margin = Cm(2.2)

    normal = doc.styles["Normal"]
    normal.font.name = TEXT_FONT
    normal.font.size = Pt(11)
    normal.font.color.rgb = INK
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.35

    for raw in md.split("\n\n"):
        block = raw.strip()
        if not block:
            continue

        if block.startswith("# "):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            style_run(p.add_run(block[2:].strip()),
                      font=DISPLAY_FONT, size=26, color=INK, bold=True, caps=True)

        elif block.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after = Pt(4)
            style_run(p.add_run(block[3:].strip()),
                      font=DISPLAY_FONT, size=14, color=RED, bold=True, caps=True)

        elif block.startswith(">"):
            body = " ".join(l.lstrip("> ").strip() for l in block.splitlines() if l.strip("> ").strip())
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            p.paragraph_format.space_before = Pt(10)
            inline(p, body, font=DISPLAY_FONT, size=14, color=INK, caps=True)

        elif all(l.lstrip().startswith(("- ", "* ")) for l in block.splitlines()):
            for line in block.splitlines():
                p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.space_after = Pt(2)
                inline(p, line.lstrip("-* ").strip())

        else:
            lines = [l.strip() for l in block.splitlines()]
            # строка-подзаголовок под титулом: набирается серым
            grey = len(lines) > 1 and lines[0].startswith("**")
            p = doc.add_paragraph()
            inline(p, " ".join(lines), color=GREY if grey else INK)

    m = re.search(r"^#\s+(.+)$", md, re.M)
    doc.core_properties.title = (m.group(1).strip() if m else "Пресс-релиз")
    doc.core_properties.author = "FANCYMUSIC"
    doc.save(dst)


PRINT_CSS = """
@page { size: A4; margin: 18mm 20mm; }
body { font-family: 'FM Text', Inter, Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.5; color: #2e2e2e; }
h1 { font-family: 'FM Display', Impact, sans-serif; font-weight: 400;
     text-transform: uppercase; font-size: 30pt; line-height: 1; margin: 0 0 6pt;
     letter-spacing: .01em; }
h2 { font-family: 'FM Display', Impact, sans-serif; font-weight: 400;
     text-transform: uppercase; font-size: 13pt; color: #ff2626;
     margin: 18pt 0 4pt; letter-spacing: .01em;
     break-after: avoid; }
p { margin: 0 0 7pt; }
strong { font-weight: 600; }
blockquote { margin: 12pt 0; padding-left: 8pt; border-left: 2.5pt solid #ff2626;
             font-family: 'FM Display', Impact, sans-serif; font-weight: 400;
             text-transform: uppercase; font-size: 14pt; line-height: 1.1; }
ul { padding-left: 14pt; margin: 0 0 7pt; }
li { margin-bottom: 2pt; }
a { color: #2e2e2e; text-decoration: none; }
.subtitle { color: #6f6f6f; }
"""


def build_pdf(md: str, dst: Path) -> Path:
    """Печатает PDF из того же Markdown через Chromium."""
    import markdown as md_lib
    from playwright.sync_api import sync_playwright

    html_body = md_lib.markdown(md, extensions=["nl2br"])
    brand = (ROOT / "brand").as_uri()
    # заголовок первого уровня становится заголовком PDF в свойствах файла
    m = re.search(r"^#\s+(.+)$", md, re.M)
    doc_title = f"{m.group(1).strip()} — пресс-релиз FANCYMUSIC" if m else "Пресс-релиз FANCYMUSIC"
    page_html = (
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f"<title>{doc_title}</title>"
        f'<link rel="stylesheet" href="{brand}/fonts.css">'
        f"<style>{PRINT_CSS}</style></head><body>{html_body}</body></html>"
    )
    tmp = dst.with_suffix(".print.html")
    tmp.write_text(page_html)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            page = browser.new_page()
            page.goto(tmp.as_uri(), wait_until="networkidle")
            page.wait_for_timeout(600)
            page.pdf(path=str(dst), format="A4", print_background=True)
            browser.close()
    finally:
        tmp.unlink(missing_ok=True)
    return dst


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    slug = sys.argv[1]
    src = ROOT / "projects" / slug / "output" / "press-release.md"
    if not src.exists():
        print(f"нет исходника: {src}")
        return 1

    out_dir = src.parent
    md = src.read_text()
    docx_path = out_dir / "press-release.docx"
    pdf_path = out_dir / "press-release.pdf"
    build_docx(md, docx_path)
    build_pdf(md, pdf_path)

    page_dir = ROOT / "docs" / "releases" / slug
    if page_dir.exists():
        for f in (docx_path, pdf_path):
            shutil.copy(f, page_dir / f.name)
        print(f"скопировано в {page_dir.relative_to(ROOT)}")

    for f in (docx_path, pdf_path):
        print(f"{f.relative_to(ROOT)} — {f.stat().st_size // 1024} КБ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Собирает чистый Word-документ программы концерта из Markdown.

    python3 tools/build-program-doc.py <slug>

Источник: projects/<slug>/output/program.md
Результат: projects/<slug>/output/program.docx

Документ без оформления: только Arial 10 pt, чёрный текст, без таблиц, подчёркиваний,
цветов и рамок. Заголовки набраны заглавными, списки — стандартные
маркированные и нумерованные стили Word. Отступов между абзацами нет:
абзацы разделены пустыми строками. Ссылки выводятся адресом как есть.

Разметка: «# Название», абзац сразу под ним — подзаголовок, «## Раздел»,
«**Ключ:** значение» — отдельная строка, «1. пункт» — нумерованный список,
«- пункт» — маркированный, остальное — абзацы.
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
FONT = "Arial"


def set_font(run_or_style, size=None, bold=None):
    f = run_or_style.font
    f.name = FONT
    el = run_or_style.element.get_or_add_rPr() if hasattr(run_or_style, "element") and hasattr(run_or_style.element, "get_or_add_rPr") else run_or_style._element.get_or_add_rPr()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        el.rFonts.set(qn(attr), FONT)
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold


def build(md: str) -> Document:
    doc = Document()
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.5)

    for name in ("Normal", "List Bullet", "List Number"):
        st = doc.styles[name]
        set_font(st, 10, False)
        st.font.color.rgb = None
        st.paragraph_format.space_before = Pt(0)
        st.paragraph_format.space_after = Pt(0)
        st.paragraph_format.line_spacing = 1.0

    def para(text, style=None, bold=None):
        p = doc.add_paragraph(style=style)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        set_font(p.add_run(text), 10, bold)
        return p

    def blank():
        doc.add_paragraph()

    def kind(ln):
        if ln.startswith("# "):
            return "title"
        if ln.startswith("## "):
            return "heading"
        if ln.startswith("- "):
            return "bullet"
        if re.match(r"^\d+\. ", ln):
            return "number"
        if re.match(r"^\*\*[^*]+:\*\*", ln):
            return "fact"
        return "text"

    lines = [l for l in md.split("\n") if l.strip()]
    prev = None
    for ln in lines:
        k = kind(ln)
        # пустая строка между блоками; подряд идущие пункты одного списка и факты — вместе,
        # заголовок прижат к своему тексту
        if prev and not (k == prev and k in ("bullet", "number", "fact")) and prev != "heading":
            blank()
        if k == "title":
            para(ln[2:].upper(), bold=True)
        elif k == "heading":
            p = para(ln[3:].upper(), bold=True)
            p.paragraph_format.keep_with_next = True
        elif k == "bullet":
            para(ln[2:], style="List Bullet")
        elif k == "number":
            para(re.sub(r"^\d+\. ", "", ln), style="List Number")
        else:
            para(ln)
        prev = k
    doc.core_properties.title = md.split("\n", 1)[0].lstrip("# ").strip()
    return doc


def main():
    slug = sys.argv[1]
    out = ROOT / "projects" / slug / "output"
    build((out / "program.md").read_text(encoding="utf-8")).save(out / "program.docx")
    print(f"готово: {out / 'program.docx'}")


if __name__ == "__main__":
    main()

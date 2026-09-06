#!/usr/bin/env python3
"""Собирает страницу релиза из шаблона и данных проекта.

    python3 tools/build-release-page.py <slug>

Читает  templates/release-page.html
        projects/<slug>/page.json — фактура: заголовок, дата, ссылки, обложка
        projects/<slug>/output/press-release.md — вся проза
Пишет   docs/releases/<slug>/index.html

Текст живёт только в Markdown: и страница, и DOCX с PDF собираются из него
одним разбором (tools/release_content.py), поэтому разойтись не могут.
Правки вёрстки идут в шаблон и в brand/release.css.
Руками index.html не трогать: он перезаписывается.

В page.json:
  values      — фактура и плейсхолдеры шаблона, кроме прозы
  artist_links, label_links — списки [иконка, подпись, ссылка];
                порядок в файле = порядок на странице
Заголовок, лид, основной текст, цитату и справки подставляет сборщик
из Markdown; спрайт пиктограмм и размеры файлов — тоже.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_content

ROOT = Path(__file__).resolve().parent.parent


def links(items):
    return "\n      ".join(
        f'<li><a href="{url}"><svg viewBox="0 0 24 24" aria-hidden="true">'
        f'<use href="#{icon}"/></svg><span>{label}</span></a></li>'
        for icon, label, url in items)


def size_kb(path: Path) -> str:
    return f"{path.stat().st_size // 1024} КБ" if path.exists() else ""


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    slug = sys.argv[1]
    data_path = ROOT / "projects" / slug / "page.json"
    if not data_path.exists():
        print(f"нет данных страницы: {data_path}")
        return 1

    data = json.loads(data_path.read_text())
    template = (ROOT / "templates/release-page.html").read_text()
    out_dir = ROOT / "docs/releases" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    sprite = (ROOT / "brand/icons.svg").read_text().replace(
        '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">',
        '<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" style="display:none">')

    prose = release_content.load(ROOT, slug)
    values = dict(data["values"])
    values["HEADLINE"] = prose["title"]
    values["LEAD"] = release_content.bold_to_html(prose["lead"])
    values["BODY"] = release_content.blocks_to_html(prose["body"])
    quote, author = prose["quote"] or ("", "")
    values["QUOTE"], values["QUOTE_AUTHOR"] = quote, author
    for heading, blocks in prose["sections"]:
        key = {"Об артисте": "ABOUT_ARTIST", "О лейбле": "ABOUT_LABEL"}.get(heading)
        if key:
            values[key] = release_content.blocks_to_html(blocks)
    values["ICON_SPRITE"] = sprite
    values["ARTIST_LINKS"] = links(data["artist_links"])
    values["LABEL_LINKS"] = links(data["label_links"])
    values["DOCX_SIZE"] = size_kb(out_dir / "press-release.docx")
    values["PDF_SIZE"] = size_kb(out_dir / "press-release.pdf")

    page = template
    for key, value in values.items():
        page = page.replace("{{" + key + "}}", value)

    left = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", page)))
    if left:
        print("НЕЗАКРЫТЫЕ ПЛЕЙСХОЛДЕРЫ:", ", ".join(left))
        return 1

    (out_dir / "index.html").write_text(page)
    print(f"собрано: docs/releases/{slug}/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


def event_block(ev) -> str:
    """Блок события: презентация, концерт. Пустой event — блока нет."""
    if not ev:
        return ""

    def column(title, rows):
        if not rows:
            return ""
        lis = "".join("<li>" + r + "</li>" for r in rows)
        return '<div><p class="fm-eyebrow">' + title + "</p><ul>" + lis + "</ul></div>"

    parts = ['<section class="rl-event">',
             "<h2>" + ev.get("title", "Презентация альбома") + "</h2>",
             '<p class="rl-event__when">' + ev.get("when", "") + "</p>"]
    where = " · ".join(x for x in (ev.get("venue"), ev.get("address")) if x)
    if where:
        parts.append('<p class="rl-event__where">' + where + "</p>")
    if ev.get("intro"):
        parts.append("<p>" + ev["intro"] + "</p>")
    cols = column("Программа", ev.get("program")) + column("Исполнители", ev.get("lineup"))
    if cols:
        parts.append('<div class="rl-event__cols">' + cols + "</div>")
    if ev.get("note"):
        parts.append('<p class="rl-event__note">' + ev["note"] + "</p>")
    if ev.get("url"):
        label = ev.get("button", "Купить билет")
        if ev.get("price"):
            label += " · " + ev["price"]
        parts.append('<a class="fm-btn fm-btn--solid" href="' + ev["url"] +
                     '" target="_blank" rel="noopener">' + label + "</a>")
    parts.append("</section>")
    return "".join(parts)


def links_block(label: str, items) -> str:
    """Подпись и чипы. Пустой список — пустой блок, без висящей подписи.

    items — либо плоский список [иконка, подпись, ссылка], либо список групп
    {"name": ..., "links": [...]}: у дуэта и ансамбля ссылки каждого участника
    идут отдельным рядом под его именем, иначе одинаковые чипы не различить.
    """
    if not items:
        return ""
    head = f'<p class="fm-eyebrow" style="margin-top: var(--fm-space-6)">{label}</p>\n'
    if isinstance(items[0], dict):
        rows = "".join(
            f'<p class="rl-links-name">{g["name"]}</p>'
            f'<ul class="rl-links">{links(g["links"])}</ul>' for g in items)
        return head + f'<div class="rl-links-groups">{rows}</div>'
    return head + (f'      <ul class="rl-links" style="margin-top: var(--fm-space-3)">'
                   f"{links(items)}</ul>")


def size_kb(path: Path) -> str:
    return f"{path.stat().st_size // 1024} КБ" if path.exists() else ""


def build_favicons(cover: Path, out_dir: Path) -> str:
    """Делает иконку вкладки из обложки релиза.

    Класть в таб саму обложку расточительно: браузер тянет её ради 16×16.
    Поэтому рядом со страницей кладутся уменьшенные копии — 32 и 180 px,
    последняя нужна для иконки на домашнем экране iOS.
    Если обложки нет, страница берёт общий знак лейбла.
    """
    if not cover.exists():
        return ('<link rel="icon" href="../../favicon.svg" type="image/svg+xml">')

    from PIL import Image
    src = Image.open(cover).convert("RGB")
    for size, name in ((32, "favicon-32.png"), (180, "apple-touch-icon.png")):
        src.resize((size, size), Image.LANCZOS).save(out_dir / name, "PNG", optimize=True)
    # знак лейбла в SVG сюда не подставляется: браузер предпочёл бы его
    # растровой обложке, и иконка релиза не появилась бы
    return ('<link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png">\n'
            '<link rel="icon" href="apple-touch-icon.png" sizes="180x180" type="image/png">\n'
            '<link rel="apple-touch-icon" href="apple-touch-icon.png">')


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
    cover_name = values.get("COVER_FILE") or ""
    values["FAVICON_TAGS"] = build_favicons(out_dir / cover_name, out_dir) if cover_name \
        else '<link rel="icon" href="../../favicon.svg" type="image/svg+xml">'
    values["HEADLINE"] = prose["title"]
    values["LEAD"] = release_content.bold_to_html(prose["lead"])
    # ссылка сразу после лида (например, на страницу события); пусто — нет строки
    lead_url = values.get("LEAD_LINK_URL", "").strip()
    values["LEAD_LINK"] = (
        '<p class="rl-lead-link"><a class="fm-btn fm-btn--solid" href="' + lead_url + '">'
        + (values.get("LEAD_LINK_LABEL") or lead_url) + '</a></p>' if lead_url else "")
    values["BODY"] = release_content.blocks_to_html(prose["body"])
    quote_body, author = prose["quote"] or ([], "")
    quote_html = ""
    if quote_body:
        cls = ("rl-quote rl-quote--verse"
               if release_content.is_verse(quote_body) else "rl-quote")
        text = "<br>".join(release_content.bold_to_html(l) for l in quote_body)
        footer = f"<footer>{author}</footer>" if author else ""
        quote_html = f'<blockquote class="{cls}">{text}{footer}</blockquote>'
    # место цитаты задаёт исходник: выше лида — эпиграф под заголовком
    first = prose["quote_first"]
    values["QUOTE_BEFORE"] = quote_html if first else ""
    values["QUOTE_AFTER"] = "" if first else quote_html
    for heading, blocks in prose["sections"]:
        if heading in release_content.ARTIST_SECTIONS:
            values["ABOUT_ARTIST"] = release_content.blocks_to_html(blocks)
            values["ABOUT_ARTIST_HEADING"] = heading
        elif heading in release_content.LABEL_SECTIONS:
            values["ABOUT_LABEL"] = release_content.blocks_to_html(blocks)
    values["ICON_SPRITE"] = sprite
    photo = values.pop("PRESS_PHOTO", "").strip()
    if photo:
        credit = values.pop("PRESS_PHOTO_CREDIT", "").strip()
        alt = values.pop("PRESS_PHOTO_ALT", "").strip()
        caption = f"<span>Фото: {credit}</span>" if credit else "<span></span>"
        values["PRESS_PHOTO_BLOCK"] = (
            f'<figure class="rl-photo"><img src="{photo}" alt="{alt}" loading="lazy">'
            f'<figcaption>{caption}'
            f'<a href="{photo}" download>Скачать фото</a></figcaption></figure>')
    else:
        values["PRESS_PHOTO_BLOCK"] = ""
        values.pop("PRESS_PHOTO_CREDIT", None)
        values.pop("PRESS_PHOTO_ALT", None)

    values["EVENT_BLOCK"] = event_block(data.get("event"))

    embed = values.pop("PLAYER_EMBED", "").strip()
    values["PLAYER_BLOCK"] = f'<div class="rl-player">{embed}</div>' if embed else ""
    values["ARTIST_LINKS_BLOCK"] = links_block(
        values.pop("ARTIST_LINKS_LABEL", "Ссылки на страницы артиста"),
        data["artist_links"])
    values["LABEL_LINKS_BLOCK"] = links_block(
        values.pop("LABEL_LINKS_LABEL", "Ссылки на страницы лейбла"),
        data["label_links"])
    gdoc = values.pop("GDOC_URL", "").strip()
    values["GDOC_BUTTON"] = (
        f'<a href="{gdoc}" target="_blank" rel="noopener">'
        '<svg viewBox="0 0 24 24" aria-hidden="true"><use href="#i-external"/></svg>'
        "<span>Google&nbsp;Docs</span></a>") if gdoc else ""
    values["DOCX_SIZE"] = size_kb(out_dir / "press-release.docx")
    values["PDF_SIZE"] = size_kb(out_dir / "press-release.pdf")

    page = template
    contact = values.pop("PRESS_CONTACT", "").strip()
    values["PRESS_CONTACT_ROW"] = (
        "<li><span>Контакт</span><span>" + contact + "</span></li>" if contact else "")
    for key, value in values.items():
        page = page.replace("{{" + key + "}}", value)

    left = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", page)))
    if left:
        print("НЕЗАКРЫТЫЕ ПЛЕЙСХОЛДЕРЫ:", ", ".join(left))
        return 1

    # версия у стилей по содержимому: браузер не держит старый CSS из кэша
    import hashlib
    for css in ("fonts.css", "design-tokens.css", "base.css", "release.css"):
        digest = hashlib.sha1((ROOT / "docs/assets" / css).read_bytes()).hexdigest()[:8]
        page = page.replace(f'assets/{css}"', f'assets/{css}?v={digest}"')
    # нет страницы релиза — кнопка не нужна
    page = page.replace('<a class="fm-btn fm-btn--outline" href="">Страница релиза</a>', "")
    (out_dir / "index.html").write_text(page)
    print(f"собрано: docs/releases/{slug}/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

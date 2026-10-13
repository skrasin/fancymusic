"""Разбор прозы пресс-релиза. Общий для страницы и для документов.

Единственный источник текста — projects/<slug>/output/press-release.md.
page.json хранит только фактуру: заголовок, дату, ссылки, обложку, контакты.
Так страница и документы не могут разойтись ни по тексту, ни по заголовку.

Структура исходника:

    # Заголовок

    Лид-абзац.

    Основной текст, сколько угодно абзацев.

    > Цитата
    >
    > — Источник

    ## Об артисте
    ...
    ## О лейбле
    ...

Разделы «Ссылки» и «Контакты» в исходнике не пишутся: они собираются
из page.json.
"""
import re
from pathlib import Path

SERVICE_SECTIONS = {"Ссылки", "Контакты для прессы"}

# Раздел об исполнителях называется по-разному в зависимости от состава:
# у сольного релиза «Об артисте», у дуэта или ансамбля — «Об артистах».
ARTIST_SECTIONS = {"Об артисте", "Об артистах"}
LABEL_SECTIONS = {"О лейбле"}


def parse(md: str) -> dict:
    """Делит исходник на лид, основной текст, цитату и разделы."""
    # комментарии-подсказки в исходнике не должны попадать ни в разметку,
    # ни тем более в DOCX и PDF, где они видны обычным текстом
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    blocks = [b.strip() for b in md.split("\n\n") if b.strip()]
    doc = {"title": "", "lead": "", "body": [], "quote": None,
           "quote_first": False, "sections": []}
    current = None
    for block in blocks:
        if block.startswith("# "):
            doc["title"] = block[2:].strip()
        elif block.startswith("## "):
            name = block[3:].strip()
            current = None if name in SERVICE_SECTIONS else (name, [])
            if current:
                doc["sections"].append(current)
        elif current is not None:
            current[1].append(block)
        elif block.startswith(">"):
            doc["quote"] = split_quote(block)
            # цитата выше лида — эпиграф: идёт сразу под заголовком
            doc["quote_first"] = not doc["lead"]
        elif not doc["lead"]:
            doc["lead"] = one_line(block)
        else:
            doc["body"].append(block)
    return doc


def one_line(block: str) -> str:
    return " ".join(l.strip() for l in block.splitlines())


def split_quote(block: str) -> tuple[list[str], str]:
    """Возвращает строки цитаты и автора.

    Переносы строк сохраняются: цитата в одну строку — проза, в несколько —
    стихи. От этого зависит и вёрстка: прозаическая цитата набирается
    дисплейным шрифтом в прописных, стихи — как есть, строчными и построчно.
    Поэтому прозаическую цитату в исходнике писать одной строкой.
    """
    lines = [l.lstrip("> ").strip() for l in block.splitlines()]
    lines = [l for l in lines if l]
    body = [l for l in lines if not l.startswith("—")]
    author = next((l.lstrip("— ").strip() for l in lines if l.startswith("—")), "")
    return body, author


def is_verse(body: list[str]) -> bool:
    return len(body) > 1


def bold_to_html(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def blocks_to_html(blocks, *, quote_class="rl-quote") -> str:
    """Абзацы, списки и цитаты — в разметку страницы."""
    out = []
    for block in blocks:
        if block.startswith(">"):
            body, author = split_quote(block)
            footer = f"<footer>{author}</footer>" if author else ""
            cls = quote_class + (" rl-quote--verse" if is_verse(body) else "")
            text = "<br>".join(bold_to_html(l) for l in body)
            out.append(f'<blockquote class="{cls}" '
                       f'style="font-size: var(--fm-text-h3); margin-top: var(--fm-space-5)">'
                       f"{text}{footer}</blockquote>")
        elif all(l.lstrip().startswith(("- ", "* ")) for l in block.splitlines()):
            items = "".join(f"<li>{bold_to_html(l.lstrip('-* ').strip())}</li>"
                            for l in block.splitlines())
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{bold_to_html(one_line(block))}</p>")
    return "\n".join(out)


def load(root: Path, slug: str) -> dict:
    return parse((root / "projects" / slug / "output" / "press-release.md").read_text())

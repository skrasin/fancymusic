#!/usr/bin/env python3
"""Собирает страницу списка Telegram-каналов для питчинга.

    python3 tools/build-channels-page.py

Читает  templates/channels-page.html
        projects/pr-telegram-channels/channels.json
Пишет   docs/pr/telegram/index.html

Данные вшиваются в страницу, а не подгружаются fetch: так она открывается
и по file://, и на Pages, и не зависит от второго запроса.
Руками index.html не трогать — он перезаписывается.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "channels-page.html"
DATA = ROOT / "projects" / "pr-telegram-channels" / "channels.json"
OUT = ROOT / "docs" / "pr" / "telegram" / "index.html"

MONTHS = ("января февраля марта апреля мая июня июля августа сентября "
          "октября ноября декабря").split()


def human_date(iso: str) -> str:
    try:
        y, m, d = (int(part) for part in iso.split("-"))
        return f"{d} {MONTHS[m - 1]} {y}"
    except (ValueError, IndexError):
        return iso


def plural(n: int) -> str:
    if 11 <= n % 100 <= 14:
        return f"{n} каналов"
    return f"{n} " + {1: "канал", 2: "канала", 3: "канала", 4: "канала"}.get(n % 10, "каналов")


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    channels = data["channels"]

    # В страницу уезжает только то, что она рисует.
    fields = ("name", "tme", "imi", "subscribers", "category", "genres",
              "author", "description", "status")
    slim = [{k: c.get(k) for k in fields if c.get(k) not in (None, "", [])}
            for c in channels]
    for c in slim:
        c.setdefault("genres", [])

    payload = json.dumps(slim, ensure_ascii=False).replace("</", "<\\/")
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("{{DATA}}", payload)
            .replace("{{COLLECTED_AT}}", human_date(data.get("collected_at", "")))
            .replace("{{TOTAL}}", plural(len(channels))))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)} — {len(channels)} каналов")


if __name__ == "__main__":
    main()

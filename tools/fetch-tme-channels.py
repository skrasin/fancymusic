#!/usr/bin/env python3
"""Добавляет в список каналы по ссылкам t.me: название, описание, подписчики.

    python3 tools/fetch-tme-channels.py https://t.me/allthatjazz t.me/warhol ...
    python3 tools/fetch-tme-channels.py --file links.txt
    python3 tools/fetch-tme-channels.py --refresh      # обновить цифры у всех

Данные берутся с публичной страницы канала t.me/<имя>: заголовок,
описание и счётчик подписчиков. Категорию и жанры Telegram не отдаёт —
у новых каналов они пустые, их проставляют руками в channels.json
(поле genres_source: fancymusic — классификация наша, не источника).

Ручные поля у уже внесённых каналов не затираются, обновляются только
подписчики. Между запросами пауза.
"""
import argparse
import html
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "projects" / "pr-telegram-channels" / "channels.json"
PAUSE = 1.0
UA = "Mozilla/5.0 (FancymusicBot; mail@fancymusic.ru)"


def handle(link: str) -> str | None:
    m = re.search(r"(?:t\.me|telegram\.me)/(?:s/)?([A-Za-z0-9_]{4,})", link)
    return m.group(1).lower() if m else None


# Регистрация в реестре РКН и на Госуслугах для питчинга бесполезна.
REGISTRY = re.compile(r"(?:РКН|№)\s*:?\s*\S+|https?://(?:www\.)?gosuslugi\.ru/\S+", re.I)


def clean(text: str) -> str:
    return " ".join(REGISTRY.sub("", text).split())


def meta(page: str, prop: str) -> str:
    m = re.search(rf'<meta property="{prop}" content="([^"]*)"', page)
    return html.unescape(m.group(1)).strip() if m else ""


def parse_count(text: str) -> int | None:
    """«12 345 subscribers», «1.2K subscribers» → число."""
    m = re.search(r"([\d][\d\s.,]*)\s*([KM])?\s*(?:subscribers|members)", text.replace("\xa0", " "))
    if not m:
        return None
    num = m.group(1).replace(" ", "")
    mult = {"K": 1_000, "M": 1_000_000}.get(m.group(2) or "", 1)
    if mult > 1:
        return int(float(num.replace(",", ".")) * mult)
    return int(num.replace(",", "").replace(".", ""))


def fetch(name: str, session) -> dict:
    url = f"https://t.me/{name}"
    r = session.get(url, timeout=30)
    r.raise_for_status()
    page = r.text
    extra = re.search(r'<div class="tgme_page_extra">\s*(.*?)\s*</div>', page, re.S)
    extra_text = html.unescape(re.sub(r"<[^>]+>", " ", extra.group(1))) if extra else ""
    title = meta(page, "og:title")
    return {
        "name": title or name,
        "tme": url,
        "subscribers": parse_count(extra_text),
        "description": clean(meta(page, "og:description")),
        "kind": "channel" if "subscribers" in extra_text
                else "group" if "members" in extra_text else "unknown",
        "_exists": bool(title) and not title.startswith("Telegram: Contact"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("links", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--refresh", action="store_true", help="обновить подписчиков у всех каналов с t.me")
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    channels = data["channels"]
    by_handle = {handle(c["tme"]): c for c in channels if c.get("tme")}

    links = list(args.links)
    if args.file:
        links += Path(args.file).read_text(encoding="utf-8").split()
    names = [h for h in map(handle, links) if h]
    if args.refresh:
        names += [h for h in by_handle if h not in names]
    if not names:
        sys.exit("Нет ссылок t.me")

    session = requests.Session()
    session.headers["User-Agent"] = UA
    added = updated = 0
    for name in dict.fromkeys(names):
        time.sleep(PAUSE)
        try:
            card = fetch(name, session)
        except requests.RequestException as e:
            print(f"  ✗ {name}: {e}")
            continue
        if not card.pop("_exists"):
            print(f"  ✗ {name}: страница канала пустая — канал удалён или закрыт")
            continue
        old = by_handle.get(name)
        if old:
            if card["subscribers"]:
                old["subscribers"] = card["subscribers"]
            old.setdefault("description", card["description"])
            updated += 1
            print(f"  ↻ {old['name']} — {old.get('subscribers')}")
            continue
        entry = {
            "name": card["name"],
            "tme": card["tme"],
            "subscribers": card["subscribers"],
            "category": None,
            "genres": [],
            "description": card["description"],
            "kind": card["kind"],
            "status": "tme",
        }
        channels.append(entry)
        by_handle[name] = entry
        added += 1
        print(f"  + {entry['name']} — {entry['subscribers']} — {entry['kind']}")

    channels.sort(key=lambda c: (-(c.get("subscribers") or 0), c["name"].lower()))
    data["collected_at"] = time.strftime("%Y-%m-%d")
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nДобавлено: {added}, обновлено: {updated}. Всего: {len(channels)}")


if __name__ == "__main__":
    main()

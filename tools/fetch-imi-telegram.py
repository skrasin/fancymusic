#!/usr/bin/env python3
"""Собирает каталог Telegram-каналов i-m-i.ru под жанры FANCYMUSIC.

Три способа получить данные — выбирается тем, откуда есть доступ к сайту:

    python3 tools/fetch-imi-telegram.py                    # сам обходит сайт
    python3 tools/fetch-imi-telegram.py --import file.json # выгрузка из консоли
    python3 tools/fetch-imi-telegram.py --from-html dir/   # сохранённые страницы

Первый способ требует, чтобы сайт открывался с этой машины. Если нет —
собрать из браузера скриптом tools/imi-console-collect.js и скормить
получившийся imi-telegram.json ключом --import. Совсем крайний случай:
сохранить страницы каналов через Ctrl+S в папку и разобрать --from-html.

Ключи --all (весь каталог, без жанрового фильтра) и --dry-run
(ничего не писать) работают с первым способом.

Пишет  projects/pr-telegram-channels/channels.json
       projects/pr-telegram-channels/output/channels.csv

Уже собранные записи не затираются: если канал есть в channels.json со
status manual, ручные поля (описание, автор, категория) остаются, а
подписчики и ссылка t.me обновляются с сайта. Записи status unverified
скрипт при встрече подтверждает и переводит в fetched.

Про сеть. Каталог отдаёт листинг только с query-параметрами
(?genres=…&page=…), а robots.txt их закрывает. Скрипт читает robots.txt
и, если правило запрещает путь, — не ходит туда, а печатает, что осталось
собрать руками. Между запросами пауза, запросы последовательные.
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.robotparser
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Нужны requests и beautifulsoup4: pip install requests beautifulsoup4")

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "projects" / "pr-telegram-channels"
DATA = PROJECT / "channels.json"
CSV_OUT = PROJECT / "output" / "channels.csv"

BASE = "https://i-m-i.ru"
LISTING = f"{BASE}/sources/telegram"
UA = ("FancymusicBot/1.0 (сбор каталога Telegram-каналов для питчинга релизов; "
      "mail@fancymusic.ru)")
PAUSE = 1.5          # секунды между запросами
MAX_PAGES = 40       # предохранитель от бесконечной пагинации

# Жанровые фильтры каталога → категория и жанры в нашем списке.
GENRES = {
    "avant-garde": ("Авангард и эксперимент", ["Авангард"]),
    "classical":   ("Академическая и классика", ["Академическая"]),
    "classic":     ("Академическая и классика", ["Классика"]),
    "jazz":        ("Джаз", ["Джаз"]),
}
# Тег: чаты сообществ, там попадаются джаз-смежные.
TAGS = {"telegram-chats": ("Чаты и сообщества", [])}

# «Арт» отдельным жанром на сайте не заводится — ловим по описанию.
ART_WORDS = ("современное искусство", "арт-", "искусств", "выставк",
             "галере", "перформанс", "саунд-арт")


def make_session():
    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


def robots(session):
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = session.get(f"{BASE}/robots.txt", timeout=30)
        rp.parse(r.text.splitlines())
    except Exception as e:
        print(f"robots.txt не прочитан ({e}) — считаем всё запрещённым", file=sys.stderr)
        rp.parse(["User-agent: *", "Disallow: /"])
    return rp


def get(session, url, rp):
    if not rp.can_fetch(UA, url):
        print(f"  robots.txt запрещает {url} — пропуск", file=sys.stderr)
        return None
    time.sleep(PAUSE)
    try:
        r = session.get(url, timeout=30)
    except requests.RequestException as e:
        print(f"  сеть: {url} — {e}", file=sys.stderr)
        return None
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}: {url}", file=sys.stderr)
        return None
    return BeautifulSoup(r.text, "html.parser")


def parse_subscribers(text):
    """«2 422 подписчика», «2.4K», «2422» → 2422."""
    t = text.replace("\xa0", " ").strip()
    m = re.search(r"(\d[\d\s.,]*)\s*([KkКк])?", t)
    if not m:
        return None
    num = m.group(1).replace(" ", "").replace(",", ".")
    try:
        value = float(num) if "." in num else int(num)
    except ValueError:
        return None
    if m.group(2):
        value *= 1000
    return int(value)


def listing_slugs(soup):
    """Слаги карточек каналов на странице листинга."""
    slugs = []
    for a in soup.select('a[href*="/sources/telegram/"]'):
        href = urllib.parse.urlparse(a["href"]).path.rstrip("/")
        slug = href.rsplit("/", 1)[-1]
        if slug and slug != "telegram" and slug not in slugs:
            slugs.append(slug)
    return slugs


def parse_card(soup, slug):
    """Страница канала → название, t.me, подписчики, описание."""
    if soup is None:
        return None
    h1 = soup.find(["h1", "h2"])
    name = h1.get_text(strip=True) if h1 else slug

    tme = None
    for a in soup.select('a[href*="t.me/"], a[href*="telegram.me/"]'):
        tme = a["href"].split("?")[0]
        break

    subscribers = None
    text = soup.get_text(" ", strip=True)
    m = re.search(r"([\d\s.,]+[KkКк]?)\s*(?:подписчик|подпис|subscriber)", text)
    if m:
        subscribers = parse_subscribers(m.group(1))

    desc = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        desc = meta["content"].strip()
    else:
        p = soup.find("p")
        desc = p.get_text(" ", strip=True) if p else ""

    return {"name": name, "tme": tme, "subscribers": subscribers,
            "description": desc, "imi": f"{LISTING}/{slug}", "slug": slug}


def collect(session, rp, filters, all_catalog):
    """{slug: запись} по жанровым фильтрам или по всему каталогу."""
    found = {}
    targets = [(LISTING, None, None)] if all_catalog else [
        (f"{LISTING}?{key}={value}", cat, genres)
        for key, table in (("genres", GENRES), ("tags", TAGS))
        for value, (cat, genres) in table.items()
    ]

    for base_url, cat, genres in targets:
        print(f"[листинг] {base_url}")
        for page in range(1, MAX_PAGES + 1):
            sep = "&" if "?" in base_url else "?"
            url = base_url if page == 1 else f"{base_url}{sep}page={page}"
            soup = get(session, url, rp)
            if soup is None:
                break
            slugs = [s for s in listing_slugs(soup)]
            new = [s for s in slugs if s not in found]
            if not slugs:
                break
            for slug in new:
                card = parse_card(get(session, f"{LISTING}/{slug}", rp), slug)
                if card is None:
                    continue
                card["category"] = cat
                card["genres"] = list(genres or [])
                card["status"] = "fetched"
                found[slug] = card
                print(f"    {card['name']} — {card['subscribers'] or '?'}")
            if not new and page > 1:
                break
    return found


def tag_art(entry):
    haystack = f"{entry.get('description','')} {entry.get('name','')}".lower()
    if any(w in haystack for w in ART_WORDS) and "Арт" not in entry["genres"]:
        entry["genres"].append("Арт")


def merge(existing, fetched):
    """Ручные поля не затираются, свежие числа с сайта — подставляются."""
    by_slug = {}
    for e in existing:
        slug = (e.get("imi") or "").rstrip("/").rsplit("/", 1)[-1]
        by_slug[slug] = e

    for slug, card in fetched.items():
        old = by_slug.get(slug)
        if old is None:
            by_slug[slug] = card
            continue
        old["subscribers"] = card["subscribers"] or old.get("subscribers")
        old["tme"] = old.get("tme") or card["tme"]
        old["name"] = old.get("name") or card["name"]
        if not old.get("description"):
            old["description"] = card["description"]
        if old.get("status") == "unverified":
            old["status"] = "fetched"
        for g in card["genres"]:
            if g not in old.get("genres", []):
                old.setdefault("genres", []).append(g)
        old["category"] = old.get("category") or card["category"]

    out = list(by_slug.values())
    for e in out:
        e.pop("slug", None)
        tag_art(e)
    out.sort(key=lambda e: (-(e.get("subscribers") or 0), e["name"]))
    return out


def write_csv(channels):
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Название", "Ссылка t.me", "Подписчики", "Категория",
                    "Жанры", "Автор", "Описание", "Страница i-m-i", "Статус"])
        for c in channels:
            w.writerow([c.get("name", ""), c.get("tme") or "",
                        c.get("subscribers") or "", c.get("category") or "",
                        ", ".join(c.get("genres") or []), c.get("author") or "",
                        c.get("description") or "", c.get("imi") or "",
                        c.get("status", "")])


def from_export(path: Path):
    """Выгрузка tools/imi-console-collect.js → {slug: запись}."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    channels = payload["channels"] if isinstance(payload, dict) else payload
    out = {}
    for c in channels:
        slug = (c.get("imi") or "").rstrip("/").rsplit("/", 1)[-1] or c.get("name")
        c.setdefault("genres", [])
        c.setdefault("status", "fetched")
        out[slug] = c
    print(f"Из выгрузки прочитано: {len(out)}")
    return out


def from_html(directory: Path):
    """Сохранённые через Ctrl+S страницы каналов → {slug: запись}."""
    out = {}
    files = sorted(p for p in Path(directory).rglob("*.htm*") if p.is_file())
    for f in files:
        soup = BeautifulSoup(f.read_text(encoding="utf-8", errors="replace"), "html.parser")
        link = soup.find("link", rel="canonical") or soup.find("meta", property="og:url")
        href = (link.get("href") if link and link.has_attr("href")
                else link.get("content") if link else None)
        slug = (href or f.stem).rstrip("/").rsplit("/", 1)[-1]
        card = parse_card(soup, slug)
        if not card:
            continue
        card["category"] = None
        card["genres"] = []
        card["status"] = "fetched"
        out[slug] = card
        print(f"    {card['name']} — {card['subscribers'] or '?'}")
    print(f"Из {len(files)} файлов прочитано: {len(out)}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="весь каталог, без жанрового фильтра")
    ap.add_argument("--dry-run", action="store_true", help="не писать файлы")
    ap.add_argument("--import", dest="import_path", metavar="FILE",
                    help="imi-telegram.json из tools/imi-console-collect.js")
    ap.add_argument("--from-html", dest="html_dir", metavar="DIR",
                    help="папка с сохранёнными страницами каналов")
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"channels": []}

    if args.import_path:
        fetched = from_export(Path(args.import_path))
    elif args.html_dir:
        fetched = from_html(Path(args.html_dir))
    else:
        session = make_session()
        rp = robots(session)
        fetched = collect(session, rp, GENRES, args.all)

    if not fetched:
        sys.exit("Ничего не собрано. Список в channels.json оставлен как был.\n"
                 "Если сайт с этой машины не открывается — соберите из браузера: "
                 "tools/imi-console-collect.js, затем --import imi-telegram.json")

    channels = merge(data.get("channels", []), fetched)
    print(f"\nВсего в списке: {len(channels)}, из них новых: {len(fetched)}")
    if args.dry_run:
        return

    data["channels"] = channels
    data["collected_at"] = time.strftime("%Y-%m-%d")
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(channels)
    print(f"Записано: {DATA.relative_to(ROOT)}, {CSV_OUT.relative_to(ROOT)}")
    print("Дальше: python3 tools/build-channels-page.py")


if __name__ == "__main__":
    main()

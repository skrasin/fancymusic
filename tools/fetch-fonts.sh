#!/usr/bin/env bash
# Скачивает свободные шрифты с Google Fonts в brand/fonts/ и пересобирает brand/fonts.css.
# Запускать только при смене набора шрифтов — в обычной работе файлы уже в репозитории.
#
# Что и зачем:
#   Bebas Neue  — латиница дисплейного шрифта (кириллицы у Bebas не существует)
#   Oswald      — кириллица того же дисплейного шрифта, подогнана под Bebas
#   Inter       — запасной текстовый шрифт там, где нет Helvetica Neue
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PY'
import re, subprocess, pathlib

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
OUT = pathlib.Path("brand/fonts")
OUT.mkdir(parents=True, exist_ok=True)

# Bebas: cap-height 0.700 em, hhea asc/desc 0.900/-0.300 — эталон для FM Display.
# Oswald: cap-height 0.810 em. 0.700 / 0.810 = 0.8642 → size-adjust, чтобы
# прописные кириллицы совпали по высоте с латиницей в одной строке.
# ascent/descent-override выравнивают строчный бокс, иначе смешанная строка «прыгает».
PLAN = [
    ("Bebas+Neue", "bebas-neue", ("latin", "latin-ext"), "FM Display",
     "  font-weight: 400 700;\n"
     "  ascent-override: 90%;\n  descent-override: 30%;\n  line-gap-override: 0%;\n"),
    ("Oswald:wght@200..700", "oswald", ("cyrillic", "cyrillic-ext"), "FM Display",
     "  font-weight: 400 700;\n  size-adjust: 86.42%;\n"
     "  ascent-override: 90%;\n  descent-override: 30%;\n  line-gap-override: 0%;\n"),
    ("Inter:wght@100..900", "inter", ("latin", "latin-ext", "cyrillic", "cyrillic-ext"),
     "FM Text", "  font-weight: 100 900;\n"),
]

blocks = []
for family, prefix, keep, css_family, descriptors in PLAN:
    url = f"https://fonts.googleapis.com/css2?family={family}&display=swap"
    css = subprocess.run(["curl", "-sS", "-A", UA, url],
                         capture_output=True, text=True, check=True).stdout
    for subset, face in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})", css, re.S):
        if subset not in keep:
            continue
        remote = re.search(r"url\((https://[^)]+\.woff2)\)", face).group(1)
        local = OUT / f"{prefix}-{subset}.woff2"
        subprocess.run(["curl", "-sS", "-o", str(local), remote], check=True)
        urange = re.search(r"unicode-range:\s*([^;]+);", face).group(1)
        blocks.append(
            f"/* {family.split(':')[0].replace('+', ' ')} — {subset} */\n"
            f"@font-face {{\n"
            f"  font-family: '{css_family}';\n"
            f"  font-style: normal;\n"
            f"  font-display: swap;\n"
            f"{descriptors}"
            f"  src: url(fonts/{local.name}) format('woff2');\n"
            f"  unicode-range: {urange};\n}}"
        )

header = """/* FANCYMUSIC — подключение шрифтов.
   Сгенерировано tools/fetch-fonts.sh, руками не править.

   FM Display — составное семейство: латиница из Bebas Neue, кириллица из Oswald,
   подогнанного по высоте прописных (size-adjust) и по строчному боксу
   (ascent/descent-override). Браузер сам берёт нужный файл по unicode-range,
   поэтому смешанная строка «FANCYMUSIC — Новый релиз» набирается однородно.
   Шрифт только заглавный: текст задавать в text-transform: uppercase.

   FM Text — Inter, переменный. Работает запасным для Helvetica Neue,
   которая проприетарная и в репозиторий не кладётся (см. brand/BRAND.md).

   Лицензии: Bebas Neue, Oswald, Inter — SIL Open Font License 1.1. */

"""
pathlib.Path("brand/fonts.css").write_text(header + "\n\n".join(blocks) + "\n")
print(f"файлов шрифтов: {len(blocks)}")
PY

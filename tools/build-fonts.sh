#!/usr/bin/env bash
# Собирает brand/fonts/*.woff2 и brand/fonts.css.
# Запускать только при смене набора шрифтов — в обычной работе всё уже в репозитории.
#
#   FM Display — Bebas Neue, пять начертаний с кириллицей.
#                Исходники .otf лежат в brand/fonts/src/, лицензия SIL OFL 1.1
#                (см. brand/fonts/LICENSE-BebasNeue.txt), @font-face разрешён.
#   FM Text     — Inter с Google Fonts, запасной для Helvetica Neue.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PY'
import re, subprocess, pathlib
from fontTools.ttLib import TTFont

OUT = pathlib.Path("brand/fonts")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Начертание -> вес в CSS.
# В самих файлах и Book, и Regular помечены весом 400, хотя рисунок разный
# (площадь «H»: 74 256 против 121 240). Поэтому вес назначается заново, так,
# чтобы 400 доставался Regular — каноническому Bebas, которого ждут от 400.
WEIGHTS = [("Thin", 100), ("Light", 200), ("Book", 300), ("Regular", 400), ("Bold", 700)]

blocks = []
for name, weight in WEIGHTS:
    src = OUT / "src" / f"BebasNeue_{name}.otf"
    dst = OUT / f"bebas-neue-{weight}.woff2"
    f = TTFont(src, fontNumber=0)
    f.flavor = "woff2"
    f.save(dst)
    blocks.append(
        f"/* Bebas Neue {name} */\n"
        f"@font-face {{\n"
        f"  font-family: 'FM Display';\n"
        f"  font-style: normal;\n"
        f"  font-weight: {weight};\n"
        f"  font-display: swap;\n"
        f"  src: url(fonts/{dst.name}) format('woff2');\n}}")

# Inter — по подмножествам, чтобы кириллица и латиница качались отдельно
url = "https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap"
css = subprocess.run(["curl", "-sS", "-A", UA, url],
                     capture_output=True, text=True, check=True).stdout
for subset, face in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})", css, re.S):
    if subset not in {"latin", "latin-ext", "cyrillic", "cyrillic-ext"}:
        continue
    remote = re.search(r"url\((https://[^)]+\.woff2)\)", face).group(1)
    local = OUT / f"inter-{subset}.woff2"
    subprocess.run(["curl", "-sS", "-o", str(local), remote], check=True)
    urange = re.search(r"unicode-range:\s*([^;]+);", face).group(1)
    blocks.append(
        f"/* Inter — {subset} */\n"
        f"@font-face {{\n"
        f"  font-family: 'FM Text';\n"
        f"  font-style: normal;\n"
        f"  font-weight: 100 900;\n"
        f"  font-display: swap;\n"
        f"  src: url(fonts/{local.name}) format('woff2');\n"
        f"  unicode-range: {urange};\n}}")

header = """/* FANCYMUSIC — подключение шрифтов.
   Сгенерировано tools/build-fonts.sh, руками не править.

   FM Display — Bebas Neue, пять начертаний, латиница и кириллица в одном файле.
   Шрифт целиком заглавный по рисунку: строчные буквы нарисованы прописными,
   поэтому регистр исходного текста на вид не влияет.

   Веса переназначены относительно файлов: Thin 100, Light 200, Book 300,
   Regular 400, Bold 700. В самих .otf и Book, и Regular помечены весом 400,
   хотя рисунок у них разный.

   FM Text — Inter, переменный. Запасной для Helvetica Neue, которая
   проприетарная и в репозиторий не кладётся (см. brand/BRAND.md).

   Лицензии: Bebas Neue и Inter — SIL Open Font License 1.1. */

"""
pathlib.Path("brand/fonts.css").write_text(header + "\n\n".join(blocks) + "\n")
print(f"начертаний и подмножеств: {len(blocks)}")
PY

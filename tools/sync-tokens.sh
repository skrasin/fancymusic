#!/usr/bin/env bash
# Канонический файл токенов — brand/design-tokens.css.
# docs/assets/design-tokens.css — его копия для GitHub Pages.
set -euo pipefail
cd "$(dirname "$0")/.."
cp brand/design-tokens.css docs/assets/design-tokens.css
echo "design-tokens.css синхронизирован в docs/assets/"

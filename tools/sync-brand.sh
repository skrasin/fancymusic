#!/usr/bin/env bash
# Канонические файлы бренда лежат в brand/. На GitHub Pages уезжает только docs/,
# поэтому перед публикацией их копия синхронизируется в docs/assets/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p docs/assets/fonts
cp brand/fonts.css brand/design-tokens.css brand/base.css docs/assets/
cp brand/fonts/*.woff2 docs/assets/fonts/
echo "бренд синхронизирован в docs/assets/"

#!/usr/bin/env bash
# Канонические файлы бренда лежат в brand/. На GitHub Pages уезжает только docs/,
# поэтому перед публикацией их копия синхронизируется в docs/assets/.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf docs/assets/fonts
mkdir -p docs/assets/fonts
cp brand/fonts.css brand/design-tokens.css brand/base.css brand/release.css docs/assets/
cp brand/fonts/*.woff2 brand/fonts/LICENSE-BebasNeue.txt docs/assets/fonts/
echo "бренд синхронизирован в docs/assets/"

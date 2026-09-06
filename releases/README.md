# Релизы

Один каталог на релиз, `slug` латиницей в kebab-case:

```
releases/{slug}/
  raw-materials/    — всё присланное как есть + meta.yml с фактами
  output/           — press-release.md, social.md, при необходимости docx/pdf
```

Свёрстанная страница релиза лежит отдельно — в `docs/releases/{slug}/index.html`,
потому что на GitHub Pages уезжает только каталог `docs/`.

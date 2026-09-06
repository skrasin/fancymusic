# fancymusic

Рабочий репозиторий лейбла [FANCYMUSIC](https://fancymusic.ru): посадочные
страницы, пресс-релизы, документы, таблицы и презентации — на единой
дизайн-системе.

## Как устроено

| Что | Где |
|---|---|
| Инструкция агенту | `CLAUDE.md` |
| Дизайн-система: токены, шрифты, компоненты | `brand/`, живая спецификация — [`/design/`](https://skrasin.github.io/fancymusic/design/) |
| Шаблоны текста, соцсетей и страницы релиза | `templates/` |
| Материалы по проектам | `projects/{slug}/` |
| Опубликованные страницы (GitHub Pages) | `docs/` |
| Сервисные скрипты | `tools/` |

## Форматы

Текстовый исходник любого материала — Markdown в `projects/{slug}/output/`.
Из него собираются `.docx` и `.pdf`. Таблицы — `.xlsx`, презентации — `.pptx`,
веб-страницы верстаются вручную на дизайн-системе.

## Публикация

Пуш в `main` с изменениями в `docs/` или `brand/` запускает
`.github/workflows/pages.yml` и выкладывает сайт:
https://skrasin.github.io/fancymusic/

## Разовая настройка GitHub Pages

Pages включается вручную один раз: **Settings → Pages → Source: GitHub Actions**.
Автоматически (`enablement: true`) не выходит — токену workflow не разрешено
создавать Pages-сайт.

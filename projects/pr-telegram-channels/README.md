# Список Telegram-каналов для питчинга

Данные — `channels.json`, выгрузка для таблицы — `output/channels.csv`,
страница — `docs/pr/telegram/`.

## Как собрать данные

Каталог i-m-i.ru закрыт сетевой политикой рабочего окружения Claude Code
на web, поэтому сбор идёт с машины, где сайт открывается. Любой из трёх
способов, дальше всё одинаково.

**1. Из браузера — ничего не устанавливать**

1. Открыть https://i-m-i.ru/sources/telegram
2. F12 → Console → вставить целиком `tools/imi-console-collect.js` → Enter
3. Дождаться строки «готово», браузер скачает `imi-telegram.json`
4. `python3 tools/fetch-imi-telegram.py --import ~/Downloads/imi-telegram.json`

**2. Скриптом с локальной машины**

```
pip install requests beautifulsoup4
python3 tools/fetch-imi-telegram.py          # читает robots.txt, идёт с паузой
```

**3. Из сохранённых страниц** — если первые два не сработали:
сохранить страницы каналов через Ctrl+S в папку, затем
`python3 tools/fetch-imi-telegram.py --from-html ~/imi-pages/`

## Дальше

```
python3 tools/build-channels-page.py         # пересобирает docs/pr/telegram/
```

Ручные поля (автор, описание, категория) при повторном сборе не затираются,
записи со статусом `unverified` при встрече на сайте становятся `fetched`.
Страницу `docs/pr/telegram/index.html` руками не править — перезаписывается.

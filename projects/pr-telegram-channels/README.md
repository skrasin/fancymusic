# Список Telegram-каналов для питчинга

Данные — `channels.json`, выгрузка для таблицы — `output/channels.csv`,
страница — `docs/pr/telegram/`.

## Добавить каналы по ссылкам t.me

Самый простой путь — t.me открывается и из облачного окружения:

```
python3 tools/fetch-tme-channels.py https://t.me/allthatjazz https://t.me/warhol
python3 tools/fetch-tme-channels.py --refresh      # обновить подписчиков у всех
python3 tools/build-channels-page.py
```

Скрипт забирает со страницы канала название, описание и подписчиков.
Категорию, жанры, контакт и правила приёма музыки (`category`, `genres`,
`contact`, `pitch`) проставляют руками в `channels.json` — по описанию
канала и его последним постам на `t.me/s/<имя>`. Такие записи помечены
`genres_source: fancymusic`: классификация наша, не источника.

## Как собрать данные из каталога i-m-i.ru

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
python3 tools/build-channels-page.py         # пересобирает страницу и output/channels.csv
```

Ручные поля (автор, описание, категория) при повторном сборе не затираются,
записи со статусом `unverified` при встрече на сайте становятся `fetched`.
Страницу `docs/pr/telegram/index.html` руками не править — перезаписывается.

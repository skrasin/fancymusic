Собери каталог Telegram-каналов с сайта i-m-i.ru для лейбла FANCYMUSIC.

Репозиторий: https://github.com/skrasin/fancymusic
Ветка: claude/telegram-channels-pr-list-rjqbi1
Вся инструкция — в projects/pr-telegram-channels/README.md

Что нужно сделать:

1. Склонируй репозиторий (или открой локальную копию) и переключись на ветку
   claude/telegram-channels-pr-list-rjqbi1.
2. pip install requests beautifulsoup4
3. python3 tools/fetch-imi-telegram.py
   Скрипт обходит https://i-m-i.ru/sources/telegram по жанровым фильтрам
   (avant-garde, classical, classic, jazz) и тегу telegram-chats, заходит в
   карточки каналов и забирает название, ссылку t.me, число подписчиков
   и описание. Он читает robots.txt и держит паузу между запросами.
4. Если скрипт ничего не собрал — значит каталог рисуется JavaScript и в
   готовом HTML ссылок нет. Тогда открой https://i-m-i.ru/sources/telegram
   в браузере, собери данные скриптом tools/imi-console-collect.js
   (вставить в консоль браузера, он скачает imi-telegram.json), затем:
   python3 tools/fetch-imi-telegram.py --import ~/Downloads/imi-telegram.json
5. python3 tools/build-channels-page.py — пересобрать страницу.
6. Проверь: в projects/pr-telegram-channels/channels.json стало заметно больше
   семи записей, у большинства заполнены поля tme и subscribers, категории и
   жанры проставлены. Открой docs/pr/telegram/index.html и убедись, что
   фильтры работают и на ширине 390px нет горизонтальной прокрутки.
7. Закоммить и запушь в ту же ветку claude/telegram-channels-pr-list-rjqbi1.
8. Напиши итог: сколько каналов собрано, сколько без ссылки t.me, сколько без
   числа подписчиков.

Ничего не выдумывай: если данных по каналу нет, оставляй поле пустым.

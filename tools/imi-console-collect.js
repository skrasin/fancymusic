/* Сбор каталога Telegram-каналов i-m-i.ru из браузера.
 *
 * Как пользоваться:
 *   1. открыть https://i-m-i.ru/sources/telegram
 *   2. F12 → вкладка Console → вставить весь этот файл → Enter
 *   3. дождаться строки «готово» и сохранить файл imi-telegram.json
 *      (браузер предложит его скачать сам)
 *   4. прислать файл в Claude Code
 *
 * Скрипт работает от имени обычной вкладки: те же права, что у человека,
 * который листает каталог руками. Между запросами пауза, всё последовательно.
 * Если разметка каталога изменится, в конце выводится образец HTML карточки —
 * пришлите его, и разбор поправится.
 */
(async () => {
  const PAUSE = 400;                 // пауза между запросами, мс
  const MAX_PAGES = 40;              // предохранитель от бесконечной пагинации
  const LISTING = '/sources/telegram';

  // жанровые фильтры каталога → категория и жанры в нашем списке
  const FILTERS = [
    ['genres=avant-garde', 'Авангард и эксперимент', ['Авангард']],
    ['genres=classical',   'Академическая и классика', ['Академическая']],
    ['genres=classic',     'Академическая и классика', ['Классика']],
    ['genres=jazz',        'Джаз', ['Джаз']],
    ['tags=telegram-chats','Чаты и сообщества', []],
  ];

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const log = (...a) => console.log('%c[i-m-i]', 'color:#ff2626;font-weight:bold', ...a);

  async function html(url) {
    await sleep(PAUSE);
    const r = await fetch(url, { credentials: 'same-origin' });
    if (!r.ok) { log('HTTP', r.status, url); return null; }
    return new DOMParser().parseFromString(await r.text(), 'text/html');
  }

  const slugOf = (href) => {
    try { return new URL(href, location.origin).pathname.replace(/\/$/, '').split('/').pop(); }
    catch { return null; }
  };

  function slugsOn(doc) {
    const out = [];
    doc.querySelectorAll('a[href*="/sources/telegram/"]').forEach(a => {
      const s = slugOf(a.getAttribute('href'));
      if (s && s !== 'telegram' && !out.includes(s)) out.push(s);
    });
    return out;
  }

  function subsFrom(text) {
    const m = text.replace(/ /g, ' ')
      .match(/([\d][\d\s.,]*)\s*([KkКк])?\s*(?:подписчик|подпис|subscriber|участник)/i);
    if (!m) return null;
    let n = parseFloat(m[1].replace(/\s/g, '').replace(',', '.'));
    if (!isFinite(n)) return null;
    if (m[2]) n *= 1000;
    return Math.round(n);
  }

  function parseCard(doc, slug) {
    if (!doc) return null;
    const h = doc.querySelector('h1, h2');
    const tmeEl = doc.querySelector('a[href*="t.me/"], a[href*="telegram.me/"]');
    const meta = doc.querySelector('meta[name="description"], meta[property="og:description"]');
    const body = doc.body ? doc.body.innerText || doc.body.textContent || '' : '';
    const p = [...doc.querySelectorAll('p')].map(e => e.textContent.trim())
      .find(t => t.length > 40);
    return {
      name: h ? h.textContent.trim() : slug,
      tme: tmeEl ? tmeEl.href.split('?')[0] : null,
      subscribers: subsFrom(body),
      description: (meta && meta.content ? meta.content : (p || '')).trim(),
      imi: location.origin + LISTING + '/' + slug,
      status: 'fetched',
    };
  }

  const found = new Map();
  let sample = null;

  for (const [query, category, genres] of FILTERS) {
    log('фильтр', query);
    for (let page = 1; page <= MAX_PAGES; page++) {
      const url = `${LISTING}?${query}` + (page > 1 ? `&page=${page}` : '');
      const doc = await html(url);
      if (!doc) break;
      const slugs = slugsOn(doc);
      if (!slugs.length) break;
      const fresh = slugs.filter(s => !found.has(s));
      if (!fresh.length && page > 1) break;
      for (const slug of fresh) {
        const doc2 = await html(`${LISTING}/${slug}`);
        if (!sample && doc2) sample = doc2.body.innerHTML.slice(0, 1500);
        const card = parseCard(doc2, slug);
        if (!card) continue;
        card.category = category;
        card.genres = [...genres];
        found.set(slug, card);
        log(`  ${card.name} — ${card.subscribers ?? '?'} — ${card.tme ?? 'без t.me'}`);
      }
    }
  }

  const channels = [...found.values()]
    .sort((a, b) => (b.subscribers || 0) - (a.subscribers || 0));

  if (!channels.length) {
    log('НИЧЕГО НЕ НАЙДЕНО. Каталог, вероятно, рисуется скриптом, а не отдаётся ' +
        'готовым HTML. Пришлите вывод следующей строки:');
    console.log(document.body.innerHTML.slice(0, 3000));
    return;
  }

  const payload = {
    source: location.origin + LISTING,
    collected_at: new Date().toISOString().slice(0, 10),
    channels,
    _sample_card_html: sample,   // для отладки разбора, в итоговый список не идёт
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'imi-telegram.json';
  document.body.appendChild(a); a.click(); a.remove();

  const noTme = channels.filter(c => !c.tme).length;
  const noSubs = channels.filter(c => !c.subscribers).length;
  log(`готово: ${channels.length} каналов, без ссылки t.me — ${noTme}, без подписчиков — ${noSubs}`);
  log('файл imi-telegram.json скачан. Пришлите его в Claude Code.');
  window.imiResult = payload;
})();

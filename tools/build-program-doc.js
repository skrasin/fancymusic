#!/usr/bin/env node
/* Собирает Word-документ программы концерта из Markdown.

     node tools/build-program-doc.js <slug>

   Источник: projects/<slug>/output/program.md
   Результат: projects/<slug>/output/program.docx

   Документ без оформления: только Arial 10 pt, чёрный текст, без таблиц,
   подчёркиваний, цветов и рамок. Заголовки заглавными и жирным. Отступов
   между абзацами нет — абзацы разделены пустыми строками. Ссылки — адресом.

   Собирается через docx-js, а не python-docx: шаблон python-docx тянет
   невалидный settings.xml и служебные части (customXml, миниатюру),
   на которых спотыкается просмотр docx в браузере.

   Разметка: «# Название», «## Раздел», «**Ключ:** значение» — отдельная
   строка, «- пункт» и «1. пункт» — стандартные списки, остальное — абзацы. */
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, LevelFormat, AlignmentType, NoBreakHyphen } = require("docx");

const FONT = "Arial";
const SIZE = 20; // половинки пункта: 10 pt

const slug = process.argv[2];
if (!slug) { console.error("usage: node tools/build-program-doc.js <slug>"); process.exit(1); }
const out = path.join(__dirname, "..", "projects", slug, "output");
const md = fs.readFileSync(path.join(out, "program.md"), "utf8").normalize("NFC");

const plain = (s) => s.replace(/\*\*(.+?)\*\*/g, "$1");
// Дефис в двойной фамилии (Мелик-Овсепян) — неразрывный, чтобы фамилия
// не рвалась на конце строки. Обычные дефисы (тенор-саксофон) не трогаем.
const NAME_HYPHEN = /(?<=[А-ЯЁA-Z][а-яёa-z]+)-(?=[А-ЯЁA-Z])/;
const runChildren = (text) => text.split(NAME_HYPHEN)
  .flatMap((part, i) => (i ? [new NoBreakHyphen(), part] : [part]));
const para = (text, opts = {}) => new Paragraph({
  ...opts,
  children: [new TextRun({ children: runChildren(plain(text)), bold: !!opts.bold, font: FONT, size: SIZE })],
});
const blank = () => new Paragraph({ children: [] });

const kind = (ln) =>
  ln.startsWith("# ") ? "title" :
  ln.startsWith("## ") ? "heading" :
  ln.startsWith("- ") ? "bullet" :
  /^\d+\. /.test(ln) ? "number" :
  /^\*\*[^*]+:\*\*/.test(ln) ? "fact" : "text";

const children = [];
let prev = null;
for (const ln of md.split("\n").filter((l) => l.trim())) {
  const k = kind(ln);
  // пустая строка между блоками; пункты одного списка и факты идут подряд,
  // заголовок прижат к своему тексту
  if (prev && prev !== "heading" && !(k === prev && ["bullet", "number", "fact"].includes(k))) children.push(blank());
  if (k === "title") children.push(para(ln.slice(2).toUpperCase(), { bold: true }));
  else if (k === "heading") children.push(para(ln.slice(3).toUpperCase(), { bold: true, keepNext: true }));
  else if (k === "bullet") children.push(para(ln.slice(2), { numbering: { reference: "bullets", level: 0 } }));
  else if (k === "number") children.push(para(ln.replace(/^\d+\. /, ""), { numbering: { reference: "numbers", level: 0 } }));
  else children.push(para(ln));
  prev = k;
}

const level = (format, text) => ({
  level: 0, format, text, alignment: AlignmentType.LEFT,
  style: { paragraph: { indent: { left: 720, hanging: 360 } }, run: { font: FONT } },
});

const doc = new Document({
  title: md.split("\n")[0].replace(/^#\s*/, ""),
  styles: {
    default: { document: {
      run: { font: FONT, size: SIZE },
      paragraph: { spacing: { before: 0, after: 0, line: 240 } },
    } },
  },
  numbering: { config: [
    { reference: "bullets", levels: [level(LevelFormat.BULLET, "•")] },
    { reference: "numbers", levels: [level(LevelFormat.DECIMAL, "%1.")] },
  ] },
  sections: [{
    properties: { page: {
      size: { width: 11906, height: 16838 }, // A4
      margin: { top: 1418, bottom: 1418, left: 1418, right: 1418 }, // 2,5 см
    } },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(out, "program.docx"), buf);
  console.log(`готово: ${path.join(out, "program.docx")}`);
});

// Title-swap layers for "The World of Bluefin": the Warner upload's
// "THE DAWN OF MAN" card becomes "A WORLD BEFORE KUBERNETES", set to look as
// though the film shipped that way. Owner: "overlay with a black box but be
// exact", then "needs another quality pass".
//
// The WORDS layer (3840x2160 RGBA), and the prologue card's line layers. The box under them is drawn from the
// frame itself by scripts/build_world_of_bluefin.py, and each layer fades on
// its own envelope there.
//
//   text.png  the new line in Marcellus with a stroke to reach the card's
//             weight -- chosen by setting "THE DAWN OF MAN" in candidate faces
//             at the card's measured cap height and width and comparing them
//             on the frame. Same cap height (66 px at 1080p), same ink top,
//             same optical centre, same colour, same film softness.
//
//   node scripts/build_world_of_bluefin_plate.mjs <out-dir>
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const outDir = process.argv[2];
if (!outDir) { console.error('usage: build_world_of_bluefin_plate.mjs <out-dir>'); process.exit(2); }
fs.mkdirSync(outDir, { recursive: true });

// Every word comes from the record; nothing on screen is typed here.
const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const record = JSON.parse(fs.readFileSync(path.join(REPO, 'stories/world-of-bluefin-plates.json'), 'utf8'));
const TEXT = record.plates.find(p => p.id === 'wob_title_swap').text.toUpperCase();  // the card is set in capitals

const S = 2;                          // 1080p measurements -> 4K
const CARD = { x0: 516, x1: 1396, y0: 670, y1: 736 };   // original ink, 1080p
const CAP = (CARD.y1 - CARD.y0) * S;                     // 132 px
const CENTRE_X = (CARD.x0 + CARD.x1) / 2 * S;            // 1912 px
const INK_TOP = CARD.y0 * S;                             // 1340 px
const COLOUR = 'rgb(150, 174, 176)';
const STROKE = 2.8 * S;               // weight match against the card's stems
const WORD_GAP = 12 * S;              // the card's word spaces are wide
const BLUR = 1.1;                     // the print's softness, 4K px

const page = await (await chromium.launch()).newPage({ viewport: { width: 3840, height: 2160 } });
await page.setContent(`<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Jost:wght@300&display=block" rel="stylesheet">
<style>html,body{margin:0;width:3840px;height:2160px;background:transparent;overflow:hidden}</style>
</head><body></body></html>`, { waitUntil: 'networkidle' });
await page.evaluate(() => Promise.all([document.fonts.load('200px Marcellus'), document.fonts.load('300 72px Jost')]));

// Layer 2: the words, placed by their measured ink box, not by CSS metrics.
const fit = await page.evaluate(({ TEXT, CAP, CENTRE_X, INK_TOP, COLOUR, STROKE, WORD_GAP, BLUR }) => {
  document.body.innerHTML = '';
  const g = document.createElement('canvas').getContext('2d');
  g.font = '200px Marcellus';
  const cap = g.measureText('H');
  const size = 200 * CAP / (cap.actualBoundingBoxAscent + cap.actualBoundingBoxDescent);
  const s = document.createElement('span');
  s.textContent = TEXT;
  Object.assign(s.style, {
    position: 'absolute', left: '0px', top: '0px', whiteSpace: 'nowrap', lineHeight: '1',
    fontFamily: 'Marcellus', fontSize: size + 'px', color: COLOUR, wordSpacing: WORD_GAP + 'px',
    webkitTextStroke: `${STROKE}px ${COLOUR}`, filter: `blur(${BLUR}px)`,
  });
  document.body.appendChild(s);
  // ink box from the canvas, at the same size, including the word gaps
  g.font = `${size}px Marcellus`;
  const words = TEXT.split(' ');
  const space = g.measureText(' ').width + WORD_GAP;
  const inkW = words.reduce((w, x) => w + g.measureText(x).width, 0) + space * (words.length - 1);
  const asc = g.measureText('H').actualBoundingBoxAscent;
  const lineTop = (size * (g.measureText('H').fontBoundingBoxAscent / size)) - asc; // CSS line box to cap top
  s.style.left = (CENTRE_X - inkW / 2) + 'px';
  s.style.top = (INK_TOP - lineTop) + 'px';
  return { size: +size.toFixed(1), inkW: Math.round(inkW), left: Math.round(CENTRE_X - inkW / 2) };
}, { TEXT, CAP, CENTRE_X, INK_TOP, COLOUR, STROKE, WORD_GAP, BLUR });
// Font metrics disagree with ink (stroke, blur, overshoot), so the words are
// fitted to the card by MEASURING the rendered pixels: ink height to the
// card's, ink top to the card's, ink centre to the card's. Three passes land
// within a pixel.
const TARGET = { top: 1341, bottom: 1474, cx: CENTRE_X };  // measured on the 4K conform
for (let pass = 0; pass < 3; pass++) {
  const png = await page.screenshot({ omitBackground: true });
  const ink = await page.evaluate(async (b64) => {
    const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data;
    let x0 = 1e9, x1 = -1, y0 = 1e9, y1 = -1;
    for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++)
      if (d[(y * c.width + x) * 4 + 3] > 128) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    return { x0, x1, y0, y1 };
  }, png.toString('base64'));
  const k = (TARGET.bottom - TARGET.top) / (ink.y1 - ink.y0);
  await page.evaluate(({ k, dx, dy }) => {
    const s = document.querySelector('span');
    s.style.fontSize = (parseFloat(s.style.fontSize) * k) + 'px';
    s.style.left = (parseFloat(s.style.left) + dx) + 'px';
    s.style.top = (parseFloat(s.style.top) + dy) + 'px';
  }, { k, dx: TARGET.cx - (ink.x0 + ink.x1) / 2, dy: TARGET.top - ink.y0 });
  fit[`pass${pass}`] = ink;
}
await page.screenshot({ path: path.join(outDir, 'text.png'), omitBackground: true });
console.log(`wrote ${outDir}/text.png`, JSON.stringify(fit));

// The prologue card: one transparent layer per line, each at its final seat,
// so the builder can fade and drift every line on its own clock. Copy is read
// verbatim from the record; case and wording are the owner's.
const prologue = record.plates.find(p => p.id === 'wob_prologue');
// Jost Light in tracked capitals: Futura lineage, the family of 2001's own
// on-screen type. Capitals are styling; the words are the owner's.
const LINE_PX = 72, LEADING = 170;
for (const [pi, lines] of prologue.panels.entries()) {
  const top = 1080 - (lines.length - 1) * LEADING / 2;
  for (const [li, line] of lines.entries()) {
    await page.evaluate(({ line, y, LINE_PX }) => {
      document.body.innerHTML = '';
      const s = document.createElement('div');
      s.textContent = line;
      Object.assign(s.style, {
        position: 'absolute', left: '0', width: '3840px', top: (y - LINE_PX * 0.6) + 'px',
        textAlign: 'center', whiteSpace: 'nowrap', lineHeight: '1',
        fontFamily: 'Jost', fontWeight: '300', fontSize: LINE_PX + 'px', letterSpacing: '0.3em',
        textTransform: 'uppercase', paddingLeft: '0.3em',
        color: 'rgb(238, 234, 226)',
        textShadow: '0 0 14px rgba(255, 230, 200, 0.18)',
      });
      document.body.appendChild(s);
    }, { line, y: top + li * LEADING, LINE_PX });
    await page.screenshot({ path: path.join(outDir, `prologue_${pi}_${li}.png`), omitBackground: true });
  }
}
console.log(`wrote ${outDir}/prologue_*.png`);
await page.context().browser().close();

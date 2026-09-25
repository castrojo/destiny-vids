import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
import fs from 'fs';

import { execFileSync } from 'child_process';
import os from 'os';
import path from 'path';

// Thumbnail for "The World of Bluefin": the standing terror-bird skeleton in
// the museum, from the on-disk 4K Perfume master (source 151.7 s, 3840x1608),
// framed as a true 16:9 window with the skull left of centre, the
// modern Bluefin wordmark + "Presents", and the act-card frame on the right so
// the art stays clear. Owner-approved composition, 2026-09-25.
const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const FFMPEG = process.env.DESTINY_FFMPEG || '/home/linuxbrew/.linuxbrew/bin/ffmpeg';
const bgPath = path.join(REPO, 'renders/plates-world-of-bluefin/thumb-terror-bird-4k.png');
fs.mkdirSync(path.dirname(bgPath), { recursive: true });
// 2859x1608 is 16:9 at the master's full height: cover-crop, never stretch.
execFileSync(FFMPEG, ['-v', 'error', '-y', '-ss', '151.7',
  '-i', path.join(REPO, 'media/yt_nightwish_perfume_of_the_timeless.mkv'), '-frames:v', '1',
  '-vf', 'crop=2859:1608:632:0,scale=3840:2160:flags=lanczos', '-update', '1', bgPath]);
const record = JSON.parse(fs.readFileSync(path.join(REPO, 'stories/world-of-bluefin-plates.json'), 'utf8'));
const thumb = record.plates.find(p => p.id === 'wob_thumbnail');
const esc = t => t.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const wordmarkPath = path.join(REPO, 'renders/marks/modern-bluefin-wordmark.png');
const outPath = path.join(os.homedir(), 'Videos/Wolves/world-of-bluefin-thumbnail.jpg');

const bgBase64 = fs.readFileSync(bgPath).toString('base64');
const wmBase64 = fs.readFileSync(wordmarkPath).toString('base64');

// Exact copy of projectbluefin website / wolves-cinematic CSS tokens and styling
const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  :root {
    --wc-gold: #60a5fa;
    --wc-white: #e9e9e5;
    --wc-grey: #8b8f96;
    --wc-line: rgb(96 165 250 / 28%);
    --wc-font-display: 'Inter', -apple-system, sans-serif;
    --wc-font-mono: 'JetBrains Mono', ui-monospace, monospace;
  }

  body {
    width: 3840px;
    height: 2160px;
    overflow: hidden;
    position: relative;
    background: #000;
    font-family: var(--wc-font-display);
  }

  /* Full bleed clean background footage: NO artificial black fade/scrim hiding the art */
  .bg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  /* Authentic Bluefin Wolves Slide Frame */
  .slide-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: flex-end;
    padding: 160px 200px;
    z-index: 10;
  }
  .top-header { align-self: flex-start; }

  /* Top brand header */
  .top-header {
    display: flex;
    align-items: center;
    gap: 20px;
    background: rgba(6, 7, 10, 0.45);
    padding: 12px 24px;
    border-radius: 8px;
    width: fit-content;
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .wordmark {
    height: 96px;
    width: auto;
  }

  .header-divider {
    width: 1px;
    height: 56px;
    background: var(--wc-line);
  }

  .eyebrow {
    font-family: var(--wc-font-mono);
    font-size: 2.3rem;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: var(--wc-gold);
    font-weight: 500;
  }

  /* Main act frame verbatim from cards/act.html */
  .frame {
    display: flex;
    flex-direction: column;
    gap: 2.4rem;
    width: min(128rem, 90vw);
    padding: 4.8rem;
    border-left: 8px solid var(--wc-gold);
    background: rgba(6, 7, 10, 0.72);
    backdrop-filter: blur(12px);
    border-radius: 0 12px 12px 0;
    text-shadow: 0 0.1rem 0.6rem rgb(0 0 0 / 85%);
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
  }

  .label {
    font-family: var(--wc-font-mono);
    font-size: 2.4rem;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--wc-gold);
    font-weight: 700;
  }

  .title {
    margin: 0;
    font-size: clamp(6rem, 11vw, 9.6rem);
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--wc-white);
    line-height: 1.05;
  }

  .subtitle {
    margin: 0;
    font-family: var(--wc-font-mono);
    font-size: 2.7rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #7fd4d4;
  }
</style>
</head>
<body>
  <img class="bg" src="data:image/png;base64,${bgBase64}" />
  <div class="slide-overlay">
    <div class="top-header">
      <img class="wordmark" src="data:image/png;base64,${wmBase64}" />
      <div class="header-divider"></div>
      <div class="eyebrow">Presents</div>
    </div>

    <div class="frame">
      <span class="label">// CHAPTER II</span>
      <h1 class="title">${esc(thumb.title)}</h1>
      <p class="subtitle">${esc(thumb.subtitle)}</p>
    </div>
  </div>
</body>
</html>`;

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 3840, height: 2160 } });
await page.setContent(html, { waitUntil: 'networkidle' });
await page.screenshot({ path: outPath, type: 'jpeg', quality: 95 });
await browser.close();
console.log("Wrote thumbnail to:", outPath);

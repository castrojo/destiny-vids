// Renders full-frame cards from a plate manifest, with a real browser.
//
// The Wolves cuts have always rendered their chrome this way -- plate.html,
// reveal.html and nimbatus-review/render/endcard.html are each screenshotted
// by playwright at the delivery size (see ~/Videos/wolves-kat/render/
// render-plates.mjs and render-endcards.mjs). This driver is the same pattern,
// pointed at a manifest instead of a hardcoded list, so the act slides and the
// comic title card use the SITE'S OWN CSS rather than a second implementation
// of it.
//
//   node cards/render-cards.mjs --manifest stories/megacut/megacut-cards.json \
//        --out-dir renders/plates-megacut-cards
//
// It renders only browser-owned card kinds; Guardian nameplates, chat and
// status plates are tools/plate.py's job and are skipped with a note.
//
// playwright is not vendored here. Point NODE_PATH or a node_modules symlink
// at a checkout that has it (~/src/website/node_modules), exactly as the
// ~/Videos render dirs do.
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, '..')

const TEMPLATES = {
  act: 'act.html',
  comic: 'comic.html',
  photo: 'photo.html',
  maintitle: 'maintitle.html',
  bookline: 'bookline.html',
  daycard: 'daycard.html',
  ending: 'ending.html',
}
// One authored row per key. A key absent from the manifest is absent from the
// URL, and the card leaves that row out: a missing string is omitted, never
// defaulted. `body` and `chapters` repeat.
// `stage` is not copy -- it is the main title's two-beat switch, and it is
// listed here only because it travels the same query string. `variant` is the
// same kind of thing: the main title's eyebrow weight option, a styling
// switch that changes no string.
const COPY = ['act', 'label', 'title', 'subtitle', 'quote', 'quote_by', 'quote_note',
  'qr_dialogue', 'qr_domain', 'stage', 'accent', 'variant', 'angle', 'size',
  'mode', 'text', 'placement', 'blue_letters']
const LISTS = ['body', 'chapters']
const ASSETS = ['art', 'qr', 'wallpaper', 'glyph_src']
// Structured copy: one JSON param, because a caption box is a variable-length
// stack of authored lines and a card may carry several.
const JSON_COPY = ['captions', 'emphasis', 'glyph']

function parseArgs(argv) {
  const args = { manifest: null, outDir: null, only: null, wallpaperSeed: null, scale: 1 }
  for (let i = 0; i < argv.length; i++) {
    const [key, inline] = argv[i].startsWith('--') ? argv[i].slice(2).split('=', 2) : []
    if (!key) { continue }
    const value = inline === undefined ? argv[++i] : inline
    if (key === 'manifest') { args.manifest = value }
    else if (key === 'out-dir') { args.outDir = value }
    else if (key === 'only') { args.only = value.split(',') }
    else if (key === 'wallpaper-seed') { args.wallpaperSeed = value }
    else if (key === 'scale') { args.scale = value }
    else { throw new Error(`unknown option --${key}`) }
  }
  if (!args.manifest || !args.outDir) {
    throw new Error('usage: render-cards.mjs --manifest <plates.json> --out-dir <dir>')
  }
  return args
}

// A card may ask for a RANDOM Bluefin wallpaper behind it rather than naming
// one, at the owner's request ("have it be a random one every time"). A random
// render is not reproducible unless the roll is written down, so the choice is
// recorded in <out-dir>/wallpapers.json and can be replayed with
// --wallpaper-seed. Chosen by hash, so the same seed always yields the same
// wallpaper regardless of how the directory is ordered on disk.
function hashString(text) {
  let hash = 2166136261
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i)
    hash = Math.imul(hash, 16777619) >>> 0
  }
  return hash
}

function chooseWallpaper(dir, cardId, seed, match) {
  const pattern = match ? new RegExp(match) : null
  const candidates = fs.readdirSync(dir)
    .filter(name => /\.(webp|png|jpe?g)$/i.test(name))
    .filter(name => !pattern || pattern.test(name))
    .sort()
  if (candidates.length === 0) {
    throw new Error(`${cardId}: wallpaper_dir has no matching images: ${dir}`)
  }
  const index = seed === null
    ? Math.floor(Math.random() * candidates.length)
    : hashString(`${seed}:${cardId}`) % candidates.length
  return path.join(dir, candidates[index])
}

const args = parseArgs(process.argv.slice(2))
const manifestPath = path.resolve(repoRoot, args.manifest)
const outDir = path.resolve(repoRoot, args.outDir)
fs.mkdirSync(outDir, { recursive: true })

const parsed = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
const entries = Array.isArray(parsed) ? parsed : parsed.plates
const cards = entries.filter(entry => TEMPLATES[entry.kind]
  && (!args.only || args.only.includes(entry.id)))
const skipped = entries.length - cards.length

const browser = await chromium.launch({
  // The comic card measures each artwork's visible alpha bounds by reading the
  // pixels back, exactly as centerComicHeroShot() does. Reading a file:// image
  // out of a canvas is cross-origin without this flag, and the card silently
  // falls back to a plain contain-fit.
  args: ['--allow-file-access-from-files'],
})
// 1920x1080 at 1x: the programme is 1080p, so this is the delivered size and
// nothing is resampled. `--scale 2` raises deviceScaleFactor to 2 for a 4K
// master, the way the ~/Videos plate renderers do for their 3840x2160
// composites.
//
// The VIEWPORT stays 1920x1080 in CSS pixels at every scale, so the layout the
// cards were authored against is bit-for-bit the same and only the device
// pixels double. That is what makes this safe for the 1080p programme: at the
// default scale of 1 the output is unchanged, so every delivered act still
// renders exactly the card it was signed off on.
const cardScale = Number(args.scale ?? 1)
if (!Number.isFinite(cardScale) || cardScale < 1) {
  throw new Error(`--scale must be a number >= 1, got ${args.scale}`)
}
const page = await browser.newPage({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: cardScale,
})

const wallpaperLog = {}

for (const card of cards) {
  const params = new URLSearchParams()
  for (const key of COPY) {
    if (card[key]) { params.set(key, String(card[key])) }
  }
  for (const key of JSON_COPY) {
    if (card[key]) { params.set(key, JSON.stringify(card[key])) }
  }
  for (const key of LISTS) {
    for (const value of card[key] ?? []) { params.append(key, String(value)) }
  }
  for (const key of ASSETS) {
    if (!card[key]) { continue }
    const asset = path.resolve(repoRoot, card[key])
    if (!fs.existsSync(asset)) {
      throw new Error(`${card.id}: ${key} does not exist: ${asset}`)
    }
    params.set(key, `file://${asset}`)
  }
  if (card.wallpaper_dir) {
    const dir = path.resolve(repoRoot, card.wallpaper_dir)
    if (!fs.existsSync(dir)) {
      throw new Error(`${card.id}: wallpaper_dir does not exist: ${dir}`)
    }
    const chosen = chooseWallpaper(dir, card.id, args.wallpaperSeed, card.wallpaper_match)
    params.set('wallpaper', `file://${chosen}`)
    wallpaperLog[card.id] = chosen
  }

  await page.goto(`file://${path.join(here, TEMPLATES[card.kind])}?${params}`)
  await page.waitForFunction('window.__renderReady === true')
  const dest = path.join(outDir, `plate_${card.id}.png`)
  // omitBackground keeps the act slide's scrim translucent, so it can be
  // flattened onto black as a programme item OR composited over footage. The
  // comic card paints its own opaque black, exactly as the site does.
  await page.screenshot({ path: dest, omitBackground: true })
  // A card that had to shrink to fit says so on the way past. Silent clipping
  // is the failure this reports: the card is 1920px wide and hides overflow,
  // so copy that does not fit simply vanishes.
  const fit = await page.evaluate('window.__fit ?? null')
  const note = fit
    ? `  [${fit.width}/${fit.room}px${fit.shrunk
        ? `, shrunk ${fit.requested} -> ${fit.rendered}px` : ''}]`
    : ''
  console.info(`wrote ${path.relative(repoRoot, dest)}  (${card.kind})${note}`)
}

await browser.close()
if (Object.keys(wallpaperLog).length > 0) {
  const logPath = path.join(outDir, 'wallpapers.json')
  const existing = fs.existsSync(logPath) ? JSON.parse(fs.readFileSync(logPath, 'utf8')) : {}
  fs.writeFileSync(logPath, `${JSON.stringify({ ...existing, ...wallpaperLog }, null, 2)}\n`)
  console.info(`recorded ${Object.keys(wallpaperLog).length} wallpaper choice(s) in ${path.relative(repoRoot, logPath)}`)
}
console.info(`${cards.length} card(s); ${skipped} non-card plate(s) left to tools/plate.py`)

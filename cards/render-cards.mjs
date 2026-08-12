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
// It renders only the full-frame kinds (`act`, `comic`); Guardian nameplates,
// the deck's title card, chat and status plates are tools/plate.py's job and
// are skipped with a note.
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

const TEMPLATES = { act: 'act.html', comic: 'comic.html' }
// One authored row per key. A key absent from the manifest is absent from the
// URL, and the card leaves that row out: a missing string is omitted, never
// defaulted. `body` and `chapters` repeat.
const COPY = ['act', 'label', 'title', 'subtitle', 'quote', 'quote_by', 'quote_note',
  'qr_dialogue', 'qr_domain']
const LISTS = ['body', 'chapters']
const ASSETS = ['art', 'qr']

function parseArgs(argv) {
  const args = { manifest: null, outDir: null, only: null }
  for (let i = 0; i < argv.length; i++) {
    const [key, inline] = argv[i].startsWith('--') ? argv[i].slice(2).split('=', 2) : []
    if (!key) { continue }
    const value = inline === undefined ? argv[++i] : inline
    if (key === 'manifest') { args.manifest = value }
    else if (key === 'out-dir') { args.outDir = value }
    else if (key === 'only') { args.only = value.split(',') }
    else { throw new Error(`unknown option --${key}`) }
  }
  if (!args.manifest || !args.outDir) {
    throw new Error('usage: render-cards.mjs --manifest <plates.json> --out-dir <dir>')
  }
  return args
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
// nothing is resampled. A 4K master would raise deviceScaleFactor to 2, the
// way the ~/Videos plate renderers do for their 3840x2160 composites.
const page = await browser.newPage({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
})

for (const card of cards) {
  const params = new URLSearchParams()
  for (const key of COPY) {
    if (card[key]) { params.set(key, String(card[key])) }
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

  await page.goto(`file://${path.join(here, TEMPLATES[card.kind])}?${params}`)
  await page.waitForFunction('window.__renderReady === true')
  const dest = path.join(outDir, `plate_${card.id}.png`)
  // omitBackground keeps the act slide's scrim translucent, so it can be
  // flattened onto black as a programme item OR composited over footage. The
  // comic card paints its own opaque black, exactly as the site does.
  await page.screenshot({ path: dest, omitBackground: true })
  console.info(`wrote ${path.relative(repoRoot, dest)}  (${card.kind})`)
}

await browser.close()
console.info(`${cards.length} card(s); ${skipped} non-card plate(s) left to tools/plate.py`)

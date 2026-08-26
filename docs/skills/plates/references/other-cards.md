# The cards that are not lower thirds

The detail behind [`../plates.md`](../SKILL.md)'s "Cards that are not lower
thirds". Four `kind`s that do not live in the reveal plate's row -- three of
them chrome the lower third can share the screen with, and one that is the
lower third's other half.

## Three cards that own a row of their own

Most cards are lower thirds and only one may be up at a time. Three are not,
and `tools/plate.py`'s `CHROME_ROWS` is the list:

| `kind` | Where it sits | What it is |
|---|---|---|
| `status` | top left, or bottom right with `position: "status-bottom"` | the site's persistent HUD nameplate (`detail` + `label`) |
| `miniboss` | top centre, `position: "boss"` | Destiny's boss bar — rank diamond, `name`, `title`, health bar |
| `achievement` | top centre, `position: "toast"` | the Xbox unlock toast — `name` + `score`, in #107C10 |

Each may share the screen with a lower third. **`miniboss` and `achievement`
may not share it with each other**, because they are the same row; the overlap
check enforces exactly that, and two `status` cards at once are still an error.

The `miniboss` bar is the one card here that may carry copy nobody's identity
was authored for — **it names a villain, not a person**. Put a real name on it
and every rule in this file applies again.

## The GUARDIAN BOND companion card

`kind: "companion"` is the site's other lower-third half
(`.wolves-companion-plate` in `WolvesIntroOverlay.vue`): the bonded dinosaur
beside a Guardian's own plate — the fixed `GUARDIAN BOND` label, the animal's
authored name, its species' scientific name, and the species artwork.

- The bonds are **read**, never composed, from `wolves-guardian-dinosaur-bonds.ts`
  and `wolves-dinosaur-species.ts`. Four exist.
- **An unnamed bond drops the name row**, exactly as the site's own `v-if`
  does — Bob Killen's Torosaurus has no `dinosaurName`, so its card has none.
- `bond_of: "<guardian plate id>"` is what lets the pair share the screen. The
  exemption is **named** on purpose: a shared `group` string could quietly
  cover somebody else's plate too. It also covers other owner-instructed
  pairs: act II's "Sup" pill bonded to Kyle's locked nameplate, and
  kolunmi's "Cardio!" bonded to that "Sup" (a pill answering a pill,
  2026-08-24). Do **not** relax the one-plate rule by lane instead — a
  left/right auto-exemption spreads to cards nobody named; it was tried and
  reverted the same day.
- Artwork is cached by `scripts/fetch_companion_art.py` into gitignored
  `renders/`; a missing file degrades to the card alone.
- `art_max_h` caps the picture's height. It is a **frame judgement**, never a
  default: act I's Alamo needs it because at full height the artwork covered
  Natali Vlatko's name, which was found on the burned frame and not in the
  manifest.

A bond does **not** follow a recast on its own. Cortney Nickerson inherits Bob
Killen's Torosaurus because the owner said so, and that is recorded on the
plate.

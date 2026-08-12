# The comm line: one file, one command, one cut

**Status: planned, not implemented.** This is the design the epics in
[`README.md`](README.md) implement. Nothing here exists yet; where it says
"does", read "will". Issue: [#9](https://github.com/castrojo/destiny-vids/issues/9).

## The problem

The index turns an outline into a cut of clean Bungie shots, and `tools/plate.py`
names the cast on screen. What it cannot do is the thing the project is actually
for: **take a month of open-source contribution and hand it back as a highlight
reel** — contributors' faces big enough to recognize from a couch, their voices on
a comm line, their affiliation and their title on the plate, and the whole thing
cut to a song.

Today that would take a maintainer six files, four commands, and an NLE. It
should take **one file and one command**.

## The shape of the answer

```
WOLVES.md ──parse──> comm log ──┬── beats ────> story.py ───> cut list ──> render.py ──┐
                                │                                ▲                     │
                                └── chatter ──> chatter.py ──> layer ──────────┐        │
                                                                              ├─ burn ─┴─> renders/wolves.mp4
people/*.json ──resolve──> cast ─────────────> plate.py ────> manifest ───────┘
                                                    ▲
tracks/*.json ──tempo.py──> beat grid ──────────────┘
```

Five inputs; a maintainer only ever edits the first.

| Input | Who writes it | Committed? |
|---|---|---|
| `WOLVES.md` | the maintainer, by hand | yes — it is the show |
| `people/<login>.json` | `tools/identity.py sync`, from GitHub | yes — metadata only |
| `tracks/<track_id>.json` | whoever adds a song | yes — metadata only |
| `segments/*.json` | the indexing pipeline (exists today) | yes |
| `vocab/*.yaml` | anyone adding an enum value | yes |

Three things are never committed, for exactly the reason footage is never
committed: `media/` (source video **and** audio), `avatars/` (profile pictures),
`emblems/` (org marks). The index references them; it does not carry them.

## 1. `WOLVES.md` — the whole Wolves experience, in five constructs

Plain markdown at the repo root, readable on GitHub with no renderer. Five
constructs. No front matter, no YAML, no timestamps:

| Construct | Means |
|---|---|
| `# Title` | the cut's title |
| `## Section` | a movement: one song section, one register, its own shots |
| `> key: value` | section directives (`track`, `register`, `hold`) |
| `- beat text` | one outline beat, exactly as `stories/*.txt` writes them today |
| `@login: line` | one line of radio chatter, spoken by that GitHub user |

Everything else — prose, `###` headings, HTML comments, tables — is **ignored**,
so the file doubles as the maintainer's notebook.

```markdown
# Wolves — August 2026

Notes to self live here and the parser ignores them.

## 1. Cold open
> track: long-way-home
> register: +2

- wide establishing shot of the Traveler
@castrojo: comms check. anybody still on this channel?
- a crowd of guardians gathered beneath it
@karenaangel: we never left.

## 2. The work
> track: long-way-home
> register: -1

- guardians parkouring across a bridge toward the light
@mrbobbytables: forty commits merged since the last broadcast.
- close up on a lone titan helmet
```

Three rules make this file safe to hand to anyone:

1. **Order is the timeline.** A chatter line is anchored to the beat above it.
   No timestamps, ever — timings are computed, and a hand-typed one is wrong the
   moment a beat above it changes.
2. **`@login` is a GitHub login and nothing else.** Not a display name, not a
   nickname. An unknown login is a **warning**, recorded by name in the
   report's unresolved-logins counter — never a silent drop, and never a hard
   error. That is the posture `story.py` already takes on an unmatched beat: it
   collects the miss in `story['misses']`, reports it, and still returns 0 with
   a cut made from the beats that did resolve.
3. **Nothing else about a person appears in this file.** No display names, no
   companies, no titles, no avatars. Every one of those is resolved from GitHub
   (§2). If it can be looked up, typing it by hand is only a way to be wrong
   later.

## 2. GitHub is the source of truth

`tools/identity.py sync` reads the public GitHub profile of every login in the
comm log and in the month's ensemble roster, and writes one **person record**
each. Metadata only — the avatar *image* lands in gitignored `avatars/`.

```jsonc
{
  "login": "castrojo",
  "display_name": "Jorge Castro",       // GitHub `name`, else the login
  "avatar_url": "https://avatars.githubusercontent.com/u/1264109?v=4&s=460",
  "avatar_sha256": "…",                 // pins the cached file; a new PFP is a diff
  "company_raw": "@github",             // verbatim, self-declared, GitHub `company`
  "affiliation": "github",              // resolved via vocab/affiliation.yaml, or null
  "project": "bluefin",                 // where they contributed, for the title
  "title": "Shipwright of Bluefin",     // generated, deterministic, stable
  "badges": [{ "issuer": "…", "name": "…", "issued_on": "2025-11-09" }],
  "withhold": []                        // any of: avatar, affiliation, badges
}
```

`company`, `name`, `blog` and `avatar_url` are all fields of the public
`GET /users/{username}` response, and `company` is **free text a person typed
about themselves** — GitHub does not validate it, though it links `@handle`
forms. Avatar URLs take `?s=<px>`, capped at 460 px, which is the ceiling on how
big a face can legitimately be drawn.

Why commit these records? The suite is offline, a render must be reproducible
without the network, and **a diff is the review**: "castrojo's affiliation
changed" belongs in a pull request, not as a surprise in a finished video.

Three rules — the casting rule, applied to real employers:

- **Never guess an affiliation.** If `vocab/affiliation.yaml` does not recognize
  `company_raw`, the resolved `affiliation` is `null` and the plate carries **no
  emblem**. The unrecognized string is reported so someone can add an alias; it
  is never fuzzy-matched. A wrong affiliation credits a real person to a company
  they do not work for — the same class of error as a wrong `character` tag.
- **Only follow links the person published.** Badges are read from a Credly
  profile **only** when that person's own GitHub profile links to it. We do not
  go looking for people.
- **`withhold` is honored on the next render and needs no reason.** Faces are
  personal. One line in a pull request opts any of avatar / affiliation / badges
  out, and the render reports who withheld what, so nobody is silently missing.

**The consent model itself is undecided.** `withhold` as written is opt-*out*;
J5 asks whether it should be opt-*in*. That is a claim about real people, which
`AGENTS.md` reserves to the owner — so this section describes the *recommended*
mechanism, not a settled one. Until J5 closes, Epic B4 is `automatable: no`,
`blocked_on: J5`, and the only consent-safe render is one with no person
records at all.

## 3. Affiliation is tiered. People are not.

The bling matches the affiliation, and only the affiliation. CNCF's actual
membership levels are **Platinum, Gold, Silver, and End User** (with Supporter
and Contributor sub-levels) — published per organization as
`cncf_membership_level` in `cncf/landscape`'s `landscape.yml`, which is where the
tier in `vocab/affiliation.yaml` comes from and what a refresh script checks
against.

| Tier | Emblem chrome |
|---|---|
| `platinum` | brightest rule, double band, widest crest |
| `gold` | the existing `leader` gold (`#facc15`) |
| `silver` | the existing `trustee` burnished silver (`#cbd5e1`) |
| `end_user` | the default blue (`#93c5fd`) |
| unrecognized / none | **no emblem band at all** |

Tier chrome is a **palette on the org band** — never on the person's name, their
avatar ring, their title, or their ribbons. A Platinum employer does not make a
contributor more important than an unaffiliated one, and the renderer makes that
structurally impossible rather than merely discouraged: the tier palette is only
ever passed to the band's draw call.

The CNCF mark is the worked example of the whole idea — a small glyph beside a
chatter line, a large one on the nameplate — because "who paid for this work" and
"which foundation it belongs to" are the two facts an open-source highlight reel
exists to show.

**But org marks are trademarks, not assets.** Everything in `cncf/artwork` is
licensed under the Linux Foundation Trademark Usage Guidelines, not an
open-source licence, and the terms are specific: do not alter colors or
proportions, do not imply sponsorship or endorsement, and **do not combine the
marks with other marks into a composite**. A CNCF logo set inside a Destiny-style
hex crest is exactly the composite that clause describes. So: marks live in
gitignored `emblems/`, are fetched from the owner's official repository, are
rendered **unmodified, uncropped, with clear space, on a neutral field beside the
chrome rather than inside it**, and a missing mark degrades to the org's *name*
set in the tier chrome. Issue #6 is the precedent for what happens when this is
settled after the design instead of before it — Epic J settles it first.

## 4. Titles: `$Position of $Project`

Named leads keep the titles they were written with — `vocab/casting.yaml`'s
`plate.title`, "Reconciler of the Plane", is authored and stays authored. This is
for **everyone else**: the contributor who showed up this month and has never
been on screen.

```
title(login, project) = positions[H(login, project, "pos") % len(positions)]
                        + " of " +
                        synonyms[project][H(login, project, "syn") % len(synonyms[project])]
```

**This mechanism is an unmade owner decision, not a specification.** A
generated title is on-screen copy nobody authored, placed beside a real
person's face — the exact thing "What this deliberately does not build" forbids
below, and one of the three classes `AGENTS.md` says an agent may never decide.
Until the owner rules on it, this section is a *proposal*: Epic D is
`automatable: no`, `blocked_on: owner decision`, and the fallback is no title
row at all (a `null` title is already a valid person record), never a generated
one.

`H` is a truncated SHA-256 over its inputs, so a person's title is **stable
forever** — a credit, not a slot machine — and changes only when they move to a
new project. ~64 Destiny-flavored positions × ~8 synonyms per project × N
projects clears a thousand combinations before the second project is added, which
is the point: "Shipwright of Kubernetes" for one contributor and "Cartographer of
the Watchfire" for the Prometheus contributor standing next to them.

Two constraints hold the vocabulary together:

- **No real governance word may ever be generated.** `maintainer`, `chair`,
  `TOC`, `TAG lead`, `steering`, `approver`, `reviewer`, `ambassador`, `fellow`,
  `board`, `owner`, `founder` are a checked-in forbidden list with a test against
  it. "Shipwright of Kubernetes" is evident fiction; "Maintainer of Kubernetes"
  is a false claim about a real role, and no amount of lore framing fixes that.
- **CNCF Code of Conduct, read first rather than last.** Positions are
  non-demeaning, non-gendered, imply no authority over another person, and carry
  no military rank. Every position ships reviewed (Epic J).

Project synonyms are nicknames of *that* project ("the Helm" for Kubernetes),
must not collide across projects, and must never be another project's mark.

## 5. Heraldry: the ribbon rack

Credly badges become a **service ribbon rack** across the bottom of the
nameplate — the medieval/military device the issue asks for, and a genuinely good
fit: a rack encodes a career at a glance, in rows, without a word of text.

- One ribbon per distinct badge, ordered by issue date (most recent first), then
  by name. Deterministic.
- The same badge earned N times collapses into one ribbon with **N−1 pips**, the
  way a repeat award takes an oak-leaf cluster instead of a second ribbon.
- Rows of three, **two rows maximum**; overflow becomes a `+N` device on the last
  ribbon. A rack that fills the plate is a rack nobody reads.
- A ribbon's colorway is **derived, not downloaded**: `H(issuer, badge_name)`
  selects a two- or three-stripe pattern from a checked-in palette that
  harmonizes with the plate chrome.

That last rule is doing real work. A user's *public* badges are readable from
`https://www.credly.com/users/<handle>/badges.json` — no key, but undocumented,
unsupported, and a side effect of profile rendering, so the pipeline caches what
it reads into the person record and degrades to "no ribbons" when it breaks.
Credly's supported display path is their embed widget, and badge *images* are the
issuer's marks with no third-party display licence. So we render heraldry *about*
a badge and never redistribute the badge artwork — the same posture the repo
takes toward footage.

## 6. Radio chatter: the face is the interface

In-universe this is a comm line. On screen it is **a big avatar, a name, a
sparkline, and almost no chrome**:

```
   ╭──────────╮
   │          │  CASTROJO   ⬡ CNCF
   │   PFP    │  ▁▂▅█▆▃▁▂▅▇█▅▂▁▁▂▃▁        ← keys open, chatters, keys shut
   │          │  comms check. anybody still on this channel?
   ╰──────────╯
```

Each rule below is a number a test can check:

- **The avatar is the largest element**: 220 px by default (20% of frame height
  at 1080p), floor 160 px, never upscaled past the 460 px GitHub serves. A face
  has to survive a ten-foot viewing distance.
- **Chrome is capped.** Box, rules, and scrim together may not exceed 35% of the
  chatter block's area. If the block occludes the shot, the thing occluding it
  must be a person's face — not the frame around a person's face. There is no
  chat box: text sits on a scrim exactly as wide as the text.
- **10-foot type, and the margins that go with it.** Android TV's design canvas
  is 960×540 dp — 1 dp = 2 px at 1080p — putting its body-text minimum of 34 sp
  at **68 px**, and EBU R 095 puts *text* inside the 10% title-safe box
  (1536×864 px, a 192 px horizontal margin). Today's plates sit at the 5%
  action-safe margin with a 28.8 px eyebrow: legible on a monitor, not from a
  couch. Nothing in the comm rail goes below **34 px**, the speaker's name is
  **≥ 48 px**, and the rail lives inside title-safe.
- **One voice at a time.** The comm line holds one line; a second waits. This is
  both in-fiction and the only readable option.
- **Chatter and a nameplate never collide** — not merely "not in the same
  window", but not in the same rectangle. The existing "two plates are never
  visible at once" invariant extends to a geometric check.

### The sparkline

Borderlands' ECHO sells a comm line with a waveform that keys open, chatters, and
keys shut. Ours does the same and needs **no audio at all** — the envelope is
generated from the text:

```
seed     = H(login, section, line_index, text)
pulses   = one per word; amplitude ∝ word length, jittered from the seed
envelope = attack ramp (mic keys open) · pulses · release ramp (mic keys shut)
idle     = a low carrier with a slow ping, so the channel reads as open
```

Same line in, same waveform out — a re-render stays diffable — and a long line
visibly chatters more than a short one, which is the only "sync" a viewer
actually perceives. It is a cheap trick, it is the fun part, and TTS is
explicitly not on the table.

### How it gets onto the video

The chatter layer is a **small rectangle, not a full frame**: 12 fps RGBA PNGs of
just the comm rail's bounding box, handed to ffmpeg as one image-sequence input
(`-framerate 12 -i chatter_%05d.png`) and composited at a fixed offset in the
**same single pass** that burns the plates, gated the same way
(`overlay=…:enable='between(t,in,out)'`). One extra input, one extra overlay, no
per-line explosion. 12 fps is five times cheaper than 60 and reads more
in-fiction than smooth. If the sequence ever gets unwieldy, VP9 with
`-pix_fmt yuva420p` carries alpha in WebM and is available even in Fedora's
`ffmpeg-free` (VP9 is royalty-free; H.264 is what is missing there) — but a PNG
sequence needs no codec at all, so it is the default.

## 7. The math: make the cut land on the music

This is what makes a highlight reel feel deliberate rather than assembled, and it
is arithmetic, not signal processing.

A **track record** (`tracks/<track_id>.json`, metadata only, audio in `media/`,
carrying `usage_class` and `source_rights_note` exactly like a video record)
declares `bpm`, `beat_offset_sec`, `meter`, and its `sections[]`.

```
beat = 60 / bpm
grid = beat_offset + n · beat
bar  = meter · beat
```

Three uses, in order:

1. **Shots snap to the beat.** A shot's duration rounds to a whole number of
   beats — **downward, always**, because the only legal edit is trimming from the
   tail (the in-point is what the index spent a detector pass to find, and a shot
   cannot be extended without freezing it). A shot shorter than one beat keeps
   its source length and is **reported as off-grid**, never stretched.
2. **Sections snap to the bar.** A `## Section` maps to one song section and its
   shots fill exactly that section's bars. Run out of beats before bars and the
   shortfall is reported while the last shot holds; run out of bars first and the
   unplaced beats are reported. Nothing is silently dropped.
3. **Chatter lands on downbeats.** A line's hold is
   `clamp(0.8 + len(text)/15, 1.8, 7.0)` seconds — a subtitle reading rate —
   rounded **up** to a whole beat, placed at the first downbeat at or after its
   anchor shot. Lines that do not fit their section are reported, never
   truncated.

**BPM is authored, not detected at render time.** `tools/tempo.py detect` may
propose a BPM from the audio when `librosa` happens to be installed, but a human
writes the number into the track record. Detection is an authoring aid; the
record is the truth. That keeps the suite offline, the render deterministic, and
the dependency optional — the same posture `scenedetect` already has, and a
practical one: librosa drags in numba, which still gates it on Python 3.13, and
`aubio`'s official wheels stopped at 2019.

**And the mix stays mixed.** Three quotas, all plain counting:

- **Source diversity** — at most two consecutive shots from the same `video_id`,
  so a highlight reel surveys the footage instead of re-cutting one trailer.
- **Register match** — a section declares a `register` (the existing −2..+2 axis,
  which already distinguishes "choir/orchestral" from "radio chatter and
  gunfire"), and the matcher biases toward shots at that register. That is the
  whole of "the shots always match the song", and it costs one weight.
- **Contributor coverage** — every login on the month's roster gets a plate
  somewhere in the cut, and nobody gets two before everybody has one. Rotation is
  by login order, not by contribution volume: `tools/ensemble.py` already
  deliberately sorts by login rather than by commit count, and this is the same
  decision applied to screen time. Anyone who still does not fit is **reported as
  uncredited** — the counter exists so that "everybody made it" and "we quietly
  ran out of room" cannot look the same.

## 8. One command, and the project stays alive

```bash
python3 tools/wolves.py render --month 2026-08 --out renders/wolves.mp4
```

Parse → resolve → match → quantize → cut → plate → chatter → burn, then one
report:

```
WOLVES — August 2026     3 sections · 41 shots · 12 lines · 2:49 · 96 BPM
  unmatched beats ......... 1   "osiris walks through the infinite forest"
  unresolved logins ....... 0
  unrecognized companies .. 1   hanthor: "the internet"
  withheld ................ 1   someone: avatar
  uncredited contributors . 0
  off-grid shots .......... 2
```

Edit `WOLVES.md`, re-run, get the new video. That is the living project: the file
is the source, the video is a build artifact, and nothing in between is
hand-maintained.

CI runs everything except the render — parse, resolve, match, quantize, plan
plates and chatter — because none of it touches a frame. **CI validates the plan;
a human with the footage renders the file.** That boundary falls straight out of
"never commit footage", and it means a pull request that breaks the comm log
fails before anyone burns an encode.

## What this deliberately does not build

Stated so nobody builds it by accident:

- **No text-to-speech, and no audio analysis at render time.** The sparkline
  comes from text; the BPM is authored.
- **No leaderboard.** The roster sorts by login, not by commit count, and it
  stays that way. Nobody is ranked by output.
- **No tier on a person.** Orgs are tiered; individuals never are.
- **No per-person hand-tuning.** If a plate needs a special case, the special
  case belongs in a vocabulary file, not in a render invocation.
- **No on-screen copy nobody authored.** The nameplate's field set is closed;
  §3–5 extend it *deliberately, once*, with a test pinning the new set, exactly
  as `docs/skills/plates.md` requires.
- **No database, no service, no web UI.** Files in git, one command.

## The rules that outrank convenience, extended

`AGENTS.md` names three. This system adds two of the same kind, and they are
non-negotiable for the same reason:

4. **Affiliation names a real employer.** Resolve it from what the person
   published about themselves, or render nothing. Never fuzzy-match a company.
5. **A face is not a widget.** Avatars, affiliations, and badges are personal.
   `withhold` is honored without discussion, and every render reports who is
   missing and why — because silently dropping a person is the one unacceptable
   outcome, which is the rule the ensemble roster card already exists to enforce.

## Sources

External behavior verified 2026-08-11 rather than recalled, per `AGENTS.md`:

| Claim | Source |
|---|---|
| CNCF levels are Platinum/Gold/Silver/End User; `cncf_membership_level` in `landscape.yml` | <https://www.cncf.io/about/members/>, <https://github.com/cncf/landscape> |
| `cncf/artwork` is under LF Trademark Usage Guidelines; no alteration, no composite marks, no implied endorsement | <https://github.com/cncf/artwork/blob/master/LICENSE.md>, <https://www.linuxfoundation.org/trademark-usage>, <https://www.cncf.io/brand-guidelines/> |
| Public badges at `credly.com/users/<handle>/badges.json`; official API is OAuth, issuer-scoped; embed widget is the supported display path | <https://api.credly.com/docs>, <https://support.credly.com/> |
| `GET /users/{username}` exposes `company`, `name`, `blog`, `avatar_url`; `company` is unvalidated free text; `?s=` caps at 460 px | <https://docs.github.com/en/rest/users/users> |
| `overlay` supports timeline `enable=`; `-framerate N -i seq_%05d.png` sets an image sequence's rate; VP9 carries alpha via `yuva420p`; Fedora `ffmpeg-free` has libvpx but not H.264 | <https://ffmpeg.org/ffmpeg-filters.html#overlay>, <https://trac.ffmpeg.org/wiki/Slideshow>, <https://trac.ffmpeg.org/wiki/Encode/VP9> |
| librosa needs numba (Python 3.13 still gated); `aubio`'s official wheels stopped at 0.4.9 (2019) | <https://librosa.org/doc/latest/install.html>, <https://pypi.org/project/aubio/> |
| Android TV: 960×540 dp canvas, 34 sp body minimum; EBU R 095 title-safe is the 10% box (1536×864 at 1080p) | <https://developer.android.com/design/ui/tv>, <https://tech.ebu.ch/publications/r095> |

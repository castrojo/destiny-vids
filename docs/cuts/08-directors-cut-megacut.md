# Seven Days to the Wolves — director's cut megacut

The finished Wolves cuts assembled into **one continuous programme**, with the
reference deck's title cards between them.

**Status: built, verified, not delivered.** It lives in `renders/` only. Nothing
goes to `~/Videos/UPLOAD/` for the Wolves feature — provenance there is an
unresolved owner decision, and this cut does not change that.

```
renders/07-seven-days-to-the-wolves-directors-cut-megacut.mp4
301.05s · 1920x1080 · H.264 High · yuv420p · BT.709 SDR · 59.94 fps · 48 kHz 5.1 · 225 MB
```

## Where the running order comes from

Not invented here. It is `buildDirectorsCutVideoSequence()` in
`~/src/website/src/data/wolves-intro-sequence.ts`, which runs
**title card → `wolves-prologue` (94s) → `wolves-intro` → wolves**. `wolves-intro`
is the Destiny hero video, and it is the one carrying the Kat and Natali
nameplates — which is how the owner identified it ("it has kat and natali in
it… after the prologue but before wolves").

| From | To | Item | Source |
|---|---|---|---|
| 0.000 | 5.000 | Card — `PROJECT BLUEFIN` / *seven days to the wolves* | rendered |
| 5.000 | 116.567 | **Destiny hero video**, six Guardians plated | `BKm0TPqeOjY` |
| 116.567 | 121.567 | Card — `Kat Cosgrove` / *Sentinel Titan* | rendered |
| 121.567 | 155.567 | Kat Cosgrove — Guardian intro | `UPLOAD/01-…` |
| 155.567 | 160.567 | Card — `Natali Vlatko` / *Behemoth Titan* | rendered |
| 160.567 | 185.825 | Natali Vlatko — Guardian arrival | `UPLOAD/02-…` |
| 185.825 | 190.825 | Card — `Europa` / *Director's Cut* | rendered |
| 190.825 | 301.025 | Europa Director's Cut — Laura Santamaria | `UPLOAD/zz-…` |

Segments 2–4 are owner-approved deliverables **reused as-is**; this repo cannot
rebuild them (they are `~/Videos` projects with their own `render/run-*.sh`).
The assembly re-encodes them once and edits nothing.

**`07-seven-days-to-the-wolves.mp4` — the musical prototype — is deliberately
not in this programme.** It is separate live work with its own unresolved
provenance question.

## The hero segment

**Source: `BKm0TPqeOjY`, "Destiny 2: Into the Light Cinematic", official
"Destiny 2" channel.** 120.2s, 1080p30, fetched **video-only** with `yt-dlp`
(cookies from the Flatpak Firefox profile). `usage_class:
third_party_copyrighted`, Bungie fan-content policy, non-commercial, no footage
committed.

**Owner decision, this session: use Bungie's own upload and drop its audio.**
The website defaults instead to `BV3BZKbpBns` ("Into the Light (Without
Dialogue)", *Destiny Music Archive* — a fan archive), and offers Bungie's as an
"Ikora voice over" toggle. Taking Bungie's silent resolves three things at once:

- **provenance** — an official upload, so the fan-archive question does not arise;
- **the voice-over** — the only reason to prefer the fan copy was that Bungie's
  carries dialogue, and dropping the audio removes the objection entirely;
- **codecs** — AV1 was available and used (format 399).

Accepted cost, recorded: Bungie's is **1080p30** where the fan copy was 1080p60,
so the hero is the only 30fps source in the programme.

### The anchors were re-verified, and they moved

The website's `startOffset: 2` / `maxDuration: 118.8` were frame-measured
against the **123s fan copy**. They do **not** both transfer:

| | Verified on `BKm0TPqeOjY` |
|---|---|
| In | **2.0s** — ESRB "TEEN" card runs 0–1.5s, black by 2.0s. Unchanged. |
| Out | **113.55s** — *not* 118.8s. |

Bungie's upload ends on a **"Season of the Wish" marketing card** from ~114.75s
to the end, which the fan copy does not have. Reusing `118.8` would have left
3.8 seconds of marketing on screen. Content ends hard between 113.50 and 113.55.

**Trimmed 2.0 → 113.55 = 111.567s.**

### The six Guardian plates

Copy reproduced verbatim from
`~/src/website/public/wolves/characters/characters.json`, cross-checked against
the overlay strings in the sequence file. Windows are the sequence file's, minus
the 2.0s offset. Manifest: `stories/megacut/megacut-hero-plates.json`.

All six were **frame-checked against this file, not assumed** — the fan copy has
~5.4s more content, so the timelines could have diverged. They do not; the
difference is entirely in the tail:

| Programme | Verified on screen | Plate |
|---|---|---|
| 3.0 – 12.5 | purple void vortex | Bob Killen — Voidwalker Warlock (trustee) |
| 12.5 – 22.5 | Ward of Dawn bubble, Titan inside | Kat Cosgrove — Sentinel Titan |
| 38.0 – 46.0 | arc lightning duel | Kaslin Fields — Stormcaller Warlock |
| 68.5 – 75.0 | solar winged Guardian | Laura Santamaria — Gunslinger Hunter |
| 83.0 – 93.0 | green Strand tendrils | Christoph Blecker — Broodweaver Warlock (leader, gold) |
| 87.5 – 94.0 | icy-blue crystal Guardian, right of frame | Natali Vlatko — Behemoth Titan |

Two behaviours are carried over from the sequence file so nobody "fixes" them:

- **Kat's plate is deliberately cued ahead of the footage cut** (source 14.5,
  not the frame-accurate 17.5) by explicit owner request, with Bob's shortened
  to match.
- **Christoph and Natali share the shot** from ~89.5, which is why they carry
  opposite `position` values and a shared `group` key — `tools/plate.py` treats
  a group row as one row, which is exactly what the live overlay renders.

## What is reproduced, and the one thing that is not

The three live-overlay behaviours this cut originally shipped without are now
**built** (2026-08-12), so the hero segment is generated end to end here rather
than approximated:

1. **The top status nameplate** — the site's persistent top-of-frame HUD
   (`Nameplate.vue`), which the intro overlay re-labels per cue. It runs the
   whole segment on the authored default from `INTRO_DISPLAY['wolves-intro']`
   (*Meet your Fireteam* / *a project to bring their stories to life*), and is
   overridden by the closing **Legends Sought** / *"Follow the path, we've got
   your back"* card at source 106.5 onward — 7 seconds of authored copy that
   used to be missing entirely.
2. **The three `#nova4ever` glitch bursts** (source 52, 60.6, 68.1 — 0.45s
   each): the red/cyan `text-shadow` split and the clip-path tear from
   `@keyframes wc-nameplate-glitch`. The split is applied to the **type**, not
   the panel, because that is what a text-shadow does.
3. **`raised` on Natali's plate** — this turned out **not** to be a visual
   judgement at all: `.wolves-guardian-plate-raised` is an authored rule
   (`bottom: auto; top: 28%`). Reproducing it lifts her card beside the
   Behemoth Guardian and staggers it against Christoph's in the lower third,
   which is how the site composes that shared shot.

**The one thing still not drawn is the rotating dinosaur avatar badge** on the
status nameplate. It is animated brand artwork rather than copy, on a
20-second cycle that no still can represent honestly, and a frozen stand-in
would put a picture on the card that nobody authored. Omitted and recorded.

## Deprecations

**The fan-archive hero source is deprecated.** `BV3BZKbpBns` ("Into the Light
(Without Dialogue)", *Destiny Music Archive*) is what the website embeds and
what the `watchUrl`s in `characters.json` point at. This cut uses Bungie's own
`BKm0TPqeOjY` instead, and nothing here should go back to the fan copy: the
official upload removes the provenance question outright, and the only reason
the fan copy was ever preferred — that Bungie's carries an Ikora voice-over —
is moot now the audio is dropped.

Anything reusing the old source must re-verify its own anchors. The two uploads
are **not** interchangeable: `maxDuration: 118.8` is correct for the fan copy
and wrong for Bungie's, whose content ends at 113.55 (see above).

**The plate-only hero is superseded.** A hero segment carrying the six Guardian
plates but no status row is an incomplete reproduction, not a lighter variant.
Rebuild with the full manifest.

## Punch-list — owner decisions, not bugs

- **Natali's title line: two authored strings disagree.** A comment in the
  sequence file says *"Punch first, document later."* per explicit user request;
  her overlay string **and** `characters.json` both say *"Shipwright of
  Kubernetes"*. The two agreeing sources are used. Choosing between two things
  the owner authored, on a real colleague's card, is not automatable.
- **The status nameplate's dinosaur avatar badge** is not drawn (see above).
- **A music bed** under the hero segment and the four cards. They are silent; a
  bed is a licensing decision.
- **Chapter card placement.** The cards use the deck's own geometry, so they sit
  as a lower third on an otherwise black frame. Centring them would look more
  deliberate, but moving authored chrome is a visual judgement.
- **Audio generation loss.** Segments 2–4 are re-encoded once, AAC→AAC at 640k.
  No peak moved (below), but the lossless-master path in `~/Videos/AUDIO.md` is
  the upgrade if a delivered master is ever wanted.
- **Cortney Nickerson stays unplated and uncarded** — unresolved identity.

## Verification

Not asserted — measured.

- **Full `-xerror` decode**: clean, 18 044 frames.
- **Duration**: 301.046s against 301.025s expected (+0.02s, ~1 audio frame of
  AAC padding).
- **Colour**: `bt709` primaries, transfer **and** matrix, matching every other
  deliverable in `UPLOAD/`. The first encode silently produced `unknown`
  primaries and transfer — `-color_primaries` describes the *frames*, and x264
  copies only the matrix from them. Fixed by writing the VUI via `-x264-params`,
  and caught only by probing the output against a known-good file.
- **Levels, per segment** — nothing lifted by the re-encode:

  | Segment | Master | Source |
  |---|---|---|
  | card0 + hero | −91.0 dB (digital silence) | silent by design |
  | card1 | −91.0 dB | silent by design |
  | Kat | −1.1 dB | −1.1 dBTP |
  | card2 | −91.0 dB | silent by design |
  | Natali | −1.0 dB | −0.9 dBTP |
  | card3 | −91.0 dB | silent by design |
  | Europa | −1.1 dB | −1.0 dBTP |

- **Frames extracted and inspected** at every join and inside all six plate
  windows.

## Reproducing

The three manifests are **authored inputs**, so they are committed under
`stories/megacut/` rather than left in the gitignored `renders/`. Everything
under `renders/` and `media/` is a regenerated artifact.

```bash
cd ~/src/destiny-vids

yt-dlp --cookies-from-browser \
  firefox:~/.var/app/org.mozilla.firefox/config/mozilla/firefox/mha2aykb.default-release \
  -f "bv*[height=1080][vcodec^=av01]/bv*[height=1080][vcodec^=vp9]/bv*[height=1080]" \
  -o media/yt_into_the_light_cinematic.%\(ext\)s \
  https://www.youtube.com/watch?v=BKm0TPqeOjY

ffmpeg -ss 2.0 -to 113.55 -i media/yt_into_the_light_cinematic.mp4 -an \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p \
  -vf "scale=1920:1080:flags=lanczos,setsar=1" renders/megacut-01-hero-raw.mp4

python3 tools/plate.py render --manifest stories/megacut/megacut-hero-plates.json \
    --out-dir renders/plates-megacut-hero
python3 tools/plate.py burn --video renders/megacut-01-hero-raw.mp4 \
    --manifest stories/megacut/megacut-hero-plates.json \
    --plates-dir renders/plates-megacut-hero --out renders/megacut-01-hero.mp4

python3 tools/plate.py render --manifest stories/megacut/megacut-cards.json \
    --out-dir renders/plates-megacut-cards
python3 tools/megacut.py stories/megacut/megacut.json
```

Use `/home/linuxbrew/.linuxbrew/bin/ffmpeg` — the system `ffmpeg` is
`ffmpeg-free`, has no H.264 decoder, and fails only once decoding starts, which
reads like a corrupt input file.

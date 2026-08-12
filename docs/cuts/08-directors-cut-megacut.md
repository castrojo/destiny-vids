# Seven Days to the Wolves — director's cut megacut

The finished Wolves cuts assembled into **one continuous programme**, with the
reference deck's title cards between them.

**Status: built, verified, and delivered.** Staged 2026-08-12 at the owner's
request as `~/Videos/UPLOAD/08-seven-days-to-the-wolves-directors-cut.mp4`
(md5 `1dfa3a0209ab8b89e4cf1fe2a568900b`, in that folder's `CHECKSUMS.md5`).

```
renders/07-seven-days-to-the-wolves-directors-cut-megacut.mp4
301.05s · 1920x1080 · H.264 High · yuv420p · BT.709 SDR · 59.94 fps · 48 kHz 5.1 · 224 MB
```

The staged copy is **regenerated, not edited**: fix the plan or an upstream cut
and re-run `tools/megacut.py`, then re-stage. It is deliberately **not** in
`yt-refresh.py`'s `VIDEOS` list, so it publishes nothing until the owner adds
it — the same treatment `04-` gets, and for the same reason: its title,
description, and one real ordering question are the owner's call.

> **It overlaps three cuts already staged.** `08-` contains Kat, Natali and
> Europa, which are also standalone files (`01-`, `02-`, `zz-`), so a playlist
> in `ls` order shows all three twice. Ship the programme *or* the singles, not
> both. Recorded in `~/Videos/UPLOAD/README.md`.

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

**Owner decision: use Bungie's own upload.** Its audio was dropped at first and
then **restored** (2026-08-12) — dropping it took the *score* with it, and the
segment played silent. The fan copy's "(Without Dialogue)" label means exactly
that: it still carries the music. Bungie's own audio is now used, so the score
is official too; Ikora's voice-over comes with it, because it is part of the
cinematic as Bungie published it.
The website defaults instead to `BV3BZKbpBns` ("Into the Light (Without
Dialogue)", *Destiny Music Archive* — a fan archive), and offers Bungie's as an
"Ikora voice over" toggle. Using Bungie's gives an **official** upload for both
picture and score, so the fan-archive provenance question does not arise, and
AV1 was available for the picture (format 399).

> **The trap, and it was walked into.** "Drop the audio, we don't use it" was
> read as *mute the segment*, and the segment then played with **no score** —
> because the fan copy's *"(Without Dialogue)"* never meant silent, it meant
> *music without the voice-over*. Muting to avoid the voice-over throws away the
> music with it. If dialogue-free music is ever wanted again, that is a
> different edit, not a mute.

Accepted cost, recorded: Bungie's is **1080p30** where the fan copy was 1080p60,
so the hero is the only 30fps source in the programme.

### The audio, and how it is sourced

From the same upload's best audio rung: **Opus 127k at native 48 kHz**
(format 251) — deliberately **not** the `-drc` rung beside it, which applies
dynamic range compression the audio tenet forbids. Trimmed to the same
`2.0 -> 113.55` window as the picture and placed **bit-exact in FL/FR** with
`pan` (never `-ac`, which would quietly rescale it), the other four channels
silent — the same shape as every other master in `~/Videos`.

The decoded audio is a half-frame shorter than the picture, so it is padded with
`apad` and the **picture decides the length** — the pattern `~/Videos/PREMIERE.md`
records. Cutting to the shorter stream instead drops a frame and, inside a
concat, drifts everything after it. Kept **lossless (FLAC)** through the
intermediate, so the only lossy step is the final assembly encode.

**Only the four title cards are silent.**

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

## On screen: the six nameplates, and nothing else

**Owner decision, 2026-08-12: "just the name plaquards."** The cut carries the
six Guardian nameplates and no other chrome. The site's persistent top-of-frame
HUD is deliberately **not** burned in — that removes the default *"Meet your
Fireteam"* / *"a project to bring their stories to life"* card, the three
`#nova4ever` glitch bursts, and the closing *"Legends Sought"* card.

**The capability is built and kept, not deleted.** `tools/plate.py` renders
`kind: "status"` — the HUD's two authored lines, the glitch's red/cyan
`text-shadow` split (applied to the *type*, not the panel, because that is what
a text-shadow does) and its clip-path tear — and all of it is tested. Putting
any of it back is a manifest edit, not new code. The rows are removed from
`stories/megacut/megacut-hero-plates.json`, which records why.

One thing about the HUD is worth keeping written down, because it is invisible
until it is wrong: it is **persistent** chrome, not a per-cue pop-in. Its copy
comes from the per-cue overrides in `wolves-intro-sequence.ts` *and* the segment
default in `INTRO_DISPLAY`. Wiring only the cues renders a card that flickers
where the site holds one continuously. And its rotating dinosaur avatar badge is
never drawn: animated brand artwork on a 20-second cycle, not copy.

**`raised` survives on Natali's plate**, and it turned out **not** to be a
visual judgement at all: `.wolves-guardian-plate-raised` is an authored rule
(`bottom: auto; top: 28%`). Reproducing it lifts her card beside the Behemoth
Guardian and staggers it against Christoph's in the lower third, which is how
the site composes that shared shot.

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
- **A music bed** under the four title cards. They are silent; a bed is a
  licensing decision. The hero segment now carries Bungie's own score.
- **Chapter card placement.** The cards use the deck's own geometry, so they sit
  as a lower third on an otherwise black frame. Centring them would look more
  deliberate, but moving authored chrome is a visual judgement.
- **Audio generation loss.** Segments 2–4 are re-encoded once, AAC→AAC at 640k.
  No peak moved (below), but the lossless-master path in `~/Videos/AUDIO.md` is
  the upgrade if a delivered master is ever wanted.
- **Cortney Nickerson stays unplated and uncarded** — unresolved identity.
- **Playlist placement.** `08-` duplicates `01-`, `02-` and `zz-` (above). Ship
  the programme or the singles, and add `08-` to `yt-refresh.py`'s `VIDEOS` with
  a title and description when that is decided.

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
  | card0 | −91.0 dB (digital silence) | silent by design |
  | hero | −4.6 dB | Bungie's score, no gain applied |
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
FFPROFILE=firefox:~/.var/app/org.mozilla.firefox/config/mozilla/firefox/mha2aykb.default-release

yt-dlp --cookies-from-browser "$FFPROFILE" \
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
    --plates-dir renders/plates-megacut-hero --out renders/megacut-01-hero-mute.mp4

# the score: best audio rung, NOT the -drc one (it compresses dynamics)
yt-dlp --cookies-from-browser "$FFPROFILE" -f 251 \
  -o media/yt_into_the_light_cinematic-audio.%\(ext\)s \
  https://www.youtube.com/watch?v=BKm0TPqeOjY

# same window as the picture; stereo bit-exact in FL/FR; picture decides length
ffmpeg -i renders/megacut-01-hero-mute.mp4 \
  -i media/yt_into_the_light_cinematic-audio.webm -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a flac -shortest \
  -af "atrim=start=2.0:end=113.55,asetpts=N/SR/TB,aresample=48000,pan=5.1|FL=FL|FR=FR,apad" \
  renders/megacut-01-hero.mkv

python3 tools/plate.py render --manifest stories/megacut/megacut-cards.json \
    --out-dir renders/plates-megacut-cards
python3 tools/megacut.py stories/megacut/megacut.json
```

Use `/home/linuxbrew/.linuxbrew/bin/ffmpeg` — the system `ffmpeg` is
`ffmpeg-free`, has no H.264 decoder, and fails only once decoding starts, which
reads like a corrupt input file.

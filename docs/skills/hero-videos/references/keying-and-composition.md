# Keying and composition

Everything here was measured once, painfully, and is written down so it is
measured correctly the next time rather than guessed. The `_what` fields in
`stories/rafi-hero-qr.json` and each `.work-rafi0N/verify-notes.md` carry the
per-video record; this file carries the technique.

## Measure these, per video, before writing a graph

A number from another video is a wrong number. Derive each of these from the
source you are actually rendering:

| Measurement | How |
|---|---|
| Frame size | Have the Argo workflow probe the source and record the result in that video's `verify-notes.md`. |
| Padding rows | Have Argo sample the last rows; padding is source-specific and must be removed before anything else. |
| Paper luma range | Measure the background histogram in Argo and record the threshold per video. |
| Character bbox | The **union** over many sampled frames, with any title plate masked. RAFI_01 sampled 2022 frames. |
| Title plate box | Look for it. It may not exist. RAFI_01's was x 990→1986, y 25→295. |
| Footage length | In Argo, against the bed duration T, to compute uniform full-source retiming. |

No local `ffmpeg` or `ffprobe` command is permitted for hero work—not for
measurement, audio, probes, frame extraction, or final verification. Argo owns
those commands. Local Pillow/OpenCV may inspect already-produced PNGs, and
ordinary Python metadata work is fine.

## The keying chain, and why each step is where it is

```
crop=W:H-pad:0:0            padding off first, or it poisons the fill
drawbox ... color=white     mask the title plate BEFORE the fill
format=rgba,split[c][m]     keep the ORIGINAL pixels as [c]
  [m] lutrgb  val>231 -> 255    floodfill is exact-match; snap near-white
      floodfill x=2:y=2 ...     verified per-video seed, on the FULL frame
      colorkey=0x0000FF
      alphaextract[al]          the matte, and only the matte
[c][al]alphamerge           matte applied to the untouched pixels
crop=<bbox>                 tight crop AFTER the fill
scale=-2:1224               85% of a 1440 frame
```

Four traps, all silent:

1. **`floodfill`'s `d0`/`d1`/`d2` are planar G, B, R.** `d0=0:d1=255:d2=0` is not
   green, it is **blue**, so the matching key is `colorkey=0x0000FF`. Writing
   `0x00FF00` keys nothing and the paper stays.
2. **Seeding inside the tight crop no-ops.** The seed lands on non-white pixels,
   the fill does nothing, and ffmpeg reports success. Fill the full frame.
3. **Keying the filled copy haloes the character blue** on downscale. The fill is
   only ever a source for `alphaextract`; the alpha goes back onto `[c]`.
4. **`floodfill` is exact-match**, so near-white paper must be snapped to 255
   first or the fill stops at the first 254 pixel.

Sample every candidate seed across the timeline before accepting it. A seed that
works on frame zero may land on artwork later, so the selected full-frame seed
set is a per-video measurement, not a shared recipe.

If the source finishes with a dimmed or otherwise intentionally translucent
treatment, the aligned finished-still alpha may replace the flood-fill alpha
only after a dense check proves the artwork is complete. Preserve the original
flood-fill alpha through the drawing interval; switching sooner inserts
future-art pixels and is not a keying correction.

## Reconciling picture to bed

The bed's duration T is authoritative. Compute
`target_frames = round(T * 24)`, apply
`setpts=(target_frames/source_frames)*PTS` to the complete source, explicitly
emit 24 fps, and cap at `target_frames`. This is a uniform retime, not an
editorial change: never trim the tail, loop material, or hold the last frame to
fit the bed. Keep the measured values and effective speed factor in that
video's `verify-notes.md`.

For a composition containing several drawing animations, compute that factor
separately for every source from its own usable frame count. They may share an
authored completion frame, but never a speed value: each drawing must reach its
own finished frame by that endpoint. If a protected full-frame passage hides
the stage, pause every drawing clock and resume on the next frame rather than
discarding unseen animation.

## Composition

- Character to **85%** of frame height. Centre by default; apply only the
  record's optional per-video `x_offset` when present. Full height puts boots
  on the bottom edge.
- **Bottom-left**: the URL as text. White glyphs, the dots in `#4285f4`
  (projectbluefin.io's `--color-blue`). *Text, not a QR code.*
- **Bottom-right**: the QR card, 280px wide, 48px from the frame edges.
- The overlay is one full-frame RGBA PNG, composited with a single `overlay=0:0`
  after the character is laid over the wallpaper. All arithmetic lives in
  `scripts/build_rafi_hero_overlay.py`, where a test can pin it.
- Global static cards are a fallback. A video-specific static-card list
  overrides it; a timed-card playlist owns its stated intervals instead of
  adding a persistent card.

## QR cards

`scripts/qrcard.py` draws them, in two styles — `slate` (engraved, dark, matches
the film's plate chrome) and `dots` (blue circles on white, matches
projectbluefin.io). It **refuses to write a card that does not decode** at its
in-frame width over both wallpapers, and exits non-zero.

Three limits were found by decoding rather than by looking. All three produce a
code that looks perfect and does not scan:

| Limit | Why |
|---|---|
| **Never invert.** Dark modules on a light field. | Light-on-dark decoded in *neither* polarity at any size. Inverted codes are a coin flip across scanners. |
| **Finder corner radius ≤ 0.13** of the finder's 7-module width — and ≤ 0.05 when the modules are bevelled. | The finder carries the 1:1:3:1:1 run the locator hunts for. Rounding eats the ratio at the corners first. Rounding *data* modules is free. |
| **Modules overlap slightly** (`inset=-0.02`). | Gaps plus LANCZOS soften every edge until the sampler cannot find a boundary. Tidier at 1024px, dead at 280px. |

Argo verifies against delivered frames, never the source PNG. Local OpenCV may
decode only PNGs already produced and returned by Argo:

```python
crop = frame.crop(card_box)          # from build_rafi_hero_overlay.card_box()
cv2.QRCodeDetector().detectAndDecode(np.array(crop)[:, :, ::-1].copy())
```

Do it at both ends of the crossfade — the daylight wallpaper and the night one.

## Extracting equipment from design sheets

A design-sheet crop is evidence for transcription, not display art. Never pass
an RGB crop through `convert("RGBA")`: that only makes the entire rectangle
opaque, including its paper, labels, leader lines, and neighbouring objects.

Use an existing source-backed RGBA equipment PNG and select only the reviewed
connected alpha component or components for the named object. Preserve its
original colour and antialiasing, crop to the selected alpha bounds, and reject
inputs with no real transparency. Record the source file and component seed
points so the extraction is reproducible.

Quarter-turning a reviewed transparent object is allowed as a per-use display
transform. Apply rotation after extraction, crop to the rotated alpha bounds,
then fit and re-measure the card. Never rotate an opaque sheet crop. Tall
weapons may be turned sideways to use a shallow bottom pocket without shrinking
them into illegibility.

## Farm plumbing

One source server and one PUT receiver per active video run on the workstation
at `192.168.1.227`: **8877** serves `~/Videos/Wolves/Hero`; each receiver uses
`.work-rafi01/upload-server.py <dest> <port>`. **Give each video its own
receiver port and destination**, or one render silently overwrites another's
output. RAFI_01 uses 8878, RAFI_02 uses 8879, and Lakshmi uses 8880. The
[authorized-audio recipe](authorized-audio-on-argo.md) uses that video's
receiver too, so its records and results cannot collide with another render.

Check the Argo `ffmpeg` log within the first minute of a submission. A
filter-graph error fails immediately; finding it 25 minutes later is a wasted
render. Argo also runs all source probes, audio checks, decode checks, and
`ffprobe` validation; record the results in `verify-notes.md`.

## Placing art over somebody else's film: clear the box, not the shot

Overlaying a *finished* music video is a different job from keying a character
onto paper. There is no matte to pull; the only question is whether the
rectangle you are about to fill is empty for the **whole time it is filled**.

**A storyboard tile is not evidence.** The rejected 2026-09-05 pass chose
placements from the public YouTube L3 storyboard — 9 tiles a sheet, one frame
every 4.82 s, 320x180. A tile that samples an empty wide cannot see the
close-up that starts two seconds later inside the same window, which is how a
composite bow ended up across an actor's forehead. The window was "reviewed"
and the frame was never looked at.

The loop that replaces it, all of it on the farm:

1. **Index the whole film at 1 fps.** `fps=1,scale=384:216,tile=10x10` gives
   sheets where sheet `S` tile `(r,c)` is exactly `t = S*100 + r*10 + c`
   seconds — dense enough to see a cut, and arithmetic rather than guesswork
   to convert a tile back into a timecode.
2. **Find the shot's real boundaries** by walking single seconds outward until
   the framing changes. Blocking moves inside a shot: at 205 s a knight is at
   the right edge and by 214 s he is centre frame, so a box cleared at the head
   of a window can be occupied by its tail.
3. **Draw the candidate box on real frames across the whole window** —
   `fps=2,drawbox=...,tile` — and look at every returned frame. This is the
   step that cannot be delegated to a heuristic, and the one the rejected pass
   skipped.
4. **Fail closed.** If any sampled frame shows a person, face, hand, weapon,
   title or logo inside the box, the window carries no artwork. Do not shrink
   or slide the box to make it fit: omission is a correct output.
5. **Measure the plate before choosing type polarity**, per
   [`plates`](../../plates/references/full-frame-cards.md): `signalstats` →
   `YAVG`/`YMAX` over the box across the full window. The misty riverbed
   *looks* bright and measures **YAVG 92.9**; dark type on a light core there
   builds exactly the pasted panel the owner rejects.

`boxcheck-W5-faceclean.jpg` is kept deliberately: it is the candidate box
landing on the actor's face, the same defect as the rejected frame, caught
before a render instead of after one. The window ships clean.

**The intro is not negotiable.** `General of the Dark Army` runs a band logo
(UNLEASH THE ARCHERS), a label card (BROTHERHOOD) and a title card until the
first measured scene change at **15.057 s**. Artwork starts after it, never
on frame 0.

**Overlays are static.** A drifting `x='1648-w/2-40+40*(t/D)'` anchor is the
rejected treatment; a static `x=` with `fade=...:alpha=1` at each end is the
approved one. The only thing that animates is opacity.

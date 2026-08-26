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

## Farm plumbing

One source server and one PUT receiver per active video run on the workstation
at `192.168.1.227`: **8877** serves `~/Videos/Wolves/Hero`; each receiver uses
`.work-rafi01/upload-server.py <dest> <port>`. **Give each video its own
receiver port and destination**, or one render silently overwrites another's
output. RAFI_01 uses 8878 and RAFI_02 uses 8879.

Check the Argo `ffmpeg` log within the first minute of a submission. A
filter-graph error fails immediately; finding it 25 minutes later is a wasted
render. Argo also runs all source probes, audio checks, decode checks, and
`ffprobe` validation; record the results in `verify-notes.md`.

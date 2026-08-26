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
| Frame size | `ffprobe -select_streams v:0 -show_entries stream=width,height` |
| Padding rows | Sample the last few rows; RAFI_01's bottom 2 rows are pure black and must be cropped off before anything else. |
| Paper luma range | Histogram the background. RAFI_01's paper ran 232–255, 99% of it at 254. |
| Character bbox | The **union** over many sampled frames, with any title plate masked. RAFI_01 sampled 2022 frames. |
| Title plate box | Look for it. It may not exist. RAFI_01's was x 990→1986, y 25→295. |
| Footage length | Against the bed's duration T, to compute the hold or the trim. |

## The keying chain, and why each step is where it is

```
crop=W:H-pad:0:0            padding off first, or it poisons the fill
drawbox ... color=white     mask the title plate BEFORE the fill
format=rgba,split[c][m]     keep the ORIGINAL pixels as [c]
  [m] lutrgb  val>231 -> 255    floodfill is exact-match; snap near-white
      floodfill x=2:y=2 ...     seed in the corner, on the FULL frame
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

## Reconciling picture to bed

The bed's duration T is authoritative. If the footage is shorter, hold the last
frame with `tpad=stop_mode=clone:stop=<frames>` and cap with
`-frames:v <total>` at `-r 24`. If it is longer, trim the tail — and say so in
`verify-notes.md` rather than letting a silent truncation stand.

## Composition

- Character to **85%** of frame height, centred. Full height puts his boots on the
  bottom edge.
- **Bottom-left**: the URL as text. White glyphs, the dots in `#4285f4`
  (projectbluefin.io's `--color-blue`). *Text, not a QR code.*
- **Bottom-right**: the QR card, 280px wide, 48px from the frame edges.
- The overlay is one full-frame RGBA PNG, composited with a single `overlay=0:0`
  after the character is laid over the wallpaper. All arithmetic lives in
  `scripts/build_rafi_hero_overlay.py`, where a test can pin it.

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

Verify against the delivered file, never the source PNG:

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

Check the ffmpeg log within the first minute of a submission. A filter-graph
error fails immediately; finding it 25 minutes later is a wasted render.

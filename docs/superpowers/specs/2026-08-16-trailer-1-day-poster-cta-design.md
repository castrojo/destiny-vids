# Trailer 1 day-poster CTA

## Decision

Trailer 1's KubeCon end card becomes a **poster** over the March Bluefin
**day** wolves wallpaper. The owner selected the poster direction and explicitly
corrected the wallpaper from night to day.

The screen's hierarchy, top to bottom:

1. `KubeCon | CloudNativeCon North America` — the event headline, retaining
   the existing blue seared divider.
2. `Salt Lake City, Utah` — the venue line.
3. `wolves.projectbluefin.io` — the largest element and the call to action.
4. `#KubeCon #CloudNativeCon #7wolves` — the quiet footer.

The card holds its existing 7.820 seconds. Trailer picture length, bridge
length, end-card cue, total 1:50 runtime, and music fade are unchanged.

## Visual treatment

The end card opens on the **ungraded daylight wallpaper**, with no text. It
crossfades into a globally darkened version of the same wallpaper, and the
text arrives in two beats:

1. The event and venue fade in during the transition.
2. `wolves.projectbluefin.io` and the tags land on the returning musical swell.

The end-card audio was measured before setting those cues: its first second is
the loudest (`-15.6 dB RMS`); it breathes down through seconds 1–3 (about
`-19.6 dB RMS`); it rises again during seconds 3–4 (`-17.4 dB RMS`). The image
holds day on the opening hit, darkens through the breath, and drops the CTA on
that rising energy. Audio is not altered. The existing tight black glyph halo
supplies local contrast; no panel is drawn behind any text. The CTA is white, with its two dots in
Bluefin blue and a restrained blue glow; its **b** and **f** stay white, per
the owner's explicit correction. It is large enough to be read as the
last instruction in the trailer, not as another event detail.

The event headline remains visually smaller than the domain. It is still
legible and retains the established seared pipe. The hashtags move from a
three-line credit stack to a single compact footer, preserving their authored
order while keeping them subordinate to the CTA.

## Data and rendering

No new copy field is added. `stories/trailer-1-plates.json` continues to use
the established title-card shape:

- `title`: event headline
- `subtitle`: venue
- `body[0]`: CTA domain
- `body[1:]`: hashtags
- `variant: "poster"`: a styling switch, not copy

`cards/maintitle.html` recognizes the `poster` variant and gives the first
body row CTA styling while compacting the rest as tags. The card remains
transparent. `scripts/build_trailer1.py` changes the end-card background from a black
colour source to two bounded loops of `03-day.png`: an ungraded lead-in and a
darkened continuation. An `xfade` joins them, preserving the fixed end-card
duration. Two transparent title cards supply the timed visual beats: the event
card hides its `body[]`, and the CTA card hides its title, subtitle, and
hairline while retaining its layout seat.

## Failure handling and verification

If the day wallpaper is unavailable, the builder exits with the same explicit
missing-wallpaper error already used for the wolves bridge; it does not
silently fall back to night or black.

Tests pin the poster variant's record shape, verbatim CTA and hashtag order,
the day-wallpaper input, and the unchanged total. Rendering verification
extracts a frame from the delivered end-card window and checks the visual
hierarchy manually.

## Scope

This changes Trailer 1 only. It does not alter the prologue, act VIII, the
megacut, the font-option decision, the b-in-KubeCon trademark exception, or
the pre-existing act VI delivery conflict.

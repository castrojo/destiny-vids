# The standalone video batch

One committed manifest, `stories/standalone/<batch>.json`, builds every
"Bluefin and the X" cut. `tools/standalone.py` owns the contract
(`schema/standalone-batch.schema.json`), the source-time → output-time
mapping every later stage reads, and three commands:

```bash
python3 tools/standalone.py fetch  <manifest> <slug>
python3 tools/standalone.py build  <manifest> <slug> [--local]
python3 tools/standalone.py verify <manifest> <slug>
```

The schema is **closed at every level**, so a hand-edited field fails loudly
instead of being silently ignored.

## What a record holds

| Field | What it is |
|---|---|
| `source` | The pinned yt-dlp formats. Never "best" — a rebuild months later takes the same bitstreams. |
| `intro` | Optional. A **different** picture spliced in front, hard cut. See below. |
| `cuts` | Excisions in SOURCE time. Every later mark is mapped through them. |
| `overlays` | Existing plate kinds. Nothing new is invented for a batch. |
| `takeover` | The full-frame CTA, composited last and opaque. |
| `thumbnail` | The key-art pick, with its `why`. |
| `audio_probes` | Marks proving the delivered sound IS the source sound. |

Marks are authored in **source time** and mapped through `cuts` before
anything renders. A seat that cannot survive that mapping — inside a removed
span, past the end, colliding with an accepted plate, or under the takeover
that covers it — is **dropped and recorded**, never slid somewhere that fits.
An authored placement is content; moving it is the owner's call.

## The audio is never remastered

One picture generation and one AAC generation, in a single pass. The
delivered-peak loop re-runs the encode from the **source** at a lower static
gain — never from the file it just wrote. There is no loudnorm, compressor or
limiter anywhere in the graph, because those rewrite dynamics that a gain only
scales.

`verify` correlates delivered windows against the source at the manifest's
`audio_probes`, searching a small lag because a codec primes and a container
delays. A window from somewhere else in the film correlates with nothing at
any lag, so this cannot be fooled by a file that merely exists.

## An intro splices a different film in front

The batch's one exception to "a video has one source". Used first by
*Bluefin and the Hive III*, which opens on the evolutionary passage from act
II — Nightwish's *Endless Forms Most Beautiful* picture — and then hard-cuts
into the Witch Queen trailer.

```json
"intro": {
  "path": "/…/renders/efmb-front.mkv",
  "sha256": "49f4fcaf…",
  "in_sec": 4.0,
  "out_sec": 70.4667,
  "why": "…"
}
```

Four rules make it safe:

1. **Referenced by path and digest, never committed.** `renders/` is
   gitignored, so an intro cut from another act's render can only be pointed
   at — the same posture `scripts/build_europa_tail.py` takes for its source
   screenshot. The digest is what makes the pointer honest.
2. **A digest mismatch DROPS the intro.** It never substitutes. Splicing a
   picture the record does not describe is the "stale is never ok" fault, and
   the cut without its intro is still a complete film.
3. **Plates are composited BEFORE the join.** Their `at` values stay
   source-relative, so adding or removing an intro cannot move an authored
   seat. Only the delivered clock moves — `intro_seconds()` is the only thing
   that needs to know.
4. **The join is a hard cut.** No xfade, no acrossfade, no dip. Owner: *"I
   want to not have a slide, slide right into the trailer dramatically. Jump
   cut."* `concat` is already how this module rejoins kept ranges, so the cut
   adds no generation.

**Cut the intro from a CLEAN render where one exists.** Act II's delivered
film burns a title card, a PLATFORM WARS card and a `[ PREPARE FOR TITANFALL ]`
card onto that picture as separate overlays; `renders/efmb-front.mkv` is the
same picture with none of them. Owner: *"no titanfall, this is going to be
strictly onboard."* Cutting from the clean render excludes all three **by
construction** rather than by trimming around them, and avoids a second
generation of somebody else's plates.

**Land the out-point in silence.** Act II's front runs its music to ≈70.407
and is silent to 76.600, so an out at 70.4667 joins without cutting a phrase
in half. Check the audio at both ends of a join before choosing the frame.

### Graph shape

The intro is appended as the **last** ffmpeg input, so the source stays input
0 and every still keeps the index the graph computed for it. The overlay chain
therefore finishes on `[mainv]` rather than `[outv]`, because the concat owns
`[outv]`/`[outa]` — a label cannot be both a filter's input and its output.
Both legs are `aformat`-normalised before the join, since an intro arriving as
24-bit PCM and a source decoded from Opus do not share a sample format.

## Verification

```bash
python3 tools/standalone.py verify <manifest> <slug>
python3 -m pytest -q tests/test_standalone.py
```

`verify` checks duration against `expected_duration` (intro included), the
delivered peak, the takeover frame against the approved CTA picture, and every
audio probe. **Then look at a frame inside a plate window** — ffmpeg exiting 0
proves the encode ran, not that a card is on screen or seated on the picture.

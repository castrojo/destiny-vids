# Indexing a video

## When to Use

- Adding a new Bungie video to the index
- Writing or reviewing tagger output (`tags/<video_id>.json`)
- Debugging a suspicious beat count, or segments that all derive `clean = false`

## When NOT to Use

- Assembling a cut from an existing index → [`editing.md`](editing/SKILL.md)
- Deciding *who* a shot depicts → [`casting.md`](casting/SKILL.md)

## Core Process

Indexing is **two passes over the same detection**, because tagging happens
out-of-band and beat index is positional:

```bash
yt-dlp -S "vcodec:h264,res:1080" --merge-output-format mp4 \
  -o "media/<video_id>.%(ext)s" <url>
python3 tools/ingest.py <url> --id <video_id>

# pass 1 — beats + one keyframe each, plus keyframes/<video_id>/beats.json
python3 tools/annotate.py index --video media/<video_id>.mp4 \
    --video-record videos/<video_id>.json

# scaffold the tag file: every beat present, every value null
python3 tools/worksheet.py generate <video_id>

# ...look at each keyframe and fill tags/<video_id>.json...
python3 tools/worksheet.py check tags/<video_id>.json   # what is left to fill

# pass 2 — replay tags into segments/
python3 tools/annotate.py index --video media/<video_id>.mp4 \
    --video-record videos/<video_id>.json --tags tags/<video_id>.json
```

Stills land in `keyframes/<video_id>/`, derived from the video record rather
than chosen at the command line. Choosing was the bug: `--keyframes-dir
keyframes/` put one video's `000.jpg` at the root of the tree, where the next
video's `000.jpg` overwrote it and the beats manifest with it — silently, since
stills are gitignored and nothing downstream reads a filename.

`scripts/make_video.sh` runs both passes and stops in between, at tagging.

Both passes must use identical detector settings. A tag file is only valid
against the shot list its own detection pass produced, which is why the beat
manifest is written next to the stills.

Keyframes come from the **middle** of each beat, not the first frame: a cut's
opening frames are frequently mid-dissolve or mid-flash, which is exactly the
material a tagger reads wrong.

## Tagging rules

- **Start from the worksheet, not an empty file.** `tools/worksheet.py
  generate` writes the skeleton: every beat index as a string key, the
  keyframe and timecodes to judge from (in a `_worksheet` block — scaffolding
  that replay strips), and `null` for every value. Null is not a default; it
  means "nobody has looked". The file's shape is generated so the tagger's
  time goes to the judgement that cannot be automated.
- **`overlays` is mandatory on every beat.** It is the input to the `clean`
  gate, which derives `false` when untagged. Use `[]` for a clean shot. The
  worksheet leaves it `null` — never `[]` — because an inherited "clean" is
  how a HUD gets into a finished cut. `tools/worksheet.py check` is the
  done-ness signal; `make_video.sh` gates stage 5 on it.
- **Every beat must be tagged, and an unreviewed beat is tagged honestly.**
  `annotate.py` refuses a gap outright (`no tags for beat N`), so a partial pass
  cannot silently index half a video. When a long source is being reviewed
  incrementally, give the unreviewed beats a record with **no `overlays`**: they
  derive `clean = false` and stay out of every cut until somebody looks at them.
  That is the gate working, not a shortcut around it — "I have not seen this
  frame" is not evidence that the frame is clean. Reviewing is additive and
  needs no re-detection, so the beat indices stay valid.
- **Only `TAGGER_FIELDS` may appear in a tag.** A bookkeeping field like
  `review_status` is rejected by `assemble_segment`, and the video record's
  schema is closed too. Reasoning about *why* a beat was tagged a certain way
  belongs in the commit message, not in the data.
- **Do not tag the source's own letterbox.** Bungie cinematics are 2.39:1 inside
  a 16:9 frame; tagging `letterbox` would reject the entire video.
- **Never return a derived field.** `clean`, `footage_tier`, `traversal_hero`
  and `casting` are computed at assembly; `assemble_segment` raises on anything
  outside `TAGGER_FIELDS`.
- **Name a character only when visible in that frame** — see
  [`casting.md`](casting/SKILL.md).
- Batch a long video across parallel taggers, but hand every batch the same enum
  list and the same reference entry, or the tags will not be comparable.

Expect a few rejects per video: ratings, title and date cards carry
`burned_text` and correctly derive `clean = false`. That is the gate working —
1/50 on the Curse of Osiris cinematic, 9/69 on the TFS launch trailer.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The shot is obviously clean, I'll skip `overlays`." | Skipping it derives `clean = false` and removes the shot from every cut. It is one field; set it. |
| "The detector found 1 scene, so it's one long take." | Check the codec. AV1 + OpenCV silently yields one scene. |
| "I'll just fix the derived field in the segment JSON." | It is recomputed on the next assembly. Fix the tag or the vocab. |
| "I can re-use these tags after re-running detection." | Beat index is positional. New detection settings mean a new tag file. |

## Red Flags

- **Exactly 1 beat for a cut-heavy video.** The codec is wrong, not the
  detector: OpenCV cannot decode AV1 and silently returns one scene. Re-fetch
  with `-S "vcodec:h264"` (`docs/rendering.md`).
- **Every "shot" the same length.** `scenedetect` is not installed and detection
  fell back to fixed 3-second windows. The result *looks* like a plausible shot
  list and is not one, so the damage only shows up later as cuts that land
  mid-shot. `detect_beats` now warns on stderr, but check the install first:

  ```bash
  python3 -c "import scenedetect, cv2; print(scenedetect.__version__)"
  python3 -m pip install --user scenedetect opencv-python-headless
  ```
- **A flood of sub-second beats.** Destiny super activations, explosions and
  muzzle flash read as cuts to a frame-difference detector. `--min-shot-sec`
  (default 0.5) merges them; raise it rather than hand-deleting segments.
- Editing a segment file to change a derived field. Fix the tag or the vocab and
  re-assemble.
- Hand-correcting a value in a committed tag or segment. It does not fail now;
  it fails at the next rebuild, on a value like `label_source: "human"` that is
  not in the enum. `tests/test_index_integrity.py` catches it.
- Committing anything under `media/`, `keyframes/` or `renders/`.

## Verification

```bash
# beat count and clean split for a video
python3 - <<'PY'
import json, glob
segs = [json.load(open(p)) for p in glob.glob('segments/*<video_id>*.json')]
print(len(segs), 'segments,', sum(s['clean'] for s in segs), 'clean')
PY

# the source really is H.264
ffprobe -v error -select_streams v -show_entries stream=codec_name \
  -of csv=p=0 media/<video_id>.mp4

python3 -m pytest -q tests/test_annotate.py
```

Field definitions and the axis reference are in `docs/taxonomy.md`; the cost
model, and why boundaries are computed before any model runs, is
`docs/pipeline.md`.

# Europa Jupiter Native Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkboxes for tracking.

**Goal:** Replace Europa's generated Jupiter transition with the native 30 fps Juno video while preserving the act's exact clock and delivering a reviewable Act VII render.

**Architecture:** The committed Europa record will split the existing intro around the 195-frame Jupiter slot and insert the project-local native Juno input. `scripts/build_europa.py` already compiles ordered picture segments through one concat graph, so no new transition or special renderer is needed; only the record and its explanatory docstring change. The render will use the existing Act VII farm path for the master, then perform the local stream-copy peak gate and delivered derivation.

**Tech Stack:** Python 3, JSON, pytest, FFmpeg, `tools/farm.py`, `tools/peaks.py`.

## Global Constraints

- The Jupiter slot remains exactly 195 frames / 6.5 seconds.
- The native input is `nimbatus-review/jupiter/cand/PIA22906_nasa.mp4`, 1920x1080 at 30 fps.
- No blend, xfade, fade, still, grade, crop, or `jupiter_styled.mp4` input is used for the Jupiter segment.
- The concat order and every downstream Europa timestamp remain unchanged.
- The megacut is not rebuilt.
- Footage and renders remain outside git; only metadata, tools, tests, and docs are committed.

---

### Task 1: Pin the native Jupiter slot in tests

**Files:**
- Modify: `tests/test_europa_act.py` near `test_walk_up_keeps_only_the_solo_wide`

**Interfaces:**
- Consumes: `load()`, `build_europa.picture_graph()`, and the committed `picture` record.
- Produces: regression coverage for the native input, exact slot boundaries, and the absence of a picture transition.

- [x] **Step 1: Write the failing test**

Add:

```python
def test_jupiter_slot_uses_native_video_without_transition():
    doc = load()
    inputs = doc["picture"]["inputs"]
    assert inputs["jupiter"] == (
        "nimbatus-review/jupiter/cand/PIA22906_nasa.mp4")

    segments = doc["picture"]["segments"]
    before, native, after = segments[:3]
    assert before == {"label": "intro-before-jupiter", "from": "intro",
                      "frames": [0, 497]}
    assert native == {
        "label": "jupiter-native",
        "from": "jupiter",
        "window": [0.0, 6.5],
        "fps": 30,
        "scale": True,
    }
    assert after == {"label": "intro-after-jupiter", "from": "intro",
                     "frames": [692, 1725]}

    picture_parts, _ = build_europa.picture_graph(doc)
    picture_graph = ";".join(picture_parts)
    assert "blend=" not in picture_graph
    assert "xfade=" not in picture_graph
    assert "jupiter_styled.mp4" not in " ".join(inputs.values())
```

- [x] **Step 2: Run the focused test to verify it fails**

Run:

```bash
python3 -m pytest -q tests/test_europa_act.py::test_jupiter_slot_uses_native_video_without_transition
```

Expected: FAIL because the current record has no `jupiter` input and its first
segment is the unsplit `cold-open`.

- [x] **Step 3: Commit the test**

```bash
git add tests/test_europa_act.py
git commit -m "test(europa): pin native Jupiter slot" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: Replace the recorded Jupiter transition

**Files:**
- Modify: `stories/07-europa-plates.json` in `picture.inputs`, `picture.segments`, `_note`, and `_sources_note`

**Interfaces:**
- Consumes: The native input and the exact intro frame boundaries from Task 1.
- Produces: A committed Act VII picture graph with a three-part Jupiter area and unchanged `master_sec`, `content_sec`, `delivered_sec`, and `delivered_frames`.

- [x] **Step 1: Replace the picture record**

Change `picture.inputs` to add:

```json
"jupiter": "nimbatus-review/jupiter/cand/PIA22906_nasa.mp4"
```

Replace the first `cold-open` segment with these three segments, in order:

```json
{
  "label": "intro-before-jupiter",
  "from": "intro",
  "frames": [0, 497]
},
{
  "label": "jupiter-native",
  "from": "jupiter",
  "window": [0.0, 6.5],
  "fps": 30,
  "scale": true
},
{
  "label": "intro-after-jupiter",
  "from": "intro",
  "frames": [692, 1725]
}
```

Keep the existing `speeder`, `approach`, `walk-up`, `wrap`, and `cover`
segments byte-for-byte unchanged. Update the picture note to say that the
195-frame slot is native Juno video with no transition or generated still, and
update the sources note with the NASA/JPL/Caltech/SwRI/MSSS/Kevin M. Gill native
video source.

- [x] **Step 2: Regenerate and run the focused tests**

Run:

```bash
python3 -m pytest -q tests/test_europa_act.py
python3 scripts/generate_skill_index.py --check
```

Expected: all Europa tests pass and the generated skill catalog remains fresh.

- [x] **Step 3: Commit the record**

```bash
git add stories/07-europa-plates.json tests/test_europa_act.py
git commit -m "fix(europa): play native Jupiter video" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 3: Keep the builder documentation aligned

**Files:**
- Modify: `scripts/build_europa.py` module docstring and segment-count wording

**Interfaces:**
- Consumes: The expanded record from Task 2.
- Produces: Documentation that accurately describes the eight-segment picture concat and the fact that the native Jupiter source is just another ordered segment.

- [x] **Step 1: Update the stale count and transition wording**

Replace the module docstring's “six-segment concat” wording with “eight-segment
concat” and describe the Jupiter input as a native 30 fps segment. Do not add
special-case code: `_segment_chain()` and `picture_graph()` already handle the
record's `window`, `fps`, `scale`, and concat ordering.

- [x] **Step 2: Run the Europa tests**

```bash
python3 -m pytest -q tests/test_europa_act.py
```

Expected: PASS.

### Task 4: Record the durable editing rule

**Files:**
- Modify: `docs/skills/editing/SKILL.md` in the common-rationalizations or red-flags section
- Regenerate: `docs/skills/index.json` and `docs/skills/index.md` if the front matter changes

**Interfaces:**
- Consumes: The verified Jupiter replacement decision from Tasks 1–3.
- Produces: A timeless editing rule against retaining a synthetic transition when a native source fills the exact frame slot.

- [x] **Step 1: Add the rule**

Add this rationalization/rebuttal:

```markdown
| "The replacement is already built, so keep its dissolve." | If the native source fills the exact slot, remove the obsolete transition and play the native frames; do not preserve a vestigial handoff just because it already renders. |
```

- [x] **Step 2: Regenerate and validate the catalog**

```bash
python3 scripts/generate_skill_index.py --write
python3 scripts/generate_skill_index.py --check
```

Expected: the catalog is generated from current front matter and the check
passes.

### Task 5: Render and verify the Europa chapter

**Files:**
- Create (ignored): `renders/europa-jupiter-native-master.mp4`
- Create (ignored): `renders/europa-jupiter-native.mp4`
- Create (ignored): `renders/europa-jupiter-native-plates/`

**Interfaces:**
- Consumes: The committed Act VII record, `/var/home/jorge/Videos/wolves-directors-cut`, and the reachable farm cluster.
- Produces: A reviewable 95.4-second Act VII file with the native Jupiter motion.

- [x] **Step 1: Render the Act VII chapter**

```bash
DESTINY_FFMPEG=/home/linuxbrew/.linuxbrew/bin/ffmpeg \
python3 scripts/build_europa.py \
  --project /var/home/jorge/Videos/wolves-directors-cut \
  --plates-dir renders/europa-jupiter-native-plates \
  --master-out renders/europa-jupiter-native-master.mp4 \
  --out renders/europa-jupiter-native.mp4 \
  --farm
```

The master encode runs on the farm; the peak trim and stream-copy delivered
derivation remain local as the builder documents.

- [x] **Step 2: Verify duration and frame count**

```bash
ffprobe -v error -count_frames \
  -show_entries format=duration:stream=nb_read_frames \
  -of default=noprint_wrappers=1 \
  renders/europa-jupiter-native.mp4
```

Expected: duration `95.4` seconds and `2862` video frames.

- [x] **Step 3: Extract the native Jupiter review frame**

```bash
mkdir -p /tmp/europa-jupiter-review
ffmpeg -hide_banner -loglevel error -y \
  -ss 18.5 -i renders/europa-jupiter-native.mp4 \
  -frames:v 1 /tmp/europa-jupiter-review/jupiter-native.png
```

View the PNG and confirm it shows native moving-cloud detail with no dissolve
handoff, synthetic still, or re-lighting.

- [x] **Step 4: Run the complete verification suite**

```bash
python3 -m pytest -q
python3 tools/corpus.py --check
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
pre-commit run --files \
  docs/skills/editing/SKILL.md docs/skills/index.json docs/skills/index.md \
  scripts/build_europa.py stories/07-europa-plates.json \
  tests/test_europa_act.py
```

Expected: all checks pass. Do not run or modify the megacut.

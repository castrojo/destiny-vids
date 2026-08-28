# Bluefin Standalone Video Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deliver four reproducible Bluefin standalone videos and matching Jungle-family thumbnails from one committed batch manifest.

**Architecture:** A schema-validated manifest records source formats, source-time edits, overlays, CTA takeovers, metadata, thumbnails, and output paths. One generic Python builder maps source time through excisions, renders existing plate kinds, performs one farm-first FFmpeg picture/audio encode, and verifies the result; the Linux Foundation CTA remains a reusable skill plus an approved static asset rather than a code-specific feature.

**Tech Stack:** Python 3, Pillow, FFmpeg/ffprobe, yt-dlp, JSON Schema, pytest, `tools.plate`, `tools.farm`, and `tools.peaks`.

## Global Constraints

- The repository stores metadata, timestamps, code, and non-footage artwork; it never commits source footage, extracted frames, or rendered videos.
- Every user-supplied timestamp is a source-video mark. Earlier excisions are mapped to output time by the builder.
- All three CTA takeovers use the same approved 1920x1080 PNG and preserve source audio unchanged through EOF.
- The CTA is a local skill and asset recipe. The builder exposes only a generic full-frame picture takeover.
- `Jorge Castro` plates are name-only. Do not add a label, class, or title.
- Final Trial uses a plain-blue Jorge/Cayde plate plus a separate promoted Bazzite `FIRETEAM // EXPERT` / `John Bazzite` status HUD.
- The Bazzite HUD is seated in the picture's **top-right** (`position: "top-right"`), as the approved player-card direction fixes it. `position: "status"` is the top-LEFT seat and is the wrong corner here.
- The Bazzite HUD uses the official tile crest and purple chrome; it does not borrow gold leader rank or a laurel.
- Store `Stay _sharp_!` verbatim and support exactly one balanced underscore emphasis span; do not add a Markdown parser.
- Source audio is fetched from an explicit non-DRC format ID at its native sample rate and receives no EQ, compression, limiting, or loudness normalization.
- Picture encoding is remote by default through `tools.farm.run_encode`; local fallback is memory-capped and states its reason.
- Delivered true peak must not exceed `-0.9 dBTP`.
- Thumbnail output is 1920x1080, below 2 MB, and readable at 336x189.
- The existing dirty checkout at `/var/home/jorge/src/destiny-vids` is not touched; implementation stays in `/var/home/jorge/src/destiny-vids-bluefin-video-batch`.

---

## File Map

| Path | Responsibility |
|---|---|
| `schema/standalone-batch.schema.json` | Closed contract for the batch record. |
| `stories/standalone/bluefin-video-batch.json` | The four videos' authored source-time instructions and delivery metadata. |
| `assets/cta/linux-foundation-training-forest.png` | Approved non-footage CTA artwork, SHA-256 pinned below. |
| `docs/skills/training-cta/SKILL.md` | Reusable CTA placement procedure and verification rules. |
| `docs/SKILL.md` | Routes full-frame LF training CTA work to the new skill. |
| `docs/skills/index.json`, `docs/skills/index.md` | Generated skill catalog outputs. |
| `tools/standalone.py` | Manifest loading, source fetch, source/output time mapping, one-pass encode, and verification CLI. |
| `tools/thumbnail.py` | Source-frame extraction and Jungle-family thumbnail rendering. |
| `tools/plate.py` | Bazzite status-HUD chrome and one-span chat emphasis. |
| `tests/test_standalone.py` | Manifest, timeline, command, farm, CTA, and verification tests. |
| `tests/test_thumbnail.py` | Thumbnail layout, dimensions, and byte-cap tests. |
| `tests/test_plate.py` | Status-HUD and chat-emphasis regressions. |
| `tests/test_index_integrity.py` | Validates the committed batch manifest against its schema. |

---

### Task 1: Define the Manifest Contract and Source-Time Mapping

**Files:**
- Create: `schema/standalone-batch.schema.json`
- Create: `tools/standalone.py`
- Create: `tests/test_standalone.py`
- Modify: `tests/test_index_integrity.py`

**Interfaces:**
- Consumes: JSON files and `jsonschema.Draft202012Validator`.
- Produces:
  - `load_manifest(path: Path) -> dict`
  - `entry_by_slug(manifest: dict, slug: str) -> dict`
  - `source_to_output(source_sec: float, cuts: list[dict]) -> float`
  - `kept_ranges(duration_sec: float, cuts: list[dict]) -> list[tuple[float, float]]`

- [ ] **Step 1: Write failing timeline and schema tests**

```python
# tests/test_standalone.py
import json
from pathlib import Path

import pytest

from tools import standalone


def test_source_time_maps_through_the_blueberries_excision():
    cuts = [{"start_sec": 46.0, "end_sec": 54.0}]
    assert standalone.source_to_output(45.0, cuts) == 45.0
    assert standalone.source_to_output(97.0, cuts) == 89.0
    with pytest.raises(ValueError, match="inside removed source range"):
        standalone.source_to_output(50.0, cuts)


def test_kept_ranges_remove_exactly_the_authored_span():
    assert standalone.kept_ranges(
        120.0, [{"start_sec": 46.0, "end_sec": 54.0}]
    ) == [(0.0, 46.0), (54.0, 120.0)]


def test_manifest_rejects_drc_audio_format(tmp_path):
    path = tmp_path / "batch.json"
    path.write_text(json.dumps({
        "version": 1,
        "cta_asset": "assets/cta/linux-foundation-training-forest.png",
        "videos": [{
            "slug": "bad",
            "source": {
                "url": "https://www.youtube.com/watch?v=example",
                "youtube_id": "example",
                "video_format_id": "137",
                "audio_format_id": "251-drc",
                "usage_class": "third_party_copyrighted",
                "source_rights_note": "Non-commercial fan creation.",
            },
            "title": "Bad",
            "output": "~/Videos/Bad.mp4",
            "thumbnail_output": "~/Videos/Bad-thumbnail.jpg",
            "thumbnail": {"source_at": 1.0},
            "audio_probes": [{"source_at": 2.0, "duration": 1.0}],
            "overlays": [],
        }],
    }))
    with pytest.raises(ValueError, match="DRC"):
        standalone.load_manifest(path)
```

- [ ] **Step 2: Run the focused tests and confirm the missing module failure**

Run:

```bash
python3 -m pytest -q tests/test_standalone.py
```

Expected: collection fails because `tools.standalone` does not exist.

- [ ] **Step 3: Add the closed JSON Schema**

Create a Draft 2020-12 schema with `additionalProperties: false` at the root,
video, source, cut, takeover, thumbnail, and overlay levels. Require these
video fields:

```json
{
  "required": [
    "slug",
    "source",
    "title",
    "output",
    "thumbnail_output",
    "thumbnail",
    "audio_probes",
    "overlays"
  ],
  "properties": {
    "slug": {"type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"},
    "source": {"$ref": "#/$defs/source"},
    "title": {"type": "string", "minLength": 1},
    "description": {"type": "string"},
    "output": {"type": "string", "minLength": 1},
    "thumbnail_output": {"type": "string", "minLength": 1},
    "cuts": {
      "type": "array",
      "items": {"$ref": "#/$defs/cut"}
    },
    "overlays": {
      "type": "array",
      "items": {"$ref": "#/$defs/overlay"}
    },
    "takeover": {"$ref": "#/$defs/takeover"},
    "thumbnail": {"$ref": "#/$defs/thumbnail"},
    "audio_probes": {
      "type": "array",
      "minItems": 1,
      "items": {"$ref": "#/$defs/audioProbe"}
    }
  }
}
```

The source definition requires `url`, `youtube_id`, `video_format_id`,
`audio_format_id`, `usage_class`, and `source_rights_note`. The overlay definition permits the existing plate fields used by this batch:
`id`, `kind`, `source_at`, `dur`, `position`, `copy_source`, `why`, `name`,
`detail`, `label`, `title`, `text`, `speaker`, `variant`, and `avatar`.

- [ ] **Step 4: Implement the loader and timeline helpers**

```python
# tools/standalone.py
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "schema" / "standalone-batch.schema.json"


def load_manifest(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ValueError("\n".join(
            f"{'/'.join(map(str, error.path))}: {error.message}"
            for error in errors
        ))
    for video in data["videos"]:
        audio_id = video["source"]["audio_format_id"]
        if audio_id.endswith("-drc"):
            raise ValueError(f"{video['slug']}: DRC audio format is forbidden")
    return data


def entry_by_slug(manifest, slug):
    matches = [video for video in manifest["videos"] if video["slug"] == slug]
    if len(matches) != 1:
        raise KeyError(f"expected one video named {slug!r}, found {len(matches)}")
    return matches[0]


def _sorted_cuts(cuts):
    ordered = sorted(cuts or [], key=lambda cut: cut["start_sec"])
    previous_end = 0.0
    for cut in ordered:
        start, end = cut["start_sec"], cut["end_sec"]
        if start < previous_end or end <= start:
            raise ValueError(f"invalid or overlapping cut {start}-{end}")
        previous_end = end
    return ordered


def source_to_output(source_sec, cuts):
    removed = 0.0
    for cut in _sorted_cuts(cuts):
        start, end = cut["start_sec"], cut["end_sec"]
        if start <= source_sec < end:
            raise ValueError(
                f"{source_sec:.3f} is inside removed source range {start}-{end}"
            )
        if end <= source_sec:
            removed += end - start
    return source_sec - removed


def kept_ranges(duration_sec, cuts):
    cursor = 0.0
    kept = []
    for cut in _sorted_cuts(cuts):
        if cursor < cut["start_sec"]:
            kept.append((cursor, cut["start_sec"]))
        cursor = cut["end_sec"]
    if cursor < duration_sec:
        kept.append((cursor, duration_sec))
    return kept
```

- [ ] **Step 5: Register the committed manifest with index-integrity tests**

Add:

```python
STANDALONE_BATCH_PATHS = sorted(
    glob.glob(str(REPO_ROOT / "stories" / "standalone" / "*.json"))
)


@pytest.mark.parametrize(
    "path", STANDALONE_BATCH_PATHS, ids=lambda path: Path(path).stem
)
def test_committed_standalone_batch_matches_the_schema(path):
    errors = sorted(
        _validator("standalone-batch.schema.json").iter_errors(_load(path)),
        key=lambda error: list(error.path),
    )
    assert not errors, "\n".join(
        f"{'/'.join(str(part) for part in error.path)}: {error.message}"
        for error in errors
    )


@pytest.mark.parametrize(
    "path", STANDALONE_BATCH_PATHS, ids=lambda path: Path(path).stem
)
def test_committed_standalone_chat_holds_are_readable(path):
    from tools.readtime import required_hold

    manifest = _load(path)
    short = []
    for video in manifest["videos"]:
        for overlay in video["overlays"]:
            text = overlay.get("text")
            if not text:
                continue
            visible = text.replace("_", "")
            need = required_hold(visible)
            if overlay["dur"] + 1e-9 < need:
                short.append(
                    f"{video['slug']}/{overlay['id']}: "
                    f"{overlay['dur']:.2f}s < {need:.2f}s"
                )
    assert not short, "\n".join(short)
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
python3 -m pytest -q tests/test_standalone.py tests/test_index_integrity.py
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit**

```bash
git add schema/standalone-batch.schema.json tools/standalone.py \
  tests/test_standalone.py tests/test_index_integrity.py
git commit -m "feat: define standalone video batch contract" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Add the Reusable Training CTA Skill and Approved Asset

**Files:**
- Create: `assets/cta/linux-foundation-training-forest.png`
- Create: `docs/skills/training-cta/SKILL.md`
- Modify: `docs/SKILL.md`
- Modify: `docs/skills/index.json`
- Modify: `docs/skills/index.md`
- Modify: `tests/test_standalone.py`

**Interfaces:**
- Consumes: the approved workspace image
  `/var/home/jorge/Videos/Wolves/work/excision-nameplates/training-cta-1080.png`.
- Produces:
  - `assets/cta/linux-foundation-training-forest.png`
  - Skill procedure for generic `takeover.source_at -> EOF` picture replacement.

- [ ] **Step 1: Write the failing asset regression**

```python
def test_training_cta_is_the_approved_1080p_asset():
    import hashlib
    from PIL import Image

    path = standalone.REPO_ROOT / "assets/cta/linux-foundation-training-forest.png"
    assert Image.open(path).size == (1920, 1080)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "46d05d65973f64c4811a02f64673db547cb2d403c58caa9fdbddc7b0da5883c5"
    )
```

- [ ] **Step 2: Run the test and confirm the asset is absent**

Run:

```bash
python3 -m pytest -q tests/test_standalone.py::test_training_cta_is_the_approved_1080p_asset
```

Expected: failure because the committed asset does not exist.

- [ ] **Step 3: Copy the approved non-footage artwork**

Run:

```bash
install -Dm644 \
  /var/home/jorge/Videos/Wolves/work/excision-nameplates/training-cta-1080.png \
  assets/cta/linux-foundation-training-forest.png
sha256sum assets/cta/linux-foundation-training-forest.png
```

Expected digest:

```text
46d05d65973f64c4811a02f64673db547cb2d403c58caa9fdbddc7b0da5883c5
```

- [ ] **Step 4: Write the CTA skill**

Use this frontmatter and contract:

```markdown
---
name: training-cta
version: "1.0"
last_updated: "2026-08-28"
id: training-cta
one_line_purpose: Replace picture with the approved LF training CTA while preserving audio.
entry_point: docs/skills/training-cta/SKILL.md
category: media-production
status: active
dependencies: []
tags:
  - cta
  - linux-foundation
  - training
  - video
description: >-
  Use when a Bluefin video should replace its remaining picture with the
  approved Linux Foundation training card while the source audio continues.
metadata:
  type: procedure
  context7-sources:
    - /websites/ffmpeg_documentation
---
```

The body must contain:

1. **When to Use** — full-frame LF training CTA through EOF.
2. **When NOT to Use** — generic title cards, upload descriptions, or changing
   CTA copy.
3. **Core Process** — use the committed asset, convert source time through
   excisions, overlay at `0:0`, preserve source audio, bound the looped still
   with `shortest=1`.
4. **Common Rationalizations** — no per-video CTA copy, no fade by default, no
   audio replacement.
5. **Red Flags** — different asset bytes, muted/restarted audio, unbounded still.
6. **Verification** — SHA-256, frame extraction after takeover, audio
   correlation before/after the mark.

- [ ] **Step 5: Route and regenerate**

Add this row to `docs/SKILL.md`:

```markdown
| Replace the rest of a video with the reusable LF training CTA | [`training-cta`](skills/training-cta/SKILL.md) |
```

Run:

```bash
python3 scripts/generate_skill_index.py --write
```

- [ ] **Step 6: Run focused checks**

Run:

```bash
python3 -m pytest -q \
  tests/test_standalone.py::test_training_cta_is_the_approved_1080p_asset \
  tests/test_skill_catalog.py
python3 scripts/generate_skill_index.py --check
```

Expected: all checks pass.

- [ ] **Step 7: Commit**

```bash
git add assets/cta/linux-foundation-training-forest.png \
  docs/skills/training-cta/SKILL.md docs/SKILL.md \
  docs/skills/index.json docs/skills/index.md tests/test_standalone.py
git commit -m "feat: add reusable Linux Foundation training CTA" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: Add Bazzite Expert HUD Chrome and One-Span Chat Emphasis

**Files:**
- Modify: `tools/plate.py:250-267`
- Modify: `tools/plate.py:1027-1145`
- Modify: `tools/plate.py:1176-1228`
- Modify: `tests/test_plate.py:981-1060`
- Modify: `tests/test_plate.py:1737-1805`

**Interfaces:**
- Consumes: existing `VARIANTS["bazzite"]`, `_bazzite_tile`, `_font`, status
  fields, and chat text.
- Produces:
  - `chat_runs(text: str) -> list[tuple[str, str]]`
  - `variant: "bazzite"` support for `kind: "status"`
  - Bazzite tile crest inside the promoted status HUD.

- [ ] **Step 1: Write failing chat emphasis tests**

```python
def test_chat_supports_one_balanced_underscore_emphasis_span():
    assert plate.chat_runs("Stay _sharp_!") == [
        ("Stay ", "bold"),
        ("sharp", "italic"),
        ("!", "bold"),
    ]


def test_unbalanced_chat_underscore_stays_literal():
    assert plate.chat_runs("Stay _sharp!") == [("Stay _sharp!", "bold")]
```

- [ ] **Step 2: Write failing Bazzite status tests**

```python
def test_bazzite_status_uses_purple_chrome_and_the_official_tile():
    plain = plate.render_plate(_status())
    expert = plate.render_plate(_status(
        detail="FIRETEAM // EXPERT",
        label="John Bazzite",
        variant="bazzite",
    ))
    assert expert.width > plain.width
    assert expert.tobytes() != plain.tobytes()
    assert any(
        b > r + 20 and b > g + 5 and a > 150
        for r, g, b, a in expert.getdata()
    )


def test_bazzite_status_remains_compatible_with_a_guardian_plate():
    plate.load_manifest_entries([
        _status(
            id="player",
            at=4.0,
            dur=100.0,
            detail="FIRETEAM // EXPERT",
            label="John Bazzite",
            variant="bazzite",
        ),
        {
            "id": "cayde",
            "at": 8.0,
            "dur": 4.0,
            "position": "left",
            "name": "Jorge Castro",
        },
    ])
```

- [ ] **Step 3: Run the tests and confirm the new behavior is absent**

Run:

```bash
python3 -m pytest -q \
  tests/test_plate.py::test_chat_supports_one_balanced_underscore_emphasis_span \
  tests/test_plate.py::test_unbalanced_chat_underscore_stays_literal \
  tests/test_plate.py::test_bazzite_status_uses_purple_chrome_and_the_official_tile \
  tests/test_plate.py::test_bazzite_status_remains_compatible_with_a_guardian_plate
```

Expected: failures for missing `chat_runs` and unchanged status chrome.

- [ ] **Step 4: Implement the minimal emphasis parser**

```python
def chat_runs(text):
    first = text.find("_")
    if first < 0:
        return [(text, "bold")]
    second = text.find("_", first + 1)
    if second < 0 or text.find("_", second + 1) >= 0:
        return [(text, "bold")]
    runs = [
        (text[:first], "bold"),
        (text[first + 1:second], "italic"),
        (text[second + 1:], "bold"),
    ]
    return [(part, weight) for part, weight in runs if part]
```

Update `_render_chat` so width calculation and drawing iterate these runs,
using `_font("bold", size)` and `_font("italic", size)`. Keep the existing
Kubernetes censor-token path intact; split each run around the censor token
before measuring and drawing.

- [ ] **Step 5: Implement Bazzite status chrome**

Add:

```python
STATUS_MARK = 48
STATUS_MARK_GAP = 16
```

Inside `_render_status`:

```python
variant_name = spec.get("variant", "default")
chrome = VARIANTS[variant_name]
show_bazzite = variant_name == "bazzite"
mark_room = STATUS_MARK + STATUS_MARK_GAP if show_bazzite else 0
box_w = int(round(
    inner + STATUS_PAD_LEFT + STATUS_PAD_RIGHT + STATUS_RULE + mark_room
))
```

Use `chrome["border"]`, `chrome["accent"]`, and `chrome["label"]` instead of
the fixed blue status colors when a variant is present. Draw
`_bazzite_tile(STATUS_MARK, chrome["accent"], None)` at the right side of the
panel. Keep the existing blue constants as the default path so every shipped
status card remains byte-stable.

- [ ] **Step 6: Run the complete plate test file**

Run:

```bash
python3 -m pytest -q tests/test_plate.py
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add tools/plate.py tests/test_plate.py
git commit -m "feat: promote the Bazzite player HUD" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: Implement the Jungle-Family Thumbnail Renderer

**Files:**
- Create: `tools/thumbnail.py`
- Create: `tests/test_thumbnail.py`

**Interfaces:**
- Consumes: a downloaded source video, a source timestamp, a display title,
  Pillow, FFmpeg, and `tools.credits._font`.
- Produces:
  - `extract_source_frame(ffmpeg: list[str], source: Path, source_at: float, out: Path) -> Path`
  - `split_bluefin_title(title: str) -> tuple[str, str]`
  - `render_jungle_thumbnail(source: Image.Image, title: str) -> Image.Image`
  - `save_jungle_thumbnail(source: Path, title: str, out: Path) -> Path`

- [ ] **Step 1: Write failing layout tests**

```python
from PIL import Image

from tools import thumbnail


def test_bluefin_prefix_becomes_the_eyebrow():
    assert thumbnail.split_bluefin_title("Bluefin: Your Final Trial") == (
        "BLUEFIN",
        "YOUR FINAL TRIAL",
    )
    assert thumbnail.split_bluefin_title("Bluefin and Saint 14") == (
        "BLUEFIN",
        "AND SAINT 14",
    )


def test_jungle_thumbnail_is_youtube_sized(tmp_path):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (480, 360), "#6b4423").save(source)
    out = tmp_path / "thumb.jpg"
    thumbnail.save_jungle_thumbnail(
        source, "Bluefin: Care for a Drink?", out
    )
    assert Image.open(out).size == (1920, 1080)
    assert out.stat().st_size < 2_000_000
```

- [ ] **Step 2: Run tests and confirm the module is missing**

Run:

```bash
python3 -m pytest -q tests/test_thumbnail.py
```

Expected: collection fails because `tools.thumbnail` does not exist.

- [ ] **Step 3: Implement deterministic source-frame extraction**

```python
import subprocess


def extract_source_frame(ffmpeg, source, source_at, out, runner=subprocess.run):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    runner([
        *ffmpeg,
        "-v", "error",
        "-y",
        "-ss", f"{source_at:.3f}",
        "-i", str(Path(source).resolve()),
        "-frames:v", "1",
        str(out.resolve()),
    ], check=True)
    return out
```

- [ ] **Step 4: Implement the approved Jungle layout**

Use `ImageOps.fit(source.convert("RGB"), (1920, 1080), Image.Resampling.LANCZOS)`.
Detect and crop uniform black letterbox bars before fitting. Draw:

- `BLUEFIN` centered at the top in `credits._font("black", 76)`;
- a 360px Bluefin-blue rule directly below it;
- the remaining title centered in `credits._font("black", 116)`;
- white fill, 8px near-black stroke, and a restrained black shadow.

Fit the title to at most two lines by reducing from 116px to a 72px floor.
Keep the title block above the frame's vertical midpoint so it follows the
Jungle reference and does not cover the central subject.

Save with:

```python
image.save(
    out,
    "JPEG",
    quality=95,
    subsampling=0,
    optimize=True,
    progressive=True,
)
```

If the file exceeds 2 MB, retry quality values `92`, `89`, and `86`, stopping
at the first result under the cap. Raise if none meets the cap.

- [ ] **Step 5: Add a small-size readability artifact test**

```python
def test_listing_size_keeps_visible_title_ink(tmp_path):
    source = Image.new("RGB", (1280, 720), "#a66a3f")
    full = thumbnail.render_jungle_thumbnail(
        source, "Bluefin and the Blueberries"
    )
    listing = full.resize((336, 189), Image.Resampling.LANCZOS)
    top = listing.crop((0, 0, 336, 95))
    assert max(pixel[0] for pixel in top.getdata()) > 240
```

- [ ] **Step 6: Run thumbnail tests**

Run:

```bash
python3 -m pytest -q tests/test_thumbnail.py
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add tools/thumbnail.py tests/test_thumbnail.py
git commit -m "feat: render Jungle-family thumbnails" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: Implement the Generic Farm-First Standalone Builder

**Files:**
- Modify: `tools/standalone.py`
- Modify: `tests/test_standalone.py`

**Interfaces:**
- Consumes:
  - Task 1 manifest functions.
  - Task 2 CTA asset.
  - Task 3 `plate.render_all`.
  - Task 4 thumbnail functions.
  - `conform.video_filter_chain`, `conform.video_encode_args`,
    `farm.run_encode`, `peaks.correct_delivered_peak`, and
    `render.find_ffmpeg`.
- Produces:
  - `fetch_command(video: dict, out: Path) -> list[str]`
  - `mapped_overlays(video: dict, source_duration: float) -> tuple[list[dict], list[dict]]`
  - `filtergraph(video: dict, duration_sec: float, overlays: list[dict]) -> str`
  - `encode_video(video: dict, source: Path, cta_asset: Path, work_dir: Path, local: bool) -> Path`
  - `build(manifest_path: Path, slug: str, local: bool = False) -> Path`
  - `verify(manifest_path: Path, slug: str) -> list[str]`
  - CLI: `fetch`, `build`, and `verify`.

- [ ] **Step 1: Write failing explicit-format fetch tests**

```python
def test_fetch_uses_explicit_non_drc_format_ids(tmp_path):
    video = {
        "slug": "trial",
        "source": {
            "url": "https://www.youtube.com/watch?v=_OvgGtnN_Ts",
            "video_format_id": "137",
            "audio_format_id": "251",
        },
    }
    command = standalone.fetch_command(video, tmp_path / "trial.mkv")
    assert command[command.index("-f") + 1] == "137+251"
    assert command[command.index("--merge-output-format") + 1] == "mkv"
    # yt-dlp takes the extractor argument as ONE token, so the pinned player
    # client is asserted inside it rather than as a bare word.
    assert command[command.index("--extractor-args") + 1] == \
        "youtube:player_client=visionos"
```

- [ ] **Step 2: Write failing filtergraph mapping tests**

```python
def test_blueberries_filtergraph_cuts_video_and_audio_before_takeover():
    video = {
        "cuts": [{"start_sec": 46.0, "end_sec": 54.0}],
        "takeover": {"source_at": 97.0},
        "overlays": [],
    }
    graph = standalone.filtergraph(video, duration_sec=120.0, overlays=[])
    assert "trim=start=0.0:end=46.0" in graph
    assert "atrim=start=54.0:end=120.0" in graph
    assert "concat=n=2:v=1:a=1" in graph
    assert "gte(t,89.0)" in graph


def test_a_video_without_a_takeover_uses_input_one_for_its_first_plate():
    video = {"cuts": [], "overlays": []}
    graph = standalone.filtergraph(
        video,
        duration_sec=120.0,
        overlays=[{"id": "player", "at": 4.0, "dur": 30.0}],
    )
    assert "[basev][1:v]overlay=0:0" in graph


def test_overlay_source_marks_are_mapped_before_render():
    video = {
        "cuts": [{"start_sec": 46.0, "end_sec": 54.0}],
        "overlays": [{
            "id": "jorge",
            "source_at": 60.0,
            "dur": 4.0,
            "position": "left",
            "name": "Jorge Castro",
        }],
    }
    overlays, unresolved = standalone.mapped_overlays(video, 120.0)
    assert overlays[0]["at"] == 52.0
    assert unresolved == []


def test_overlay_inside_a_removed_span_degrades_to_unresolved():
    video = {
        "cuts": [{"start_sec": 46.0, "end_sec": 54.0}],
        "overlays": [{
            "id": "bad-seat",
            "source_at": 50.0,
            "dur": 4.0,
            "position": "left",
            "name": "Jorge Castro",
        }],
    }
    overlays, unresolved = standalone.mapped_overlays(video, 120.0)
    assert overlays == []
    assert unresolved[0]["id"] == "bad-seat"
```

- [ ] **Step 3: Write failing farm and peak-loop tests**

```python
def test_build_routes_the_encode_through_run_encode(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        standalone.farm,
        "run_encode",
        lambda argv, **kwargs: calls.append((argv, kwargs)) or "cluster",
    )
    monkeypatch.setattr(standalone, "_source_duration", lambda *args: 120.0)
    monkeypatch.setattr(standalone, "_ensure_source", lambda *args: tmp_path / "src.mkv")
    monkeypatch.setattr(standalone.plate, "render_all", lambda *args, **kwargs: [])
    monkeypatch.setattr(standalone.thumbnail, "extract_source_frame", lambda *args, **kwargs: tmp_path / "src.png")
    monkeypatch.setattr(standalone.thumbnail, "save_jungle_thumbnail", lambda *args: tmp_path / "thumb.jpg")
    monkeypatch.setattr(standalone.peaks, "correct_delivered_peak", lambda *args, **kwargs: 1.0)
    monkeypatch.setattr(Path, "exists", lambda self: True)

    standalone.encode_video(
        {
            "slug": "x",
            "cuts": [],
            "overlays": [],
            "output": str(tmp_path / "x.mp4"),
        },
        tmp_path / "src.mkv",
        tmp_path / "cta.png",
        tmp_path,
        local=False,
    )
    assert len(calls) == 1
    assert calls[0][1]["local"] is False
```

Use narrower monkeypatches if patching `Path.exists` affects unrelated code.
The assertion is that no bare local video encode path bypasses `run_encode`.

- [ ] **Step 4: Run the focused tests and confirm the functions are absent**

Run:

```bash
python3 -m pytest -q tests/test_standalone.py
```

Expected: failures naming the missing builder functions.

- [ ] **Step 5: Implement explicit source fetching**

```python
# Measured on yt-dlp 2026.08.19: `android_vr` warns that its https formats
# require a GVS PO token and answers with one muxed 360p/44.1 kHz rung, so a
# manifest pinning 137+251 cannot fetch. `visionos` still lists the full
# video-only AVC and non-DRC 48 kHz Opus ladder with no token.
PLAYER_CLIENT = "visionos"


def fetch_command(video, out):
    source = video["source"]
    return [
        "yt-dlp",
        "--extractor-args", f"youtube:player_client={PLAYER_CLIENT}",
        "--no-playlist",
        "--no-part",
        "-f", f"{source['video_format_id']}+{source['audio_format_id']}",
        "--merge-output-format", "mkv",
        "-o", str(Path(out).resolve()),
        source["url"],
    ]
```

`_ensure_source` writes to `media/standalone/{slug}.mkv`, skips a non-empty
existing source, and otherwise runs the command with `subprocess.run(...,
check=True)`.

- [ ] **Step 6: Implement mapped overlays and degradation records**

```python
def mapped_overlays(video, source_duration):
    cuts = video.get("cuts", [])
    accepted = []
    unresolved = []
    for overlay in video.get("overlays", []):
        item = dict(overlay)
        source_at = item.pop("source_at")
        try:
            item["at"] = source_to_output(source_at, cuts)
            if source_at >= source_duration:
                raise ValueError(
                    f"source mark {source_at:.3f} exceeds {source_duration:.3f}"
                )
            plate.load_manifest_entries([*accepted, item])
        except ValueError as error:
            unresolved.append({"id": item["id"], "reason": str(error)})
            continue
        accepted.append(item)
    return accepted, unresolved
```

Write the unresolved list to
`renders/standalone/<video-slug>-unresolved.json`, even when it is empty.
Render accepted entries once with `plate.render_all(accepted, plates_dir)`.
The returned PNGs are already full-frame and positioned, so every FFmpeg
overlay is `x=0:y=0`.

- [ ] **Step 7: Implement the one-pass filtergraph**

For each kept source range, emit paired video/audio legs:

```text
[0:v]trim=start=0.0:end=46.0,scale=1920:1080:flags=lanczos,setsar=1,fps=60000/1001,format=yuv420p,setpts=PTS-STARTPTS[v0]
[0:a]atrim=start=0.0:end=46.0,asetpts=PTS-STARTPTS[a0]
```

Join multiple legs with:

```text
[v0][a0][v1][a1]concat=n=2:v=1:a=1[basev][basea]
```

For an uncut source, use
`[0:v]{conform.video_filter_chain()}[basev]` and
`[0:a]asetpts=PTS-STARTPTS[basea]`.

Overlay each rendered plate input in order:

```text
[basev][2:v]overlay=0:0:enable='between(t,33.0,35.4)'[v1]
```

Overlay the CTA input last:

```text
[vN][1:v]overlay=0:0:enable='gte(t,89.0)':shortest=1[outv]
```

Only add the CTA input when `takeover` exists. The first plate input index is
`1 + int(bool(video.get("takeover")))`, so Final Trial's first plate is input
`1`, while CTA videos reserve input `1` for the CTA and begin plates at `2`.
Add every still input with `-loop 1 -framerate 60000/1001`, and apply
`shortest=1` to each overlay so the finite source video controls output length.

Map `[outv]` and `[basea]`. Encode H.264 picture and AAC audio once from the
explicit H.264+Opus source:

```python
[
    *conform.video_encode_args(),
    "-c:a", "aac",
    "-b:a", "320k",
    "-movflags", "+faststart",
]
```

Apply static audio gain with `volume=<gain>` inside the audio leg only when the
peak loop requests a value below `1.0`.

- [ ] **Step 8: Run farm-first with measured peak correction**

Call:

```python
farm.run_encode(
    command,
    inputs=[source, cta_asset, *plate_paths],
    out=out,
    local=local,
    expected_duration=expected_duration,
    label=f"Standalone {video['slug']}",
)
```

Then call `peaks.correct_delivered_peak` with
`margin_db=peaks.DELIVERED_BAND_MARGIN_DB`. Its rerun callback rebuilds from the
same source and overlays at the lower static audio gain, never from the prior
lossy output.

- [ ] **Step 9: Implement thumbnail delivery**

After the video encode:

```python
source_thumb = work_dir / f"{video['slug']}-source-thumbnail.png"
thumbnail.extract_source_frame(
    ffmpeg,
    source,
    video["thumbnail"]["source_at"],
    source_thumb,
)
thumbnail.save_jungle_thumbnail(
    source_thumb,
    video["title"],
    Path(video["thumbnail_output"]).expanduser(),
)
```

- [ ] **Step 10: Implement verification**

`verify` must:

1. compare output duration with source duration minus cut durations, tolerance
   `0.08s`;
2. verify video is H.264 and audio is present with ffprobe;
3. extract one second of mono 8 kHz PCM from source and output at every
   manifest `audio_probe.source_at`, map the output mark through cuts, and
   require normalized correlation `>= 0.97`;
4. extract a frame `0.5s` after takeover and compare it to the CTA asset after
   JPEG-free RGB scaling, requiring mean absolute channel error `<= 3.0`;
5. write review PNGs at every overlay midpoint and `0.5s` after takeover under
   `renders/standalone/review/<video-slug>/`;
6. verify thumbnail dimensions and byte cap.

Use stdlib `array` and `math` for correlation:

```python
def correlation(left, right):
    count = min(len(left), len(right))
    left, right = left[:count], right[:count]
    lm = sum(left) / count
    rm = sum(right) / count
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    left_energy = sum((a - lm) ** 2 for a in left)
    right_energy = sum((b - rm) ** 2 for b in right)
    return numerator / math.sqrt(left_energy * right_energy)
```

Raise explicit errors for zero-energy probe windows so silence cannot produce a
false success.

- [ ] **Step 11: Add CLI commands**

```text
python3 tools/standalone.py fetch stories/standalone/bluefin-video-batch.json SLUG
python3 tools/standalone.py build stories/standalone/bluefin-video-batch.json SLUG [--local]
python3 tools/standalone.py verify stories/standalone/bluefin-video-batch.json SLUG
```

- [ ] **Step 12: Run focused tests**

Run:

```bash
python3 -m pytest -q tests/test_standalone.py tests/test_thumbnail.py tests/test_plate.py
```

Expected: all selected tests pass.

- [ ] **Step 13: Commit**

```bash
git add tools/standalone.py tests/test_standalone.py
git commit -m "feat: build standalone videos from one manifest" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 6: Inspect the Four Sources and Commit the Authored Batch Manifest

**Files:**
- Create: `stories/standalone/bluefin-video-batch.json`

**Interfaces:**
- Consumes: Task 1 schema, Task 5 fetch CLI, the four user-supplied YouTube
  URLs, and the approved copy in the design spec.
- Produces: one complete, schema-valid batch manifest with explicit format IDs,
  evidenced plate source marks, and non-silent audio probes.

- [ ] **Step 1: Inspect each format ladder before fetching**

Run:

```bash
for id in ZJLAJVmggt0 rQ4i0AT8c-M _OvgGtnN_Ts iVZ-G88rOYg; do
  yt-dlp --extractor-args "youtube:player_client=visionos" \
    --no-playlist -F "https://www.youtube.com/watch?v=$id"
done
```

`visionos` is the client `tools/standalone.py` pins, and it is the one measured
to still list the full ladder on yt-dlp 2026.08.19. `android_vr` warns that its
https formats need a GVS PO token and answers with a single muxed
360p/44.1 kHz rung, which is the sourcing failure the audio tenet forbids —
check the ladder with `-F` before trusting any client.

For each source, record:

- the best AVC/H.264 video-only format at or below the source's native
  resolution;
- audio format `251` when present;
- another explicit 48 kHz Opus format only when `251` is absent;
- never a format ID ending in `-drc`.

- [ ] **Step 2: Write the fixed manifest fields**

The root values are:

```json
{
  "version": 1,
  "cta_asset": "assets/cta/linux-foundation-training-forest.png",
  "videos": []
}
```

Use these entries and delivery paths:

| Slug | Title | Output | Thumbnail |
|---|---|---|---|
| `bluefin-and-the-blueberries` | `Bluefin and the Blueberries` | `~/Videos/Bluefin and the Blueberries.mp4` | `~/Videos/Bluefin and the Blueberries-thumbnail.jpg` |
| `bluefin-care-for-a-drink` | `Bluefin: Care for a Drink?` | `~/Videos/Bluefin - Care for a Drink.mp4` | `~/Videos/Bluefin - Care for a Drink-thumbnail.jpg` |
| `bluefin-your-final-trial` | `Bluefin: Your Final Trial` | `~/Videos/Bluefin - Your Final Trial.mp4` | `~/Videos/Bluefin - Your Final Trial-thumbnail.jpg` |
| `bluefin-and-saint-14` | `Bluefin and Saint 14` | `~/Videos/Bluefin and Saint 14.mp4` | `~/Videos/Bluefin and Saint 14-thumbnail.jpg` |

Every source uses:

```json
{
  "usage_class": "third_party_copyrighted",
  "source_rights_note": "Third-party upload of Bungie in-engine footage. Used only in a non-commercial fan creation under Bungie's fan-content forbearance. The repository stores metadata and timestamps, never the footage."
}
```

- [ ] **Step 3: Fetch sources**

After the explicit format IDs are in the manifest, run:

```bash
for slug in \
  bluefin-and-the-blueberries \
  bluefin-care-for-a-drink \
  bluefin-your-final-trial \
  bluefin-and-saint-14
do
  python3 tools/standalone.py fetch \
    stories/standalone/bluefin-video-batch.json "$slug"
done
```

- [ ] **Step 4: Find evidenced Cayde plate windows**

For Blueberries, Drink, and Final Trial, generate contact sheets from the
downloaded source:

```bash
for slug in \
  bluefin-and-the-blueberries \
  bluefin-care-for-a-drink \
  bluefin-your-final-trial
do
  mkdir -p "renders/standalone/$slug-contact"
  ffmpeg -v error -y -i "media/standalone/$slug.mkv" \
    -vf "fps=1/2,scale=320:-1,tile=5x5" \
    "renders/standalone/$slug-contact/sheet-%03d.jpg"
done
```

Open the sheets and then extract full frames around the first unambiguous Cayde
appearance. Record the selected source second and a `why` string naming what is
visibly in frame. Use a `4.0s` hold unless the shot ends earlier; a plate may
continue across a cut, but its anchor frame must show Cayde.

The plate object is:

```json
{
  "id": "jorge-cayde",
  "dur": 4.0,
  "position": "left",
  "copy_source": "owner_supplied",
  "why": "Cayde-6 is unambiguously visible on the selected source frame",
  "name": "Jorge Castro"
}
```

Add the measured `source_at` number from the inspected frame.

Use the same contact sheets to choose each thumbnail's `source_at`: the subject
must remain clear under the approved top title band, and no burned-in publisher
title may sit under the Bluefin lockup. Record that numeric source mark in the
entry's required `thumbnail` object.

- [ ] **Step 5: Author the fixed Blueberries instructions**

Use:

```json
{
  "cuts": [{"start_sec": 46.0, "end_sec": 54.0}],
  "takeover": {"source_at": 97.0},
  "audio_probes": [
    {"source_at": 40.0, "duration": 1.0},
    {"source_at": 100.0, "duration": 1.0}
  ]
}
```

The builder maps the takeover to output `89.0`.

- [ ] **Step 6: Author the fixed Drink instructions**

Use:

```json
{
  "takeover": {"source_at": 56.0},
  "audio_probes": [
    {"source_at": 45.0, "duration": 1.0},
    {"source_at": 58.0, "duration": 1.0}
  ]
}
```

- [ ] **Step 7: Author the fixed Final Trial instructions**

Add the evidenced Cayde/Jorge plate, then:

```json
[
  {
    "id": "john-bazzite-expert",
    "kind": "status",
    "position": "top-right",
    "detail": "FIRETEAM // EXPERT",
    "label": "John Bazzite",
    "variant": "bazzite",
    "copy_source": "owner_supplied",
    "why": "The Excision player identity returns at expert tier"
  },
  {
    "id": "trial-quip-1",
    "kind": "chat",
    "source_at": 33.0,
    "dur": 2.4,
    "position": "center",
    "speaker": "castrojo",
    "avatar": "renders/avatars/castrojo.png",
    "text": "You knew this would happen",
    "copy_source": "owner_supplied",
    "why": "Owner-authored Final Trial exchange"
  },
  {
    "id": "trial-quip-2",
    "kind": "chat",
    "source_at": 35.6,
    "dur": 2.2,
    "position": "center",
    "speaker": "castrojo",
    "avatar": "renders/avatars/castrojo.png",
    "text": "Stay _sharp_!",
    "copy_source": "owner_supplied",
    "why": "Owner-authored Final Trial exchange"
  },
  {
    "id": "trial-nix-1",
    "kind": "chat",
    "source_at": 94.0,
    "dur": 2.2,
    "position": "center",
    "speaker": "castrojo",
    "avatar": "renders/avatars/castrojo.png",
    "text": "I don't hate nix users",
    "copy_source": "owner_supplied",
    "why": "Owner-authored Final Trial exchange"
  },
  {
    "id": "trial-nix-2",
    "kind": "chat",
    "source_at": 96.4,
    "dur": 3.2,
    "position": "center",
    "speaker": "castrojo",
    "avatar": "renders/avatars/castrojo.png",
    "text": "That's your character to play, not mine",
    "copy_source": "owner_supplied",
    "why": "Owner-authored Final Trial exchange"
  },
  {
    "id": "trial-nix-3",
    "kind": "chat",
    "source_at": 99.8,
    "dur": 4.8,
    "position": "center",
    "speaker": "castrojo",
    "avatar": "renders/avatars/castrojo.png",
    "text": "Because I did just beat you, but that's a 50/50 call every time",
    "copy_source": "owner_supplied",
    "why": "Owner-authored Final Trial exchange"
  },
  {
    "id": "trial-nix-4",
    "kind": "chat",
    "source_at": 104.8,
    "dur": 3.2,
    "position": "center",
    "speaker": "castrojo",
    "avatar": "renders/avatars/castrojo.png",
    "text": "You need to carry me through Duality",
    "copy_source": "owner_supplied",
    "why": "Owner-authored Final Trial exchange"
  }
]
```

Set the status HUD's measured `source_at` to the first full gameplay frame and
its `dur` to the last gameplay frame minus that mark. Add audio probes in two
non-silent gameplay regions.

Populate the existing avatar cache before rendering:

```bash
python3 tools/avatars.py --from-actions
test -s renders/avatars/castrojo.png
```

- [ ] **Step 8: Author the fixed Saint-14 instructions**

Use:

```json
{
  "description": "The Standard for others to Follow",
  "overlays": [{
    "id": "activating-cncf-community",
    "kind": "title",
    "source_at": 106.0,
    "dur": 5.0,
    "position": "top-right",
    "title": "Activating CNCF Community",
    "copy_source": "owner_supplied",
    "why": "Owner-authored top-right activation plate"
  }],
  "takeover": {"source_at": 123.0},
  "audio_probes": [
    {"source_at": 115.0, "duration": 1.0},
    {"source_at": 125.0, "duration": 1.0}
  ]
}
```

- [ ] **Step 9: Validate readability and the manifest**

Run:

```bash
python3 -m pytest -q \
  tests/test_standalone.py \
  tests/test_index_integrity.py
```

If the readable-hold integrity test reports one of the new pills, increase that
pill's `dur` and shift only the later pills within the same owner-authored
sequence. Do not move the `0:33` or `1:34` sequence anchors and do not change
picture timing.

- [ ] **Step 10: Commit**

```bash
git add stories/standalone/bluefin-video-batch.json
git commit -m "feat: author Bluefin standalone video batch" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 7: Render and Verify the Four Videos with the Fleet

**Files:**
- Media outputs only; do not commit them.

**Interfaces:**
- Consumes: the committed manifest and completed shared tooling.
- Produces:
  - `~/Videos/Bluefin and the Blueberries.mp4`
  - `~/Videos/Bluefin and the Blueberries-thumbnail.jpg`
  - `~/Videos/Bluefin - Care for a Drink.mp4`
  - `~/Videos/Bluefin - Care for a Drink-thumbnail.jpg`
  - `~/Videos/Bluefin - Your Final Trial.mp4`
  - `~/Videos/Bluefin - Your Final Trial-thumbnail.jpg`
  - `~/Videos/Bluefin and Saint 14.mp4`
  - `~/Videos/Bluefin and Saint 14-thumbnail.jpg`

- [ ] **Step 1: Confirm no authored work is stranded before rendering**

Run:

```bash
for worktree in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
  head=$(git -C "$worktree" rev-parse HEAD)
  [ "$(git branch -r --contains "$head" 2>/dev/null | wc -l)" -eq 0 ] &&
    echo "UNPUSHED: $worktree ($head)"
done
```

Push the implementation branch before starting the renders so the manifest and
code that create the videos are not stranded.

- [ ] **Step 2: Dispatch one render worker per slug in parallel**

Give each worker one exact command pair:

```bash
# Worker 1
python3 tools/standalone.py build stories/standalone/bluefin-video-batch.json bluefin-and-the-blueberries
python3 tools/standalone.py verify stories/standalone/bluefin-video-batch.json bluefin-and-the-blueberries

# Worker 2
python3 tools/standalone.py build stories/standalone/bluefin-video-batch.json bluefin-care-for-a-drink
python3 tools/standalone.py verify stories/standalone/bluefin-video-batch.json bluefin-care-for-a-drink

# Worker 3
python3 tools/standalone.py build stories/standalone/bluefin-video-batch.json bluefin-your-final-trial
python3 tools/standalone.py verify stories/standalone/bluefin-video-batch.json bluefin-your-final-trial

# Worker 4
python3 tools/standalone.py build stories/standalone/bluefin-video-batch.json bluefin-and-saint-14
python3 tools/standalone.py verify stories/standalone/bluefin-video-batch.json bluefin-and-saint-14
```

Workers own distinct outputs and must not edit the repository. If a worker
finds a manifest problem, it reports the exact slug and evidence to the parent;
the parent makes one serialized manifest correction and reruns that slug.

- [ ] **Step 3: Inspect requested visual windows**

`verify` has already written exact midpoint frames from the manifest. List them:

```bash
find renders/standalone/review -type f -name '*.png' -print | sort
```

Inspect at least:

- each Jorge plate;
- Final Trial's Bazzite HUD;
- one Final Trial pill from each dialogue sequence;
- Saint-14's top-right plate;
- every CTA takeover;
- all four thumbnails at full size and 336x189.

- [ ] **Step 4: Confirm delivery paths**

Run:

```bash
stat \
  "$HOME/Videos/Bluefin and the Blueberries.mp4" \
  "$HOME/Videos/Bluefin - Care for a Drink.mp4" \
  "$HOME/Videos/Bluefin - Your Final Trial.mp4" \
  "$HOME/Videos/Bluefin and Saint 14.mp4"
```

Expected: all four files exist, are non-empty, and have current timestamps.

---

### Task 8: Run Repository Gates, Open the PR, and Enable Auto-Merge

**Files:**
- No new files unless a source-backed production lesson requires updating the
  nearest existing skill in the same branch.

**Interfaces:**
- Consumes: all implementation commits and delivered artifacts.
- Produces: a clean branch, pushed PR, and enabled auto-merge.

- [ ] **Step 1: Run the required repository sequence**

Run:

```bash
python3 -m pytest -q
python3 tools/corpus.py --check
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
pre-commit run --all-files
```

Expected: all commands exit zero. If a generated catalog is stale, regenerate
it with its documented `--write` command and commit the generated output.

- [ ] **Step 2: Confirm no media is staged or untracked in git**

Run:

```bash
git status --short
git ls-files media keyframes renders '*.mp4'
```

Expected: only intended source/docs/test changes are tracked; no footage or
rendered video is listed.

- [ ] **Step 3: Inspect the full branch diff**

Run:

```bash
git --no-pager diff --check origin/main...HEAD
git --no-pager diff --stat origin/main...HEAD
git --no-pager log --oneline origin/main..HEAD
```

- [ ] **Step 4: Push the branch**

Run:

```bash
git push -u origin feat/bluefin-video-batch
```

- [ ] **Step 5: Read the PR template and create the PR**

Run:

```bash
find .github -iname 'pull_request_template.md' \
  -o -path '.github/PULL_REQUEST_TEMPLATE/*'
```

Use the discovered template, then create the PR with the GitHub MCP
`create_pull_request` tool. The PR body must name:

- the four delivered video paths;
- the reusable CTA skill and asset;
- the generic manifest-driven builder;
- the Bazzite expert HUD and chat emphasis;
- the exact repository gate results.

- [ ] **Step 6: Enable auto-merge**

Run:

```bash
gh pr merge --auto --squash
```

If the branch is behind current `main`, update it through the repository's
normal PR branch-update path, rerun the full required sequence, push, and leave
auto-merge enabled.

- [ ] **Step 7: Final clean-worktree proof**

Run:

```bash
git status --short
```

Expected: no output.

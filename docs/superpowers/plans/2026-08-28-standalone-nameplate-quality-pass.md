# Standalone Nameplate Quality Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `Bluefin and the Blueberries` and `Bluefin: Your Final Trial` with the approved nameplates, corrected timing, and a clean Blueberries ending.

**Architecture:** Keep `stories/standalone/bluefin-video-batch.json` as the only authored timeline record. Extend its existing overlay schema only for the already-supported `trustee` chrome flag, pin both corrected overlay records in offline tests, then rebuild each video from its pinned source through the farm-first standalone builder.

**Tech Stack:** Python 3, pytest, JSON Schema 2020-12, Pillow-backed `tools/plate.py`, FFmpeg through `tools/farm.py`, yt-dlp pinned source formats.

## Global Constraints

- Finished series nameplates use their established authored identity; never replace them with placeholders, compact approximations, or invented fields.
- Castrojo's plate is exactly `TRUSTEE // GUARDIAN` / `Harbinger Titan` / `Jorge Castro` / `Upender of Antipatterns | The First Disciple` with `trustee: true`.
- John Bazzite's normal plate carries only `name: John Bazzite` and `variant: bazzite`; no label, class, or title is authored.
- Blueberries seats Castrojo at source/output `31.2` for `2.2` seconds and starts the CTA at source `93.5`.
- Final Trial seats John Bazzite at source `16.2` for `2.2` seconds and removes the persistent status HUD.
- Existing dialogue, audio probes, cuts, thumbnails, and the Final Trial Jorge/Cayde plate stay unchanged.
- Build from source through the farm-first path; do not patch delivered H.264 files.
- Never commit footage, extracted frames, thumbnails, or rendered videos.

---

### Task 1: Pin the corrected authored records

**Files:**
- Modify: `tests/test_standalone.py:808-913`
- Modify: `schema/standalone-batch.schema.json:210-285`
- Modify: `stories/standalone/bluefin-video-batch.json:16-185`

**Interfaces:**
- Consumes: `standalone.mapped_overlays(video: dict, duration: float) -> tuple[list[dict], list[dict]]`
- Produces: schema-valid literal overlay records consumed unchanged by `tools.standalone.encode_video`

- [ ] **Step 1: Replace the retired HUD test with the landing plate test**

Replace `test_the_bazzite_hud_is_seated_in_the_pictures_top_right` with:

```python
def test_final_trial_uses_one_normal_bazzite_plate_on_the_landing():
    video = _batch_video("bluefin-your-final-trial")
    john = _batch_overlay("bluefin-your-final-trial", "john-bazzite-landing")

    assert john == {
        "id": "john-bazzite-landing",
        "kind": "guardian",
        "source_at": 16.2,
        "dur": 2.2,
        "position": "left",
        "name": "John Bazzite",
        "variant": "bazzite",
        "copy_source": "owner_supplied",
        "why": (
            "The player lands at source 15.9-16.0, settles into the crouch "
            "at 16.2, rises through 16.4 and stands by 17.0. The wide "
            "plateau shot holds until the hard cut at 21.3, so the complete "
            "2.2s lower-third stays on the landed player."
        ),
    }
    assert not any(overlay["kind"] == "status"
                   for overlay in video["overlays"])
```

- [ ] **Step 2: Replace the old Cayde shot constant and assertions**

Replace `BLUEBERRIES_CAYDE_SHOT` and the two Cayde seat tests with:

```python
BLUEBERRIES_CAYDE_SHOT = (30.797, 37.771)
CASTROJO_PLATE = {
    "label": "TRUSTEE // GUARDIAN",
    "class": "Harbinger Titan",
    "name": "Jorge Castro",
    "title": "Upender of Antipatterns | The First Disciple",
    "trustee": True,
}


def test_the_blueberries_jorge_plate_is_the_established_identity():
    plate = _batch_overlay("bluefin-and-the-blueberries", "jorge-cayde")
    assert {key: plate[key] for key in CASTROJO_PLATE} == CASTROJO_PLATE
    assert (plate["source_at"], plate["dur"]) == (31.2, 2.2)
    assert _batch_video("bluefin-and-the-blueberries")["takeover"] == {
        "source_at": 93.5,
    }


def test_the_blueberries_plate_envelope_stays_on_evidenced_cayde():
    from tools import plate as plate_module

    seat = _batch_overlay("bluefin-and-the-blueberries", "jorge-cayde")
    visible_from = seat["source_at"] - plate_module.LEAD_IN
    visible_to = seat["source_at"] + seat["dur"] + plate_module.TAIL_OUT

    assert visible_from >= BLUEBERRIES_CAYDE_SHOT[0] - 1e-6
    assert visible_to <= BLUEBERRIES_CAYDE_SHOT[1] + 1e-6
```

- [ ] **Step 3: Run the focused tests and confirm they fail against the old manifest**

Run:

```bash
python3 -m pytest -q \
  tests/test_standalone.py::test_final_trial_uses_one_normal_bazzite_plate_on_the_landing \
  tests/test_standalone.py::test_the_blueberries_jorge_plate_is_the_established_identity \
  tests/test_standalone.py::test_the_blueberries_plate_envelope_stays_on_evidenced_cayde
```

Expected: all three fail because the committed manifest still has the
persistent status HUD, the late compact Castrojo pill, and the `97.0` CTA.

- [ ] **Step 4: Allow the existing trustee chrome flag in the standalone schema**

Add this property beside `variant` in the overlay definition:

```json
"trustee": {
  "type": "boolean",
  "description": "Use the established burnished-silver trustee chrome for an authored Guardian identity."
},
```

Do not add new copy fields or relax `additionalProperties: false`.

- [ ] **Step 5: Update the Blueberries manifest entry**

Replace `jorge-cayde` with the complete literal record:

```json
{
  "id": "jorge-cayde",
  "kind": "guardian",
  "source_at": 31.2,
  "dur": 2.2,
  "position": "left",
  "copy_source": "owner_supplied",
  "why": "The battlefield advance from source 30.797-37.771 keeps Cayde visibly in frame throughout. The plate lead-in starts at 30.8 on the cut, the 2.2s hold runs 31.2-33.4, and the tail clears at 33.65, so the complete established identity stays on evidenced Cayde picture near the first 30 seconds.",
  "label": "TRUSTEE // GUARDIAN",
  "class": "Harbinger Titan",
  "name": "Jorge Castro",
  "title": "Upender of Antipatterns | The First Disciple",
  "trustee": true
}
```

Change its takeover to:

```json
"takeover": {
  "source_at": 93.5
}
```

Update the cut note so it says the takeover maps to output `85.5`, not `89.0`.

- [ ] **Step 6: Replace the Final Trial persistent HUD with the landing plate**

Remove the complete `john-bazzite-expert` object and add:

```json
{
  "id": "john-bazzite-landing",
  "kind": "guardian",
  "source_at": 16.2,
  "dur": 2.2,
  "position": "left",
  "name": "John Bazzite",
  "variant": "bazzite",
  "copy_source": "owner_supplied",
  "why": "The player lands at source 15.9-16.0, settles into the crouch at 16.2, rises through 16.4 and stands by 17.0. The wide plateau shot holds until the hard cut at 21.3, so the complete 2.2s lower-third stays on the landed player."
}
```

In the unchanged `jorge-cayde` record, replace the sentence that says the
persistent HUD celebrates the player with: `The player's separate landing
plate has already cleared, so this card remains Cayde's identity only.`

- [ ] **Step 7: Run the focused manifest tests**

Run:

```bash
python3 -m pytest -q \
  tests/test_standalone.py::test_final_trial_uses_one_normal_bazzite_plate_on_the_landing \
  tests/test_standalone.py::test_every_committed_batch_seat_maps_and_collides_with_nothing \
  tests/test_standalone.py::test_the_blueberries_jorge_plate_is_the_established_identity \
  tests/test_standalone.py::test_the_blueberries_plate_envelope_stays_on_evidenced_cayde \
  tests/test_index_integrity.py
```

Expected: PASS.

- [ ] **Step 8: Commit the authored record change**

```bash
git add schema/standalone-batch.schema.json \
  stories/standalone/bluefin-video-batch.json tests/test_standalone.py
git commit -m "fix: finish standalone nameplate timing

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Record the finished-nameplate policy

**Files:**
- Modify: `docs/skills/plates/SKILL.md:36-65`

**Interfaces:**
- Consumes: authored identity authority already described in `docs/skills/plates/references/copy-authoring.md`
- Produces: a direct agent rule distinguishing identity plates from prose placeholders

- [ ] **Step 1: Add the finished-nameplate rule after “The field set is closed”**

Add:

```markdown
### Finished identities never degrade to placeholders

Once a person's Guardian identity is authored, every finished series video
reproduces that complete identity and its chrome flags. Do not replace it with
a name-only approximation, generic Blueberry copy, or a placeholder plate to
make a timing pass look complete.

Placeholder machinery is for undecided ensemble casting and unwritten prose.
It is never a fallback for an established real identity. If a new person has
only partial authored copy, render only those authored rows and record the
missing metadata; never borrow or invent the rest.
```

- [ ] **Step 2: Run documentation and skill checks**

Run:

```bash
python3 scripts/generate_skill_index.py --check
python3 -m pytest -q tests/test_doc_links.py
```

Expected: PASS; the skill index does not change because front matter is
unchanged.

- [ ] **Step 3: Commit the policy**

```bash
git add docs/skills/plates/SKILL.md
git commit -m "docs(plates): require finished authored identities

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: Rebuild and inspect both delivered videos

**Files:**
- Generated, ignored: `media/standalone/*`
- Generated, ignored: `renders/standalone/bluefin-and-the-blueberries/*`
- Generated, ignored: `renders/standalone/bluefin-your-final-trial/*`
- Deliver: `~/Videos/Bluefin and the Blueberries.mp4`
- Deliver: `~/Videos/Bluefin - Your Final Trial.mp4`

**Interfaces:**
- Consumes: `python3 tools/standalone.py build <manifest> <slug>`
- Produces: one farm-rendered H.264/AAC delivery and thumbnail per slug

- [ ] **Step 1: Prove no authored work is stranded before encoding**

Run:

```bash
python3 tools/worktrees.py
git status --short
```

Expected: the quality-pass branch is clean after its commits; any unrelated
worktree findings are reported but do not redirect this render.

- [ ] **Step 2: Fetch the pinned Blueberries source if absent**

Run:

```bash
python3 tools/standalone.py fetch \
  stories/standalone/bluefin-video-batch.json bluefin-and-the-blueberries
```

Expected: prints the local source path under `media/standalone/`.

- [ ] **Step 3: Build Blueberries through the farm-first path**

Run:

```bash
python3 tools/standalone.py build \
  stories/standalone/bluefin-video-batch.json bluefin-and-the-blueberries
```

Expected: reports `encoded on cluster` when the farm is reachable and delivers
`~/Videos/Bluefin and the Blueberries.mp4`.

- [ ] **Step 4: Verify Blueberries**

Run:

```bash
python3 tools/standalone.py verify \
  stories/standalone/bluefin-video-batch.json bluefin-and-the-blueberries
```

Expected: `bluefin-and-the-blueberries verified`.

Inspect extracted review frames:

```bash
ffmpeg -v error -y -ss 32.3 \
  -i "$HOME/Videos/Bluefin and the Blueberries.mp4" -frames:v 1 \
  "$HOME/Videos/Wolves/work/blueberries-quality-pass-plate.png"
ffmpeg -v error -y -ss 85.4 \
  -i "$HOME/Videos/Bluefin and the Blueberries.mp4" -frames:v 1 \
  "$HOME/Videos/Wolves/work/blueberries-quality-pass-tail.png"
ffmpeg -v error -y -ss 85.6 \
  -i "$HOME/Videos/Bluefin and the Blueberries.mp4" -frames:v 1 \
  "$HOME/Videos/Wolves/work/blueberries-quality-pass-cta.png"
```

Expected: 32.3 shows the complete trustee plate on Cayde; 85.4 contains no
publisher title; 85.6 is the approved CTA.

- [ ] **Step 5: Fetch and build Final Trial**

Run:

```bash
python3 tools/standalone.py fetch \
  stories/standalone/bluefin-video-batch.json bluefin-your-final-trial
python3 tools/standalone.py build \
  stories/standalone/bluefin-video-batch.json bluefin-your-final-trial
```

Expected: delivers `~/Videos/Bluefin - Your Final Trial.mp4` through the
farm-first path.

- [ ] **Step 6: Verify Final Trial**

Run:

```bash
python3 tools/standalone.py verify \
  stories/standalone/bluefin-video-batch.json bluefin-your-final-trial
```

Expected: `bluefin-your-final-trial verified`.

Inspect representative frames:

```bash
ffmpeg -v error -y -ss 10.0 \
  -i "$HOME/Videos/Bluefin - Your Final Trial.mp4" -frames:v 1 \
  "$HOME/Videos/Wolves/work/final-trial-quality-pass-no-hud.png"
ffmpeg -v error -y -ss 17.3 \
  -i "$HOME/Videos/Bluefin - Your Final Trial.mp4" -frames:v 1 \
  "$HOME/Videos/Wolves/work/final-trial-quality-pass-landing.png"
ffmpeg -v error -y -ss 60.0 \
  -i "$HOME/Videos/Bluefin - Your Final Trial.mp4" -frames:v 1 \
  "$HOME/Videos/Wolves/work/final-trial-quality-pass-no-persistent-hud.png"
```

Expected: 10.0 and 60.0 have no John HUD; 17.3 shows the normal name-only
Bazzite lower-third on the landed player.

- [ ] **Step 7: Run the repository gate**

Run:

```bash
python3 -m pytest -q
python3 tools/corpus.py --check
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
pre-commit run --all-files
```

Expected: PASS.

- [ ] **Step 8: Confirm the checkout and delivery boundary are clean**

Run:

```bash
git status --short
git ls-files --error-unmatch \
  "$HOME/Videos/Bluefin and the Blueberries.mp4" 2>/dev/null && exit 1 || true
git ls-files --error-unmatch \
  "$HOME/Videos/Bluefin - Your Final Trial.mp4" 2>/dev/null && exit 1 || true
```

Expected: no uncommitted repository changes and neither delivered video is
tracked.

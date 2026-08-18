# Programme Intro Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved programme-time review notes, rebuild each affected upstream component, then deliver one fresh watchable programme.

**Architecture:** Keep every edit in the builder or authored record that owns the affected screen. Reuse existing card, boss-bar, banner, dialogue, ending, and delivery paths; add only one new renderer primitive (`countdown`) and one cursor-only choice layer. Build touched acts independently, publish named acts, then assemble the programme from fresh inputs.

**Tech Stack:** Python 3.13, pytest, Pillow, FFmpeg 8.1 through existing container/farm wrappers, Playwright card renderer, JSON manifests and JSON Schema.

## Global Constraints

- Approved design: `docs/superpowers/specs/2026-08-18-programme-intro-revision-design.md`.
- Review baseline: `~/Videos/Wolves/review/intro-notes-baseline.mp4`; all supplied timestamps refer to this file.
- Preserve owner copy exactly. Split messages without paraphrasing or changing capitalization.
- Never invent speakers, identities, footage, art, or plate fields.
- Remove Sarah Novotny and Brent Burns from Act II scheduling only; keep casting records.
- Missing art renders as polished text on black. Stale or unsupported plates are re-rendered or omitted.
- Preserve source audio and existing gains; no normalization, EQ, compression, or unnecessary audio encode.
- Video encoding uses the ghost farm when reachable. Local encoding requires an explicit cluster-unavailable reason.
- Write each failing test first and observe the expected failure before production edits.
- Regenerate derived JSON with its generator; never hand-edit generated records.
- Use exact-path `git add`; never `git add -A`.

---

## File Structure

**Existing records and builders modified:**

- `stories/00-prologue-plates.json` — briefing and moved book card records.
- `scripts/build_prologue.py` — prologue card inputs and timing.
- `stories/megacut/megacut-hero-plates.json` — Act I `Your Potential` copy and retired copy.
- `stories/00-perfume-thread.json` — declares the movement-2 countdown derivative without polluting the clean movement.
- `scripts/build_interludes.py` — keeps clean movement generation unchanged.
- `scripts/build_countdown.py` — creates frame-derived countdown entries and burns the movement-2 derivative.
- `tools/plate.py` — countdown plate; persistent choice base plus cursor-only animation.
- `scripts/build_efmb_plates.py` — all Act II copy, layout, sequence, and scheduling changes.
- `stories/02-endless-forms-plates.json` — regenerated Act II manifest.
- `scripts/build_efmb.py` — only if action/pause edit timing must change; source of hallway constants.
- `dialogue/yt_curse_of_osiris_opening_cinematic/DIALOGUE.md` — owner-edited Act III dialogue surface.
- `dialogue/yt_curse_of_osiris_opening_cinematic/dialogue.json` — regenerated dialogue record.
- `stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json` — gold Bob plate and top-right sign.
- `scripts/build_scream_card.py` — opaque interstitial generation/freshness.
- `scripts/build_wolves.py` — removes the duplicated Amber interruption upstream.
- `stories/seven-days-timing-pass.json` — regenerated Act VI timing pass.
- `stories/megacut/ending-cards.json` — ending copy/order.
- `schema/ending-cards.schema.json` — authored ending subtitle and added `prove-it` card.
- `cards/ending.html` — mission-card size and per-card optical placement.
- `scripts/build_ending_pause.py`, `scripts/build_ending_overlays.py` — consume current rendered cards; no new render system.
- `docs/skills/review.md` — durable burned-pixel and baseline-clock lesson.

**Tests modified or created:**

- `tests/test_prologue.py`
- `tests/test_act1_cinematic.py`
- `tests/test_interludes.py`
- `tests/test_countdown.py` (new)
- `tests/test_efmb_act.py`
- `tests/test_plate_choice_video.py` (new)
- `tests/test_dialogue.py`
- `tests/test_dialogue_md.py`
- `tests/test_cards.py`
- `tests/test_wolves_timing_pass.py`
- `tests/test_ending_sequence.py`
- `tests/test_ending_overlays.py`

---

### Task 1: Make LFX Menu Persistent Through Every Burned Frame

**Files:**
- Modify: `tools/plate.py:1776-1960, 3415-3595`
- Modify: `scripts/build_efmb_plates.py:833-864, 1900-1935`
- Modify: `tests/test_efmb_act.py:1129-1210`
- Create: `tests/test_plate_choice_video.py`

**Interfaces:**
- Consumes: `tools.plate.render_plate(spec)`, `tools.plate.burn(video, entries, plates_dir, out_path)`.
- Produces: `kind="choice"` static base entry and `kind="choice_cursor"` animation entries sharing `group="choice_lfx_cursor"`.

- [ ] **Step 1: Write failing manifest-structure test**

Add to `tests/test_efmb_act.py`:

```python
def test_choice_menu_is_one_persistent_base_with_cursor_only_animation():
    frames = _choice_frames()
    base = [p for p in frames if p["id"] == "choice_lfx_base"]
    cursor = [p for p in frames if p["id"].startswith("choice_lfx_cursor_")]
    assert len(base) == 1
    assert base[0]["kind"] == "choice"
    assert base[0]["dur"] == pytest.approx(build_efmb_plates.CHOICE_HOLD)
    assert cursor
    assert all(p["kind"] == "choice_cursor" for p in cursor)
    assert all(p["group"] == "choice_lfx_cursor" for p in cursor)
```

Change `_choice_frames()` to select IDs beginning with `choice_lfx_`, preserving existing authored-option assertions.

- [ ] **Step 2: Run test and confirm RED**

Run:

```bash
python3 -m pytest -q tests/test_efmb_act.py::test_choice_menu_is_one_persistent_base_with_cursor_only_animation
```

Expected: FAIL because current generator emits only full-frame `kind="choice"` animation frames.

- [ ] **Step 3: Add real burned-pixel regression test**

Create `tests/test_plate_choice_video.py` using `tools.render.find_ffmpeg(prefer_container=False)`. Build a 1-second `60000/1001` black source, render one 0.5-second static choice plus cursor sequence, call real `plate.burn`, decode output frames to PNG, then assert:

```python
assert len(window_frames) in (29, 30, 31)
for image in window_frames:
    assert image.getpixel((960, 540)) != (0, 0, 0)
for before, after in zip(window_frames, window_frames[1:]):
    diff = ImageChops.difference(before, after)
    assert diff.getbbox() is not None
    assert diff.crop((0, 0, 700, 1080)).getbbox() is None
```

Use a source with static black pixels so all changed pixels come from cursor motion. Skip only when no H.264-capable local test encoder is available; CI remains offline.

- [ ] **Step 4: Run pixel test and confirm RED**

Run:

```bash
python3 -m pytest -q tests/test_plate_choice_video.py
```

Expected: FAIL because `choice_cursor` is not renderable and no persistent base exists.

- [ ] **Step 5: Implement minimal persistent layer**

In `tools/plate.py`, extract choice geometry into `_choice_layout(spec)`. Keep `_render_choice` drawing the scrim/menu; add `_render_choice_cursor(spec)` returning a transparent 1920×1080 frame containing only `_cursor()` at the eased position. Dispatch `kind="choice_cursor"` in `render_plate`.

In `scripts/build_efmb_plates.py`, emit:

```python
plates.append({
    "id": "choice_lfx_base", "kind": "choice", "at": start,
    "dur": CHOICE_HOLD, "position": "full",
    "copy_source": "owner_supplied", "label": spec["text"],
    "options": CHOICE_OPTIONS,
})
for n in range(frames):
    plates.append({
        "id": f"choice_lfx_cursor_{n:02d}",
        "kind": "choice_cursor", "at": round(start + n * step, 3),
        "dur": step, "position": "full", "group": "choice_lfx_cursor",
        "order": n, "animation": True, "copy_source": "owner_supplied",
        "options": CHOICE_OPTIONS,
        "pointer": round((n / (frames - 1)) * CHOICE_POINTER_CUT, 4),
    })
```

Do not change generic `_burn_units`; its one-input animation-group path already serves the cursor sequence.

- [ ] **Step 6: Verify GREEN and regenerate**

Run:

```bash
python3 -m pytest -q tests/test_plate_choice_video.py tests/test_efmb_act.py -k 'choice or frames_are_contiguous'
python3 scripts/build_efmb_plates.py --write
python3 scripts/build_efmb_plates.py --check
```

Expected: PASS; committed manifest contains one static menu and one cursor animation group.

- [ ] **Step 7: Commit**

```bash
git add tools/plate.py scripts/build_efmb_plates.py stories/02-endless-forms-plates.json tests/test_efmb_act.py tests/test_plate_choice_video.py
git commit -m "fix(act2): keep choice menu visible"
```

---

### Task 2: Insert Mission Briefing and Move Prologue Book Slide

**Files:**
- Modify: `stories/00-prologue-plates.json`
- Modify: `scripts/build_prologue.py:111-145, 199-290`
- Modify: `tests/test_prologue.py`

**Interfaces:**
- Consumes: existing browser renderer mapping for `kind="act"` and `cards/act.html` body rows.
- Produces: `plate_mission-briefing.png`; unchanged `plate_book-a.png` at a later window.

- [ ] **Step 1: Write failing record/timing tests**

Add to `tests/test_prologue.py`:

```python
def test_volunteer_briefing_precedes_the_moved_book():
    doc = json.loads(build_prologue.MANIFEST.read_text())
    by_id = {p["id"]: p for p in doc["plates"]}
    card = by_id["mission-briefing"]
    assert card == {
        "id": "mission-briefing", "kind": "act",
        "at": 26.9, "dur": 6.74,
        "label": "PROJECT BLUEFIN MISSION BRIEFING",
        "title": "Thanks for Volunteering",
        "body": [
            "Tophee Protocol Quick Insertion // ACTIVATED",
            "Agones Cluster // Cycling",
            "Mechaphippy Deployment // UNAUTHORIZED",
        ],
        "copy_source": "owner_supplied",
    }
    assert by_id["book-a"]["at"] == 34.0
    assert card["at"] + card["dur"] <= by_id["book-a"]["at"]
```

Add a filtergraph test asserting `mission-briefing` overlays before `book-a` and both use manifest-derived constants.

- [ ] **Step 2: Run test and confirm RED**

```bash
python3 -m pytest -q tests/test_prologue.py -k 'volunteer or moved_book'
```

Expected: FAIL because `mission-briefing` does not exist and `book-a` remains at 26.9.

- [ ] **Step 3: Add authored card and manifest-derived timing**

Add exact object above to `stories/00-prologue-plates.json`. Move `book-a.at` to `34.0`; preserve its full object and retired companion `book-b` unchanged.

In `scripts/build_prologue.py`, load `at`/`dur` by ID once, add `plate_mission-briefing.png` as an FFmpeg input, and replace hard-coded book window with manifest values. Add the briefing PNG to the explicit `freshness.needs_render` output list and add `cards/act.html` to its template inputs. Render all prologue cards through existing `cards/render-cards.mjs`; no new HTML template.

- [ ] **Step 4: Verify GREEN and card freshness**

```bash
python3 -m pytest -q tests/test_prologue.py
python3 scripts/build_prologue.py --cards
python3 scripts/build_prologue.py --print-command | grep 'plate_mission-briefing.png'
```

Expected: tests pass; command includes briefing and moved book overlays.

- [ ] **Step 5: Commit**

```bash
git add stories/00-prologue-plates.json scripts/build_prologue.py tests/test_prologue.py
git commit -m "feat(prologue): add volunteer mission briefing"
```

---

### Task 3: Replace Act I Caption and Build Countdown to 4:44

**Files:**
- Modify: `stories/megacut/megacut-hero-plates.json`
- Modify: `tests/test_act1_cinematic.py`
- Create: `scripts/build_countdown.py`
- Create: `tests/test_countdown.py`
- Modify: `tools/plate.py`
- Modify: `stories/00-perfume-thread.json`
- Modify: `stories/megacut/megacut.json`
- Modify: `tests/test_interludes.py`

**Interfaces:**
- Consumes: current megacut item durations, clean `renders/perfume-2.mp4`, `plate.render_all`, `plate.burn`.
- Produces: `countdown_entries(segment_programme_start, segment_duration, target=264.0) -> list[dict]` and `renders/perfume-2-countdown.mp4`.

- [ ] **Step 1: Write failing Act I copy test**

```python
def test_your_potential_replaces_machine_and_nerve_on_the_review_mark():
    by_id = {p["id"]: p for p in hero_manifest()["plates"]}
    cue = by_id["act-i-cue-09b"]
    assert cue["text"] == "Your Potential is Off the Charts"
    assert cue["at"] == pytest.approx(107.8, abs=0.05)
    assert cue["at"] + cue["dur"] <= by_id["act-i-warning"]["at"]
```

Run and expect FAIL on old machine-and-nerve copy. Update the manifest object, retain old text in `_retired_copy`, and verify this focused test passes.

- [ ] **Step 2: Write failing countdown arithmetic tests**

Create `tests/test_countdown.py`:

```python
def test_countdown_first_zero_is_exactly_programme_444():
    entries = build_countdown.countdown_entries(217.6, 46.6, target=264.0)
    zero = next(e for e in entries if e["text"] == "00:00")
    assert zero["programme_at"] == pytest.approx(264.0, abs=1e-9)
    assert all(e["text"] != "00:00" for e in entries[:entries.index(zero)])


def test_countdown_values_are_derived_not_authored():
    entries = build_countdown.countdown_entries(260.2, 4.8, target=264.0)
    assert [e["text"] for e in entries] == ["00:04", "00:03", "00:02", "00:01", "00:00"]
```

Use `Fraction(60000, 1001)` inside implementation and convert target/segment boundaries to frame numbers before deriving labels.

- [ ] **Step 3: Run countdown tests and confirm RED**

```bash
python3 -m pytest -q tests/test_countdown.py
```

Expected: import failure because `scripts/build_countdown.py` does not exist.

- [ ] **Step 4: Implement countdown plate and derivative builder**

Add `kind="countdown"` to `tools.plate.render_plate`. `_render_countdown` draws only `MM:SS` in existing display font and Bluefin accent chrome on a transparent tight card; `position="countdown-bottom"` seats it centered in the lower matte/safe area.

Implement `scripts/build_countdown.py` to:

1. Read `stories/megacut/megacut.json` and calculate movement-2's programme start from preceding item durations.
2. Generate whole-second entries through target frame 4:44.
3. Render PNGs into `renders/perfume-2/countdown/`.
4. Burn onto clean `renders/perfume-2.mp4`, outputting `renders/perfume-2-countdown.mp4` with audio copied.

Do not add countdown fields to `stories/00-perfume-thread.json` movement itself; keep `test_the_renders_stay_clean` valid. Add a sibling `_derivatives` record naming source and output, then point the movement-2 megacut item to the derivative.

- [ ] **Step 5: Assert clean-source/derived-output split**

Add to `tests/test_interludes.py`:

```python
def test_movement_two_countdown_is_a_derivative_of_the_clean_movement(thread, plan):
    derivative = thread["_derivatives"]["perfume-2-countdown"]
    assert derivative["source"] == "renders/perfume-2.mp4"
    assert derivative["out_file"] == "renders/perfume-2-countdown.mp4"
    assert _item(plan, "perfume-2-countdown")["path"] == derivative["out_file"]
```

- [ ] **Step 6: Verify focused suite**

```bash
python3 -m pytest -q tests/test_countdown.py tests/test_act1_cinematic.py tests/test_interludes.py
python3 scripts/build_countdown.py --print-plan
```

Expected: first `00:00` reports programme frame corresponding to 264.0 seconds; clean thread invariants still pass.

- [ ] **Step 7: Commit**

```bash
git add stories/megacut/megacut-hero-plates.json stories/00-perfume-thread.json stories/megacut/megacut.json tools/plate.py scripts/build_countdown.py tests/test_countdown.py tests/test_act1_cinematic.py tests/test_interludes.py
git commit -m "feat(programme): count down to act two"
```

---

### Task 4: Apply Act II Opening, Layout, and Split-Message Notes

**Files:**
- Modify: `scripts/build_efmb_plates.py`
- Modify: `tests/test_efmb_act.py`
- Regenerate: `stories/02-endless-forms-plates.json`
- Modify: `tools/plate.py` only for `position="letterbox-top"`

**Interfaces:**
- Consumes: `OPENING_HEAD_CARD`, `LATE_PASS`, `MAPPED_PASS`, existing `miniboss`, `banner`, `chat`, and `title` kinds.
- Produces: regenerated non-overlapping Act II manifest.

- [ ] **Step 1: Write failing removal and major-title tests**

Add focused assertions:

```python
def test_opening_removes_sarah_and_brent_from_this_act_only():
    ids = {p["id"] for p in build_efmb_plates.build()["plates"]}
    assert "opening_sarahnovotny" not in ids
    assert "opening_bdburns" not in ids
    casting = Path("vocab/casting.yaml").read_text()
    assert "sarahnovotny:" in casting and "bdburns:" in casting


def test_black_head_and_present_day_use_major_title_treatment():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["opening_black_head"]["position"] == "center"
    assert by_id["opening_black_head"]["scale"] >= 1.25
    assert by_id["late_present_day"]["position"] == "center"
    assert by_id["late_present_day"]["scale"] >= 1.25
```

Run tests; expect failures on scheduled names and old scale/position.

- [ ] **Step 2: Write failing boss/banner tests**

```python
def test_bad_decisions_and_haters_use_red_boss_chrome():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["late_poor_technical_decisions"]["kind"] == "miniboss"
    assert by_id["late_poor_technical_decisions"]["name"] == "POOR TECHNICAL DECISIONS"
    assert by_id["mapped_haters"]["kind"] == "miniboss"
    assert by_id["mapped_haters"]["name"] == "HATERS"


def test_ogc_banner_uses_top_letterbox_lane():
    banners = [p for p in build_efmb_plates.build()["plates"]
               if p["id"].startswith("top_banner_ogc_")]
    assert banners and all(p["position"] == "letterbox-top" for p in banners)
```

- [ ] **Step 3: Write failing split-copy tests**

Assert IDs and exact strings for each owner-marked split. Use capitalization boundaries already present in source copy:

```python
expected = {
    "late_metrics_1": "Projects Teams Metrics are strong",
    "late_metrics_2": "They just need mentoring in the right skills",
    "mapped_lionheartp_hardware": "Why spend the extra dollar to support Linux hardware",
    "mapped_lionheartp_together_1": "When we work together",
    "mapped_lionheartp_together_2": "This gets easier",
    "mapped_eggroll_title_1": "Nice work testing that patch",
    "mapped_eggroll_title_2": "Usually Blueberries just Send me a bunch of crap",
    "mapped_redacted_options_1": "Your options are success",
    "mapped_redacted_options_2": "Or a lifetime of servitude in the Toilmaster's Packaging Mines",
}
for plate_id, text in expected.items():
    assert by_id[plate_id]["text"] == text
```

The 7:50 note removes only the extra dollar line from scheduling; retain its authored object in a `RETIRED` constant or unresolved record.

- [ ] **Step 4: Implement minimal generator changes**

- Set `OPENING_NAMEPLATES = []`; do not edit `vocab/casting.yaml`.
- Preserve existing head/PRESENT DAY copy, set centered major-title scale.
- Convert bad-decisions and HATERS entries to existing `miniboss` shape using `name`, optional empty `title`, and `position="boss"`.
- Add `letterbox-top` placement by mirroring existing banner centering against `picture` and seating it in the top matte (`y = max(0, py - plate.height)`); do not add another banner renderer.
- Replace long chat objects with two sequential objects, using existing cursor/gap scheduling.
- Remove scheduled extra-dollar entry while preserving copy in the generator record.

- [ ] **Step 5: Regenerate and verify**

```bash
python3 scripts/build_efmb_plates.py --write
python3 scripts/build_efmb_plates.py --check
python3 -m pytest -q tests/test_efmb_act.py tests/test_plate.py
```

Expected: all targeted copy/layout tests pass and no overlap validator fails.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_efmb_plates.py stories/02-endless-forms-plates.json tools/plate.py tests/test_efmb_act.py tests/test_plate.py
git commit -m "feat(act2): apply opening and dialogue notes"
```

---

### Task 5: Rebuild Act II Hallway and End-Fight Order

**Files:**
- Modify: `scripts/build_efmb_plates.py:500-610, 2335-2420`
- Modify: `scripts/build_efmb.py:190-230, picture_sequence()` only if shot windows change
- Modify: `tests/test_efmb_act.py:788-860, 930-1020`
- Regenerate: `stories/02-endless-forms-plates.json`

**Interfaces:**
- Consumes: `HALLWAY_AT`, `AMBER_AT`, `HALLWAY_AFTER_AMBER_AT`, `HALLWAY_RETURN_AT`, owner-evidenced Amber clip.
- Produces: Hikari-first pause → akgraner help → action → hallway pause → Owen → Kyle question → existing akgraner dialogue → end-fight lines.

- [ ] **Step 1: Write failing sequence test**

```python
def test_hallway_round_follows_owner_order():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    ordered = [
        "mapped_hikari_ouch",
        "mapped_akgraner_help",
        "mapped_akgraner_take_care",
        "mapped_owen_slay",
        "mapped_which_kyle",
        "mapped_akgraner_kindness_1",
    ]
    assert [by_id[i]["text"] for i in ordered] == [
        "Ouch man wtf!",
        "Sounds like you need some help",
        "Let me take care of this for you",
        "Slay out, Queen!",
        "Which one of you is Kyle?",
        "Kindness is doing what's right",
    ]
    assert [by_id[i]["at"] for i in ordered] == sorted(by_id[i]["at"] for i in ordered)
    assert by_id["mapped_akgraner_help"]["at"] < build_efmb.AMBER_AT
    assert by_id["mapped_owen_slay"]["at"] >= build_efmb.HALLWAY_AFTER_AMBER_AT
```

- [ ] **Step 2: Write failing restored/end-fight copy test**

```python
def test_restored_empathy_and_endfight_lines_are_exact():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["mapped_empathy_tacos"]["speaker"] == "Empathy"
    assert by_id["mapped_empathy_tacos"]["text"] == "tacos."
    assert by_id["mapped_kyle_sup"]["speaker"] == "kylegospo"
    assert by_id["mapped_kyle_sup"]["text"] == "Sup"
    assert by_id["mapped_kolunmi_disco"]["text"] == "Disco!"
    assert by_id["mapped_redacted_harbringer"]["text"] == "Harbringer to the TOC"
    assert by_id["mapped_redacted_ready"]["text"] == "They're ready"
    assert by_id["mapped_akgraner_disco"]["text"] == "Disco!"
```

- [ ] **Step 3: Run focused tests and confirm RED**

```bash
python3 -m pytest -q tests/test_efmb_act.py -k 'hallway_round or restored_empathy or endfight'
```

Expected: missing IDs and wrong existing order.

- [ ] **Step 4: Implement schedule using existing two freeze windows**

Update `BLACK_CONVERSATION` so Hikari begins the first paused hallway and akgraner help lines finish before `AMBER_AT`. Keep the existing Amber action run unchanged unless the sequence lacks room. Update `AFTER_AMBER_CONVERSATION` so Owen and Kyle question precede the existing kindness dialogue. Add exact 9:57–10:26 end-fight entries after the evidenced bad-guy shot.

The pre-action sequence needs 23.0 seconds at the existing holds and 0.25-second gaps. Change `HALLWAY_FREEZE_SEC` from `22.000` to `24.000`, leaving 1.0 second of visual air; derive `AMBER_AT` and every later constant as today. Keep `HALLWAY_AFTER_AMBER_SEC = 21.500`, which fits Owen, Kyle's question, and six kindness messages. Add assertions for both derived windows and the resulting +2.0-second act duration; never shorten a message below `MIN_HOLD`.

- [ ] **Step 5: Regenerate and verify**

```bash
python3 scripts/build_efmb_plates.py --write
python3 scripts/build_efmb_plates.py --check
python3 -m pytest -q tests/test_efmb_act.py
```

Expected: exact owner order, no overlaps, action remains between two hallway holds.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_efmb_plates.py stories/02-endless-forms-plates.json tests/test_efmb_act.py
git diff --quiet -- scripts/build_efmb.py || git add scripts/build_efmb.py
git commit -m "feat(act2): resequence amber hallway dialogue"
```

---

### Task 6: Update Act III Dialogue, Gold Plate, and Email Sign

**Files:**
- Modify: `dialogue/yt_curse_of_osiris_opening_cinematic/DIALOGUE.md`
- Regenerate: `dialogue/yt_curse_of_osiris_opening_cinematic/dialogue.json`
- Modify: `stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json`
- Modify: `scripts/build_uncut_credited.sh`
- Modify: `tests/test_dialogue.py`
- Modify: `tests/test_dialogue_md.py`

**Interfaces:**
- Consumes: `tools/dialogue_md.py apply`, `scripts/build_uncut_credited.sh`, `vocab/casting.yaml` Osiris→mrbobbytables binding.
- Produces: current dialogue record plus fixed Bob gold plate and top-right sign.

- [ ] **Step 1: Write failing exact-copy test**

Add to `tests/test_dialogue.py`:

```python
def test_act_three_review_copy_and_splits_are_exact():
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    by_id = {c["id"]: c for c in data["cues"]}
    assert by_id["d01"]["text"] == "What a shitshow"
    assert by_id["d20a"]["text"] == "Everyone forgot how to use KVM! We need to split up"
    assert by_id["d20b"]["text"] == "Everyone's making their own and it's all bad!"
    assert by_id["d21"]["text"] == "They've broken out of the sandbox"
    assert by_id["d23a"]["text"] == "The open rate of maintainer emails is 7%"
    assert by_id["d23b"]["text"] == "I don't like this plan"
    ids = [c["id"] for c in data["cues"]]
    assert ids.index("d20a") < ids.index("d20b") < ids.index("d21")
    assert ids.index("d23a") < ids.index("d23b") < ids.index("d24")
```

The 64-character gate forces 11:16 and 12:56 to remain multiple readable cues rather than one auto-shrunk pill.

- [ ] **Step 2: Write failing fixed-plate test**

```python
def test_act_three_fixed_deck_has_gold_bob_and_top_right_email_sign():
    doc = json.loads(Path("stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json").read_text())
    by_id = {p["id"]: p for p in doc["plates"]}
    bob = by_id["mrbobbytables-gold"]
    assert bob["name"] == "Bob Killen"
    assert bob["variant"] == "leader"
    sign = by_id["maintainer-emails"]
    assert sign["position"] == "top-right"
    assert sign["title"] == "Maintainers Reading Emails"
    assert sign["subtitle"] == "And Other Preposterous Tales"
    assert sign["body"] == ["Summer 2027"]
```

- [ ] **Step 3: Run tests and confirm RED**

```bash
python3 -m pytest -q tests/test_dialogue.py tests/test_dialogue_md.py -k 'act_three_review or gold_bob or email_sign'
```

Expected: old dialogue and missing fixed cards.

- [ ] **Step 4: Edit owner surface and regenerate JSON**

Edit only authored text and the split cue headings in `DIALOGUE.md`. Preserve every unaffected cue, speaker label, and source window. Replace `d01`; keep existing `d02`/`d03` as the two 11:16 messages; split original `d20`'s 121.44–128.91 window into adjacent `d20a`/`d20b` windows; keep `d21` immediately after them; split original `d23`'s 134.64–137.59 window into adjacent `d23a`/`d23b` windows. No words outside the owner-supplied replacements change.

Run:

```bash
python3 tools/dialogue_md.py apply yt_curse_of_osiris_opening_cinematic
```

Add fixed cards using Bob's existing authored plate fields from `vocab/casting.yaml`; use `variant="leader"` for gold. Add `position="top-right"` by reusing title-card rendering and adding one placement branch in `tools/plate.py`. In `scripts/build_uncut_credited.sh`, merge the fixed manifest with lead reveals before `tools/dialogue.py --around`, so dialogue routes around the gold plate and sign rather than failing overlap validation; reuse that merged manifest for the final fixed inputs.

- [ ] **Step 5: Verify generated dialogue and build command**

```bash
python3 -m pytest -q tests/test_dialogue.py tests/test_dialogue_md.py tests/test_plate.py
ACODEC=flac scripts/build_uncut_credited.sh yt_curse_of_osiris_opening_cinematic renders/roster-2026-08.json
```

This step must print final path `renders/yt_curse_of_osiris_opening_cinematic-credited-hq.mp4`; do not substitute a new roster.

- [ ] **Step 6: Commit**

```bash
git add dialogue/yt_curse_of_osiris_opening_cinematic/DIALOGUE.md dialogue/yt_curse_of_osiris_opening_cinematic/dialogue.json stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json scripts/build_uncut_credited.sh tests/test_dialogue.py tests/test_dialogue_md.py
git diff --quiet -- tools/plate.py tests/test_plate.py || git add tools/plate.py tests/test_plate.py
git commit -m "feat(act3): apply dialogue review notes"
```

---

### Task 7: Remove Slide Bleed and Duplicated Act VI Amber Interruption

**Files:**
- Modify: `tests/test_cards.py`
- Modify: `scripts/build_wolves.py:514-564`
- Modify: `tests/test_wolves_timing_pass.py`
- Regenerate: `stories/seven-days-timing-pass.json`

**Interfaces:**
- Consumes: opaque scream card, `Timeline` bed clock, existing continuous Act III-B→III-C footage. Programme 21:37 maps into the interruption being removed.
- Produces: opaque interstitial and Act VI timeline with no silence/slide/Amber gameplay interruption.

- [ ] **Step 1: Pin the already-correct opaque scream-card contract**

At programme 16:22 the current builder contract must prevent any earlier Project Bluefin slide from showing through. The builder already creates an RGB frame on black; preserve that behavior while forcing a fresh render in Task 10. Add this regression to `tests/test_cards.py`:

```python
def test_scream_card_is_opaque_black(tmp_path, monkeypatch):
    monkeypatch.setattr(build_scream_card, "OUT", tmp_path / "scream.png")
    build_scream_card.render()
    image = Image.open(build_scream_card.OUT)
    assert image.mode == "RGB"
    assert image.getpixel((0, 0)) == (0, 0, 0)
    assert image.getpixel((1919, 1079)) == (0, 0, 0)
```

Run it before Act VI edits. Expected: PASS, proving the reported bleed is not authored alpha and needs a fresh generated card plus final-window inspection, not a new renderer.

- [ ] **Step 2: Write failing Act VI removal test**

Add to `tests/test_wolves_timing_pass.py`:

```python
def test_amber_interruption_is_removed_because_act_two_now_owns_it(cut):
    descriptions = "\n".join(s["description"] for s in cut["shots"])
    assert "INTERRUPTION A" not in descriptions
    assert "INTERRUPTION B" not in descriptions
    assert "INTERRUPTION C" not in descriptions
    assert "INTERRUPTION D" not in descriptions
    assert not any(s.get("video_id") == build_wolves.GAMEPLAY for s in cut["shots"])
```

Run; expect FAIL because the four interruption units remain.

- [ ] **Step 3: Remove interruption upstream**

Delete the A/B/C cards and Amber gameplay `t.run` from `build_wolves.timeline()`. Remove the paired pause assertion; let the bed and authored picture continue directly from Act III-B into Act III-C. Keep constants and rights records only if used by another build path; otherwise delete dead interruption-only constants.

Do not edit `stories/megacut/megacut.json` to hide the section.

- [ ] **Step 4: Regenerate and verify music/credit invariants**

```bash
python3 scripts/build_wolves.py
python3 -m pytest -q tests/test_wolves_timing_pass.py tests/test_cards.py
```

Expected: bed still consumed exactly once, no shot reused, tail credit windows remain inside output, act duration shrinks by the interruption's exact film duration.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_wolves.py stories/seven-days-timing-pass.json tests/test_cards.py tests/test_wolves_timing_pass.py
git commit -m "fix(programme): remove duplicate amber interruption"
```

---

### Task 8: Apply Ending Mission and Call-to-Action Copy

**Files:**
- Modify: `stories/megacut/ending-cards.json`
- Modify: `schema/ending-cards.schema.json`
- Modify: `cards/ending.html`
- Modify: `tests/test_ending_sequence.py`
- Modify: `tests/test_ending_overlays.py`

**Interfaces:**
- Consumes: `cards/render-cards.mjs`, `scripts/build_ending_pause.py`, `scripts/build_ending_overlays.py`.
- Produces: five updated pause cards, renamed support card, added `prove-it` underwater card.

- [ ] **Step 1: Write failing exact-copy/order tests**

Replace old expectations in `tests/test_ending_sequence.py` with:

```python
def test_reviewed_pause_copy_is_exact_and_ordered():
    cards = selected(ending(), "pause")
    assert [(c.get("label"), c["title"], c.get("subtitle")) for c in cards[:4]] == [
        ("Our Mission", "Bring new contributors to cloud native", None),
        (None, "We are Bluefin", None),
        (None, "We are not nice.", None),
        (None, "We do what must be done.", "(Wait for it)"),
    ]


def test_support_and_prove_it_cards_are_exact():
    by_id = {p["id"]: p for p in ending()["plates"]}
    assert by_id["fight-for-us"]["text"] == '"We support the Community"'
    assert by_id["prove-it"]["text"] == "Prove it."
    assert by_id["prove-it"]["placement"] == "center"
    assert by_id["prove-it"]["at"] == pytest.approx(93.075, abs=0.05)
```

- [ ] **Step 2: Write failing visual-hook tests**

```python
def test_mission_is_larger_and_bird_card_moves_right_and_down():
    template = TEMPLATE.read_text()
    assert "document.body.dataset.cardId = card.id" in template
    assert 'body[data-card-id="mission"]' in template
    assert 'body[data-card-id="purpose"]' in template
    assert "translate(8vw, 7vh)" in template
```

The existing dark `bluefin-night.png` remains the wallpaper for `we-are`; set `mission.wallpaper` to an existing dark wallpaper rather than adding art.

- [ ] **Step 3: Run tests and confirm RED**

```bash
python3 -m pytest -q tests/test_ending_sequence.py tests/test_ending_overlays.py
```

Expected: old copy, no subtitle field, no `prove-it`, old schema cardinality.

- [ ] **Step 4: Update record, schema, and existing template**

- Change exact copy as asserted.
- Add optional non-empty `subtitle` to pause-card schema.
- Increase underwater `plate_ids` and `plates` cardinality from 10/15 to 11/16.
- Insert `prove-it` before `for-nova` at 93.075 with same centered treatment, 4.4-second hold, and 0.6-second fades.
- In `cards/ending.html`, set `document.body.dataset.cardId = card.id`; use ID-specific CSS for mission size and purpose optical translation. Render subtitle smaller beneath lesson title. No generic offset/config abstraction.

- [ ] **Step 5: Render and verify card record**

```bash
python3 -m pytest -q tests/test_ending_sequence.py tests/test_ending_overlays.py
node cards/render-cards.mjs --manifest stories/megacut/ending-cards.json --out-dir renders/ending/cards
python3 scripts/build_ending_pause.py --print-command
python3 scripts/build_ending_overlays.py --print-command
```

Expected: schema passes; all 16 card PNGs exist; pause remains 1380 frames; underwater windows do not overlap.

- [ ] **Step 6: Commit**

```bash
git add stories/megacut/ending-cards.json schema/ending-cards.schema.json cards/ending.html tests/test_ending_sequence.py tests/test_ending_overlays.py
git commit -m "feat(ending): apply mission review copy"
```

---

### Task 9: Document Review Lessons

**Files:**
- Modify: `docs/skills/review.md`
- Test: `tests/test_doc_links.py`

**Interfaces:**
- Produces: durable rule for baseline-clock translation and animated-card pixel verification.

- [ ] **Step 1: Add two concise current-state rules**

Under the review verification section, add:

```markdown
A programme timestamp belongs to the exact review baseline that produced it. Keep that baseline until every note has been translated with `--locate`; after an upstream duration changes, re-running the same timestamp against the new plan answers a different question.

Animation timing is not visual continuity. Any animated plate must pass a burned-pixel check at delivery frame rate: decode every frame in its visible window and assert the persistent chrome never disappears.
```

- [ ] **Step 2: Verify docs**

```bash
python3 -m pytest -q tests/test_doc_links.py
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add docs/skills/review.md
git commit -m "docs(review): require burned-frame animation checks"
```

---

### Task 10: Rebuild, Publish, Assemble, and Verify Delivery

**Files:**
- Generated only: `renders/`, `~/Videos/Wolves/Prod/`, `~/Videos/Wolves/megacut/`, eligible `~/Videos/Wolves/10mb/`.
- Update through tools: `stories/megacut/delivery.json` digests only via `deliver.py publish`.

**Interfaces:**
- Consumes: all previous committed tasks.
- Produces: fresh changed acts and final review programme.

- [ ] **Step 1: Prove current graph before encoding**

```bash
python3 tools/deliver.py status --check
python3 tools/megacut.py stories/megacut/megacut.json --dry-run
```

Expected: changed acts may report stale inputs; dry-run must resolve every source. Inspect Act VII mismatch against current rendered copy before rebuilding: compare frames at every Act VII plate window. Re-render or omit stale plates; never certify on digest alone.

- [ ] **Step 2: Run all offline gates**

```bash
python3 -m pytest -q
python3 tools/corpus.py --check
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
```

Expected: all PASS.

- [ ] **Step 3: Render current cards before acts**

```bash
python3 scripts/build_prologue.py --cards
python3 scripts/build_efmb_plates.py --write
python3 scripts/build_efmb_plates.py --check
node cards/render-cards.mjs --manifest stories/megacut/ending-cards.json --out-dir renders/ending/cards
python3 scripts/build_scream_card.py
```

Expected: derived PNG mtimes are newer than their manifests/templates.

- [ ] **Step 4: Rebuild independent encode units on farm**

Use existing farm-enabled builders/commands. Submit independent prologue, Act I/countdown, Act II, Act III, Act VI, Act VII-if-pixels-changed, mission pause, and ending overlay jobs separately so Kubernetes can schedule both nodes. Never launch two writers for one output.

Required outputs:

```text
renders/00-prologue.mp4
renders/megacut-01-hero.mp4
renders/perfume-2-countdown.mp4
renders/efmb-plated.mp4
renders/yt_curse_of_osiris_opening_cinematic-credited-hq.mp4
~/Videos/wolves-musical/wolves-7days-plated-master-v8.mp4
~/Videos/wolves-directors-cut/wolves-directors-cut-beauty-of-the-beast-hq-nocover.mp4
renders/ending/mission-pause.mp4
renders/perfume-5-ending.mp4
```

If a builder lacks `--farm`, stage its exact printed FFmpeg argv through `tools/farm.py`; do not silently run the encode locally.

- [ ] **Step 5: Decode and gate each changed master**

For each output, run one exact loop:

```bash
for output in \
  renders/00-prologue.mp4 \
  renders/megacut-01-hero.mp4 \
  renders/perfume-2-countdown.mp4 \
  renders/efmb-plated.mp4 \
  renders/yt_curse_of_osiris_opening_cinematic-credited-hq.mp4 \
  /var/home/jorge/Videos/wolves-musical/wolves-7days-plated-master-v8.mp4 \
  renders/ending/mission-pause.mp4 \
  renders/perfume-5-ending.mp4; do
  /home/linuxbrew/.linuxbrew/bin/ffmpeg -v error -xerror -i "$output" -f null -
  python3 tools/peaks.py measure "$output"
  ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,r_frame_rate,color_primaries,color_transfer,color_space \
    -of default=noprint_wrappers=1 "$output"
done
```

Expected: clean decode; 1920×1080; `60000/1001`; BT.709 tags; delivered true peak inside project gate; unchanged audio stream MD5 for picture-only revisions.

- [ ] **Step 6: Publish named acts only**

```bash
python3 tools/deliver.py publish --act 0
python3 tools/deliver.py publish --act I
python3 tools/deliver.py publish --act II
python3 tools/deliver.py publish --act III
python3 tools/deliver.py publish --act VI
python3 tools/deliver.py publish --act VII
```

Skip `--act VII` only when pixel/copy inspection proves its current master already matches the record and no Act VII source changed in this work. Never use blanket `publish`.

- [ ] **Step 7: Reassemble programme remotely**

```bash
python3 tools/megacut.py stories/megacut/megacut.json --dry-run
python3 tools/megacut.py stories/megacut/megacut.json --farm --no-copy --farm-jobs 3
python3 tools/transitions.py stories/megacut/megacut.json --measure ~/Videos/Wolves/megacut/seven-days-to-the-wolves-v3.9.mp4
```

Record provenance through `deliver.py build` or `deliver.record_megacut_provenance`; direct assembly alone does not close provenance.

- [ ] **Step 8: Inspect every changed visual window**

Generate contact sheets around all supplied timestamps from the new programme. Specifically verify:

- 0:35 briefing → moved book → TITANFALL.
- 3:27 `Your Potential`.
- First countdown `00:00` frame at 4:44.
- LFX menu never disappears frame-to-frame.
- Act II boss bars, top-letterbox banner, split chats, hallway/action order, and 9:57–10:26 lines.
- Act III gold plate/sign and all split dialogue.
- No old slide under scream card.
- Act VI plays naturally across removed interruption.
- Ending copy, bird clearance, support line, and `Prove it.`.

- [ ] **Step 9: Rebuild eligible social copies and final status**

```bash
python3 tools/deliver.py build
python3 tools/deliver.py status --check
~/Videos/audio-check.sh --all
```

Expected: Act I social copy current; absent-by-design acts remain recorded as such; no stale deliverable rung; programme provenance matches current `Prod/` checksums.

- [ ] **Step 10: Copy final review artifact**

```bash
cp --reflink=auto ~/Videos/Wolves/megacut/seven-days-to-the-wolves-v3.9.mp4 ~/Videos/Wolves/review/intro-notes-revision.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 ~/Videos/Wolves/review/intro-notes-revision.mp4
```

Report path and runtime first.

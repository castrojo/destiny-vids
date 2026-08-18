"""Act I cinematic overlays: owner-supplied narrative cues and source swap.

Task 1 adds:
* kind: caption (top rail)
* kind: context (lower-left stack)
* kind: warning (full-frame red deployment warning)
* an act slide for the Platform Wars
* a dialogue-free audio source with an explicit sync offset

All copy is owner_supplied and asserted verbatim.
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import plate
from scripts import build_act1

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "stories" / "megacut" / "megacut-hero-plates.json"

CUES = [
    (9.000, 18.500, "What is a Contributor-Guardian?"),
    (19.000, 22.500, "We are connected to the weft and weave of the universe."),
    (22.750, 26.250, "No one knows how long we will serve."),
    (26.500, 30.500, "We stand alongside those without our gifts"),
    (31.000, 42.500, "When all else fails, we fight for the user."),
    (43.000, 51.000, "Every Seven Years, the Kube of Destiny visits the Sol System."),
    (51.250, 59.500, "An ancient artifact from beyond The Veil"),
    (60.000, 69.500, "Inside, the generational knowledge of an entire civilization - unlimited power"),
    (70.000, 73.250, "Now, across our ecosystem, the forces of the Toilmaster surge."),
    (73.500, 76.750, "Our borders are under siege."),
    (77.000, 80.500, "Across Sol, our Guardians fight."),
    (81.000, 90.500, "Pushing back buys us only time, but the alternative is unthinkable."),
    (91.000, 94.500, "We built a Community none of us dared to dream of, with allies from unlikely places."),
    (94.750, 98.500, "We have never had more to lose."),
    (99.000, 105.000, "You are the dream of many ancestors"),
    (107.800, 112.000, "Your Potential is Off the Charts"),
    (112.000, 114.200, "[ PREPARE FOR TITANFALL ]"),
]

PLATFORM_WARS = {
    "at": 114.200, "dur": 4.000,
    "title": "The Platform Wars",
    "subtitle": "2015-2019",
    "body": ["Guardians Deliver the Final Blow", "to Legacy Infrastructure"],
}


def _manifest():
    with MANIFEST.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data["plates"]


def test_ten_narrative_cues_are_in_the_manifest():
    entries = _manifest()
    captions = [e for e in entries if e.get("kind") == "caption"]
    assert len(captions) == 16

    by_start = {round(e["at"], 3): e for e in captions}
    for start, end, text in CUES:
        if start == 112.0:
            continue  # the warning is a separate kind
        key = round(start, 3)
        assert key in by_start, f"missing caption at {start}"
        assert by_start[key]["text"] == text
        assert by_start[key]["dur"] == pytest.approx(end - start, abs=0.01)
        assert by_start[key].get("position") == "caption"
        assert by_start[key].get("copy_source") == "owner_supplied"


def test_the_community_cue_carries_a_kubernetes_glyph():
    entries = _manifest()
    cue = next(e for e in entries if e.get("kind") == "caption"
               and " Community" in e.get("text", ""))
    assert cue["text"] == "We built a Community none of us dared to dream of, with allies from unlikely places."
    glyphs = cue.get("glyphs", [])
    assert len(glyphs) == 1
    glyph = glyphs[0]
    assert glyph.get("word") == "Community"
    assert glyph.get("token") == "o"
    assert glyph.get("index") == 0
    assert "kubernetes" in glyph.get("src", "")


def test_the_ancestral_cue_uses_two_cards_at_the_authored_line_break():
    entries = _manifest()
    pair = [e for e in entries if e.get("id") in
            {"act-i-cue-09a", "act-i-cue-09b"}]
    assert [e["text"] for e in pair] == [
        "You are the dream of many ancestors",
        "Your Potential is Off the Charts",
    ]
    assert all(plate.render_plate(e).getchannel("A").getbbox() for e in pair)


def test_your_potential_replaces_machine_and_nerve_on_the_review_mark():
    by_id = {p["id"]: p for p in _manifest()}
    cue = by_id["act-i-cue-09b"]
    assert cue["text"] == "Your Potential is Off the Charts"
    assert cue["at"] == pytest.approx(107.8, abs=0.05)
    assert cue["at"] + cue["dur"] <= by_id["act-i-warning"]["at"]
    assert cue["_retired_copy"] == "This one is machine and nerve, and has its mind concluded"


def test_clankers_context_moved_out_of_act_i():
    entries = _manifest()
    assert not any(e.get("kind") == "context" for e in entries)


def test_act_i_captions_use_one_authored_sentence_per_card():
    captions = [e for e in _manifest() if e.get("kind") == "caption"]
    assert captions
    assert all("\n" not in e["text"] for e in captions)
    assert all(". " not in e["text"] for e in captions)


def test_orlix_nameplate_uses_the_owner_supplied_github_identity():
    entry = next(e for e in _manifest() if e.get("id") == "orlix")
    assert entry["name"] == "Orlix"
    assert entry["avatar"] == "renders/avatars/OrlinVasilev.jpg"
    assert entry["at"] == pytest.approx(68.5)
    assert entry["dur"] == pytest.approx(6.5)
    assert entry["position"] == "left"
    note = entry.get("note", "")
    assert "https://github.com/OrlinVasilev" in note
    assert "https://avatars.githubusercontent.com/u/7236111?v=4" in note
    assert "7236111" in note
    raw = MANIFEST.read_text(encoding="utf-8")
    assert "github.com/orlix" not in raw
    assert "891481" not in raw


def test_warning_card_at_112_with_exact_text():
    entries = _manifest()
    warn = next(e for e in entries if e.get("kind") == "warning")
    assert warn["at"] == pytest.approx(112.0, abs=0.01)
    assert warn["dur"] == pytest.approx(2.2, abs=0.01)
    assert warn["position"] == "warning"
    assert warn["text"] == "[ PREPARE FOR TITANFALL ]"
    assert warn.get("copy_source") == "owner_supplied"


def test_platform_wars_act_card_follows_the_warning():
    entries = _manifest()
    pw = next(e for e in entries if e.get("kind") == "act" and "Platform Wars" in e.get("title", ""))
    warn = next(e for e in entries if e.get("kind") == "warning")
    assert pw["at"] == pytest.approx(warn["at"] + warn["dur"], abs=0.01)
    assert pw["dur"] == pytest.approx(PLATFORM_WARS["dur"], abs=0.01)
    assert pw["title"] == PLATFORM_WARS["title"]
    assert pw["subtitle"] == PLATFORM_WARS["subtitle"]
    assert pw["body"] == PLATFORM_WARS["body"]


def test_manifest_loads_without_overlapping_errors():
    # Overlaps are intentional and resolved by chrome rows / group.
    plate.load_manifest(MANIFEST)


def test_caption_renders_in_the_top_safe_lane():
    spec = {"id": "c1", "kind": "caption", "text": CUES[0][2]}
    img = plate.place(plate.render_plate(spec), "caption")
    x0, y0, x1, y1 = img.getchannel("A").getbbox()
    assert y1 <= plate.FRAME_H * 0.35, "caption must stay in the top safe lane"
    assert x0 >= 0 and x1 <= plate.FRAME_W


def test_context_renders_lower_left_above_the_plaque_lane():
    spec = {
        "id": "ctx", "kind": "context",
        "title": "Clankers and Contributors",
        "subtitle": "2026",
        "body": ["The Community fights its way", "Through the Chaos", "To Find the Kube of Destiny"],
    }
    img = plate.place(plate.render_plate(spec), "context")
    x0, y0, x1, y1 = img.getchannel("A").getbbox()
    assert x0 < plate.FRAME_W * 0.30, "context is lower-left"
    assert y1 <= plate.FRAME_H * 0.72, "context must clear the lower-third plaque lane"
    assert y0 >= plate.FRAME_H * 0.35, "context must not ride into the top rail"


def test_warning_renders_full_frame():
    spec = {"id": "warn", "kind": "warning", "text": "[ PREPARE FOR TITANFALL ]"}
    img = plate.place(plate.render_plate(spec), "warning")
    bbox = img.getchannel("A").getbbox()
    assert bbox == (0, 0, plate.FRAME_W, plate.FRAME_H)


def test_warning_uses_diagonal_deployment_hazard_stripes():
    img = plate.render_plate({"kind": "warning", "text": "ALERT"})
    top_bar = img.crop((0, 0, plate.FRAME_W, plate.WARNING_STRIPE_H))
    colours = set(top_bar.getdata())
    assert len(colours) >= 2
    assert max(r for r, _, _, _ in colours) - min(r for r, _, _, _ in colours) > 80


def test_two_captions_at_once_are_rejected():
    with pytest.raises(ValueError, match="visible at the same time"):
        plate.load_manifest_entries([
            {"id": "a", "kind": "caption", "at": 0.0, "dur": 5.0, "position": "caption", "text": "x"},
            {"id": "b", "kind": "caption", "at": 3.0, "dur": 5.0, "position": "caption", "text": "y"},
        ])


def test_caption_may_overlap_a_guardian_plate():
    plate.load_manifest_entries([
        {"id": "cap", "kind": "caption", "at": 10.0, "dur": 5.0, "position": "caption", "text": "x"},
        {"id": "guard", "at": 11.0, "dur": 5.0, "position": "left",
         "label": "TRUSTEE // GUARDIAN", "name": "A Guardian", "title": "T"},
    ])


def test_build_contract_describes_the_current_dialogue_free_cut():
    contract = build_act1.__doc__
    assert "yt_into_the_light_without_dialogue.webm" in contract
    assert "1.978625" in contract
    assert "118.2" in contract
    assert "Ikora" not in contract
    assert "111.55 output" not in contract


def test_trim_command_switches_to_the_dialogue_free_source():
    cmd = build_act1.trim_command(["ffmpeg"])
    assert build_act1.AUDIO_SRC.endswith("without_dialogue.webm")
    audio_index = cmd.index("-i") + 1  # first input is video, second is audio
    # find the audio -i token
    inputs = [i for i, token in enumerate(cmd) if token == "-i"]
    assert len(inputs) == 2
    assert build_act1.AUDIO_SRC in cmd[inputs[1] + 1]


def test_terminal_source_frame_held_by_tpad_is_black(tmp_path):
    """The half-open picture trim must include the first black frame."""
    source = ROOT / build_act1.VIDEO_SRC
    if not source.exists():
        pytest.skip("footage is gitignored")
    import subprocess
    from PIL import Image

    frame = tmp_path / "terminal.png"
    sample_at = build_act1.TRIM_END - (1 / 30)
    ffmpeg = Path("/home/linuxbrew/.linuxbrew/bin/ffmpeg")
    if not ffmpeg.exists():
        pytest.skip("H.264-capable ffmpeg is unavailable")
    subprocess.run([
        str(ffmpeg), "-v", "error", "-y",
        "-ss", f"{sample_at:.6f}", "-i", str(source),
        "-frames:v", "1", str(frame),
    ], check=True)
    image = Image.open(frame).convert("L")
    assert sum(image.getdata()) / (image.width * image.height) < 1.0


def test_trim_command_offsets_audio_and_holds_the_picture_to_118_2():
    cmd = build_act1.trim_command(["ffmpeg"])
    audio_ss_idx = None
    for i, token in enumerate(cmd):
        if token == "-ss" and i > 0 and cmd[i - 1] == "-i":
            continue  # video -ss is before -i
    # More robust: locate the second -ss, which belongs to the audio input.
    ss_positions = [i for i, token in enumerate(cmd) if token == "-ss"]
    assert len(ss_positions) == 2
    audio_ss = float(cmd[ss_positions[1] + 1])
    assert audio_ss == pytest.approx(build_act1.TRIM_START + build_act1.AUDIO_SYNC_OFFSET, abs=1e-6)
    assert build_act1.OUTPUT_DURATION == 118.2
    assert "-t" in cmd
    assert any(float(cmd[i+1]) == pytest.approx(build_act1.OUTPUT_DURATION, abs=0.01) for i, tok in enumerate(cmd) if tok == "-t")
    assert "tpad" in " ".join(cmd), "the video must freeze its last decoded frame"


def _synthetic_mark(tmp_path, *, fill=(255, 0, 0, 255)):
    from PIL import Image
    path = tmp_path / "mark.png"
    Image.new("RGBA", (80, 80), fill).save(path)
    return path


def _boxes_overlap(a, b):
    """True when two (x0, y0, x1, y1) bboxes intersect."""
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


# --- Review finding 1: farm encode legs must expect OUTPUT_DURATION ----------

def test_farm_trim_and_burn_legs_expect_output_duration(monkeypatch):
    """Both farm legs receive the final output duration, not the source trim."""
    captured = []

    def fake_farm(argv, inputs, out, expected_duration):
        captured.append((str(out), expected_duration))

    monkeypatch.setattr("tools.farm.run_ffmpeg_on_cluster", fake_farm)
    monkeypatch.setattr("tools.render.find_ffmpeg", lambda: ["ffmpeg"])
    monkeypatch.setattr(build_act1, "cover_art", lambda: None)
    monkeypatch.setattr(build_act1, "render_cards", lambda: None)
    monkeypatch.setattr(plate, "render_all", lambda entries, out_dir, picture=None: [])

    def fake_burn(*args, **kwargs):
        # The burn leg hands a runner that eventually calls the farm helper.
        kwargs["runner"](["ffmpeg", "-i", "dummy"])

    monkeypatch.setattr(plate, "burn", fake_burn)
    build_act1.build_act1(skip_encode=False, use_farm=True)

    assert len(captured) == 2, f"expected two farm legs, got {captured}"
    for out, dur in captured:
        assert dur == pytest.approx(build_act1.OUTPUT_DURATION, abs=0.01), out


# --- Review finding 2: caption glyph must truly replace the target letter ----

def test_caption_glyph_substitutes_for_target_character(tmp_path):
    """A transparent mark proves the original character is not rasterized."""
    mark = _synthetic_mark(tmp_path, fill=(0, 0, 0, 0))
    spec = {
        "id": "glyph", "kind": "caption", "text": "Community",
        "glyphs": [{"word": "Community", "token": "o", "index": 0,
                    "src": str(mark)}],
    }
    plain = plate.place(plate.render_plate({"id": "plain", "kind": "caption",
                                            "text": "Community"}), "caption")
    glyph = plate.place(plate.render_plate(spec), "caption")
    # Locate the 'o' position on the plain line (layout is the same in glyph).
    from PIL import Image, ImageDraw
    from tools.plate import _font, CAPTION_FS
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    f_text = _font("bold", CAPTION_FS)
    line = "Community"
    full_w = probe.textlength(line, font=f_text)
    char_pos = [probe.textlength(line[:i], font=f_text) for i in range(len(line))]
    plain_bbox = plain.getchannel("A").getbbox()
    line_x = plain_bbox[0] + (plain_bbox[2] - plain_bbox[0] - full_w) / 2
    ox = int(line_x + char_pos[1] + probe.textlength("o", font=f_text) / 2)
    oy = (plain_bbox[1] + plain_bbox[3]) // 2
    # With a transparent mark replacing the 'o', the pixel must not be white text.
    r, g, b, a = glyph.getpixel((ox, oy))
    assert max(r, g, b) < 180 or a < 50, "the target letter must not be painted beneath the mark"

def test_caption_glyph_falls_back_to_plain_letter_when_mark_missing(tmp_path):
    """Approved requirement: a missing mark degrades gracefully to the plain letter."""
    spec = {
        "id": "missing", "kind": "caption", "text": "Community",
        "glyphs": [{"word": "Community", "token": "o", "index": 0,
                    "src": str(tmp_path / "missing.png")}],
    }
    plain = plate.place(plate.render_plate({"id": "plain", "kind": "caption",
                                            "text": "Community"}), "caption")
    fallback = plate.place(plate.render_plate(spec), "caption")
    assert fallback.tobytes() == plain.tobytes()


# --- Review finding 3: Platform Wars body second row has no period -----------

def test_platform_wars_body_second_row_has_no_period():
    entries = _manifest()
    pw = next(e for e in entries if e.get("kind") == "act" and "Platform Wars" in e.get("title", ""))
    assert pw["body"] == ["Guardians Deliver the Final Blow", "to Legacy Infrastructure"]


# --- Review finding 4: card freshness must not silently reuse stale/missing ---

def test_render_cards_reuses_fresh_cards_without_playwright(monkeypatch, tmp_path):
    manifest = tmp_path / "cards.json"
    manifest.write_text(json.dumps({"plates": [{
        "id": "platform-wars", "kind": "act", "at": 0, "dur": 4,
        "title": "The Platform Wars", "subtitle": "2015-2019",
        "body": ["Guardians Deliver the Final Blow", "to Legacy Infrastructure"],
    }]}))
    out_dir = tmp_path / "plates"
    out_dir.mkdir()
    png = out_dir / "plate_platform-wars.png"
    png.write_bytes(b"png")
    # Make the output newer than the manifest: fresh.
    mtime = manifest.stat().st_mtime
    os.utime(png, (mtime + 10, mtime + 10))
    ran = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: ran.append(a) or type("P", (), {"returncode": 0})())
    build_act1.render_cards(manifest=manifest, out_dir=out_dir,
                            website_modules=tmp_path / "missing")
    assert not ran


def test_render_cards_fails_when_stale_and_playwright_missing(tmp_path):
    manifest = tmp_path / "cards.json"
    manifest.write_text(json.dumps({"plates": [{
        "id": "platform-wars", "kind": "act", "at": 0, "dur": 4,
        "title": "The Platform Wars", "subtitle": "2015-2019",
        "body": ["Guardians Deliver the Final Blow", "to Legacy Infrastructure"],
    }]}))
    out_dir = tmp_path / "plates"
    out_dir.mkdir()
    png = out_dir / "plate_platform-wars.png"
    png.write_bytes(b"png")
    # Make the output older than the manifest: stale.
    mtime = manifest.stat().st_mtime
    os.utime(png, (mtime - 10, mtime - 10))
    with pytest.raises(RuntimeError, match="website playwright checkout is missing"):
        build_act1.render_cards(manifest=manifest, out_dir=out_dir,
                                website_modules=tmp_path / "missing")


def test_render_cards_renders_stale_cards_when_playwright_available(tmp_path):
    manifest = tmp_path / "cards.json"
    manifest.write_text(json.dumps({"plates": [{
        "id": "platform-wars", "kind": "act", "at": 0, "dur": 4,
        "title": "The Platform Wars", "subtitle": "2015-2019",
        "body": ["Guardians Deliver the Final Blow", "to Legacy Infrastructure"],
    }]}))
    out_dir = tmp_path / "plates"
    out_dir.mkdir()
    png = out_dir / "plate_platform-wars.png"
    png.write_bytes(b"png")
    mtime = manifest.stat().st_mtime
    os.utime(png, (mtime - 10, mtime - 10))
    wm = tmp_path / "website" / "node_modules"
    wm.mkdir(parents=True)
    ran = []
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("subprocess.run",
                        lambda cmd, **k: ran.append(cmd) or type("P", (), {"returncode": 0, "stderr": ""})())
    try:
        build_act1.render_cards(manifest=manifest, out_dir=out_dir,
                                website_modules=wm)
    finally:
        monkeypatch.undo()
    assert any("render-cards.mjs" in str(part) for cmd in ran for part in cmd)


def test_render_cards_renders_when_template_is_newer_than_output(monkeypatch, tmp_path):
    """A newer HTML template must trigger re-rendering even if the manifest is old."""
    manifest = tmp_path / "cards.json"
    manifest.write_text(json.dumps({"plates": [{
        "id": "platform-wars", "kind": "act", "at": 0, "dur": 4,
        "title": "The Platform Wars", "subtitle": "2015-2019",
        "body": ["Guardians Deliver the Final Blow", "to Legacy Infrastructure"],
    }]}))
    out_dir = tmp_path / "plates"
    out_dir.mkdir()
    png = out_dir / "plate_platform-wars.png"
    png.write_bytes(b"png")

    # Set up a temp cards/ tree so no real file mtimes are mutated.
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    renderer = cards_dir / "render-cards.mjs"
    renderer.write_text("// renderer")
    template = cards_dir / "act.html"
    template.write_text("<html></html>")

    # Output is newer than manifest and renderer (would skip without templates).
    base = manifest.stat().st_mtime
    os.utime(renderer, (base, base))
    os.utime(png, (base + 10, base + 10))
    # Template is newer than output: must invalidate cache.
    os.utime(template, (base + 20, base + 20))

    wm = tmp_path / "website" / "node_modules"
    wm.mkdir(parents=True)

    monkeypatch.setattr(build_act1, "REPO_ROOT", tmp_path)
    ran = []
    monkeypatch.setattr("subprocess.run",
                        lambda cmd, **k: ran.append(cmd) or type("P", (), {"returncode": 0, "stderr": ""})())
    build_act1.render_cards(manifest=manifest, out_dir=out_dir,
                            website_modules=wm)
    assert any("render-cards.mjs" in str(part) for cmd in ran for part in cmd)


# --- Review finding 5: layout at 44-46s and caption over title-cover at 31-36 -

def test_layout_at_44_46s_caption_and_guardian_lanes_do_not_overlap(tmp_path):
    entries = _manifest()
    by_id = {e["id"]: e for e in entries}
    caption = by_id["act-i-cue-04a"]
    kaslin = by_id["kaslin"]
    companion = dict(by_id["kaslin-katerina"])
    # Do not rely on the real cached companion artwork.
    from PIL import Image
    synth = tmp_path / "katerina.png"
    Image.new("RGBA", (200, 120), (120, 120, 120, 255)).save(synth)
    companion["art"] = str(synth)
    frames = {}
    for spec, pos in ((caption, "caption"), (kaslin, "left"),
                      (companion, "right")):
        img = plate.place(plate.render_plate(spec), pos)
        frames[spec["id"]] = img.getchannel("A").getbbox()
    cap_box, guard_box, bond_box = (
        frames["act-i-cue-04a"], frames["kaslin"],
        frames["kaslin-katerina"]
    )
    assert cap_box[3] <= plate.FRAME_H * 0.35, "caption stays in top safe lane"
    assert guard_box[3] <= plate.FRAME_H * (1 - plate.MARGIN_BOTTOM)
    assert bond_box[3] <= plate.FRAME_H * (1 - plate.MARGIN_BOTTOM)
    assert not _boxes_overlap(cap_box, guard_box)
    assert not _boxes_overlap(cap_box, bond_box)


def test_caption_over_title_cover_at_31_36_is_allowed_and_stays_in_top_lane():
    entries = _manifest()
    by_id = {e["id"]: e for e in entries}
    caption = by_id["act-i-cue-03"]
    cover = by_id["title-cover"]
    # A chrome caption may share the screen with a full-frame photo card.
    assert plate.load_manifest_entries([caption, cover]) == [caption, cover]
    cap_frame = plate.place(plate.render_plate(caption), "caption")
    _, _, _, y1 = cap_frame.getchannel("A").getbbox()
    assert y1 <= plate.FRAME_H * 0.35, "caption remains top-safe over the title cover"


# --- Review finding 6: Christoph's title uses a literal em dash -------------

def test_christoph_title_carries_literal_em_dash():
    entries = _manifest()
    christoph = next(e for e in entries
                     if e.get("name") == "Christoph Blecker")
    assert "—" in christoph["title"]
    # The manifest on disk must use the literal character, not a JSON escape.
    raw = MANIFEST.read_text(encoding="utf-8")
    assert "First Among Equals — The North Star" in raw
    assert "\\u2014" not in raw


# --- Glyph-aware layout: adjacent characters stay visible ------------------

def test_caption_glyph_reserves_mark_width_and_does_not_obscure_next_character(tmp_path):
    """Regression: a Kubernetes mark wider than the 'o' it replaces must push
    the following text rightward so the adjacent characters stay visible."""
    from PIL import Image, ImageDraw

    def rightmost_ink(img, y):
        # ignore the red glyph mark and the faint shadow; look for solid text
        for x in range(img.width - 1, -1, -1):
            r, g, b, a = img.getpixel((x, y))
            if a > 200 and not (r > 220 and g < 50 and b < 50):
                return x
        return None

    mark = Image.new("RGBA", (33, 33), (255, 0, 0, 255))
    mark_path = tmp_path / "kube.png"
    mark.save(mark_path)

    text = "Community"
    spec = {
        "id": "c", "kind": "caption", "text": text,
        "glyphs": [{"word": "Community", "token": "o", "index": 0,
                    "src": str(mark_path)}],
    }
    img = plate.render_plate(spec)
    plain = plate.render_plate({"id": "c2", "kind": "caption", "text": text})

    f_text = plate._font("bold", plate.CAPTION_FS)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    char_w = probe.textlength("C", font=f_text)
    mark_h = int(round(f_text.size * 0.85))
    mark_w = int(round(mark.width * mark_h / mark.height))
    a, d = f_text.getmetrics()
    mid_y = int(round(plate.CAPTION_PAD + (a + d) / 2))

    plain_right = rightmost_ink(plain, mid_y)
    glyph_right = rightmost_ink(img, mid_y)
    assert plain_right is not None and glyph_right is not None
    # the line is visually wider by (mark_w - char_w); the text tail must move
    # right by that delta once the placeholder reserves the mark's real width.
    delta = mark_w - char_w
    assert glyph_right >= plain_right + delta - 2, (
        f"glyph replacement did not shift following text right "
        f"({glyph_right} vs {plain_right}, delta {delta:.1f})"
    )

    # and the reserved gap actually contains the red mark
    red_right = max(
        (x for x in range(img.width)
         if all(v > 220 if i == 0 else v < 50 for i, v in enumerate(img.getpixel((x, mid_y))[:3]))),
        default=None,
    )
    assert red_right is not None, "Kubernetes mark was not drawn"
    assert red_right <= glyph_right, "mark bleeds past the shifted text"


# --- Stale output naming ----------------------------------------------------

def test_render_cards_names_stale_output_when_playwright_unavailable(tmp_path):
    """A stale (not missing) card output is named in the fail-closed error."""
    manifest = tmp_path / "cards.json"
    manifest.write_text(json.dumps({"plates": [{
        "id": "platform-wars", "kind": "act", "at": 0, "dur": 4,
        "title": "The Platform Wars", "subtitle": "2015-2019",
        "body": ["Guardians Deliver the Final Blow", "to Legacy Infrastructure"],
    }]}))
    out_dir = tmp_path / "plates"
    out_dir.mkdir()
    png = out_dir / "plate_platform-wars.png"
    png.write_bytes(b"png")
    # Make the output older than the manifest: stale, not missing.
    mtime = manifest.stat().st_mtime
    os.utime(png, (mtime - 10, mtime - 10))
    with pytest.raises(RuntimeError, match=r"plate_platform-wars\.png"):
        build_act1.render_cards(manifest=manifest, out_dir=out_dir,
                                website_modules=tmp_path / "missing")

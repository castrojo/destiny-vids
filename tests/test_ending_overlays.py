"""The underwater coda: the closing lines burned into a movement-5
DERIVATIVE, never into the clean movement.

The clean movement 5 (renders/perfume-5.mp4) stays clean for the dinosaur
pass. The derivative (renders/perfume-5-ending.mp4) is rebuilt directly from
the SAME original source window -- source 389.800 for 117.221 s -- so the
megacut does not stack a second x264 generation on the clean render, and the
decoded PCM of the two files is bit-identical.
"""

import json
from pathlib import Path

import pytest

from scripts import build_ending_overlays
from scripts import build_interludes

REPO = Path(__file__).resolve().parents[1]
THREAD = REPO / "stories" / "00-perfume-thread.json"
MANIFEST = REPO / "stories" / "megacut" / "ending-cards.json"


def ending():
    return json.loads(MANIFEST.read_text())


def thread():
    return json.loads(THREAD.read_text())


def movement_five(doc):
    return next(m for m in doc["movements"] if m["id"] == "perfume-5")


def underwater(doc):
    by_id = {card["id"]: card for card in doc["plates"]}
    return [by_id[id_] for id_ in doc["underwater"]["plate_ids"]]


def build_command(tmp_path):
    return build_ending_overlays.command(
        ending(),
        str(THREAD),
        tmp_path / "cards",
        tmp_path / "perfume-5-ending.mp4",
        ffmpeg=["ffmpeg"],
    )


def test_overlay_command_reads_the_original_source_and_keeps_audio_untreated(
        tmp_path):
    cmd = build_command(tmp_path)
    joined = " ".join(cmd)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "media/yt_nightwish_perfume_of_the_timeless.mkv" in joined
    assert "-c:a flac" in joined
    assert "afade" not in graph
    assert "volume=" not in graph
    assert "overlay=" in graph


def test_each_line_replaces_the_previous_line():
    cards = underwater(ending())
    for previous, current in zip(cards, cards[1:]):
        assert previous["at"] + previous["dur"] < current["at"]


def test_support_and_prove_it_keep_their_authored_windows():
    cards = {card["id"]: card for card in underwater(ending())}
    assert cards["fight-for-us"]["text"] == '"We support the Community"'
    assert cards["prove-it"] == {
        "id": "prove-it",
        "kind": "ending",
        "section": "underwater",
        "mode": "overlay",
        "placement": "center",
        "text": "Prove it.",
        "at": 93.075,
        "dur": 4.4,
        "fade_in": 0.6,
        "fade_out": 0.6,
        "_what": "Owner 2026-08-18: show Prove it. in the same centered treatment before For Nóva.",
    }


def test_the_command_renders_the_full_movement_from_its_measured_in_point(
        tmp_path):
    """Source 389.800 for exactly 117.221 s -- the clean movement's window."""
    cmd = build_command(tmp_path)
    assert cmd[cmd.index("-ss") + 1] == "389.800"
    # The last -t is the global output duration; earlier ones bound the
    # looped plate inputs.
    out_t = [cmd[i + 1] for i, a in enumerate(cmd[:-1]) if a == "-t"][-1]
    assert out_t == "117.221"
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "pad=1920:1080:0:138" in graph
    assert "aresample=48000" in graph


def test_enable_windows_are_half_open(tmp_path):
    """gte/lt, never between(): between() includes its upper bound, so the
    next line's first frame would carry the ghost of the previous one."""
    graph = build_command(tmp_path)[
        build_command(tmp_path).index("-filter_complex") + 1]
    assert "between(" not in graph
    assert "enable='gte(t,6.920)*lt(t,10.320)'" in graph
    # Seven Days: 33.000 + 4.200, half-open.
    assert "enable='gte(t,33.000)*lt(t,37.200)'" in graph
    # For Nóva, the last card, holds to the passage's own out point.
    assert "enable='gte(t,106.000)*lt(t,109.500)'" in graph


def test_alpha_fades_stay_inside_their_windows(tmp_path):
    graph = build_command(tmp_path)[
        build_command(tmp_path).index("-filter_complex") + 1]
    for card in underwater(ending()):
        at = float(card["at"])
        end = at + float(card["dur"])
        assert f"fade=t=in:st={at:.3f}:d={float(card['fade_in']):.3f}:alpha=1" \
            in graph, card["id"]
        fade_out_at = end - float(card["fade_out"])
        assert f"fade=t=out:st={fade_out_at:.3f}:" \
            f"d={float(card['fade_out']):.3f}:alpha=1" in graph, card["id"]


def test_overlays_apply_in_manifest_order(tmp_path):
    graph = build_command(tmp_path)[
        build_command(tmp_path).index("-filter_complex") + 1]
    chain = [m.start() for m in
             __import__("re").finditer(r"overlay=0:0", graph)]
    assert len(chain) == len(underwater(ending()))
    assert chain == sorted(chain)


def test_every_underwater_plate_png_is_required(tmp_path):
    """A missing plate is a failed render, not a silently skipped line."""
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    missing = build_ending_overlays.missing_cards(ending(), cards_dir)
    assert len(missing) == len(underwater(ending()))
    for path in missing:
        path.touch()
    assert build_ending_overlays.missing_cards(ending(), cards_dir) == []


def test_stale_ending_cards_use_the_browser_renderer(tmp_path, monkeypatch):
    cards_dir = tmp_path / "cards"
    ran = []
    monkeypatch.setattr(
        build_ending_overlays.freshness, "stale_outputs",
        lambda inputs, outputs: outputs,
    )
    monkeypatch.setattr(
        build_ending_overlays.subprocess, "run",
        lambda cmd, **kwargs: ran.append((cmd, kwargs)),
    )

    assert build_ending_overlays.refresh_cards(
        MANIFEST, ending(), cards_dir
    ) == [cards_dir / f"plate_{card['id']}.png" for card in underwater(ending())]

    cmd, kwargs = ran.pop()
    assert cmd[:6] == [
        "node", "cards/render-cards.mjs",
        "--manifest", str(MANIFEST),
        "--out-dir", str(cards_dir),
    ]
    assert cmd[6] == "--only"
    assert cmd[7].split(",") == [card["id"] for card in underwater(ending())]
    assert kwargs == {"check": True, "cwd": REPO}


def test_the_clean_movement_declares_the_derivative_separately():
    """The canonical movement stays clean; the derivative is a pointer out."""
    move = movement_five(thread())
    assert move["out_file"] == "renders/perfume-5.mp4"
    burned = {"fade_in", "fade_out", "fade", "plates", "overlay", "cards"}
    assert not burned & set(move)
    derivative = move["ending_derivative"]
    assert derivative["out_file"] == "renders/perfume-5-ending.mp4"
    assert derivative["overlay_manifest"] == "stories/megacut/ending-cards.json"
    assert derivative["overlay_section"] == "underwater"


def test_the_derivative_window_matches_the_clean_movement():
    move = movement_five(thread())
    assert float(move["in"]) == pytest.approx(389.800)
    assert float(move["duration"]) == pytest.approx(117.221)


# --- the generalisation, 2026-08-17 ----------------------------------------
#
# Movement 4 needed the same one-encode derivative as movement 5, but its
# plates ride on a picture that ALSO carries the movement's own
# replacements. The trap a naive copy would fall into: the old base chain
# never applied replacements, so the derivative would ship the chat OR the
# wallpapers and never both. The base is now build_interludes.video_chain
# itself, and these tests pin the composition.

CHAT = REPO / "stories" / "00-perfume-4-plates.json"


def chat():
    return json.loads(CHAT.read_text())


def movement_four(doc):
    return next(m for m in doc["movements"] if m["id"] == "perfume-4")


def chat_command(tmp_path, monkeypatch=None):
    """The movement-4 chat derivative's command.

    The replacement artwork lives in gitignored ``renders/artwork/``, which
    is FETCHED, so on a fresh checkout `usable_replacements` correctly finds
    nothing and the graph degrades to the bare source. That degrade is right
    and is tested below -- but it made the graph-shape assertions pass only
    on a machine that happened to have the pictures, and fail on CI. So the
    shape tests resolve artwork deterministically instead of asking the disk.
    """
    if monkeypatch is not None:
        monkeypatch.setattr(
            build_interludes, "art_path",
            lambda name: (REPO / name["file"]) if isinstance(name, dict)
            else build_interludes.ARTWORK_DIR / f"{name}.png")
    return build_ending_overlays.command(
        chat(),
        str(THREAD),
        tmp_path / "plates",
        tmp_path / "perfume-4-overlays.mp4",
        ffmpeg=["ffmpeg"],
        movement_id="perfume-4",
        section="chat",
    )


def test_movement_four_declares_its_own_derivative():
    move = movement_four(thread())
    assert move["out_file"] == "renders/perfume-4.mp4"
    burned = {"fade_in", "fade_out", "fade", "plates", "overlay", "cards"}
    assert not burned & set(move)
    derivative = move["ending_derivative"]
    assert derivative["out_file"] == "renders/perfume-4-overlays.mp4"
    assert derivative["overlay_manifest"] == "stories/00-perfume-4-plates.json"
    assert derivative["overlay_section"] == ["chat_wolf", "chat"]


def test_the_derivative_composes_replacements_and_plates_in_one_encode(
        tmp_path, monkeypatch):
    cmd = chat_command(tmp_path, monkeypatch)
    joined = " ".join(cmd)
    graph = cmd[cmd.index("-filter_complex") + 1]
    # The source is read ONCE: swaps and words come out of a single encode.
    assert joined.count("media/yt_nightwish_perfume_of_the_timeless.mkv") == 1
    # The seven replacement clips are concat'd into the base the plates then
    # overlay -- wallpapers AND chat, never one without the other.
    assert "concat=n=12:v=1:a=0[base]" in graph
    assert "[base][ov0]overlay=0:0:eof_action=pass:" in graph
    assert "[v5]format=yuv420p[vout]" in graph
    assert "-c:a flac" in joined
    assert "afade" not in graph


def test_plate_inputs_are_numbered_after_the_artwork(tmp_path, monkeypatch):
    """Source is input 0, the seven artwork loops are 1..7, the six chat
    pills are 8..13. The graph and the argv must be the same ordering."""
    cmd = chat_command(tmp_path, monkeypatch)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "[8:v]format=rgba,setpts=PTS-STARTPTS+53.951/TB" in graph
    assert "[13:v]format=rgba,setpts=PTS-STARTPTS+65.236/TB" in graph
    inputs = [cmd[i + 1] for i, a in enumerate(cmd[:-1]) if a == "-i"]
    assert len(inputs) == 1 + 7 + 6
    assert inputs[0].endswith("yt_nightwish_perfume_of_the_timeless.mkv")
    assert inputs[1].endswith("renders/artwork/bluefin-day.png")
    assert inputs[3].endswith("renders/summit-plates/enemy_cu.jpg")
    assert inputs[4].endswith("renders/artwork/huntress.png")
    assert inputs[5].endswith("renders/artwork/duality-day.png")
    assert inputs[7].endswith("renders/artwork/eyes.png")
    assert inputs[8].endswith("plate_chat_loose_end.png")
    assert inputs[13].endswith("plate_chat_wolves.png")


def test_the_chat_windows_are_half_open_and_faded_inside(tmp_path):
    cmd = chat_command(tmp_path)
    graph = cmd[cmd.index("-filter_complex") + 1]
    by_id = {p["id"]: p for p in chat()["plates"]}
    assert "between(" not in graph
    for id_ in chat()["chat"]["plate_ids"]:
        card = by_id[id_]
        at = float(card["at"])
        end = at + float(card["dur"])
        assert f"enable='gte(t,{at:.3f})*lt(t,{end:.3f})'" in graph, card["id"]
        assert f"fade=t=in:st={at:.3f}:d={float(card['fade_in']):.3f}:alpha=1" \
            in graph, card["id"]
        fade_out_at = end - float(card["fade_out"])
        assert f"fade=t=out:st={fade_out_at:.3f}:" \
            f"d={float(card['fade_out']):.3f}:alpha=1" in graph, card["id"]


def test_the_chat_copy_is_verbatim_and_one_line_at_a_time():
    """The owner's six whale-shot lines, in the two groups he wrote, never
    edited -- and never overlapping, so no pill ghosts onto the next."""
    doc = chat()
    by_id = {p["id"]: p for p in doc["plates"]}
    plates = [by_id[id_] for id_ in doc["chat"]["plate_ids"]]
    assert [p["text"] for p in plates] == [
        "One more loose end",
        "You can't escape yourself",
        "You promised",
        "Fine",
        "Show them the minds",
        "Of the wolves",
    ]
    assert [p["speaker"] for p in plates] == [
        "Jill Castro", "Valerie", "Rafael", "castrojo", "LH", "Valerie"]
    assert all(p["kind"] == "chat" and p["position"] == "letterbox"
               and p["copy_source"] == "owner_supplied" for p in plates)
    for previous, current in zip(plates, plates[1:]):
        assert previous["at"] + previous["dur"] < current["at"]
    # act VI's pill shape: fade_out_at is the window's end minus fade_out.
    for p in plates:
        assert p["fade_out_at"] == pytest.approx(
            p["at"] + p["dur"] - p["fade_out"])


def test_the_exchange_sits_inside_the_measured_whale_shot():
    """The pills live inside one measured shot -- the divers and the whale
    skeleton, source 328.080 -> 343.080 -- and the last line is out 0.6 s
    before the cut so the cut is the picture's own."""
    doc = chat()
    window = doc["chat"]
    local_in = window["source_in"] - 274.240
    local_out = window["source_out"] - 274.240
    by_id = {p["id"]: p for p in doc["plates"]}
    plates = [by_id[id_] for id_ in window["plate_ids"]]
    assert plates[0]["at"] >= local_in
    assert plates[-1]["at"] + plates[-1]["dur"] <= local_out
    assert [p["id"] for p in plates] == window["plate_ids"]


def test_unresolved_speakers_carry_no_avatar():
    """Never guess a login for a real person: the unresolved three render
    the drawn crest, and the manifest records the gap."""
    doc = chat()
    by_speaker = {}
    for p in doc["plates"]:
        by_speaker.setdefault(p["speaker"], p)
    for name in ("Jill Castro", "Rafael", "LH"):
        assert "avatar" not in by_speaker[name], name
    unresolved = " ".join(doc["unresolved"])
    for name in ("Jill Castro", "Rafael", "LH"):
        assert name in unresolved



def test_chat_wolf_cue_is_exactly_at_local_17_163():
    """Rafael's programme note at 23:30 is locked to the movement-local
    seat derived from the old programme clock: 23:30 - 23:12.837 = 17.163.
    No avatar: Rafael has no resolved login on record.
    """
    doc = chat()
    by_id = {p["id"]: p for p in doc["plates"]}
    wolf = by_id["chat_wolf"]
    assert float(wolf["at"]) == pytest.approx(17.163)
    assert float(wolf["dur"]) == pytest.approx(3.0)
    assert float(wolf["fade_in"]) == pytest.approx(0.4)
    assert float(wolf["fade_out"]) == pytest.approx(0.25)
    assert float(wolf["fade_out_at"]) == pytest.approx(19.913)
    assert wolf["speaker"] == "Rafael"
    assert wolf["text"] == "What's a wolf?"
    assert wolf["kind"] == "chat"
    assert wolf["position"] == "letterbox"
    assert wolf["copy_source"] == "owner_supplied"
    assert "avatar" not in wolf


def test_chat_wolf_section_is_separate_from_whale_chat():
    doc = chat()
    assert doc["chat"]["plate_ids"] == [
        "chat_loose_end",
        "chat_escape",
        "chat_promised",
        "chat_fine",
        "chat_minds",
        "chat_wolves",
    ]
    assert doc["chat_wolf"]["plate_ids"] == ["chat_wolf"]


def test_default_sections_burn_all_seven_plates_in_one_encode(
        tmp_path, monkeypatch):
    """The derivative's ordered section list flattens to all seven plates
    in source-time order, in a single source encode."""
    monkeypatch.setattr(
        build_interludes, "art_path",
        lambda name: (REPO / name["file"]) if isinstance(name, dict)
        else build_interludes.ARTWORK_DIR / f"{name}.png")
    move = movement_four(thread())
    section = move["ending_derivative"]["overlay_section"]
    assert section == ["chat_wolf", "chat"]
    cmd = build_ending_overlays.command(
        chat(),
        str(THREAD),
        tmp_path / "plates",
        tmp_path / "perfume-4-overlays.mp4",
        ffmpeg=["ffmpeg"],
        movement_id="perfume-4",
        section=section,
    )
    joined = " ".join(cmd)
    graph = cmd[cmd.index("-filter_complex") + 1]
    # One read of the original source: no stacked encode.
    assert joined.count("media/yt_nightwish_perfume_of_the_timeless.mkv") == 1
    # Replacements are still composed into the same base chain.
    assert "concat=n=12:v=1:a=0[base]" in graph
    assert "[base][ov0]overlay=0:0:eof_action=pass:" in graph
    # Seven plates, numbered after the seven artwork inputs.
    inputs = [cmd[i + 1] for i, a in enumerate(cmd[:-1]) if a == "-i"]
    assert len(inputs) == 1 + 7 + 7
    assert inputs[0].endswith("yt_nightwish_perfume_of_the_timeless.mkv")
    plate_inputs = inputs[8:]
    assert [Path(p).name for p in plate_inputs] == [
        "plate_chat_wolf.png",
        "plate_chat_loose_end.png",
        "plate_chat_escape.png",
        "plate_chat_promised.png",
        "plate_chat_fine.png",
        "plate_chat_minds.png",
        "plate_chat_wolves.png",
    ]
    # chat_wolf sits at the movement-local seat 17.163.
    assert "[8:v]format=rgba,setpts=PTS-STARTPTS+17.163/TB" in graph
    assert "[14:v]format=rgba,setpts=PTS-STARTPTS+65.236/TB" in graph
    assert "enable='gte(t,17.163)*lt(t,20.163)'" in graph
    assert "-c:a flac" in joined
    assert "afade" not in graph


def test_chat_wolf_window_is_half_open_and_faded_inside(tmp_path, monkeypatch):
    monkeypatch.setattr(
        build_interludes, "art_path",
        lambda name: (REPO / name["file"]) if isinstance(name, dict)
        else build_interludes.ARTWORK_DIR / f"{name}.png")
    move = movement_four(thread())
    section = move["ending_derivative"]["overlay_section"]
    cmd = build_ending_overlays.command(
        chat(),
        str(THREAD),
        tmp_path / "plates",
        tmp_path / "perfume-4-overlays.mp4",
        ffmpeg=["ffmpeg"],
        movement_id="perfume-4",
        section=section,
    )
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "between(" not in graph
    assert "enable='gte(t,17.163)*lt(t,20.163)'" in graph
    assert "fade=t=in:st=17.163:d=0.400:alpha=1" in graph
    assert "fade=t=out:st=19.913:d=0.250:alpha=1" in graph


def test_a_checkout_with_no_cached_artwork_still_builds_a_valid_encode(
        tmp_path, monkeypatch):
    """The degrade the two tests above deliberately look past.

    `renders/artwork/` is fetched and gitignored, so a fresh checkout has
    none of it. Movement 4 must then play its own picture with the words
    still on it -- not fail, and above all not pass ``None`` to ffmpeg as an
    input path, which is what an unguarded `art_path` would do.
    """
    monkeypatch.setattr(build_interludes, "art_path", lambda name: None)
    cmd = chat_command(tmp_path)
    inputs = [cmd[i + 1] for i, a in enumerate(cmd[:-1]) if a == "-i"]
    assert "None" not in inputs
    assert len(inputs) == 1 + 6          # the source, and the six chat pills
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "concat=" not in graph        # nothing to concat: no replacements
    assert "[vout]" in graph and "[aout]" in graph

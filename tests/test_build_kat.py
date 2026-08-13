"""Act IV's committed record: the words, the windows, and the build it drives.

Act IV had no committed inputs at all (#152), so nothing could edit the words
on screen and nothing could tell whether a revision took. These tests guard the
record that fixed that. They are offline and need no footage: the manifest and
the generated ffmpeg command are both pure data.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import build_kat  # noqa: E402
from tools import plate  # noqa: E402


@pytest.fixture(scope="module")
def doc():
    return build_kat.load_manifest()


def test_manifest_renders_as_a_plate_manifest(doc):
    """plate.py loads it unmodified -- it is not a private format."""
    entries = plate.load_manifest(build_kat.MANIFEST)
    assert [e["id"] for e in entries] == [p["id"] for p in doc["plates"]]


def test_every_dialogue_plate_is_a_chat_pill_in_the_letterbox(doc):
    for cue in doc["plates"]:
        assert cue["kind"] == "chat"
        # The pill seats INSIDE the bottom matte, always on black, so it never
        # covers picture. Anything else is the lower-third row, which on this
        # letterboxed act lands 18px onto the frame.
        assert cue["position"] == "letterbox"


def test_the_words_are_the_owners(doc):
    """The copy is a RECORD of what shipped, reproduced, never re-authored."""
    assert [(c["speaker"], c["text"]) for c in doc["plates"]] == [
        ("kat", "Open telnet port?"),
        ("ian", "Look it up baby!"),
        ("tabbysable", "How come no one's shooting at you?"),
        ("cailyn-codes", "Security by hyperspace?"),
        ("kat", "Remember kids, cardio!"),
    ]


def test_no_two_plates_share_the_screen(doc):
    """One plate at a time -- plate.py enforces it, and so does the record."""
    windows = sorted((c["at"], c["at"] + c["dur"]) for c in doc["plates"])
    for (_, end), (start, _) in zip(windows, windows[1:]):
        assert start > end, f"{start} overlaps a plate still on screen at {end}"


def test_every_plate_lands_after_the_hero_reveal(doc):
    """The owner's rule for this act: nothing precedes the nameplate."""
    reveal = doc["reveal"]
    reveal_end = reveal["at"] + reveal["dur"]
    assert min(c["at"] for c in doc["plates"]) > reveal_end


def test_fade_out_finishes_inside_the_window(doc):
    for cue in [*doc["plates"], doc["reveal"]]:
        end = cue["at"] + cue["dur"]
        assert cue["fade_out_at"] + cue["fade_out"] == pytest.approx(end), cue["id"]
        assert cue["at"] + cue["fade_in"] <= cue["fade_out_at"], cue["id"]


def test_ians_answer_lands_on_the_measured_cut(doc):
    """The owner pinned the line to the cut where the camera starts shaking.

    That cut was measured at 14.833 and is in the record's cut list. Kat's
    question must clear BEFORE it and Ian's answer must start after, or the
    exchange no longer breaks on the shake.
    """
    cut = 14.833
    assert 14.83 in doc["cut_list"]
    kat, ian = doc["plates"][0], doc["plates"][1]
    assert kat["at"] + kat["dur"] < cut
    assert ian["at"] > cut


def test_the_delivered_variant_is_lossless_stereo(doc):
    """Prod/04 hardlinks the FLAC stereo master, not the AAC 5.1 sibling.

    run-kat.sh's own defaults built the OTHER file. A builder that inherited
    them would quietly replace a lossless master with a lossy one.
    """
    delivered = doc["encode"]["delivered"]
    assert delivered["acodec"] == "flac"
    assert delivered["surround"] is False
    assert "audio_bitrate" not in delivered, "a bitrate is meaningless for FLAC"


def test_the_delivered_command_carries_no_bitrate_and_no_upmix(doc):
    cmd, target = build_kat.build_command(doc, "/tmp/proj", "delivered",
                                          ffmpeg=["ffmpeg"])
    assert "-b:a" not in cmd
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "[apre]anull[aout]" in graph, "the bed reaches the encoder untouched"
    assert "pan=5.1" not in graph
    assert target.name == "wolves-kat-reveal-hq.mp4"


def test_the_51_variant_adds_only_an_lfe(doc):
    """The stereo mix passes through bit-exact; FC/BL/BR stay digital silence."""
    cmd, _ = build_kat.build_command(doc, "/tmp/proj", "variant_51",
                                     ffmpeg=["ffmpeg"])
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "pan=5.1|FL=c0|FR=c1" in graph
    assert "LFE=c0" in graph
    # ffmpeg's `surround` filter resynthesises the soundfield and adds ~43ms of
    # latency, which would desync audio from picture.
    assert "surround" not in graph


def test_every_cue_becomes_one_input_in_order(doc):
    cmd, _ = build_kat.build_command(doc, "/tmp/proj", "delivered",
                                     ffmpeg=["ffmpeg"])
    offsets = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-itsoffset"]
    assert offsets == [f"{float(c['at']):g}" for c in build_kat._cues(doc)]
    # source + five pills + the reveal + the bed
    assert cmd.count("-i") == len(doc["plates"]) + 3


def test_the_reveal_is_taken_from_the_project_not_rendered(doc):
    """Its copy is an authored Guardian identity, reproduced, never written."""
    assert doc["reveal"]["file"]
    assert "_not_repo_rendered" in doc["reveal"]
    cmd, _ = build_kat.build_command(doc, "/tmp/proj", "delivered",
                                     ffmpeg=["ffmpeg"])
    assert "/tmp/proj/render/reveal-options/kat-reveal.png" in cmd


def test_the_letterbox_rect_is_measured_not_probed(doc):
    """detect_picture probes at 40s and this act is 34s, so it finds nothing.

    The rect is recorded instead, which is both reproducible and offline.
    """
    assert doc["film_sec"] < 40.0
    assert build_kat.picture_rect(doc) == (0, 140, 1920, 800)


def test_the_picture_rect_seats_the_pill_in_the_matte(doc):
    """The measured rect is what puts the pill on black rather than 18px up."""
    x, y, w, h = build_kat.picture_rect(doc)
    pill = plate.render_plate(dict(doc["plates"][0]))
    frame = plate.place(pill, position="letterbox", picture=(x, y, w, h))
    top, bottom = frame.getbbox()[1], frame.getbbox()[3]
    assert top >= y + h, "the pill must start below the picture, on the matte"
    assert bottom <= 1080


def test_parse_picture_rejects_nonsense():
    assert plate.parse_picture("0,140,1920,800") == (0, 140, 1920, 800)
    for bad in ("0,140,1920", "a,b,c,d", "0,140,0,800", "0,140,1920,-1"):
        with pytest.raises(ValueError):
            plate.parse_picture(bad)


def test_act_iv_is_declared_repo_driven():
    """The delivery map must agree that act IV now has inputs."""
    doc = json.loads((REPO_ROOT / "stories" / "megacut"
                      / "delivery.json").read_text(encoding="utf-8"))
    act = doc["masters"]["IV"]
    assert act["sources"], "act IV is repo-driven now -- #152"
    assert "stories/04-kat-plates.json" in act["sources"]
    assert "scripts/build_kat.py" in act["sources"]
    assert "sources_note" not in act, "that note said it had no inputs"

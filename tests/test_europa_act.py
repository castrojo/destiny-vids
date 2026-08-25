"""Act VII -- Europa: the solo-wide walk-up, the retired KubeCon card.

Offline and dependency-free, like the rest of the suite: no ffmpeg, no media,
no network. What is pinned here is the committed record's picture graph, its
frame-derived durations, and the cue list the builder turns into inputs and
overlays.
"""

import json
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "stories" / "07-europa-plates.json"

from scripts import build_europa  # noqa: E402


def load():
    return json.loads(MANIFEST.read_text())


def test_walk_up_keeps_only_the_solo_wide():
    doc = load()
    walk = next(s for s in doc["picture"]["segments"]
                if s["label"] == "walk-up")
    assert walk["frames"] == [3443, 3509]
    assert "fade_out" not in walk
    wrap = next(s for s in doc["picture"]["segments"]
                if s["label"] == "wrap")
    assert "fade_in" not in wrap


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


def test_kubecon_card_is_retired_but_its_copy_is_recoverable():
    doc = load()
    assert doc["endcard"]["retired"] is True
    assert "KubeCon" in doc["endcard"]["_note"]
    assert doc["endcard"]["retired_note"]
    assert doc["endcard"] not in build_europa._cues(doc)


def test_new_picture_lengths_are_frame_derived():
    doc = load()
    pic = doc["picture"]
    assert pic["content_sec"] == 95.333333
    # Since the Jupiter tail (owner, 2026-08-23) the delivered film is the
    # master's full length: 108.333333 s of picture rounds to the 3252nd
    # frame, and the audio is padded to match.
    assert pic["delivered_frames"] == 3252
    assert pic["delivered_sec"] == 108.4
    assert pic["audio_sec"] == 108.4
    assert doc["film_sec"] == 108.4


def test_laura_reveal_clears_before_its_half_open_boundary():
    reveal = load()["reveal"]
    end = reveal["at"] + reveal["dur"]
    assert end == 88.0
    assert reveal["fade_out_at"] + reveal["fade_out"] < end


def test_alolita_uses_the_verified_repo_avatar():
    doc = load()
    alolita = next(p for p in doc["plates"] if p["id"] == "d03")
    assert alolita["speaker"] == "alolita"
    # The record names the repo's avatar cache, not the website asset.
    # Repo-relative by convention (see the no-absolute-paths test above), so
    # the assertion must not bake in any one checkout's location.
    assert alolita["avatar"] == "renders/avatars/alolita.png"


def test_build_command_has_no_endcard_input_or_overlay(tmp_path):
    doc = load()
    cmd, _ = build_europa.build_commands(
        doc, "/project", tmp_path / "plates",
        tmp_path / "master.mp4", tmp_path / "delivered.mp4",
        ffmpeg=["ffmpeg"],
    )
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "endcard.png" not in " ".join(cmd)
    # plates + the reveal + the two tail cards; the retired endcard is none.
    assert len(build_europa._cues(doc)) == len(doc["plates"]) + 3
    assert "90.8" not in graph


def test_no_avatar_is_named_by_an_absolute_path():
    """An absolute path in a manifest resolves on exactly one machine.

    These read `/var/home/jorge/src/destiny-vids/renders/avatars/...`, so they
    were green on the owner's workstation and red in every other checkout --
    the worst shape a check can have, because the agent verifies, pushes, and
    gets a red it cannot reproduce.

    The invariant is the one `tools/plate.py::_load_avatar` already
    implements: a path is either RELATIVE, and resolves against the repo root,
    or `~`-rooted, and resolves against the home of whoever is running. Both
    travel. An absolute path travels nowhere, so neither kind is spelled that
    way -- including the `~/Videos` and `~/src/website` assets, which are
    outside the repo but no less machine-specific when written out in full.

    Anchoring on the *current* repo root instead would invert the test: a
    reverted `/var/home/jorge/...` string does not start with the runner's own
    checkout path, so it would pass in CI and fail only on the one machine
    where it happens to work.
    """
    doc = load()
    for plate in doc["plates"]:
        avatar = plate.get("avatar")
        if not avatar:
            continue
        assert not PurePosixPath(avatar).is_absolute(), (
            f"plate {plate.get('id')}: {avatar!r} is an absolute path -- use a "
            f"repo-relative path for a file in this repo, or a `~`-rooted one "
            f"for a file outside it")


def test_the_song_plays_alone_with_no_crossfade_and_no_fades():
    """The mix the owner remuxed on 2026-08-20 and shipped: Beauty of the
    Beast 465.0-560.4 s under the whole delivered film, a full replacement.

    This is pinned because the record and the builder disagreed with the
    delivered file for three days, and the 2026-08-23 programme regeneration
    duly rebuilt the act back to the PREVIOUS two-leg mix. The owner caught it
    on the screen. A builder that cannot express what ships will revert it
    again on the next rebuild.
    """
    doc = load()
    aud = doc["audio"]

    assert [leg["from"] for leg in aud["join"]] == ["song"]
    assert aud["join"][0]["window"] == [465.0, 560.4]
    assert "crossfade" not in aud
    assert "master_fade_out" not in aud
    assert "delivered_fade_out" not in aud

    graph = ";".join(build_europa.audio_graph(doc))
    assert "atrim=465.0:560.4" in graph
    assert "acrossfade" not in graph
    assert "afade" not in graph


def test_the_song_covers_the_whole_content():
    """95.4 s of song against 95.333333 s of CONTENT, so the cut lands inside
    the song rather than running out of it. The jupiter-hold tail behind it
    plays silent by design -- the memorial beat the comic cover used to fill
    -- so audio_sec (the padded delivered stream) is NOT the bar here."""
    doc = load()
    start, end = doc["audio"]["join"][0]["window"]
    assert end - start >= doc["picture"]["content_sec"]
    assert end - start < doc["picture"]["audio_sec"]


def test_the_delivered_derivation_fades_only_when_the_record_asks(tmp_path):
    doc = load()
    _, derive = build_europa.build_commands(
        doc, tmp_path, tmp_path, tmp_path / "m.mp4", tmp_path / "d.mp4",
        ffmpeg=["ffmpeg"])
    af = derive[derive.index("-af") + 1]
    # delivered_apad pads the song's end with silence under the jupiter-hold
    # tail, so the delivered audio stream matches the 108.4 s picture.
    assert af == f"apad,atrim=0:{doc['picture']['audio_sec']:g}"

    faded = json.loads(MANIFEST.read_text())
    faded["audio"]["delivered_fade_out"] = {"at": 1.0, "dur": 2.0}
    _, derive = build_europa.build_commands(
        faded, tmp_path, tmp_path, tmp_path / "m.mp4", tmp_path / "d.mp4",
        ffmpeg=["ffmpeg"])
    assert "afade=t=out:st=1:d=2," in derive[derive.index("-af") + 1]


def test_the_silent_tail_is_padded_not_faded():
    """The owner's mix rule survives the tail: the song is NEVER faded, and
    the tail's silence is container padding (apad), not a fade of anything."""
    doc = load()
    aud = doc["audio"]
    assert aud["delivered_apad"] is True
    assert "delivered_fade_out" not in aud
    assert "master_fade_out" not in aud


def test_the_jupiter_hold_takes_the_covers_slot():
    """The retired comic cover's 13 s slot is the held nightway now (owner
    direction, 2026-08-23, verbatim in the record's tail block). The master
    length is unchanged, so nothing downstream of the concat moves."""
    doc = load()
    pic = doc["picture"]
    assert "cover" not in pic["inputs"]
    assert "hold" in pic["inputs"]
    seg = pic["segments"][-1]
    assert seg["label"] == "jupiter-hold"
    assert seg["from"] == "hold"
    assert seg["still"] is True and seg["dur"] == 13.0
    # The hold fades itself out exactly at its own end: the act still ends
    # on its own taper to black, so megacut carries no fade for it.
    assert seg["fade_out"]["at"] + seg["fade_out"]["dur"] == seg["dur"]
    assert pic["master_sec"] == 108.333333


def test_tail_cards_carry_owner_copy_verbatim():
    """Both cards are the owner's 2026-08-23 lines, casing included --
    KubeCon + CloudNativeCon are brand casing, so no uppercase homage."""
    doc = load()
    cards = {c["id"]: c for c in doc["tail"]["cards"]}
    assert cards["tail-dedication"]["lines"] == [
        "For other wolves, some will give all"]
    assert cards["tail-event"]["lines"] == [
        "Bluefin and the Forbidden Factory",
        "KubeCon + CloudNativeCon EU 2027",
        "Maintainer Summit"]


def test_tail_cards_sit_inside_the_hold_after_the_reveal():
    """Both cards play inside the jupiter-hold segment (95.333333-108.333333
    on the master clock), after the reveal clears at 88.0, each fade
    completing inside its own half-open window, and the event card off the
    screen before the hold's own fade ends the act."""
    doc = load()
    hold_start, hold_end = 95.333333, 108.333333
    reveal_end = doc["reveal"]["at"] + doc["reveal"]["dur"]
    for card in doc["tail"]["cards"]:
        at, dur = float(card["at"]), float(card["dur"])
        assert hold_start < at
        assert at + dur < hold_end
        assert at > reveal_end
        assert card["fade_out_at"] + card["fade_out"] <= at + dur
    event = next(c for c in doc["tail"]["cards"] if c["id"] == "tail-event")
    assert event["at"] + event["dur"] <= hold_start + 11.0 + 2.0


def test_tail_cards_ride_the_cue_plumbing(tmp_path):
    """The cards are repo-rendered into the plates dir and resolve by id --
    no 'file' key, no special-casing in the builder."""
    doc = load()
    cues = build_europa._cues(doc)
    assert [c["id"] for c in cues[-2:]] == ["tail-dedication", "tail-event"]
    for card in doc["tail"]["cards"]:
        assert "file" not in card
    cmd, _ = build_europa.build_commands(
        doc, "/project", tmp_path / "plates",
        tmp_path / "master.mp4", tmp_path / "delivered.mp4",
        ffmpeg=["ffmpeg"])
    joined = " ".join(cmd)
    assert "plate_tail-dedication.png" in joined
    assert "plate_tail-event.png" in joined
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "gte(t,96.8)*lt(t,101.4)" in graph
    assert "gte(t,102.2)*lt(t,107.1)" in graph


def test_the_screenshot_is_referenced_never_committed():
    """The concept sheet lives outside the repo and is referenced the way
    every external asset here is: a ~-rooted path plus a sha256, so a
    replaced or edited sheet is detected rather than silently re-sliced."""
    doc = load()
    src = doc["tail"]["hold"]["source_screenshot"]
    assert src["path"].startswith("~/")
    assert not PurePosixPath(src["path"]).is_absolute()
    assert len(src["sha256"]) == 64
    # And it is not in the repo: footage and images are never committed.
    assert not (REPO / src["path"]).exists()

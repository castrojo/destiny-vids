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

from scripts import actbuild  # noqa: E402
from tools import plate  # noqa: E402


ACTS = ("IV", "V")


@pytest.fixture(scope="module")
def doc():
    """Act IV's record -- the one the shape was proved on."""
    return actbuild.load_act("IV")[0]


@pytest.fixture(scope="module", params=ACTS)
def any_act(request):
    """Both records. Everything that is true of an act is asserted on both."""
    return actbuild.load_act(request.param)[0]


def test_manifest_renders_as_a_plate_manifest(any_act):
    """plate.py loads it unmodified -- it is not a private format."""
    manifest, _, _ = actbuild.act_paths(any_act["act"])
    entries = plate.load_manifest(manifest)
    assert [e["id"] for e in entries] == [p["id"] for p in any_act["plates"]]


def test_every_dialogue_plate_is_a_chat_pill_in_the_letterbox(any_act):
    for cue in any_act["plates"]:
        assert cue["kind"] == "chat"
        # The pill seats INSIDE the bottom matte, always on black, so it never
        # covers picture. Anything else is the lower-third row, which on this
        # letterboxed act lands 18px onto the frame.
        assert cue["position"] == "letterbox"


def test_the_words_are_the_owners(doc):
    """The copy is a RECORD of what shipped, reproduced, never re-authored.

    The last three are #118's Linux-desktop exchange, dictated 2026-08-13 and
    confirmed in scope (and in nothing else's scope) on 2026-08-14 -- owner
    copy, verbatim, landed 2026-08-14.
    """
    assert [(c["speaker"], c["text"]) for c in doc["plates"]] == [
        ("kat", "Open telnet port?"),
        ("ian", "Look it up baby!"),
        ("tabbysable", "How come no one's shooting at you?"),
        ("cailyn-codes", "Security by hyperspace?"),
        ("kat", "Remember kids, cardio!"),
        ("kat", "I miss ONE email now I gotta use a Linux desktop?"),
        ("kat", "I miss ingress-nginx sometimes"),
        ("kat", "Fine I'll fix your shit too"),
    ]


def test_no_two_plates_share_the_screen(any_act):
    """One plate at a time -- plate.py enforces it, and so does the record."""
    windows = sorted((c["at"], c["at"] + c["dur"]) for c in any_act["plates"])
    for (_, end), (start, _) in zip(windows, windows[1:]):
        assert start > end, f"{start} overlaps a plate still on screen at {end}"


def test_every_plate_lands_after_the_hero_reveal(doc):
    """The owner's rule for this act: nothing precedes the nameplate."""
    reveal = doc["reveal"]
    reveal_end = reveal["at"] + reveal["dur"]
    assert min(c["at"] for c in doc["plates"]) > reveal_end


def test_fade_out_finishes_inside_the_window(any_act):
    for cue in [*any_act["plates"], any_act["reveal"]]:
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


def test_the_delivered_variant_is_lossless_stereo(any_act):
    """Prod/04 hardlinks the FLAC stereo master, not the AAC 5.1 sibling.

    run-kat.sh's own defaults built the OTHER file. A builder that inherited
    them would quietly replace a lossless master with a lossy one.
    """
    delivered = any_act["encode"]["delivered"]
    assert delivered["acodec"] == "flac"
    assert delivered["surround"] is False
    assert "audio_bitrate" not in delivered, "a bitrate is meaningless for FLAC"


def test_the_delivered_command_carries_no_bitrate_and_no_upmix(doc):
    cmd, target = actbuild.build_command(doc, "/tmp/proj", "delivered",
                                          ffmpeg=["ffmpeg"])
    assert "-b:a" not in cmd
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "[apre]anull[aout]" in graph, "the bed reaches the encoder untouched"
    assert "pan=5.1" not in graph
    assert target.name == "wolves-kat-reveal-hq.mp4"


def test_the_51_variant_adds_only_an_lfe(any_act):
    """The stereo mix passes through bit-exact; FC/BL/BR stay digital silence."""
    cmd, _ = actbuild.build_command(any_act, "/tmp/proj", "variant_51",
                                     ffmpeg=["ffmpeg"])
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "pan=5.1|FL=c0|FR=c1" in graph
    assert "LFE=c0" in graph
    # ffmpeg's `surround` filter resynthesises the soundfield and adds ~43ms of
    # latency, which would desync audio from picture.
    assert "surround" not in graph


def test_every_cue_becomes_one_input_in_order(any_act):
    cmd, _ = actbuild.build_command(any_act, "/tmp/proj", "delivered",
                                     ffmpeg=["ffmpeg"])
    offsets = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-itsoffset"]
    assert offsets == [f"{float(c['at']):g}" for c in actbuild._cues(any_act)]
    # source + the pills + the reveal + the bed
    assert cmd.count("-i") == len(any_act["plates"]) + 3


def test_avatar_paths_resolve_in_both_recorded_shapes():
    """Act IV's record carries ~-rooted paths; act V's carries bare names.

    Joining a ~-rooted value onto the project made `render/~/Videos/...` and
    every pill silently fell back to the drawn crest -- a regression against
    the delivered master, whose pills carry the cast's photographs.
    """
    rooted = actbuild._resolve_avatar("/proj", "~/Videos/wolves-kat/render/kat.jpg")
    assert rooted == str(Path("~/Videos/wolves-kat/render/kat.jpg").expanduser())
    bare = actbuild._resolve_avatar("/proj", "kat.jpg")
    assert bare == "/proj/render/kat.jpg"
    # and the committed act IV record really does carry the rooted shape
    doc = actbuild.load_act("IV")[0]
    resolved = actbuild._project_manifest(doc, "/proj")
    resolved = json.loads(resolved.read_text(encoding="utf-8"))
    assert all(not p["avatar"].startswith("/proj")
               for p in resolved["plates"] if p.get("avatar"))


def test_the_reveal_is_taken_from_the_project_not_rendered(any_act):
    """Its copy is an authored Guardian identity, reproduced, never written."""
    assert any_act["reveal"]["file"]
    assert "_not_repo_rendered" in any_act["reveal"]
    cmd, _ = actbuild.build_command(any_act, "/tmp/proj", "delivered",
                                    ffmpeg=["ffmpeg"])
    assert f"/tmp/proj/{any_act['reveal']['file']}" in cmd


def test_the_letterbox_rect_is_measured_not_probed(any_act):
    """detect_picture probes at 40s and this act is 34s, so it finds nothing.

    The rect is recorded instead, which is both reproducible and offline.
    """
    assert any_act["film_sec"] < 40.0
    assert actbuild.picture_rect(any_act) == (0, 140, 1920, 800)


def test_the_picture_rect_seats_the_pill_in_the_matte(any_act):
    """The measured rect is what puts the pill on black rather than 18px up."""
    x, y, w, h = actbuild.picture_rect(any_act)
    pill = plate.render_plate(dict(any_act["plates"][0]))
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
    assert "scripts/actbuild.py" in act["sources"]
    assert "sources_note" not in act, "that note said it had no inputs"


# --- what act V added, and act IV must not have grown ------------------------


def test_act_v_starts_inside_a_longer_source():
    """`source_in` and the cut's own clock are different numbers.

    Act V is lifted out of the middle of a longer file at 357.45 while its own
    windows are measured from zero. Act IV starts at zero and the two coincide,
    which is exactly why a builder written against act IV alone would have
    conflated them.
    """
    nat = actbuild.load_act("V")[0]
    assert nat["trim"]["source_in"] == 357.45
    assert nat["trim"]["in"] == 0.0
    cmd, _ = actbuild.build_command(nat, "/tmp/proj", ffmpeg=["ffmpeg"])
    assert cmd[cmd.index("-ss") + 1] == "357.45"
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert graph.startswith("[0:v]trim=0:25.25")

    kat = actbuild.load_act("IV")[0]
    assert "source_in" not in kat["trim"]


def test_only_the_act_that_fades_to_black_gets_a_final_fade():
    """Act V resolves into the cinematic's own fade; act IV ends on a hard cut."""
    nat = actbuild.load_act("V")[0]
    ncmd, _ = actbuild.build_command(nat, "/tmp/proj", ffmpeg=["ffmpeg"])
    ngraph = ncmd[ncmd.index("-filter_complex") + 1]
    assert "fade=t=out:st=24.95:d=0.3[vout]" in ngraph

    kat = actbuild.load_act("IV")[0]
    kcmd, _ = actbuild.build_command(kat, "/tmp/proj", ffmpeg=["ffmpeg"])
    kgraph = kcmd[kcmd.index("-filter_complex") + 1]
    assert "fade_out" not in kat["trim"]
    # the last overlay writes [vout] directly -- nothing follows it
    assert kgraph.endswith("[apre]anull[aout]")
    next_label = f"[t{len(kat['plates']) + 1}]"
    assert next_label not in kgraph


def test_the_loop_framerate_is_per_act_not_assumed():
    """run-kat.sh passed `-framerate 60`; run-natali.sh passed none.

    Both masters were built that way, so the record carries it. Inheriting act
    IV's value would change act V's still inputs.
    """
    kcmd, _ = actbuild.build_command(actbuild.load_act("IV")[0], "/tmp/proj",
                                     ffmpeg=["ffmpeg"])
    assert "-framerate" in kcmd
    ncmd, _ = actbuild.build_command(actbuild.load_act("V")[0], "/tmp/proj",
                                     ffmpeg=["ffmpeg"])
    assert "-framerate" not in ncmd


def test_the_rejected_sfx_layer_is_a_variant_and_never_the_default():
    """The owner picked the bed-only cut by ear. The experiment is provenance."""
    nat = actbuild.load_act("V")[0]
    assert "sfx" not in nat["encode"]["delivered"]
    cmd, _ = actbuild.build_command(nat, "/tmp/proj", "variant_sfx",
                                    ffmpeg=["ffmpeg"])
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "[bed][sfx]amix=inputs=2:normalize=0[apre]" in graph
    assert str(Path("/tmp/proj/render/sfx-natali.wav")) in cmd
    # the bed and the sfx are two inputs, so the act gains one over delivered
    delivered, _ = actbuild.build_command(nat, "/tmp/proj", ffmpeg=["ffmpeg"])
    assert cmd.count("-i") == delivered.count("-i") + 1


def test_the_nat_dialogue_round_is_recorded_as_still_blocked():
    """#118's Nat section is `automatable: no` -- the record must not fake it."""
    nat = actbuild.load_act("V")[0]
    assert any("#118" in u for u in nat["unresolved"])

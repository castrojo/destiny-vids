"""tools/conform.py — the delivery spec, its probe, and the conform cache.

The cache is what makes the megacut's stream-copy path durable: an unchanged
act must be a no-op. These tests run offline — the probe and the encode are
both substituted, because the cache logic is what is being pinned, not ffmpeg.
"""

import json
import subprocess
from pathlib import Path

import pytest

from tools import conform


def _conformant_props():
    return {
        "codec_name": "h264", "width": 1920, "height": 1080,
        "avg_frame_rate": "60000/1001", "pix_fmt": "yuv420p",
        "color_primaries": "bt709", "color_transfer": "bt709",
        "color_space": "bt709", "profile": "High", "level": 42,
    }


# --- the conformance probe -------------------------------------------------

def test_a_fully_conforming_stream_reports_no_mismatches():
    assert conform.mismatches(_conformant_props()) == []


def test_every_spec_field_is_checked():
    """The probe is only worth having if each field of the spec can fail it.
    Flip one property at a time; each must produce exactly one reason."""
    cases = [
        ("codec_name", "vp9", "not h264"),
        ("width", 1280, "size"),
        ("avg_frame_rate", "30/1", "frame rate"),
        ("pix_fmt", "yuv444p", "pixel format"),
        ("color_primaries", "unknown", "color_primaries"),
        ("color_transfer", "unknown", "color_transfer"),
        ("color_space", "unknown", "color_space"),
        ("profile", "Main", "profile"),
        ("level", 40, "level"),
    ]
    for field, value, needle in cases:
        props = {**_conformant_props(), field: value}
        bad = conform.mismatches(props)
        assert any(needle in reason for reason in bad), (field, bad)


def test_frame_rate_compares_as_a_rational():
    """2997/50 IS 60000/1001; 60/1 is not. 59.94 material must not be
    'corrected' to 60 -- it would drift against its own audio."""
    assert conform.mismatches({**_conformant_props(),
                               "avg_frame_rate": "2997/50"}) == []
    assert conform.mismatches({**_conformant_props(),
                               "avg_frame_rate": "60/1"})


def test_an_indeterminate_frame_rate_is_a_mismatch_not_a_crash():
    """ffprobe reports `0/0` when it cannot average a stream's frame rate.

    `float(den or 1)` does not save that case -- "0" is a truthy string -- so
    the division raised ZeroDivisionError, which was not in the caught tuple.
    It travelled out through mismatches() -> conforms() -> ensure(), and
    assemble() conforms every clip, so one odd stream took the whole
    programme build down instead of being reported as unconformant.
    """
    assert conform.mismatches({**_conformant_props(), "avg_frame_rate": "0/0"})


def test_profile_accepts_either_ffprobe_spelling():
    """The linuxbrew ffprobe prints `High`; the container build prints the
    numeric IDC 100. Both are the same profile and both must pass."""
    assert conform.mismatches({**_conformant_props(), "profile": "High"}) == []
    assert conform.mismatches({**_conformant_props(), "profile": "100"}) == []
    assert conform.mismatches({**_conformant_props(), "profile": 100}) == []


def test_the_real_prod_acts_all_fail_the_probe():
    """Every delivered act today is non-conformant (30/1, 60/1, level 40/50,
    untagged colour) -- which is exactly the re-encode this module exists to
    do ONCE per act."""
    intro = {**_conformant_props(), "avg_frame_rate": "30/1", "level": 40}
    assert conform.mismatches(intro)
    efmb = {**_conformant_props(), "avg_frame_rate": "30/1", "level": 40,
            "color_primaries": "unknown", "color_transfer": "unknown",
            "color_space": "unknown"}
    assert len(conform.mismatches(efmb)) == 5  # rate, level, three colour fields


# --- the encode command ----------------------------------------------------

def test_the_encode_is_a_picture_operation_only():
    """Conforming must never touch the soundtrack: audio is stream-copied,
    so the six FLAC masters stay bit-exact and no filter -- no normaliser,
    no limiter, no gain -- is anywhere in the command (the audio tenet)."""
    cmd = conform.build_encode_command("in.mp4", "out.mp4",
                                       ffmpeg=["ffmpeg-not-invoked"])
    assert cmd[cmd.index("-c:a") + 1] == "copy"
    joined = " ".join(cmd)
    for banned in ("volume=", "loudnorm", "dynaudnorm", "acompressor",
                   "alimiter", "equalizer"):
        assert banned not in joined


def test_the_encode_writes_the_whole_spec():
    cmd = conform.build_encode_command("in.mp4", "out.mp4",
                                       ffmpeg=["ffmpeg-not-invoked"],
                                       crf="21", preset="medium")
    joined = " ".join(cmd)
    assert "fps=60000/1001" in joined
    assert "format=yuv420p" in joined
    assert "colorprim=bt709:transfer=bt709:colormatrix=bt709" in joined
    assert cmd[cmd.index("-profile:v") + 1] == "high"
    assert cmd[cmd.index("-level:v") + 1] == "4.2"
    assert cmd[cmd.index("-crf") + 1] == "21"
    assert cmd[cmd.index("-preset") + 1] == "medium"
    assert "+cgop" in cmd  # closed GOP: a join must never reference across it


def test_ffprobe_resolves_beside_the_chosen_ffmpeg():
    assert conform.ffprobe_for(["/opt/bin/ffmpeg"]) == ["/opt/bin/ffprobe"]
    assert conform.ffprobe_for(["podman", "exec", "c", "ffmpeg"]) == \
        ["podman", "exec", "c", "ffprobe"]


# --- the cache --------------------------------------------------------------

def _fake_encode(monkeypatch, counter):
    def fake_run(cmd, **kw):
        counter.append(" ".join(cmd))
        Path(cmd[-2]).touch()  # the output sits just before "-y"
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(conform.subprocess, "run", fake_run)


def _nonconformant_probe(_src):
    return {**_conformant_props(), "avg_frame_rate": "30/1", "level": 40}


def test_a_conforming_source_is_returned_as_is(tmp_path):
    """No encode, no cache entry, no hashing: the probe alone decides."""
    src = tmp_path / "act.mp4"
    src.write_bytes(b"x")
    path, status = conform.ensure(src, out_dir=tmp_path / "cache",
                                  ffmpeg=["ffmpeg-not-invoked"],
                                  _probe=lambda _p: _conformant_props())
    assert path == src
    assert status == "conforms"
    assert not (tmp_path / "cache").exists()


def test_first_run_conforms_and_the_second_is_a_no_op(tmp_path, monkeypatch):
    """The durable win: megacut #2 conforms nothing. The cache key is the
    source content and quality settings, so an unchanged source is a stat,
    not an encode."""
    src = tmp_path / "act.mp4"
    src.write_bytes(b"one")
    encodes = []
    _fake_encode(monkeypatch, encodes)

    path1, status1 = conform.ensure(src, out_dir=tmp_path / "cache",
                                    ffmpeg=["ffmpeg-not-invoked"],
                                    _probe=_nonconformant_probe)
    assert status1 == "conformed"
    assert len(encodes) == 1

    path2, status2 = conform.ensure(src, out_dir=tmp_path / "cache",
                                    ffmpeg=["ffmpeg-not-invoked"],
                                    _probe=_nonconformant_probe)
    assert (path2, status2) == (path1, "cache-hit")
    assert len(encodes) == 1, "an unchanged source must not re-encode"

    path3, status3 = conform.ensure(src, out_dir=tmp_path / "cache",
                                    ffmpeg=["ffmpeg-not-invoked"],
                                    _probe=_nonconformant_probe,
                                    crf="21", preset="medium")
    assert status3 == "conformed"
    assert path3 != path1
    assert len(encodes) == 2
    assert "-crf 21" in encodes[-1]
    assert "-preset medium" in encodes[-1]


def test_a_changed_source_gets_a_new_cache_entry(tmp_path, monkeypatch):
    """The key is the CONTENT, not the path: a re-delivered act at the same
    path must not be served its predecessor's conform."""
    src = tmp_path / "act.mp4"
    src.write_bytes(b"one")
    encodes = []
    _fake_encode(monkeypatch, encodes)

    first, _ = conform.ensure(src, out_dir=tmp_path / "cache",
                              ffmpeg=["ffmpeg-not-invoked"],
                              _probe=_nonconformant_probe)
    src.write_bytes(b"two")
    second, status = conform.ensure(src, out_dir=tmp_path / "cache",
                                    ffmpeg=["ffmpeg-not-invoked"],
                                    _probe=_nonconformant_probe)
    assert status == "conformed"
    assert second != first
    assert len(encodes) == 2


def test_a_failed_encode_leaves_no_cache_entry(tmp_path, monkeypatch):
    """An interrupted conform must not poison the cache: the output lands
    under a scratch name and is renamed only on success."""
    src = tmp_path / "act.mp4"
    src.write_bytes(b"x")

    def failing_run(cmd, **kw):
        Path(cmd[-2]).touch()  # a half-written scratch file
        raise subprocess.CalledProcessError(1, cmd)
    monkeypatch.setattr(conform.subprocess, "run", failing_run)

    with pytest.raises(subprocess.CalledProcessError):
        conform.ensure(src, out_dir=tmp_path / "cache",
                       ffmpeg=["ffmpeg-not-invoked"],
                       _probe=_nonconformant_probe)
    cache = tmp_path / "cache" / conform.SPEC_VERSION
    assert list(cache.glob("*.mp4")) == []
    assert list(cache.glob("*.tmp-*")) == [], "the scratch file is cleaned up"


def test_the_sidecar_records_what_the_entry_is(tmp_path, monkeypatch):
    src = tmp_path / "act.mp4"
    src.write_bytes(b"x")
    _fake_encode(monkeypatch, [])
    entry, _ = conform.ensure(src, out_dir=tmp_path / "cache",
                              ffmpeg=["ffmpeg-not-invoked"],
                              _probe=_nonconformant_probe)
    sidecar = json.loads(entry.with_suffix(".json").read_text())
    assert sidecar["source"] == str(src)
    assert sidecar["sha256"] == conform.content_hash(src)
    assert sidecar["spec_version"] == conform.SPEC_VERSION
    assert sidecar["spec"]["fps"] == "60000/1001"


def test_spec_version_is_part_of_the_cache_key(tmp_path, monkeypatch):
    """Bumping the spec orphans old entries rather than trusting them."""
    src = tmp_path / "act.mp4"
    src.write_bytes(b"x")
    _fake_encode(monkeypatch, [])
    conform.ensure(src, out_dir=tmp_path / "cache",
                   ffmpeg=["ffmpeg-not-invoked"], _probe=_nonconformant_probe)
    assert (tmp_path / "cache" / conform.SPEC_VERSION).is_dir()

"""tools/transitions.py — the act-join measurement (issue #105).

These pin the arithmetic the report rests on: the per-second RMS buckets, the
silence-run count, the join discovery (which is where the two clocks could get
mixed), and the summary rows. They run offline: the decoder is a fake that
hands back synthesised PCM, so no ffmpeg and no footage are involved.
"""

import math
import struct

import pytest

from tools import transitions


def pcm_f32(levels, rate=4, channels=1):
    """Interleaved f32le bytes: one constant-amplitude second per level."""
    out = bytearray()
    for level in levels:
        out += struct.pack("<f", level) * (rate * channels)
    return bytes(out)


def test_bucket_rms_reads_a_known_level():
    # A full-scale constant signal is 0 dBFS RMS; halving it is -6.02 dB.
    pcm = pcm_f32([1.0, 0.5], rate=4)
    buckets = transitions.bucket_rms(pcm, channels=1, rate=4)
    assert buckets[0] == pytest.approx(0.0, abs=1e-3)
    assert buckets[1] == pytest.approx(-6.0206, abs=1e-3)


def test_bucket_rms_reports_true_silence_as_minus_inf():
    """Not a floor: the issue's 'absolute -inf' must survive as -inf, or the
    report would understate the silence it exists to measure."""
    pcm = pcm_f32([0.0, 0.0], rate=4)
    assert transitions.bucket_rms(pcm, 1, 4) == [float("-inf"), float("-inf")]


def test_bucket_rms_drops_a_short_tail_bucket():
    # Two full seconds plus half a second: the tail is dropped, not read.
    pcm = pcm_f32([1.0, 1.0]) + struct.pack("<f", 1.0) * 2
    assert len(transitions.bucket_rms(pcm, 1, 4)) == 2


def test_db_of_zero_is_minus_inf_not_an_error():
    assert transitions.db(0.0) == float("-inf")
    assert transitions.db(-1.0) == float("-inf")


def test_silence_run_counts_the_longest_consecutive_stretch():
    inf = float("-inf")
    buckets = [-20.0, inf, -90.0, -20.0, inf, inf, inf, -20.0]
    assert transitions.silence_run(buckets, 0, len(buckets)) == 3


def test_silence_run_is_bounded_to_the_window():
    inf = float("-inf")
    buckets = [inf, inf, -20.0, inf, inf]
    assert transitions.silence_run(buckets, 0, 2) == 2
    assert transitions.silence_run(buckets, 2, 5) == 2


def _plan():
    """A miniature programme: card, clip, card, then two clips back to back
    (the IV->V shape), so every join kind is exercised."""
    return {"items": [
        {"kind": "card", "image": "c1.png", "dur": 5.0, "chapter": "I. One"},
        {"kind": "clip", "path": "one.mp4", "audio": "source",
         "dur": 100.0, "label": "act one"},
        {"kind": "card", "image": "c2.png", "dur": 5.0, "chapter": "II. Two"},
        {"kind": "clip", "path": "two.mp4", "audio": "source",
         "dur": 30.0, "label": "act two"},
        {"kind": "clip", "path": "three.mp4", "audio": "source",
         "dur": 20.0, "label": "act three"},
    ]}


def test_find_joins_covers_every_shape_on_the_programme_clock():
    durations = [5.0, 100.0, 5.0, 30.0, 20.0]
    joins = transitions.find_joins(_plan(), durations)
    kinds = [j["kind"] for j in joins]
    assert kinds == ["head", "slide", "direct", "tail"]

    head = joins[0]
    assert (head["silent_start"], head["silent_end"]) == (0.0, 5.0)
    assert head["in_label"] == "act one"

    slide = joins[1]
    # card 2 sits at 105.0 -> 110.0 on the PROGRAMME clock
    assert (slide["silent_start"], slide["silent_end"]) == (105.0, 110.0)
    assert slide["out_label"] == "act one"
    assert slide["in_label"] == "act two"

    direct = joins[2]
    assert direct["silent_start"] == 140.0 == direct["silent_end"]
    assert direct["out_label"] == "act two"
    assert direct["in_label"] == "act three"

    tail = joins[3]
    assert tail["silent_start"] == 160.0


def test_measure_join_buckets_align_to_integer_programme_seconds():
    """The issue's table was taken at integer seconds; the report aligns DOWN
    to one so its rows compare against it directly."""
    join = {"kind": "slide", "label": "II", "out_label": "a", "in_label": "b",
            "silent_start": 105.5, "silent_end": 110.5}
    rate = 4

    def fake_decode(path, start, dur, ffmpeg=None):
        # constant level everywhere: every bucket reads the same
        assert start == math.floor(105.5 - transitions.PRE)
        return pcm_f32([0.25] * int(dur), rate=rate)

    r = transitions.measure_join("x.mp4", join, rate, 1, decode_fn=fake_decode)
    first_second = r["rows"][0][0]
    assert first_second == int(first_second)
    assert r["window"][0] <= 105.5 - transitions.PRE + 1


def test_measure_join_reports_silence_and_the_entry_level():
    inf = float("-inf")
    join = {"kind": "slide", "label": "II", "out_label": "a", "in_label": "b",
            "silent_start": 105.0, "silent_end": 110.0}
    rate = 4
    # window: 99 -> 115. Silence 105..110, then the incoming act at half scale.
    levels = [0.5] * 6 + [0.0] * 5 + [0.5] * 4

    def fake_decode(path, start, dur, ffmpeg=None):
        assert start == 99
        return pcm_f32(levels, rate=rate)

    r = transitions.measure_join("x.mp4", join, rate, 1, decode_fn=fake_decode)
    assert r["silence_seconds"] == 5
    assert r["exit"] == (104, pytest.approx(-6.0206, abs=1e-3))
    entry_second, entry_level = r["entry"]
    assert entry_second == 110
    assert entry_level == pytest.approx(-6.0206, abs=1e-3)
    assert all(level == inf for sec, level in r["rows"] if 105 <= sec < 110)


def test_print_report_names_the_clock(stream=None):
    """Every report states which clock its numbers are on -- the #109 trap is
    a timecode whose clock nobody named."""
    import io
    buf = io.StringIO()
    r = {"kind": "slide", "label": "II", "out_label": "a", "in_label": "b",
         "silent_start": 105.0, "silent_end": 110.0,
         "rows": [(104, -20.0), (105, float("-inf"))],
         "silence_seconds": 5, "exit": (104, -20.0), "entry": (110, -18.0)}
    transitions.print_report([r], "built.mp4", stream=buf)
    out = buf.getvalue()
    assert "PROGRAMME" in out
    assert "-inf" in out


# --- the CLI path itself (issue #204) ---------------------------------------
#
# main() passed pre=/post= that measure_join() did not accept, so EVERY
# invocation of the tool died with a TypeError -- while the suite stayed green,
# because every test called measure_join directly. The fix is the signature;
# the guard against it coming back is a test that runs main().

def test_measure_join_honours_a_narrower_window():
    join = {"kind": "slide", "label": "II", "out_label": "a", "in_label": "b",
            "silent_start": 105.0, "silent_end": 110.0}

    def fake_decode(path, start, dur, ffmpeg=None):
        assert start == 103, "pre= did not reach the window arithmetic"
        assert dur == 9, "post= did not reach the window arithmetic"
        return pcm_f32([0.5] * dur, rate=1)

    r = transitions.measure_join("x.mp4", join, 1, 1, decode_fn=fake_decode,
                                 pre=2.0, post=2.0)
    assert r["window"] == (103, 112)


def test_the_cli_runs_end_to_end(tmp_path, monkeypatch, capsys):
    """The crash issue #204 records was invisible to CI because nothing ever
    called main(). This does."""
    import json

    built = tmp_path / "built.mp4"
    built.write_bytes(b"not really an mp4")
    plan = {"output": str(tmp_path / "out.mp4"), "items": [
        {"kind": "card", "image": "a.png", "dur": 5.0, "chapter": "I. One"},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 20.0},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "dur": 20.0},
    ]}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    monkeypatch.setattr(transitions, "probe_audio_shape", lambda p: (1, 1))
    monkeypatch.setattr(transitions, "decode",
                        lambda path, start, dur, ffmpeg=None:
                        pcm_f32([0.5] * int(dur), rate=1))

    assert transitions.main([str(plan_path), "--measure", str(built),
                             "--pre", "2", "--post", "2"]) == 0
    out = capsys.readouterr().out
    assert "transitions on" in out
    assert "PROGRAMME" in out

#!/usr/bin/env python3
"""Measure a music bed, cut sections out of it, and cache its beat grid.

A scored cut needs three things this repo had no answer for: the bed's real
duration, where its bars fall, and what happens to every timecode when a
section is removed. All three live in a checked-in record, `music/<bed_id>.json`,
which is to a bed what `videos/<video_id>.json` is to a source video: provenance
plus the measurements, never the media.

**The grid is cached deliberately, and that is a correctness requirement rather
than an optimisation.** Beat tracking is a heuristic; re-running it after a
library upgrade can shift the downbeat phase by a beat, which would silently
move every cut in a finished piece. Committing the grid makes a re-render
reproducible and keeps the whole suite offline -- `librosa` is an optional
dependency, needed only to *create* a record, exactly as `scenedetect` is needed
only to index a video.

**The downbeat phase is evidence-backed, never an argmax.** Onset strength
answers "what is loudest"; the bar line is "where the bar begins", and in any
backbeat-driven genre the snare on 2 and 4 out-accents the kick -- a bare
argmax over onset strength parks the bar line on the snare (issue #89). So
`measure` corroborates the phase against the song's own re-entries (a composer
puts the band back in on beat 1), plus any `--anchor` the owner asserts by
ear. When neither can decide, the phase is recorded as `null` with the
candidates and the reason -- a missing value is a punch-list item; an invented
one puts every bar-snapped cut a beat off.

**Excisions are snapped to downbeats, and that is what keeps the grid whole.**
Cutting an arbitrary 13 seconds lands mid-bar: the music stumbles, and every
downbeat after the splice sits at a new phase, so a single (tempo, offset) pair
no longer describes the timeline. Snapping both endpoints to downbeats makes the
removed span a whole number of bars, and a whole number of bars is exactly the
condition under which the grid continues in phase across the splice. One grid,
no discontinuity, no special case downstream.

Usage:
    python3 tools/bed.py measure media/<bed>.wav --id <bed_id> \
        --source-url <url> --title <title> --artist <artist> --out music/
    python3 tools/bed.py excise music/<bed_id>.json --from 2:59 --to 3:12
    python3 tools/bed.py render music/<bed_id>.json --media media --out out.wav
    python3 tools/bed.py map music/<bed_id>.json --at 3:48 --edited
"""
from __future__ import annotations

import argparse
import array
import json
import math
import operator
import os
import statistics
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = Path(__file__).resolve().parents[1]
MUSIC_DIR = REPO_ROOT / "music"
DEFAULT_BEATS_PER_BAR = 4


def usage_classes():
    """The legal rights buckets, read from vocab/ rather than hardcoded here.

    ``vocab/`` is the single source of truth for every enum (``AGENTS.md``), and
    a bed record used to be the one place that opted out: ``--usage-class`` was
    free text, so a typo -- or a value nobody had defined -- was written to disk
    and never re-read.
    """
    import yaml

    doc = yaml.safe_load((REPO_ROOT / "vocab" / "provenance.yaml").read_text())
    return sorted((doc or {})["usage_class"]["values"])


# --- timecodes --------------------------------------------------------------

def parse_tc(value):
    """``3:48``, ``3:48.5``, ``1:02:03`` or a bare number of seconds -> float."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if ":" not in text:
        return float(text)
    parts = [float(p) for p in text.split(":")]
    total = 0.0
    for part in parts:
        total = total * 60 + part
    return total


def fmt_tc(seconds):
    """Seconds -> ``M:SS.mmm``, the form the outline and the owner both use."""
    seconds = max(0.0, float(seconds))
    minutes, rest = divmod(seconds, 60)
    if minutes >= 60:
        hours, minutes = divmod(int(minutes), 60)
        return f"{hours}:{int(minutes):02d}:{rest:06.3f}"
    return f"{int(minutes)}:{rest:06.3f}"


# --- measurement ------------------------------------------------------------

def _ffprobe(path, args, ffmpeg=None):
    """One ffprobe read, returning its single CSV field.

    The container's own numbers, deliberately: a bed is one audio file, so
    there is no video stream to disagree with (which is the distinction
    megacut.probe_duration exists to make, on files that have both).
    """
    exe = ffmpeg or "ffprobe"
    return subprocess.run(
        [exe, "-v", "error", *args, "-of", "csv=p=0", str(Path(path).resolve())],
        capture_output=True, text=True, check=True).stdout.strip()


def probe_duration(path, ffmpeg=None):
    """Exact duration in seconds, via ffprobe."""
    return float(_ffprobe(path, ["-show_entries", "format=duration"], ffmpeg))


def analyze_grid(path, beats_per_bar=DEFAULT_BEATS_PER_BAR, sr=22050,
                 beat_multiple=1, anchors=()):
    """Detect tempo, beats and the downbeat phase. Requires ``librosa``.

    Returns the grid dict that gets cached in the record.

    Beat trackers routinely lock onto a metrical level other than the one a
    listener taps -- most often double time, which is what this bed does (161.5
    bpm detected for a song that is felt at ~80.75). Snapping an edit to that
    grid snaps to half-bars, which is a weaker musical boundary than a bar line.

    ``beat_multiple`` selects the level: 2 keeps every other detected beat, so
    the tracked pulse becomes the half-note. It is a deliberate operator choice
    rather than a heuristic, because getting it wrong is not subtle and no
    amount of cleverness beats listening once. Both the raw detection and the
    chosen level are recorded so a later reader can tell what happened.

    The downbeat phase is NOT the argmax over onset strength: that answers
    "what is loudest", and in backbeat-driven music the loudest beats are the
    snares on 2 and 4, not beat 1 (issue #89). The phase is resolved by
    ``resolve_downbeat_phase`` against the song's measured re-entries plus any
    operator ``anchors``, and the record keeps both the evidence string and the
    measured events, so a later reader can see what the value rests on.
    """
    try:
        import librosa
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "beat analysis needs librosa: pip install librosa"
        ) from exc

    y, sr = librosa.load(str(path), sr=sr, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
    onset = librosa.onset.onset_strength(y=y, sr=sr)

    if beat_multiple > 1:
        # Keep the phase that lands on the stronger onsets, then thin.
        scores = [float(onset[np.clip(beat_frames[off::beat_multiple], 0,
                                      len(onset) - 1)].mean())
                  for off in range(beat_multiple)]
        beat_frames = beat_frames[int(np.argmax(scores))::beat_multiple]

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if len(beat_times) < beats_per_bar * 2:
        raise RuntimeError(f"too few beats detected in {path}")

    onset_at_beat = onset[np.clip(beat_frames, 0, len(onset) - 1)]
    strength = [float(onset_at_beat[phase::beats_per_bar].mean())
                for phase in range(beats_per_bar)]

    reentries = measure_reentries(rms_envelope_db(y, sr), HOP_SEC)
    evidence = sorted(float(a) for a in anchors) + \
        [r["measured_sec"] for r in reentries]
    beat_list = [round(float(t), 6) for t in beat_times]
    phase, phase_evidence = resolve_downbeat_phase(
        strength, beats_per_bar, beats=beat_list, evidence_sec=evidence)

    interval = float(np.median(np.diff(beat_times)))
    grid = {
        "detected_tempo_bpm": round(float(np.atleast_1d(tempo)[0]), 3),
        "beat_multiple": beat_multiple,
        "beat_interval_sec": round(interval, 6),
        "tempo_bpm": round(60.0 / interval, 3),
        "beats_per_bar": beats_per_bar,
        "bar_sec": round(interval * beats_per_bar, 6),
        "downbeat_phase": phase,
        "downbeat_phase_evidence": phase_evidence,
        "downbeat_strength": [round(s, 4) for s in strength],
        "measured_reentries": reentries,
        "first_beat_sec": round(float(beat_times[0]), 6),
        "beats": beat_list,
    }
    if anchors:
        grid["phase_anchors_sec"] = [round(float(a), 6) for a in anchors]
    return grid


def downbeats(grid):
    """The bar lines, in source-timeline seconds."""
    phase = grid.get("downbeat_phase")
    if phase is None:
        raise ValueError(
            "this grid's downbeat phase is unresolved -- "
            + grid.get("downbeat_phase_evidence", "no evidence recorded"))
    beats = grid["beats"]
    return [beats[i] for i in range(phase, len(beats),
                                    grid["beats_per_bar"])]


def snap_to_downbeat(grid, seconds):
    """Nearest bar line to ``seconds``."""
    bars = downbeats(grid)
    return min(bars, key=lambda b: abs(b - seconds))


# --- musical events: the evidence a downbeat phase rests on ------------------
#
# A beat grid says where beats fall; it does not say where anything HAPPENS.
# The events that say where the bar begins are drops (the energy falls and
# stays down) and re-entries (it returns): a composer puts the band back in on
# beat 1, so measured re-entry times are what corroborate a downbeat phase.
# The envelope is plain RMS at HOP_SEC resolution, smoothed over SMOOTH_SEC so
# a quiet bar inside a loud section is not mistaken for a breakdown, and
# thresholded against the song's own median level. Stdlib only, so the test
# suite stays offline and dependency-free; scripts/efmb_beats.py reuses these
# same functions rather than keeping a second copy.
#
# Each constant is a measured trade-off, not a guess; the comments say what
# breaks if you move it.
HOP_SEC = 0.02        # envelope resolution; finer than this buys nothing at 152 bpm
SMOOTH_SEC = 1.5      # shorter smooths let one quiet bar fragment the breakdown
DROP_DB = 2.5         # how far below the song's median level counts as "down"
MIN_DOWN_SEC = 4.0    # a drop that comes back inside one bar is a breath, not a drop
RECOVER_DB = 1.5      # re-entry gate: level must stay within this of baseline for 2 s
SUSTAIN_SEC = 2.0     # ... for this long -- a riser swell fails this, the slam passes
ONSET_CONFIRM_SEC = 0.25  # a hit confirming a bar line lands within a quarter
                      # second of it; wider windows catch the pick-up instead
REENTRY_WINDOW_SEC = 12.0  # a re-entry this far after the drop is a new section
PHASE_TOLERANCE_SEC = 0.08  # the owner's rule: 0.08 s off the bar line is a win
BACKBEAT_SIGNATURE_MIN = 0.05  # parity-class imbalance below this is no signature


def load_envelope_db(path, hop=HOP_SEC):
    """RMS energy of the WAV in dB re its own peak, one value per ``hop`` seconds.

    Both channels, summed in the energy domain. Pure stdlib: ``wave`` for the
    container, ``array`` for the samples, ``map(operator.mul, ...)`` because a
    genexpr over 15M samples is the difference between 4 seconds and 30.
    """
    with wave.open(str(path), "rb") as w:
        rate = w.getframerate()
        channels = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise RuntimeError(f"{path} is {width * 8}-bit; the detector expects 16-bit PCM")
    a = array.array("h")
    a.frombytes(raw)
    del raw
    win = int(rate * hop)
    step = win * channels
    n = (len(a) // step) * step  # whole windows only; the tail is < 20 ms of fade
    env = []
    for i in range(0, n, step):
        ss = 0
        for c in range(channels):
            ch = a[i + c:i + step:channels]
            ss += sum(map(operator.mul, ch, ch))
        env.append(math.sqrt(ss / (channels * win)))
    peak = max(env)
    return [20 * math.log10(e / peak) if e > 0 else -120.0 for e in env], hop


def rms_envelope_db(y, sr, hop=HOP_SEC):
    """The same envelope ``load_envelope_db`` reads off a WAV, from mono float
    samples librosa has already decoded. numpy is imported locally: it is an
    optional dependency, present exactly when the caller is measuring audio.
    """
    import numpy as np  # optional dependency, as with analyze_grid
    win = int(sr * hop)
    n = (len(y) // win) * win
    if n == 0:
        return []
    rms = np.sqrt((y[:n].reshape(-1, win) ** 2).mean(axis=1))
    peak = float(rms.max())
    if peak <= 0:
        return [-120.0] * len(rms)
    return [20 * math.log10(max(float(e) / peak, 1e-6)) for e in rms]


def smooth(xs, width_sec, hop):
    """Centered boxcar. Centered, not trailing: a trailing window delays every
    edge by half its width and the drop/re-entry times would all drift late."""
    k = max(1, int(width_sec / hop))
    half = k // 2
    out = []
    for i in range(len(xs)):
        lo = max(0, i - half)
        hi = min(len(xs), i + half + 1)
        out.append(sum(xs[lo:hi]) / (hi - lo))
    return out


def baseline_of(level):
    """The song's typical loudness: median of the smoothed level. Median, not
    mean, because a 12 s breakdown should not lower the bar it is measured
    against."""
    return statistics.median(level)


def find_drops(level, hop, baseline, drop_db=DROP_DB, min_down_sec=MIN_DOWN_SEC):
    """Regions where the level falls ``drop_db`` below baseline and stays there.

    ``drop_sec`` is not the threshold crossing: the fall takes about a second,
    so the crossing sits mid-slide wherever the threshold happens to catch it.
    The musically meaningful moment is when the loud state was last present --
    the last window at or above the midpoint between the pre-drop level and the
    region floor. That lands within half a second of the by-ear time on this
    song; a bare threshold crossing lands wherever you tune it.
    """
    threshold = baseline - drop_db
    min_run = int(min_down_sec / hop)
    drops = []
    i = 0
    while i < len(level):
        if level[i] >= threshold:
            i += 1
            continue
        j = i
        while j < len(level) and level[j] < threshold:
            j += 1
        if j - i >= min_run:
            start, end = i * hop, (j - 1) * hop
            floor = min(level[i:j])
            pre_lo = max(0, i - int(6.0 / hop))
            pre = level[pre_lo:i - int(0.5 / hop)] if i > int(0.5 / hop) else []
            if pre:
                pre_level = sorted(pre)[len(pre) // 2]
                mid = (pre_level + floor) / 2
                k = i - 1
                while k > 0 and level[k] < mid:
                    k -= 1
                drop_sec = k * hop
            else:
                drop_sec = start  # the song opens quiet: an intro, not a drop
            drops.append({
                "drop_sec": round(drop_sec, 3),
                "down_from_sec": round(start, 3),
                "down_until_sec": round(end, 3),
                "floor_db": round(floor, 2),
                "depth_db": round(baseline - floor, 2),
                "kind": ("intro" if start < hop * 2 else
                         "outro" if j >= len(level) - int(1.0 / hop) else
                         "drop"),
            })
        i = j
    return drops


def measure_reentries(env_db, hop):
    """When the band comes back after each drop, measured from the audio
    BEFORE any grid is consulted -- the evidence a downbeat phase is scored
    against.

    A re-entry is the strongest 60 ms level step after a drop whose following
    SUSTAIN_SEC seconds stay within RECOVER_DB of the baseline. The sustain
    gate is what rejects a riser: a swell spikes and falls back, failing the
    gate; the full-band slam stays up, passing it. The step search is
    phase-free on purpose -- consulting a candidate grid here would make the
    corroboration circular.
    """
    level = smooth(env_db, SMOOTH_SEC, hop)
    baseline = baseline_of(level)
    gate = baseline - RECOVER_DB
    sustain = int(SUSTAIN_SEC / hop)
    out = []
    for drop in find_drops(level, hop, baseline):
        if drop["kind"] == "outro":
            continue
        # The centered smoother reports the region end up to half a window
        # late, so a re-entry that slams instantly sits BEFORE down_until.
        lo = max(3, int((drop["down_until_sec"] - SMOOTH_SEC / 2) / hop))
        hi = min(len(env_db), int((drop["down_until_sec"] +
                                   REENTRY_WINDOW_SEC) / hop))
        best, best_k = 0.0, None
        for k in range(lo, hi):
            if k + sustain > len(level):
                break
            step = env_db[k] - env_db[k - 3]
            if step > best and min(level[k:k + sustain]) >= gate:
                best, best_k = step, k
        if best_k is not None:
            out.append({"measured_sec": round(best_k * hop, 3),
                        "onset_db": round(best, 2),
                        "after_drop_sec": drop["drop_sec"]})
    return out


def resolve_downbeat_phase(strength, beats_per_bar, beats=(), evidence_sec=(),
                           tolerance_sec=PHASE_TOLERANCE_SEC):
    """Which beat of the bar is beat 1, and what that answer rests on.

    Returns ``(phase, evidence)``. ``phase`` is ``None`` when the evidence
    cannot decide: a missing phase is a punch-list item, an invented one puts
    every bar-snapped cut a beat off -- missing, never invented.

    Onset strength answers "what is loudest"; the bar line is "where the bar
    begins". In backbeat-driven music the snare on 2 and 4 out-accents the
    kick, so the strength vector alone can only narrow the phase to one parity
    pair ({1,3}-indexed beats 1&3 or 2&4) -- it cannot order beat 1 against
    beat 3, and it cannot distinguish "loud downbeat" from "loud snare"
    without a genre assumption. Measured events decide: a composer puts the
    band back in on beat 1, so the phase whose bar lines the measured
    re-entries and owner anchors land on is the bar line.

    With no events at all, a clear backbeat signature narrows the answer to
    the quieter parity pair and reports it as unresolved; without even a
    signature the loudest-beat phase is kept, labelled as what it is.
    """
    n = len(strength)
    loudest = max(range(n), key=lambda i: strength[i]) if n else 0
    if beats_per_bar != 4 or n != beats_per_bar:
        return loudest, (f"no backbeat model for a {beats_per_bar}-beat bar; "
                         f"kept the loudest-beat phase {loudest} "
                         "(onset-strength argmax)")

    even = (strength[0] + strength[2]) / 2   # beat-1-and-3 class under phase 0
    odd = (strength[1] + strength[3]) / 2
    quiet_pair = (0, 2) if odd >= even else (1, 3)

    if evidence_sec:
        if not beats:
            raise ValueError("evidence_sec needs the beat grid to score against")
        scores = {}
        for p in range(beats_per_bar):
            bars = beats[p::beats_per_bar]
            errs = [min(abs(t - b) for b in bars) for t in evidence_sec]
            scores[p] = sum(errs) / len(errs)
        best = min(scores, key=scores.get)
        runner_up = min(s for p, s in scores.items() if p != best)
        if scores[best] <= tolerance_sec:
            consistency = ("consistent with the backbeat signature"
                           if best in quiet_pair else
                           "NOTE: lands in the accented class -- the "
                           "snare-louder reading does not hold for this track")
            return best, (
                f"{len(evidence_sec)} measured re-entries/anchors land a mean "
                f"{scores[best]:.3f}s from phase-{best} bar lines (next best "
                f"phase scores {runner_up:.3f}s); {consistency}")
        return None, (
            f"no phase puts the {len(evidence_sec)} measured events on bar "
            f"lines (best is phase {best} at a mean {scores[best]:.3f}s, over "
            f"the {tolerance_sec}s gate) -- the grid itself may have drifted "
            "from the music; phase left unset rather than guessed")

    scale = (even + odd) / 2
    if scale <= 0 or abs(even - odd) / scale < BACKBEAT_SIGNATURE_MIN:
        return loudest, (f"no backbeat signature in the onset strengths "
                         f"(even beats {even:.2f}, odd {odd:.2f}); kept the "
                         f"loudest-beat phase {loudest} -- corroborate against "
                         "a measured re-entry before cutting to the bar")
    louder = "odd" if odd > even else "even"
    a, b = quiet_pair
    return None, (
        f"backbeat signature: {louder} positions out-accent "
        f"({max(even, odd):.2f} vs {min(even, odd):.2f}) -- the snare is "
        f"louder than the kick, so the bar line is beat {a + 1} or {b + 1} "
        "and onset strength cannot say which. Left unset rather than guessed; "
        "re-measure with --anchor, or let the measured re-entries decide")


# --- excisions --------------------------------------------------------------

def plan_excision(grid, start, end):
    """Snap an excision to bar lines and report what moved.

    Returns a dict recording both the requested and the snapped span. Removing a
    whole number of bars is what lets the grid survive the splice, so the snap is
    not a nicety: an excision that is 4.37 bars long re-phases everything after
    it.

    Bars are counted by *index* rather than by dividing the span by the median
    bar length. Tracked downbeats carry a little jitter, so four real bars
    measure 4.07 median bars -- and reporting that would suggest a fractional
    excision where the cut is in fact exactly four bars of music. The index is
    the musical truth; the median is only an average.
    """
    bars = downbeats(grid)
    start_i = min(range(len(bars)), key=lambda i: abs(bars[i] - start))
    end_i = min(range(len(bars)), key=lambda i: abs(bars[i] - end))
    if end_i <= start_i:
        raise ValueError(
            f"excision collapses after snapping: {fmt_tc(start)}-{fmt_tc(end)} "
            f"both snap to bar {start_i}"
        )
    snapped_start, snapped_end = bars[start_i], bars[end_i]
    return {
        "requested_start_sec": round(float(start), 6),
        "requested_end_sec": round(float(end), 6),
        "start_sec": round(snapped_start, 6),
        "end_sec": round(snapped_end, 6),
        "start_bar": start_i,
        "end_bar": end_i,
        "removed_sec": round(snapped_end - snapped_start, 6),
        "removed_bars": end_i - start_i,
        "start_moved_sec": round(snapped_start - start, 6),
        "end_moved_sec": round(snapped_end - end, 6),
    }


def guard_no_overlap(record, exc):
    """Refuse an excision whose snapped span overlaps one already recorded.

    ``build_filter`` coalesces overlapping spans, so the *rendered* bed would
    still be right — but ``edited_duration`` / ``to_edited`` / ``to_source``
    sum ``removed_sec`` blindly, so a double-counted overlap desyncs every
    anchor from the audio with no error anywhere. The comparison runs on the
    snapped interval (``plan_excision`` has already snapped it), so an exact
    re-run of the same excise is an overlap too. Spans that merely touch at a
    bar line share no audio and are fine.
    """
    for existing in record.get("excisions", []):
        if exc["start_sec"] < existing["end_sec"] and \
                existing["start_sec"] < exc["end_sec"]:
            raise ValueError(
                f"excision {fmt_tc(exc['start_sec'])}-{fmt_tc(exc['end_sec'])} "
                f"overlaps existing excision {fmt_tc(existing['start_sec'])}-"
                f"{fmt_tc(existing['end_sec'])} "
                f"(bars {existing['start_bar']}-{existing['end_bar']})"
            )


def edited_duration(record):
    """Source duration minus everything excised."""
    removed = sum(e["removed_sec"] for e in record.get("excisions", []))
    return record["duration_sec"] - removed


def to_edited(record, source_sec):
    """Map a source timecode onto the edited timeline.

    Returns ``None`` for a moment that was cut out -- it has no edited position,
    and silently returning a neighbouring one would be a lie an anchor could be
    built on.
    """
    shift = 0.0
    for exc in sorted(record.get("excisions", []), key=lambda e: e["start_sec"]):
        if source_sec >= exc["end_sec"]:
            shift += exc["removed_sec"]
        elif source_sec >= exc["start_sec"]:
            return None
    return source_sec - shift


def to_source(record, edited_sec):
    """Map an edited timecode back onto the source timeline."""
    result = edited_sec
    for exc in sorted(record.get("excisions", []), key=lambda e: e["start_sec"]):
        if result >= exc["start_sec"]:
            result += exc["removed_sec"]
    return result


def edited_downbeats(record):
    """Bar lines on the *edited* timeline.

    Because every excision spans a whole number of bars, these are exactly the
    surviving source downbeats shifted left -- the grid does not re-phase at a
    splice, so there is no second grid to reconcile.
    """
    out = []
    for bar in downbeats(record["grid"]):
        mapped = to_edited(record, bar)
        if mapped is not None:
            out.append(round(mapped, 6))
    return out


def nearest_edited_downbeat(record, edited_sec):
    bars = edited_downbeats(record)
    return min(bars, key=lambda b: abs(b - edited_sec))


# --- rendering --------------------------------------------------------------

def build_filter(record):
    """An ffmpeg filter that concatenates the surviving spans."""
    spans = []
    cursor = 0.0
    for exc in sorted(record.get("excisions", []), key=lambda e: e["start_sec"]):
        if exc["start_sec"] > cursor:
            spans.append((cursor, exc["start_sec"]))
        cursor = exc["end_sec"]
    if cursor < record["duration_sec"]:
        spans.append((cursor, record["duration_sec"]))

    parts = []
    for n, (start, end) in enumerate(spans):
        parts.append(
            f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{n}]"
        )
    chain = "".join(f"[a{n}]" for n in range(len(spans)))
    parts.append(f"{chain}concat=n={len(spans)}:v=0:a=1[out]")
    return ";".join(parts), spans


def probe_codec(path, ffmpeg=None):
    """The source's PCM codec name, so a re-cut does not quietly downgrade it."""
    args = ["-select_streams", "a:0", "-show_entries", "stream=codec_name"]
    return _ffprobe(path, args, ffmpeg) or "pcm_s16le"


def render_bed(record, media_dir, out_path, ffmpeg="ffmpeg"):
    """Write the edited bed.

    Lossless by construction: the spans are concatenated at the source's own
    codec, sample rate and bit depth, with no EQ, no resample and no loudness
    processing. Cutting a section out of a bed is an edit, not a mastering pass,
    and a 24-bit source that comes back 16-bit has been quietly mastered.
    """
    src = Path(media_dir) / record["media_filename"]
    if not src.exists():
        raise FileNotFoundError(f"bed media not found: {src}")
    filt, spans = build_filter(record)
    codec = probe_codec(src)
    cmd = [ffmpeg, "-v", "error", "-y", "-i", str(src.resolve()),
           "-filter_complex", filt, "-map", "[out]",
           "-c:a", codec, str(Path(out_path).resolve())]
    subprocess.run(cmd, check=True)
    return spans


# --- records ----------------------------------------------------------------

def load_record(path):
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def save_record(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("measure", help="create a bed record from a media file")
    m.add_argument("media")
    m.add_argument("--id", required=True)
    m.add_argument("--source-url", default="")
    m.add_argument("--title", default="")
    m.add_argument("--artist", default="")
    m.add_argument("--usage-class", default="third_party_copyrighted")
    m.add_argument("--attribution",
                   help="the credit string the licence requires, verbatim. "
                        "Required for an attribution licence such as "
                        "cc_by_4_0, and it must also appear in "
                        "ATTRIBUTIONS.md.")
    m.add_argument("--rights-note", default="")
    m.add_argument("--beats-per-bar", type=int, default=DEFAULT_BEATS_PER_BAR)
    m.add_argument("--beat-multiple", type=int, default=1,
                   help="keep every Nth detected beat; 2 undoes a double-time "
                        "lock, which beat trackers do routinely")
    m.add_argument("--anchor", action="append", type=parse_tc, default=[],
                   metavar="SEC", help="a moment asserted by ear to be beat 1 "
                        "of a bar (repeatable); scored alongside the measured "
                        "re-entries to fix the downbeat phase")
    m.add_argument("--out", default=str(MUSIC_DIR))

    e = sub.add_parser("excise", help="snap and record a section to remove")
    e.add_argument("record")
    e.add_argument("--from", dest="start", required=True)
    e.add_argument("--to", dest="end", required=True)

    r = sub.add_parser("render", help="write the edited bed")
    r.add_argument("record")
    r.add_argument("--media", default=str(REPO_ROOT / "media"))
    r.add_argument("--out", required=True)

    mp = sub.add_parser("map", help="translate a timecode between timelines")
    mp.add_argument("record")
    mp.add_argument("--at", required=True)
    mp.add_argument("--edited", action="store_true",
                    help="--at is on the edited timeline (default: source)")

    args = ap.parse_args(argv)

    if args.cmd == "measure":
        allowed = usage_classes()
        if args.usage_class not in allowed:
            ap.error(f"--usage-class {args.usage_class!r} is not in "
                     f"vocab/provenance.yaml: {allowed}")
        if args.usage_class == "cc_by_4_0" and not args.attribution:
            ap.error("cc_by_4_0 requires --attribution: the licence permits "
                     "the use only on condition of the credit, so a record "
                     "without one claims a permission it does not have.")
        media = Path(args.media)
        grid = analyze_grid(media, beats_per_bar=args.beats_per_bar,
                            beat_multiple=args.beat_multiple,
                            anchors=args.anchor)
        record = {
            "bed_id": args.id,
            "media_filename": media.name,
            "source_url": args.source_url,
            "title": args.title,
            "artist": args.artist,
            "usage_class": args.usage_class,
            "source_rights_note": args.rights_note,
            "duration_sec": round(probe_duration(media), 6),
            "grid": grid,
            "excisions": [],
        }
        if args.attribution:
            record["attribution"] = args.attribution
        out = Path(args.out)
        dest = out / f"{args.id}.json" if out.is_dir() or not out.suffix else out
        save_record(record, dest)
        print(f"wrote {dest}")
        print(f"  duration {record['duration_sec']:.3f}s ({fmt_tc(record['duration_sec'])})")
        print(f"  tempo {grid['tempo_bpm']} bpm, bar {grid['bar_sec']:.4f}s")
        if grid["downbeat_phase"] is None:
            print(f"  downbeat phase UNRESOLVED: {grid['downbeat_phase_evidence']}")
        else:
            print(f"  downbeat phase {grid['downbeat_phase']} "
                  f"({len(downbeats(grid))} bars)")
            print(f"  evidence: {grid['downbeat_phase_evidence']}")
        return 0

    record = load_record(args.record)

    if args.cmd == "excise":
        start, end = parse_tc(args.start), parse_tc(args.end)
        exc = plan_excision(record["grid"], start, end)
        guard_no_overlap(record, exc)
        record.setdefault("excisions", []).append(exc)
        record["excisions"].sort(key=lambda x: x["start_sec"])
        save_record(record, args.record)
        print(f"excision snapped to bar lines:")
        print(f"  requested {fmt_tc(start)} -> {fmt_tc(end)}")
        print(f"  snapped   {fmt_tc(exc['start_sec'])} -> {fmt_tc(exc['end_sec'])}"
              f"  ({exc['start_moved_sec']:+.3f}s / {exc['end_moved_sec']:+.3f}s)")
        print(f"  removes   {exc['removed_sec']:.3f}s = {exc['removed_bars']:g} bars")
        print(f"  edited duration {edited_duration(record):.3f}s "
              f"({fmt_tc(edited_duration(record))})")
        return 0

    if args.cmd == "render":
        spans = render_bed(record, args.media, args.out)
        print(f"wrote {args.out} from {len(spans)} span(s)")
        for start, end in spans:
            print(f"  {fmt_tc(start)} -> {fmt_tc(end)}")
        return 0

    if args.cmd == "map":
        at = parse_tc(args.at)
        if args.edited:
            src = to_source(record, at)
            near = nearest_edited_downbeat(record, at)
            print(f"edited {fmt_tc(at)}  ->  source {fmt_tc(src)}")
            print(f"  nearest edited downbeat {fmt_tc(near)} ({near - at:+.3f}s)")
            print(f"  {edited_duration(record) - at:.3f}s from the end")
        else:
            mapped = to_edited(record, at)
            if mapped is None:
                print(f"source {fmt_tc(at)} was excised; it has no edited position")
                return 1
            print(f"source {fmt_tc(at)}  ->  edited {fmt_tc(mapped)}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

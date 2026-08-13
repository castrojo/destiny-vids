#!/usr/bin/env python3
"""Delivered true-peak measurement and static-gain headroom correction.

Shared by ``tools/redact.py`` (scored uncut videos) and ``tools/render.py``
(every cut), so no deliverable ships above the delivery band. The rules that
live here are ``docs/skills/references/audio-standard.md``'s:

- headroom is a derived **static gain**, never a limiter, never a normaliser --
  loudnorm/compression would rewrite the dynamics the artist chose, where a
  gain only ever scales;
- the **delivered** file's peak is what counts, not the bed's: a lossy encoder
  reconstructs inter-sample peaks above the samples it was given (measured:
  0.2 dB of overshoot on one bed, 1.5 dB on another), so a mix correct at
  every earlier step can still clip after AAC;
- corrections only ever go **down** and stop at the first safe result, because
  the overshoot is not monotonic in the gain (measured: gain 0.658 delivered
  -2.5 dBTP while 0.675 delivered -0.8) and chasing a narrow window on that
  curve oscillates at a full encode per attempt.
"""
import re
import subprocess
from pathlib import Path

# Headroom for the deliverable, in dBTP. Intersample peaks exceed sample peaks,
# and a lossy decoder can overshoot further still, so a deliverable that sits at
# 0 dBFS clips on playback. ~1 dB of headroom is the usual delivery allowance.
DEFAULT_TARGET_DBTP = -1.1

# How far above the target a delivered file may land and still be accepted.
# The delivered acts in ~/Videos/Wolves/Prod sit at -0.9..-1.2 dBTP, so this keeps
# the accepted band flush with what has actually shipped while staying clear
# of full scale.
PEAK_ACCEPT_MARGIN_DB = 0.6

# The margin render.py uses instead: the delivered band ~/Videos/audio-check.sh
# enforces is -0.9..-1.1 dBTP, so a cut fresh out of render.py is held to a
# ceiling of -1.1 + 0.2 = -0.9 -- the band's top. redact.py keeps the wider
# margin above because it re-measures files that already shipped; a new cut has
# no such legacy and must not leave the renderer above the band (issue #44:
# one chapter shipped at -0.7, which the wider margin would have waved through).
DELIVERED_BAND_MARGIN_DB = 0.2

# Below this far under target, say so: safe, but quieter than the other cuts.
QUIET_WARN_DB = 1.0


def measure_true_peak(path, ffmpeg=None):
    """True peak of ``path`` in dBFS, via ffmpeg's ebur128 (ITU-R BS.1770).

    True peak, not sample peak: the question is whether the reconstructed
    analogue waveform clips, and intersample peaks routinely exceed the highest
    sample by a dB or more.
    """
    if ffmpeg is None:
        from tools.render import find_ffmpeg

        ffmpeg = find_ffmpeg()
    proc = subprocess.run(
        [*ffmpeg, "-nostdin", "-hide_banner", "-nostats", "-i", str(Path(path).resolve()),
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True)
    peaks = re.findall(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", proc.stderr)
    if not peaks:
        raise RuntimeError(f"could not measure true peak of {path}")
    return float(peaks[-1])


def gain_for_headroom(path, target_dbtp=DEFAULT_TARGET_DBTP, ffmpeg=None):
    """Linear gain that lands ``path`` at ``target_dbtp``.

    A STATIC gain, deliberately: the alternative is a normaliser, and
    loudnorm/compression would rewrite the dynamics the artist chose. This only
    ever scales; it never reshapes. A track already quieter than the target is
    left alone (gain 1.0) rather than being pushed up to meet it.
    """
    peak = measure_true_peak(path, ffmpeg)
    if peak <= target_dbtp:
        return 1.0, peak
    return 10 ** ((target_dbtp - peak) / 20.0), peak


def correct_delivered_peak(out_path, gain, target_dbtp, rerun, ffmpeg=None,
                           attempts=5, log=print, margin_db=PEAK_ACCEPT_MARGIN_DB):
    """Measure the delivered file and re-encode at a corrected gain until safe.

    ``gain`` is the static gain the file on disk was just encoded with (1.0 for
    none). ``rerun(new_gain)`` must re-encode ``out_path`` at the new static
    gain and raise on encoder failure. Returns the gain that produced the file
    on disk.

    The loop is measure-and-verify on the DELIVERED file, not the input:
    deriving the gain from the source fixed the old hardcoded-gain bug, but a
    lossy encoder adds inter-sample overshoot of its own -- a -1.1 dBTP mix
    came back from AAC at +0.3 dBTP. Each correction is another static gain,
    never a limiter; corrections only go down and stop at the first result
    with real headroom. A file still hot after ``attempts`` passes is warned
    about rather than failed: degrade, never block.
    """
    ceiling = target_dbtp + margin_db
    for attempt in range(attempts):
        delivered = measure_true_peak(out_path, ffmpeg)
        if delivered <= ceiling:
            log(f"  delivered true peak {delivered:+.1f} dBTP")
            if delivered < target_dbtp - QUIET_WARN_DB:
                log(f"  note: {target_dbtp - delivered:.1f} dB below the "
                    f"{target_dbtp:+.1f} dBTP target -- the encoder left "
                    f"more headroom than asked for, which is safe but "
                    f"quieter than the other cuts")
            return gain
        if attempt == attempts - 1:
            log(f"  WARNING: delivered true peak {delivered:+.1f} dBTP "
                f"still above {ceiling:+.1f} after {attempts} "
                f"attempts -- verify before shipping")
            return gain
        gain *= 10 ** (-(delivered - target_dbtp) / 20.0)
        log(f"  delivered true peak {delivered:+.1f} dBTP -- the encoder "
            f"added {delivered - target_dbtp:.1f} dB over the target; "
            f"re-running at static gain {gain:.3f}")
        rerun(gain)
    return gain

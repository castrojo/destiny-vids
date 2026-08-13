#!/usr/bin/env python3
"""Map act II's cut points onto the music, and find the music's real events.

The owner asked for "an analysis of the beats to find opportunities to sync".
One such opportunity was found by hand and is already shipped: the Sentinel
shield lands on the re-entry at 269.700 s. That poke was manual; this script
makes the analysis reproducible and finds the syncs nobody has looked for.

Run it:  ``python3 scripts/efmb_beats.py``  (add ``--json [path]`` for data).

FILM TIME IS BED TIME
---------------------
The bed plays end to end with no excisions, and the picture is fitted to it
(``build_efmb.py`` derives head and tail from the anchor, never types them).
So film second T is bed second T, and every kept-run boundary can be laid
directly on the beat grid. The numbers come FROM ``build_efmb.build()`` --
importing it, never retyping it, is what keeps this map honest when a run
moves. Nothing here mutates the cut: this is a report.

SIGNED ERRORS, BECAUSE EARLY AND LATE ARE DIFFERENT EDITS
----------------------------------------------------------
``err = film_t - grid_t``. Positive means the cut lands AFTER the grid point:
the picture is late, and syncing it means taking picture out before the cut.
Negative means the cut anticipates the beat. Ranking is by |downbeat error| --
the owner's own rule: 0.08 s off is a free win, 0.7 s off is a re-cut.

THE GRID IS NOT THE MUSIC
-------------------------
A beat grid says where beats fall; it does not say where anything HAPPENS.
The events a cut should hit are drops (energy falls and stays down) and
re-entries (it returns). Those are measured from the WAV itself: an RMS
envelope at 50 windows/second, smoothed over 1.5 s so a quiet bar inside a
loud section is not mistaken for a breakdown, thresholded against the song's
own median level. Stdlib ``wave`` + ``array`` only -- no audio library, so
the test suite stays offline and dependency-free.

The known ground truth this detector must reproduce: the song breaks down at
258.0 s, stays down to 268.0, and the full band re-enters at 269.700. A
detector that misses the one event the whole act is built on is wrong, and
the test suite says so.

THE RE-ENTRY IS A DOWNBEAT, AND THE GRID'S PHASE IS ONE BEAT OFF
----------------------------------------------------------------
The stored ``downbeat_phase: 3`` is librosa's global argmax over onset
strength -- a guess, and the file's own ``downbeat_strength`` vector shows
why it guessed wrong: positions 1 and 3 measure 3.61 and 3.81 against 3.13
and 3.25 for 0 and 2. That is a backbeat -- the snares on 2 and 4 out-accent
the kicks on 1 and 3, which is what metal does -- and argmax picked one of
the strong positions, landing the "bar line" on beat 4. The owner set the
film's one hard anchor BY EAR at the re-entry slam, 269.700, and under the
stored phase that moment is not a downbeat at all (the stored phase puts the
bar line at 269.328, one beat early). The anchor is the measurement made by
a human at the one moment that matters; the strength vector agrees with the
human once the snare positions are read as snares. So this script reports
downbeats at the anchor-verified phase and says so, loudly, every time it
runs. Fixing the committed grid is a separate decision -- this script only
reports.
"""
from __future__ import annotations

import array
import json
import math
import operator
import sys
import wave
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_efmb  # noqa: E402 -- the authority on the cut; never re-typed here

BED_PATH = REPO_ROOT / "music" / f"{build_efmb.BED_ID}.json"
WAV_PATH = REPO_ROOT / "media" / f"{build_efmb.BED_ID}.wav"

# --- detector constants -----------------------------------------------------
# Each is a measured trade-off, not a guess; the comments say what breaks if
# you move it.
HOP_SEC = 0.02        # envelope resolution; finer than this buys nothing at 152 bpm
SMOOTH_SEC = 1.5      # shorter smooths let one quiet bar fragment the breakdown
DROP_DB = 2.5         # how far below the song's median level counts as "down"
MIN_DOWN_SEC = 4.0    # a drop that comes back inside one bar is a breath, not a drop
RECOVER_DB = 1.5      # re-entry gate: level must stay within this of baseline for 2 s
SUSTAIN_SEC = 2.0     # ... for this long -- a riser swell fails this, the slam passes
ONSET_CONFIRM_SEC = 0.25  # a hit confirming a bar line lands within a quarter
                      # second of it; wider windows catch the pick-up instead


# --- the envelope ------------------------------------------------------------

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
    s = sorted(level)
    return s[len(s) // 2]


# --- drops and re-entries ----------------------------------------------------

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


def find_reentry(level, hop, raw_db, downbeats, drop, baseline,
                 recover_db=RECOVER_DB, sustain_sec=SUSTAIN_SEC):
    """The downbeat the music comes back on after a drop, or None.

    Two gates, and the order matters. The SUSTAIN gate first: the next two
    seconds after the downbeat must stay within ``recover_db`` of baseline. A
    riser swell (this song has one at 268.1, on a bar line, exactly where a
    naive "first loud onset after the drop" would land) spikes and falls back,
    failing the gate; the full-band slam stays up, passing it. Then the ONSET
    confirmation: the strongest positive 60 ms step within a quarter second of
    that downbeat is the measured hit. Wider than that and the window swallows
    the pick-up hit on the beat before, and the re-entry is reported one beat
    early -- which is precisely the mistake this function exists to avoid.
    """
    if drop["kind"] == "outro":
        return None
    gate = baseline - recover_db
    # The centered smoother reports the region end up to half a window late,
    # so a re-entry that slams instantly (no riser) sits BEFORE down_until.
    lo = drop["down_until_sec"] - SMOOTH_SEC / 2
    for d in downbeats:
        if d < lo:
            continue
        if d > drop["down_until_sec"] + 12.0:
            break
        seg = level[int(d / hop):int((d + sustain_sec) / hop)]
        if not seg or min(seg) < gate:
            continue
        # sustain gate passed: confirm with a real transient near the downbeat
        i0 = max(3, int((d - ONSET_CONFIRM_SEC) / hop))
        i1 = min(len(raw_db), int((d + ONSET_CONFIRM_SEC) / hop))
        best, best_i = 0.0, None
        for k in range(i0, i1):
            step_db = raw_db[k] - raw_db[k - 3]
            if step_db > best:
                best, best_i = step_db, k
        return {
            "downbeat_sec": round(d, 3),
            "measured_sec": round(best_i * hop, 3) if best_i is not None else None,
            "onset_db": round(best, 2),
            "onset_offset_sec": (round(best_i * hop - d, 3)
                                 if best_i is not None else None),
        }
    return None


# --- the grid ----------------------------------------------------------------

def nearest(times, t):
    """(nearest grid time, signed error film - grid). The sign is the edit:
    positive means the cut is late and picture must come out before it."""
    near = min(times, key=lambda x: abs(x - t))
    return near, t - near


def verify_downbeat_phase(grid, anchor_film):
    """Which beats are bar lines: the stored phase, checked against the anchor.

    The stored phase is librosa's argmax over onset strength. The anchor is the
    owner's by-ear fix at the one moment the film cannot get wrong. When they
    disagree, the tie-break is in the file itself: under the true phase, the
    backbeat positions (2 and 4) must out-accent 1 and 3 -- if argmax landed on
    a snare, the phase is one beat early. Returns (phase, note); the note is
    printed every run, because a phase the file and the film disagree about is
    a fact nobody should have to re-derive.
    """
    beats = grid["beats"]
    bpb = grid["beats_per_bar"]
    stored = grid["downbeat_phase"]
    idx = min(range(len(beats)), key=lambda i: abs(beats[i] - anchor_film))
    if abs(beats[idx] - anchor_film) > 0.02:
        # The anchor not landing on ANY beat is a different, worse problem:
        # the grid itself has drifted from the music.
        return stored, (f"WARNING: anchor {anchor_film} is "
                        f"{abs(beats[idx] - anchor_film):.3f}s from the nearest "
                        "beat -- the grid itself has drifted, phase not checked")
    if idx % bpb == stored:
        return stored, "stored phase and the shipped anchor agree"
    candidate = idx % bpb
    strength = grid.get("downbeat_strength", [])
    if len(strength) == bpb:
        snares = ((candidate + 1) % bpb, (candidate + bpb - 1) % bpb)
        kicks = (candidate, (candidate + 2) % bpb)
        snare_mean = sum(strength[s] for s in snares) / len(snares)
        kick_mean = sum(strength[k] for k in kicks) / len(kicks)
        if snare_mean > kick_mean:
            return candidate, (
                f"stored downbeat_phase {stored} puts the bar line one beat "
                f"EARLY of the music: the file's own strength vector has the "
                f"backbeat positions out-accenting 1 and 3 ({snare_mean:.2f} vs "
                f"{kick_mean:.2f}), and the shipped anchor at {anchor_film}s -- "
                f"set by ear at the re-entry -- is an exact beat. Downbeats "
                f"reported at anchor-verified phase {candidate}; the committed "
                "grid's phase is a separate fix, this script only reports.")
    return stored, (f"WARNING: anchor lands on beat residue {candidate}, not the "
                    f"stored phase {stored}, and the strength vector does not "
                    "support re-phasing; reporting the stored phase")


def downbeat_times(grid, phase):
    beats = grid["beats"]
    return beats[phase::grid["beats_per_bar"]]


# --- the cut points ----------------------------------------------------------

def film_boundaries(plan):
    """The run-join cut points in film time: bed lead + cumulative kept picture.

    Interior boundaries only -- the head and tail are black by design, and a
    cut to or from black is already synced to whatever it likes.
    """
    lead = plan["bed_lead_sec"]
    rows = []
    elapsed = 0.0
    for i, (left, right) in enumerate(zip(plan["runs"], plan["runs"][1:])):
        elapsed += left["sec"]
        rows.append({
            "label": f"run {i + 1} -> run {i + 2}",
            "film_sec": round(lead + elapsed, 3),
            "src_out": left["in"] + left["sec"],
            "src_in": right["in"],
            "seam": f"{left['why']}  |  {right['why']}",
        })
    return rows


def analyze(plan=None, grid=None, envelope=None):
    """The whole report as data. Injectable pieces so the tests can feed a
    synthetic grid/envelope without touching the WAV or the plan."""
    if plan is None:
        plan = build_efmb.build()
    if grid is None:
        with open(BED_PATH) as fh:
            grid = json.load(fh)["grid"]

    phase, phase_note = verify_downbeat_phase(grid, plan["sync_anchor_film"])
    beats = grid["beats"]
    downbeats = downbeat_times(grid, phase)

    rows = []
    for b in film_boundaries(plan):
        beat, beat_err = nearest(beats, b["film_sec"])
        down, down_err = nearest(downbeats, b["film_sec"])
        rows.append({**b,
                     "nearest_beat_sec": round(beat, 3),
                     "beat_err_sec": round(beat_err, 3),
                     "nearest_downbeat_sec": round(down, 3),
                     "downbeat_err_sec": round(down_err, 3)})
    # The anchor is a row too: it is the one cut point already synced, and its
    # near-zero error is the calibration that proves the whole mapping.
    beat, beat_err = nearest(beats, plan["sync_anchor_film"])
    down, down_err = nearest(downbeats, plan["sync_anchor_film"])
    rows.append({
        "label": "SYNC ANCHOR (shipped)",
        "film_sec": plan["sync_anchor_film"],
        "src_out": plan["sync_anchor_src"],
        "src_in": plan["sync_anchor_src"],
        "seam": "the Sentinel shield -- anchored to the re-entry by the owner",
        "nearest_beat_sec": round(beat, 3),
        "beat_err_sec": round(beat_err, 3),
        "nearest_downbeat_sec": round(down, 3),
        "downbeat_err_sec": round(down_err, 3),
    })
    rows.sort(key=lambda r: abs(r["downbeat_err_sec"]))

    events = {"baseline_db": None, "drops": [], "note": None}
    if envelope is not None:
        raw_db, hop = envelope
        level = smooth(raw_db, SMOOTH_SEC, hop)
        baseline = baseline_of(level)
        events["baseline_db"] = round(baseline, 2)
        for drop in find_drops(level, hop, baseline):
            re = find_reentry(level, hop, raw_db, downbeats, drop, baseline)
            events["drops"].append({**drop, "reentry": re})
    else:
        events["note"] = f"WAV not found at {WAV_PATH}; grid analysis only"

    return {
        "act": plan["act"],
        "title": plan["title"],
        "bed_lead_sec": plan["bed_lead_sec"],
        "picture_sec": plan["picture_sec"],
        "grid": {
            "tempo_bpm": grid["tempo_bpm"],
            "bar_sec": grid["bar_sec"],
            "beats": len(beats),
            "stored_downbeat_phase": grid["downbeat_phase"],
            "reported_downbeat_phase": phase,
        },
        "phase_note": phase_note,
        "opportunities": rows,
        "events": events,
    }


# --- printing ----------------------------------------------------------------

def fmt(seconds):
    return build_efmb.fmt(seconds)


def print_report(rep):
    print(f"Act II -- {rep['title']}: beat map")
    print("  film time IS bed time: the bed plays end to end and the picture is "
          "fitted to it")
    print(f"  bed leads picture by {rep['bed_lead_sec']:.3f}s; kept picture "
          f"{rep['picture_sec']:.3f}s\n")

    g = rep["grid"]
    print(f"GRID  {g['beats']} beats, {g['tempo_bpm']} bpm, bar {g['bar_sec']}s")
    print(f"  stored downbeat_phase {g['stored_downbeat_phase']}, reported "
          f"phase {rep_phase(rep)}")
    print(f"  {rep['phase_note']}\n")

    print("CUT POINTS ON THE GRID -- ranked by how little the picture must move")
    print("  (signed err = film - grid: + is late, - is early)")
    print(f"  {'film':>10}  {'source seam':>22}  {'beat':>10}  {'err':>7}  "
          f"{'downbeat':>10}  {'err':>7}  what is across the seam")
    for r in rep["opportunities"]:
        flag = ""
        if abs(r["downbeat_err_sec"]) <= 0.05:
            flag = "  ON DOWNBEAT"
        elif abs(r["beat_err_sec"]) <= 0.05:
            flag = "  on beat"
        print(f"  {fmt(r['film_sec']):>10}  "
              f"{fmt(r['src_out']) + '->' + fmt(r['src_in']):>22}  "
              f"{fmt(r['nearest_beat_sec']):>10}  {r['beat_err_sec']:+7.3f}  "
              f"{fmt(r['nearest_downbeat_sec']):>10}  "
              f"{r['downbeat_err_sec']:+7.3f}  {r['label']}{flag}")
        print(f"{'':>14}{r['seam']}")

    ev = rep["events"]
    print("\nMUSICAL EVENTS -- measured from the WAV, not read off the grid")
    if ev["note"]:
        print(f"  {ev['note']}")
    else:
        print(f"  baseline level {ev['baseline_db']} dB (median of the "
              "1.5s-smoothed envelope)")
        for d in ev["drops"]:
            if d["kind"] == "intro":
                print(f"  intro    0:00.000 -> {fmt(d['down_until_sec'])}  "
                      f"({d['depth_db']:.1f} dB down) -- the song opens quiet")
            elif d["kind"] == "outro":
                print(f"  outro    {fmt(d['drop_sec'])} -> end  "
                      f"({d['depth_db']:.1f} dB down) -- the fade, no re-entry")
            else:
                print(f"  drop     {fmt(d['drop_sec'])} -> "
                      f"{fmt(d['down_until_sec'])}  "
                      f"({d['depth_db']:.1f} dB down)")
            re = d["reentry"]
            if re:
                off = re["onset_offset_sec"]
                off_txt = (f", hit measured {off:+.3f}s from the downbeat"
                           if off is not None else "")
                print(f"    re-enters on the downbeat at "
                      f"{fmt(re['downbeat_sec'])}{off_txt}")
    anchor = next(r for r in rep["opportunities"]
                  if r["label"].startswith("SYNC ANCHOR"))
    print(f"\nANCHOR  source {fmt(anchor['src_out'])} -> film "
          f"{fmt(anchor['film_sec'])}:  beat err "
          f"{anchor['beat_err_sec']:+.3f}s, downbeat err "
          f"{anchor['downbeat_err_sec']:+.3f}s")
    print("  the one cut already synced; its near-zero error calibrates all "
          "the others")


def rep_phase(rep):
    return rep["grid"]["reported_downbeat_phase"]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    envelope = None
    if WAV_PATH.exists():
        envelope = load_envelope_db(WAV_PATH)
    rep = analyze(envelope=envelope)

    if "--json" in argv:
        out = (argv[argv.index("--json") + 1]
               if len(argv) > argv.index("--json") + 1 else None)
        text = json.dumps(rep, indent=2)
        if out and not out.startswith("-"):
            Path(out).write_text(text + "\n")
            print(f"wrote {out}")
        else:
            print(text)
        return 0

    print_report(rep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

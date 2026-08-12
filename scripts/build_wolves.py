#!/usr/bin/env python3
"""Build the authored shotlist for *Seven Days to the Wolves*.

This is NOT ``tools/story.py``. There is no matcher and no index lookup for the
two new sources: their shots were picked by eye from contact sheets, because
tagging exists to feed the matcher and nothing here uses it.

Three acts, hinged on two measured moments in the bed:

    Act I    0.000 -> 182.834   the existing index
    Act II   182.834 -> 259.390 the compilation, from source 23:47
    Act III  259.390 -> 423.993 the crash, the swing, then the montage

The window crash (compilation source 24:46) is the FIRST shot of Act III, so it
lands on the flute entry. That is the one frame-accurate obligation in the cut.

Editorial rules enforced here rather than remembered:
  * no Savathun, ever
  * the Witness only as eyes or smoke, never its body
  * no major-enemy subject shots, no long drawn-out enemy holds
  * every mechanic card becomes the wolves artwork, in every instance
"""
import json
import glob
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BED = json.loads((REPO / "music/bed_seven_days_to_the_wolves.json").read_text())
GRID = BED["grid"]
BEAT = GRID["beat_interval_sec"]
BEATS = GRID["beats"]

ACT2_IN = 182.834          # the gallop
ACT3_IN = 259.390          # the flute entry — the crash lands here
END = 423.993

ART = str(Path.home() / "Pictures/Artwork/wolves.jpg")
COMP = "wolves_act2"       # compilation extract, source offset +1380s
TRAILER = "wolves_act3"    # Collection Trailer extract, 0:00-1:32

# --- the two new sources, picked by eye -------------------------------------
# (shot#, in, out) from /tmp/sheets/*/shots.json, rejects already removed.

# Act II: Neomuna. Source 23:47 is extract 47.1s.
ACT2_SHOTS = [
    (18, 47.1, 51.1), (19, 51.1, 54.0), (20, 54.0, 58.3), (21, 58.3, 59.2),
    (22, 59.2, 59.8), (23, 59.8, 60.9), (25, 63.1, 63.8), (26, 63.8, 65.0),
    (27, 65.0, 66.4), (28, 66.4, 67.4), (29, 67.4, 68.0), (30, 68.0, 69.4),
    (31, 69.4, 70.2), (32, 70.2, 71.7), (33, 71.7, 73.1), (34, 73.1, 74.9),
    (36, 76.8, 79.1), (37, 79.1, 80.2), (38, 80.2, 81.3), (39, 81.3, 83.3),
    (40, 83.3, 86.2), (41, 86.2, 88.2), (42, 88.2, 90.2), (44, 91.4, 92.2),
    (45, 92.2, 95.1), (46, 95.1, 99.8), (47, 99.8, 101.6),
]
# rejected: 24/35 (Cabal + Tormentor subject), 43 (smoke faces), 48/49 (Calus)

# Act III part A: the crash, then the strand descent. #50 IS the crash.
ACT3_COMP_A = [
    (50, 105.4, 107.4), (51, 107.4, 110.1), (52, 110.1, 111.1),
    (53, 111.1, 111.6), (54, 111.6, 113.1), (55, 113.1, 115.5),
    (56, 115.5, 116.5), (57, 116.5, 117.6), (58, 117.6, 119.8),
    (59, 119.8, 123.3), (61, 123.8, 125.3), (62, 125.3, 129.1),
    (63, 129.1, 133.0),
]
# Act III part C: the Final Shape climax — Guardians outnumbered in the Pale Heart.
ACT3_COMP_C = [
    (72, 152.8, 155.6), (74, 157.5, 159.5), (75, 159.5, 161.2),
    (76, 161.2, 163.2), (79, 171.0, 173.0), (80, 173.0, 175.0),
    (81, 175.0, 176.9), (82, 176.9, 179.6), (83, 179.6, 181.2),
    (86, 185.2, 187.0), (88, 195.7, 197.7), (89, 197.7, 198.8),
    (91, 199.3, 201.0), (92, 201.0, 202.8), (93, 202.8, 203.9),
    (94, 203.9, 204.9), (96, 205.8, 206.9), (98, 207.9, 210.0),
]
# rejected: 84/85/87/90/95/97 (pyramid/Witness body, debris holds), 71 (10s wasteland)

# Act III part B: the Collection Trailer montage, after the branded stretch ends.
ACT3_TRAILER = [
    (51, 55.0, 55.5), (52, 55.5, 56.0), (53, 56.0, 56.5), (54, 56.5, 57.0),
    (55, 57.0, 57.4), (56, 57.4, 58.4), (57, 58.4, 58.9), (58, 58.9, 59.3),
    (59, 59.3, 59.8), (60, 59.8, 60.9), (61, 60.9, 63.3),
    (65, 66.3, 67.4), (66, 67.4, 68.2), (67, 68.2, 68.8), (68, 68.8, 69.8),
    (69, 69.8, 70.3), (70, 70.3, 71.0),
    (72, 73.0, 74.2), (74, 74.6, 75.6), (75, 75.6, 76.5), (76, 76.5, 77.7),
    (77, 77.7, 78.5), (78, 78.5, 79.5), (79, 79.5, 80.1), (80, 80.1, 80.7),
    (81, 80.7, 81.2), (84, 82.4, 83.2), (85, 83.2, 84.2), (86, 84.2, 84.9),
    (87, 84.9, 86.5), (88, 86.5, 87.0), (89, 87.0, 87.4),
    (91, 89.4, 90.5), (92, 90.5, 91.4), (93, 91.4, 92.0),
]
# rejected: 62/71/90 are cards (below); 63/64 boss ogres; 73/82/83 enemy subjects

# Every black card that explains a mechanic. Recovered from the frames, not
# invented — each is replaced by the artwork, in every instance.
CARDS = [
    ("5 EXPANSIONS", 18.1, 19.9), ("4 CONTENT PACKS", 37.6, 39.6),
    ("10 DUNGEONS", 53.1, 55.0), ("7 RAIDS", 63.3, 65.2),
    ("ENDLESS BUILDCRAFTING", 71.0, 73.0), ("COUNTLESS LEGENDS", 87.4, 89.4),
]

# --- Act I: the existing index ----------------------------------------------
ENEMY_SUBJECT = (
    "ogre", "minotaur", "tormentor", "calus", "savathun", "witness", "wizard",
    "knight", "thrall", "goblin", "hydra", "acolyte", "shank", "captain",
    "cabal", "psion", "harpy", "servitor", "colossus", "centurion", "legionary",
)
BANNED = ("savathun", "witness")


def load_index():
    # Only sources whose media is actually present: a shot render.py cannot
    # resolve is silently skipped, which shortens the cut and slides every
    # later anchor off the beat. media/ is gitignored, so this varies by host.
    have = {p.stem for p in (REPO / "media").glob("*") if p.is_file()}
    segs = []
    for f in glob.glob(str(REPO / "segments/*.json")):
        d = json.loads(Path(f).read_text())
        segs.extend(d if isinstance(d, list) else [d])
    out = []
    for s in segs:
        if not s.get("clean"):
            continue
        if s["video_id"] not in have:
            continue
        cap = (s.get("caption") or "").lower()
        chars = " ".join(
            (c.get("name", "") if isinstance(c, dict) else str(c)).lower()
            for c in (s.get("character") or [])
        )
        # Never Savathun; never the Witness (its only clean shots here are body).
        if any(b in cap[:60] for b in BANNED) or any(b in chars for b in BANNED):
            continue
        # The enemy must not be the subject of the frame.
        if any(w in cap[:46] for w in ENEMY_SUBJECT):
            continue
        out.append(s)
    return out


def heroic(s):
    sc = 0
    comp = s.get("composition") or []
    if s.get("camera_angle") == "low":
        sc += 3
    if "group" in comp or "crowd" in comp:
        sc += 3
    if "establishing" in comp:
        sc += 1
    if s.get("subject_salience") == "hero":
        sc += 2
    sc += min(s.get("register", 0), 3)
    if s.get("action"):
        sc += 1
    if s.get("faction"):
        sc += 1          # Guardians with hostiles in frame = outnumbered
    return sc


def snap(t):
    """Nearest beat — every cut lands on the grid."""
    return min(BEATS, key=lambda b: abs(b - t))


def fill(span_start, span_end, pool, max_hold, min_hold, video_id, offset=0.0,
         cards=None, beat_step=1):
    """Lay shots across a span, snapping every cut to the beat grid."""
    shots = []
    t = span_start
    i = 0
    cards = list(cards or [])
    while t < span_end - 0.05 and (i < len(pool) or cards):
        # A card interrupts wherever its source moment falls in the montage.
        use_card = cards and i and i % max(1, len(pool) // (len(cards) + 1)) == 0
        if use_card:
            name, cs, ce = cards.pop(0)
            dur = min(ce - cs, span_end - t)
            dur = max(dur, BEAT * 2)
            shots.append({
                "segment_id": f"card_{len(shots):03d}",
                "still": ART, "duration": round(min(dur, span_end - t), 3),
                "beat": f"ARTWORK (was: {name})",
            })
            t += shots[-1]["duration"]
            continue
        n, a, b = pool[i]
        i += 1
        avail = b - a
        want = min(max_hold, avail)
        # Snap the out-point to the grid so the cut lands with the music.
        end = snap(t + want)
        dur = end - t
        if dur < min_hold:
            dur = min(min_hold, avail)
        if dur > avail:
            dur = avail
        if t + dur > span_end:
            dur = span_end - t
        if dur < 0.25:
            break
        shots.append({
            "segment_id": f"{video_id}_{n:03d}",
            "video_id": video_id,
            "start_sec": round(a, 3), "end_sec": round(b, 3),
            "duration": round(dur, 3),
            "start_tc": f"{int(a)//60}:{a%60:04.1f}",
            "end_tc": f"{int(b)//60}:{b%60:04.1f}",
            "beat": f"{video_id} #{n} (source {int((a+offset)//60)}:{(a+offset)%60:04.1f})",
        })
        t += dur
    return shots, t


def main():
    shots = []

    # ---- Act I ------------------------------------------------------------
    idx = load_index()
    idx.sort(key=lambda s: -heroic(s))
    # Open wide and quiet, end loud: establishing shots first, action last.
    picked = sorted(idx, key=lambda s: (
        0 if "establishing" in (s.get("composition") or []) else 1,
        -(s.get("register") or 0) if s.get("action") else 0,
    ))
    used = set()
    t = 0.0
    for s in picked:
        if t >= ACT2_IN - 0.05:
            break
        avail = s["end_sec"] - s["start_sec"]
        want = min(3.2, avail)
        dur = snap(t + want) - t
        if dur < 0.8:
            dur = min(1.2, avail)
        dur = min(dur, avail, ACT2_IN - t)
        if dur < 0.3:
            continue
        used.add(s["segment_id"])
        shots.append({
            "segment_id": s["segment_id"], "video_id": s["video_id"],
            "start_sec": s["start_sec"], "end_sec": s["end_sec"],
            "duration": round(dur, 3),
            "start_tc": s["start_tc"], "end_tc": s["end_tc"],
            "beat": f"I. {s['caption'][:70]}",
        })
        t += dur
    act1_end = t
    assert abs(act1_end - ACT2_IN) < 0.15, (
        f"Act I is {act1_end:.2f}s but the gallop is at {ACT2_IN:.2f}s. "
        "The cut is a concatenation, so a short act slides every later anchor.")

    # ---- Act II: the gallop ----------------------------------------------
    a2, t = fill(ACT2_IN, ACT3_IN, ACT2_SHOTS, max_hold=3.0, min_hold=0.8,
                 video_id=COMP, offset=1380.0)
    shots += a2
    # Anything left before the crash is covered by holding the last Neomuna beats.
    while t < ACT3_IN - 0.05:
        extra, t2 = fill(t, ACT3_IN, ACT2_SHOTS[::-1], 2.4, 0.8, COMP, 1380.0)
        if not extra:
            break
        shots += extra
        t = t2
    assert abs(t - ACT3_IN) < 0.15, (
        f"Act II ends at {t:.2f}s but the flute entry is at {ACT3_IN:.2f}s. "
        "The window crash must land on the beat change.")

    # ---- Act III: the crash lands exactly here ---------------------------
    for pool, mx, mn, vid, off, cards in (
        (ACT3_COMP_A, 2.6, 0.6, COMP, 1380.0, None),
        (ACT3_TRAILER, 1.6, 0.45, TRAILER, 0.0, CARDS),
        (ACT3_COMP_C, 2.0, 0.6, COMP, 1380.0, None),
    ):
        part, t = fill(t, END, pool, mx, mn, vid, off, cards=cards)
        shots += part

    # Still short? The index closes it out rather than the cut ending early.
    tail = [s for s in idx if s["segment_id"] not in used]
    ti = 0
    while t < END - 0.05 and ti < len(tail):
        s = tail[ti]
        ti += 1
        avail = s["end_sec"] - s["start_sec"]
        dur = min(snap(t + min(1.8, avail)) - t, avail, END - t)
        if dur < 0.4:
            continue
        shots.append({
            "segment_id": s["segment_id"], "video_id": s["video_id"],
            "start_sec": s["start_sec"], "end_sec": s["end_sec"],
            "duration": round(dur, 3),
            "start_tc": s["start_tc"], "end_tc": s["end_tc"],
            "beat": f"III. {s['caption'][:60]}",
        })
        t += dur

    # The song fades to silence over its last bars. Rather than truncate the
    # bed (concat passes -shortest, so a short picture would cut the fade off),
    # hold the artwork over it: the outro card the cut was always going to want.
    if t < END - 0.05:
        shots.append({
            "segment_id": "card_outro",
            "still": ART, "duration": round(END - t, 3),
            "beat": "ARTWORK (outro, over the fade)",
        })
        t = END

    out = {
        "title": "Seven Days to the Wolves",
        "bed": "bed_seven_days_to_the_wolves",
        "anchors": {"act2_gallop_in": ACT2_IN, "act3_flute_change": ACT3_IN},
        "note": "AUTHORED shotlist, not a story.py output. Hand-picked from "
                "contact sheets; the two new sources are not in segments/.",
        "shots": shots,
    }
    dest = REPO / "stories/seven-days-prototype.json"
    dest.write_text(json.dumps(out, indent=1))
    total = sum(s["duration"] for s in shots)
    print(f"{len(shots)} shots, {total:.1f}s (bed {END:.1f}s)")
    print(f"  Act I   {act1_end:6.1f}s")
    print(f"  Act II  {ACT3_IN - ACT2_IN:6.1f}s")
    print(f"  Act III {total - ACT3_IN:6.1f}s")
    print(f"  cards placed: {sum(1 for s in shots if s.get('still'))}/{len(CARDS)}")
    print(f"-> {dest}")


if __name__ == "__main__":
    main()

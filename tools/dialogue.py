#!/usr/bin/env python3
"""Recovered dialogue -> timed chat plates on a rendered cut.

The repo never invents on-screen copy, so a conversation shown on screen has to
come from somewhere: ``dialogue/<video_id>/dialogue.json`` holds the recovered
lines, their source timecodes, and which cast character said each one, beside
the ``DIALOGUE.md`` the owner edits. This module maps those source-timed cues
onto the timeline a cut actually produced, and emits chat-card entries for
tools/plate.py.

Two rules follow from the repo contract:

* **The speaker is the cast person, resolved from vocab/casting.yaml.** A cue
  names a *character*; the card shows the *person* bound to that character. An
  uncast character produces no card rather than a guessed name.
* **A line whose footage is not in the cut is dropped and reported.** The cut is
  built from the shots that exist; dialogue does not get to drag unused footage
  back in, and it is never dropped silently.
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.plate import MIN_HOLD, TAIL_OUT, cut_timeline  # noqa: E402

DIALOGUE_DIR = REPO_ROOT / "dialogue"

# One folder per video, so a video's conversation sits beside the Markdown the
# owner actually edits (``DIALOGUE.md``) instead of being a lone JSON file named
# after it. The record the pipeline reads is ``dialogue.json``; the Markdown is
# the authoring surface, and tools/dialogue_md.py keeps the two in step.
RECORD_NAME = "dialogue.json"
MARKDOWN_NAME = "DIALOGUE.md"


def video_dir(video_id, root=DIALOGUE_DIR):
    """The folder holding one video's conversation."""
    return Path(root) / video_id


def record_path(video_id, root=DIALOGUE_DIR):
    return video_dir(video_id, root) / RECORD_NAME


def markdown_path(video_id, root=DIALOGUE_DIR):
    return video_dir(video_id, root) / MARKDOWN_NAME

# A dialogue card is read, not studied: long enough to finish the line, short
# enough that it does not outstay the shot it belongs to.
MAX_CHAT_HOLD = 6.0


def load_dialogue(video_id, root=DIALOGUE_DIR):
    with record_path(video_id, root).open(encoding="utf-8") as fh:
        return json.load(fh)


def _speaker_for(character, leads):
    """Character key -> its canonical GitHub login on the chat pill."""
    identity = _identity_for(character, leads)
    return identity["speaker"] if identity else None


def _identity_for(character, leads):
    """Character key -> its canonical chat identity, or None when unbound."""
    entry = leads.get(character) or {}
    login = entry.get("person")
    if not login:
        return None
    from tools.identity import chat_identity
    return chat_identity(login)


def _avatar_for(character, leads):
    identity = _identity_for(character, leads)
    return identity["avatar"] if identity else None


def lanes_for(cues):
    """Character -> chat lane, so a two-hander reads as two sides.

    Every pill in one lane is the fault the owner named on act III: the cards
    stack in the same place and the eye has to *read the name* to tell a reply
    from the same person carrying on. Sides do that work before the words are
    read at all, which is how every chat interface has ever done it.

    Lanes go by first appearance, so the mapping is deterministic and stable
    across rebuilds. Two voices take the two sides; a THIRD takes the centre,
    which still gives every speaker a position of their own -- and an
    interloper in the middle of a two-hander reads as exactly that.

    Beyond three, a position stops identifying anybody, so everybody keeps the
    single centre lane and the name does the work again. That is the fault the
    owner named on this act -- cards stacking in one place, so the eye has to
    *read the name* to tell a reply from the same person carrying on -- and it
    is accepted only when there is no arrangement that avoids it.
    """
    order = []
    for cue in cues:
        who = cue.get("character")
        if who and who not in order:
            order.append(who)
    if len(order) == 2:
        return {order[0]: "left", order[1]: "right"}
    if len(order) == 3:
        return {order[0]: "left", order[1]: "right", order[2]: "center"}
    return {}


def plan_chat(cues, shots, leads, max_shot_sec=None, hold=MAX_CHAT_HOLD, busy=None,
              skip_uncertain=True, log=None):
    """Source-timed cues + a cut list -> chat plate entries.

    Returns ``(entries, dropped)``. ``dropped`` carries a reason per cue so an
    unheard line is always accounted for.

    ``busy`` holds windows that are already spoken for -- in practice the lead
    reveals, which are planned first because naming the cast correctly is the
    job this index exists to do. An anchored line cannot slide out of the way
    without landing after its own beat, so a line that collides is dropped and
    reported rather than shown late.

    A cue the recovered record marks ``evidence: "uncertain"`` is a turn the
    anchors do not settle -- the record is saying it does not know which of two
    real people said it. Rendering it anyway picks one of them and credits a
    real person with words that may be somebody else's, so it is dropped by
    default, exactly as ``plan_script`` already did. ``skip_uncertain=False``
    is available for a caller who has settled the speaker another way.
    """
    timeline = cut_timeline(shots, max_shot_sec)
    total = sum(duration for _, duration, _ in timeline)
    busy = list(busy or [])
    lanes = lanes_for(cues)

    placed, dropped = [], []
    for cue in cues:
        if skip_uncertain and cue.get("evidence") == "uncertain":
            dropped.append({**cue, "reason": "speaker not settled by the anchors"})
            continue
        speaker = _speaker_for(cue["character"], leads)
        if not speaker:
            dropped.append({**cue, "reason": f"{cue['character']} is not cast"})
            continue

        # Earliest point in the finished cut where this cue's footage appears.
        landing = None
        for out_start, duration, shot in timeline:
            src_start = shot["start_sec"]
            src_end = src_start + duration  # the hold cap trims from the tail
            overlap = min(cue["end_sec"], src_end) - max(cue["start_sec"], src_start)
            if overlap <= 0:
                continue
            at = out_start + max(0.0, cue["start_sec"] - src_start)
            if landing is None or at < landing:
                landing = at
        if landing is None:
            dropped.append({**cue, "reason": "its footage is not in this cut"})
            continue

        spoken = cue["end_sec"] - cue["start_sec"]
        entry = {
            "id": cue["id"], "at": round(landing, 3),
            "dur": round(min(spoken, hold), 3),
            "position": lanes.get(cue["character"], "center"), "kind": "chat",
            "speaker": speaker, "text": cue["text"],
        }
        avatar = _avatar_for(cue["character"], leads)
        if avatar:
            entry["avatar"] = avatar
        placed.append(entry)

    placed.sort(key=lambda e: e["at"])

    # One plate at a time: clamp each card against the next one and the end of
    # the cut, then drop whatever no longer holds long enough to read.
    entries = []
    for i, entry in enumerate(placed):
        ceiling = placed[i + 1]["at"] if i + 1 < len(placed) else total
        for b_start, b_end in busy:
            if b_start >= entry["at"]:
                ceiling = min(ceiling, b_start)
        if any(b_start <= entry["at"] < b_end for b_start, b_end in busy):
            dropped.append({"id": entry["id"], "text": entry["text"],
                            "reason": "a reveal already holds the screen here"})
            continue
        room = ceiling - TAIL_OUT - entry["at"]
        if room < MIN_HOLD:
            dropped.append({"id": entry["id"], "text": entry["text"],
                            "reason": "no readable gap before the next line"})
            continue
        entry["dur"] = round(min(entry["dur"], room), 3)
        entries.append(entry)
        if log:
            log(f"  {entry['id']:<4} {entry['at']:6.2f}s +{entry['dur']:.1f}s  "
                f"{entry['speaker']}: {entry['text'][:52]}")

    if log:
        for item in dropped:
            log(f"  DROPPED {item.get('id', '?'):<4} {item['reason']}: "
                f"{item.get('text', item.get('raw', ''))[:48]}")
    return entries, dropped


def plan_script(cues, shots, leads, max_shot_sec=None, hold=MAX_CHAT_HOLD,
                busy=None, skip_uncertain=True, log=None, start_at=0.0):
    """Same cues, laid out as a SCRIPT rather than anchored to their footage.

    ``plan_chat`` puts every line where its own footage landed, which is the
    honest mapping and the right one for an uncut source. A re-ordered cut
    breaks it: the shots arrive in editorial order, so the surviving lines play
    out of sequence and stop reading as a conversation.

    Script mode keeps the exchange in the order it was spoken and paces it
    across the finished cut, flowing around ``busy`` windows so a Guardian
    reveal is never buried under dialogue. The words and the speakers are still
    only ever the recovered ones; what changes is *when* a line appears, which
    is an editing decision the cut already made for the picture.
    """
    timeline = cut_timeline(shots, max_shot_sec)
    total = sum(duration for _, duration, _ in timeline)
    busy = sorted(busy or [])
    lanes = lanes_for(cues)

    def next_free(cursor, duration):
        """First point at or after ``cursor`` where ``duration`` fits."""
        moved = True
        while moved:
            moved = False
            for b_start, b_end in busy:
                if cursor < b_end and cursor + duration + TAIL_OUT > b_start:
                    cursor = b_end + TAIL_OUT
                    moved = True
        return cursor

    entries, dropped, cursor = [], [], float(start_at)
    for cue in cues:
        if skip_uncertain and cue.get("evidence") == "uncertain":
            dropped.append({**cue, "reason": "speaker not settled by the anchors"})
            continue
        speaker = _speaker_for(cue["character"], leads)
        if not speaker:
            dropped.append({**cue, "reason": f"{cue['character']} is not cast"})
            continue

        spoken = cue["end_sec"] - cue["start_sec"]
        duration = max(MIN_HOLD, min(spoken, hold))
        pin = cue.get("pin_sec")
        if pin is not None:
            # An owner-placed pin lands exactly (film seconds). The packing
            # rules are not consulted: the pin IS the instruction. Both
            # collisions it can cause -- onto the previous line, or onto a
            # fixed card -- are refused loudly downstream by
            # load_manifest_entries, and warned about here so the log says
            # which pin did it before the build fails.
            at = float(pin)
            if log:
                if at < cursor:
                    log(f"  WARNING {cue['id']}: pinned at {at:.2f}s but the "
                        f"previous line holds until {cursor - TAIL_OUT:.2f}s")
                for b_start, b_end in busy:
                    if at < b_end and at + duration + TAIL_OUT > b_start:
                        log(f"  WARNING {cue['id']}: pinned at {at:.2f}s "
                            f"inside a fixed card window "
                            f"{b_start:.2f}-{b_end:.2f}s")
        else:
            at = next_free(cursor, duration)
        if at + duration > total - TAIL_OUT:
            dropped.append({**cue, "reason": "the cut ends before this line"})
            continue
        entry = {
            "id": cue["id"], "at": round(at, 3), "dur": round(duration, 3),
            "position": lanes.get(cue["character"], "center"), "kind": "chat",
            "speaker": speaker, "text": cue["text"],
        }
        avatar = _avatar_for(cue["character"], leads)
        if avatar:
            entry["avatar"] = avatar
        entries.append(entry)
        cursor = at + duration + TAIL_OUT
        if log:
            log(f"  {cue['id']:<4} {at:6.2f}s +{duration:.1f}s  "
                f"{speaker}: {cue['text'][:52]}")

    if log:
        for item in dropped:
            log(f"  DROPPED {item.get('id', '?'):<4} {item['reason']}: "
                f"{item.get('text', item.get('raw', ''))[:48]}")
    return entries, dropped


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Plan chat plates from recovered dialogue.")
    ap.add_argument("shotlist", help="JSON cut list from tools/story.py")
    ap.add_argument("--video-id", required=True,
                    help="which dialogue/<video_id>/dialogue.json to read")
    ap.add_argument("--max-shot-sec", type=float, default=None,
                    help="the same hold cap render.py was given, so timings line up")
    ap.add_argument("--hold", type=float, default=MAX_CHAT_HOLD)
    ap.add_argument("--mode", choices=("anchored", "script"), default=None,
                    help="anchored: each line sits where its own footage landed. "
                         "script: the exchange runs in spoken order across the cut. "
                         "Defaults to the dialogue record's display.mode, then "
                         "anchored.")
    ap.add_argument("--around", default=None,
                    help="a plate manifest whose windows the dialogue must avoid, "
                         "so a reveal is never buried under a line")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    from tools.derive import load_leads
    from tools.plate import load_manifest, load_manifest_entries
    from tools.render import load_shots

    data = load_dialogue(args.video_id)
    display = data.get("display") or {}
    mode = args.mode or display.get("mode", "anchored")
    shots, leads = load_shots(args.shotlist), load_leads()
    busy = []
    if args.around:
        busy = [(float(e["at"]), float(e["at"]) + float(e["dur"]))
                for e in load_manifest(args.around)]

    if mode == "script":
        entries, dropped = plan_script(
            data["cues"], shots, leads, max_shot_sec=args.max_shot_sec,
            hold=args.hold, busy=busy,
            skip_uncertain=True, log=print,
            start_at=float(display.get("start_sec", 0.0)))
    else:
        entries, dropped = plan_chat(
            data["cues"], shots, leads, max_shot_sec=args.max_shot_sec,
            hold=args.hold, busy=busy,
            skip_uncertain=True, log=print)

    load_manifest_entries(entries)  # the same validation the burn path applies
    with Path(args.out).open("w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2)
        fh.write("\n")
    print(f"wrote {args.out} ({len(entries)} line(s), {len(dropped)} dropped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

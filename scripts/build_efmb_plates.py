#!/usr/bin/env python3
"""Build act II's plate manifest -- who is on screen, and when.

    python3 scripts/build_efmb_plates.py            # print the manifest
    python3 scripts/build_efmb_plates.py --write    # write it
    python3 scripts/build_efmb_plates.py --check    # CI: committed == generated

WHY THIS SCRIPT EXISTS
----------------------
``vocab/casting.yaml`` holds the **copy** -- the words on the card -- and
``tools/ensemble.py`` assigns anonymous slots by deterministic round-robin.
Neither can do what act II needs, which is **positional casting**: the owner
named specific people in specific places in the frame.

    "0:55 left to right, Joseph Sandoval, Ricardo from CERN, Karena Angel"

Round-robin cannot express that, and it must not try -- it would put a real
person's name on whichever body the rotation happened to land on. So the
binding of person to shot is authored here, once, and everything else is
derived.

THE TWO CLOCKS, AND WHY EVERY WINDOW BELOW IS IN SOURCE TIME
------------------------------------------------------------
Every mark the owner gave for this act was a FILM timecode, and the film has
moved under all of them: the head lead went 8.564 -> 10.650, run 1's out point
moved 6.467 -> 4.017, and the mech and the publisher end cards are gone. His
``0:55`` now points 0.364 s away from what he meant, and his ``4:50`` by 2.131.

So the windows below are **source** timecodes -- positions in a file that has
not changed -- and film time is computed by ``build_efmb.film_for_source``.
Nothing here types a film timecode, and a binding whose frame gets cut raises
rather than silently sliding onto whatever now occupies that second.

MEASURED, NOT GUESSED
---------------------
Every window is a shot boundary from ``ContentDetector(threshold=27)`` over the
source, and every one was then **looked at** before a name was attached to it.
That second step is not ceremony. Detection reported the trio as a single
18.77 s shot, because the sequence is built from dissolves and a dissolve is
invisible to a content detector -- the same blind spot that let 2.45 s of
live-action framing narration survive the pass whose whole purpose was removing
it. Detection proposes; the eye disposes.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
- **No invented copy.** Every word comes from ``vocab/casting.yaml`` verbatim.
  A person the owner named but authored no plate for (``ensemble.placeholders``)
  renders as a *named placeholder*, never as a credit with a title nobody wrote.
- **No plate on the burned-in title.** Source 356.500 -> 358.200 carries
  Bungie's "NEW LEGENDS WILL RISE" across the middle of frame. Nothing is
  placed there.
- **No pointer at a body.** A row of names is spread evenly across the frame in
  the order the owner gave, never positioned to single out a figure -- the rule
  ``tools/plate.py`` already applies to ensemble rows, for the same reason.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_efmb  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "02-endless-forms-plates.json"
# THE ROSTER IS AN INPUT, SO IT IS COMMITTED.
#
# tools/ensemble.py FETCHES a month's contributors from GitHub into
# gitignored renders/. That is fine for a scratch artifact and wrong for this:
# the roster decides WHICH REAL PEOPLE this act credits, so it is an authored
# input to the cut, and a manifest generated from a file nobody else has cannot
# be checked, reproduced, or reviewed. CI proved the point by failing on a
# missing renders/roster-2026-08.json.
#
# Committed under stories/, the same way the summit photo list and the megacut
# manifests are, and for the same reason.
ROSTER = REPO_ROOT / "stories" / "roster-2026-08.json"

# WHERE AVATARS LIVE, AND WHY THE MANIFEST NEVER CARRIES A URL.
#
# vocab/casting.yaml records each person's avatar as a GitHub URL, because that
# is the durable identifier. tools/plate.py needs a LOCAL FILE -- the renderer
# never touches the network -- so a URL handed to it silently falls back to the
# drawn crest with a punch-list warning, which is how every wreathed plate in
# this act was quietly rendering without its portrait.
#
# So the manifest carries the cache path and keeps the URL beside it as
# provenance. The picture is a fetched artifact, so it lives in gitignored
# renders/ like every other one; missing it degrades to the crest rather than
# blocking, and `--fetch-avatars` fills it in.
AVATAR_DIR = Path("renders") / "avatars"

# --- the authored bindings -------------------------------------------------
# (source_in, source_out) is the SHOT, measured. `hold` is how long the plate
# stays up; it may ride past the shot's out point, which is normal for a lower
# third and is what lets a 1.6 s shot carry a 2.2 s credit.

# The trio. One continuous dissolve sequence, 69.533 -> 88.300 by detection,
# but the three Guardians only read as three separate figures between ~71.5 and
# ~75.0: after that the camera pushes in and the hooded Hunter fills the frame
# alone. So the row goes up inside that window and is gone before the push-in.
#
# The ORDER is the owner's, left to right. The x positions are an even spread
# computed by tools/plate.py, NOT a pointer at each body -- naming the order he
# gave is honouring the instruction; drawing an arrow at a specific Guardian
# would claim more than anyone verified.
TRIO_IN, TRIO_OUT = 72.000, 75.000
# `position` is the frame third each card sits in, in the owner's order. Three
# cards at full size would collide across 1920 px, so the row is scaled down --
# the same lever the reference deck's roll call pulls.
TRIO_SCALE = 0.62
TRIO = [
    ("joseph_sandoval", "left"),
    ("rochaporto", "center"),
    ("mara_sov", "right"),
]

# One person, one shot. Each verified by eye at the frame named in `seen`.
SOLO = [
    {
        "key": "wrkode",
        "src": (185.233, 188.067),
        "seen": 185.502,
        "why": "the lone Hunter walking the Dreadnaught, Ghost at his shoulder",
    },
    {
        "key": "KyleGospo",
        "src": (335.267, 339.767),
        "seen": 338.200,
        # HIS NAME ARRIVES ON THE SLAM. 338.200 is the sync anchor -- the
        # Sentinel's shield at full extension -- pinned to film 269.700, the
        # downbeat the full band re-enters on after the breakdown. Deriving the
        # plate's `at` from the same anchor means the card and the shield and
        # the drum land together, and stay together if a run ever moves.
        "at_src": build_efmb.SYNC_ANCHOR_SRC,
        "why": "the Sentinel raising the Void shield, on the re-entry downbeat",
    },
    {
        "key": "p5",
        "src": (342.433, 344.000),
        "seen": 343.500,
        "why": "the hooded, caped Hunter, blade raised, magenta arc blooming",
    },
    {
        "key": "EyeCantCU",
        "src": (353.533, 355.167),
        "seen": 354.600,
        "why": "the Warlock, arms spread, going off in a wreath of solar fire",
    },
]

# The people the owner NAMED for act II but authored no plate copy for
# (`ensemble.placeholders`). They are credited as named placeholders: the name
# he gave, and the neutral eyebrow -- no title, no class, no seal, because
# nobody wrote one. This is the "missing, so omit and record" case, and it is
# the opposite of inventing the words to fill the row.
PLACEHOLDERS = [
    {"key": "dylan_taylor", "src": (147.633, 150.533), "seen": 148.500,
     "why": "the Titan walking out of the dark"},
    # RE-ANCHORED. He was on 171.800 -> 174.433, which ends under Bungie's
    # burned-in "BECOME LEGEND" -- the plate went up and the publisher's title
    # came up with it. Found by looking at the burned film rather than at the
    # manifest, which is the only place it was ever going to show.
    {"key": "ahmedadan", "src": (241.167, 244.833), "seen": 242.500,
     "why": "three Guardians, supers lit, before the throne"},
]

# The blueberries -- the month's contributors, in the anonymous slots. Copy is
# resolved by tools/plate.py's own ensemble path, so a contributor whose
# identity IS authored gets it verbatim and everyone else gets the generic
# blueberry plate with the eyebrow their org membership earns. Leads are
# excluded: castrojo is Cayde-6 and is credited only where Cayde is on screen.
BLUEBERRY_SHOTS = [
    {"src": (90.767, 96.500), "seen": 92.500,
     "why": "the hooded Hunter and his Ghost, close"},
    {"src": (195.267, 198.967), "seen": 196.500,
     "why": "two Guardians climbing the stair into the light"},
    {"src": (233.500, 238.200), "seen": 235.000,
     "why": "the Guardian reaching out over the neon city"},
]
BLUEBERRY_EXCLUDE = {"castrojo"}  # a lead; see the comment above

# Cayde signs off. Source 358.200 -> 360.500 is 2.30 s against a 2.2 s minimum
# hold, so it fits by a tenth of a second -- DO NOT SHORTEN IT. It is the
# second-to-last shot: he says it, and then three figures walk into the
# cathedral light.
#
# The line is the OWNER'S, not Bungie's. Bungie's Cayde never said it, so it
# lives in dialogue/ as owner-authored and is reproduced here; it must never
# read as recovered source dialogue.
#
# THE SPEAKER IS REDACTED, AND ONLY IN THIS ACT. The `cayde_6` binding names
# Jorge Castro, and that name is correct everywhere else in the programme --
# he is revealed as Cayde later, so acts I and III-VII are untouched. Here the
# joke depends on the audience not being told yet, so the pill reads
# `[ REDACTED ]`. The bracketed form is the owner's own treatment, the same one
# he authored for `[ p5 ]` and `[ EyeCantCU ]`; it is a redaction of a name
# this repo already knows, never an invented one.
CAYDE = {
    "src": (358.200, 360.500),
    "seen": 359.000,
    "why": "the hero pose under the caged Traveler, neon city behind",
    "redacted_speaker": "[ REDACTED ]",
    "reveals": "cayde_6",
}

LEAD_IN = 0.4      # let the cut land before the plate arrives
MIN_HOLD = 2.2     # below this a plate cannot be read

# ACT II'S SUB-CHAPTERS.
#
# The act has two moments the owner wants findable from a scrub bar: the TOC
# trio arriving out of the fog, and Rizzo's shot. They are anchored to the same
# SOURCE timecodes the plates use, so a chapter and the credit it belongs to
# can never drift apart.
#
# A chapter starts where the SHOT starts, not where the plate does -- the plate
# is 0.4 s late on purpose, to let the cut land first, and a marker that drops
# the audience 0.4 s into a shot has dropped them into the middle of it.
#
# These are emitted in FILM time and go no further. tools/megacut.py derives
# the programme's chapters from act SLIDES only, and stories/megacut/megacut.json
# belongs to whoever is assembling the programme -- an act does not get to
# write into it. Consuming these is issue #92.
CHAPTERS = [
    (TRIO_IN, "TOC"),
    (185.233, "Rizzo"),
]
# HOW LONG A CREDIT STAYS UP.
#
# Owner instruction, from the first alpha watch: "at a bare minimum keep the
# nameplates up longer it's worth it this is a hero video we want people's
# moments to shine". These held 3.2 s and 2.6 s for the alpha; that was long
# enough to READ a name and too short for it to land.
#
# The ceiling is not the shot. A lower third may ride past its shot's out point
# -- that is normal, and it is what lets a 1.6 s shot carry a credit -- so the
# real ceiling is the NEXT plate in the same frame position, enforced by
# `space_plates` rather than by hand-checking pairs.
SOLO_HOLD = 4.5
TRIO_HOLD = 4.0

# The gap between two credits in the same position. Below this the outgoing
# card and the incoming one read as one flicker rather than two people.
PLATE_GAP = 0.25

# The trio arrives one card at a time, 0.8 s apart, and the row clears
# together. Owner instruction, same note: "stagger intros so that each
# character has a shot to shine". Sequential lower thirds -- one card up, out,
# then the next -- would need 3 x (2.2 + 0.25) = 7.35 s and the trio only reads
# as three separate figures for 3.0 s, so the row still assembles inside the
# window it is true for; what is staggered is the ENTRANCE, which is the beat
# that gives each name its own moment.
TRIO_STAGGER = 0.8

# Spans no plate may be visible over, in SOURCE time.
#
# Bungie burns "NEW LEGENDS WILL RISE" across the middle of the frame here. The
# act removes every other title card in the source -- including one named in
# build_efmb.REMOVED as "burned-in end title: BECOME LEGEND" -- but this one is
# welded to picture the act keeps, the end fight, so it cannot be cut without
# losing the fight. Laying our own credit over the publisher's is the one thing
# that would make it look deliberate, so the plates clear it instead.
NO_PLATE_SRC = [
    # Bungie burns "BECOME LEGEND" over the cave at the end of run 2, fading in
    # around 172.5 and holding to the cut. The act removes a DIFFERENT instance
    # of this same title (build_efmb.REMOVED names 244.833 -> 246.100); this one
    # is inside picture the act keeps.
    (172.500, 174.433, "Bungie's burned-in 'BECOME LEGEND'"),
    (356.500, 358.200, "Bungie's burned-in 'NEW LEGENDS WILL RISE'"),
]


def _zones(film_of):
    return [(film_of(a), film_of(b - 0.001), why) for a, b, why in NO_PLATE_SRC]


def clamp_hold(at, hold, film_of):
    """Shorten a plate so it never runs into a no-plate zone.

    Returns None if the shortened plate would be too brief to read -- better no
    credit than an unreadable one, and the caller reports it rather than
    quietly dropping somebody.
    """
    for start, end, why in _zones(film_of):
        if start <= at <= end:
            raise ValueError(
                f"a plate at {at:.3f}s starts inside {why} -- re-anchor it to "
                "another shot rather than trimming it")
        if at < start < at + hold:
            hold = round(start - at, 3)
    return hold if hold >= MIN_HOLD else None


def load_casting():
    import yaml
    with open(REPO_ROOT / "vocab" / "casting.yaml") as fh:
        return yaml.safe_load(fh)


def _titles(casting):
    return {k: v for k, v in casting["ensemble"]["titles"].items()
            if k != "description"}


def authored_copy(key, casting):
    """The plate copy for ``key``, verbatim from vocab/casting.yaml.

    Two places hold authored copy and they are not interchangeable: a LEAD's
    plate lives on its binding (Karena is cast as Mara Sov), and an individual
    contributor's lives under ``ensemble.titles``. Reproducing, never
    composing, is the whole rule -- so this raises rather than falling back to
    generic copy if a key is missing, because a silent fallback would put the
    blueberry plate on somebody whose identity the owner actually wrote.
    """
    titles = _titles(casting)
    if key in titles:
        return dict(titles[key])
    binding = casting.get("leads", {}).get("values", {}).get(key)
    if binding and binding.get("plate"):
        return dict(binding["plate"])
    raise KeyError(
        f"no authored plate copy for {key!r} in vocab/casting.yaml -- copy is "
        "reproduced, never composed, so this is a gap for the owner to fill "
        "rather than something to work around")


def placeholder_copy(key, casting):
    """A named placeholder badge: the owner's name, and nothing invented.

    ``ensemble.placeholders`` is a queue, not copy -- these are people he named
    with no plate authored. They are still credited, because a missing word is
    omitted and recorded rather than allowed to block, but every row nobody
    wrote is simply absent.
    """
    entry = casting["ensemble"]["placeholders"][key]
    generic = casting["ensemble"]["plate"]
    return {
        "label": generic.get("label_unknown", "GUARDIAN"),
        "name": entry["name"],
        "placeholder": True,
    }


def roster_items(casting):
    """The month's contributors, minus anyone already credited elsewhere.

    Two exclusions, and both are about not crediting one person twice with two
    different faces. A LEAD is credited where their character is on screen
    (castrojo is Cayde-6). A PLACEHOLDER is someone the owner named for this
    act, so they already have a badge of their own -- letting the roster hand
    them a second, generic blueberry plate would put the same person on two
    different Guardians in the same five minutes.
    """
    with open(ROSTER) as fh:
        roster = json.load(fh)
    named = {p["key"] for p in PLACEHOLDERS}
    skip = BLUEBERRY_EXCLUDE | named
    return [c for c in roster["contributors"] if c["login"] not in skip]


def blueberry_entry(item, at, dur, casting):
    """One contributor's credit, resolved the same way tools/plate.py does."""
    authored = _titles(casting).get(item["login"])
    if authored:
        return {"copy_source": "casting", **dict(authored)}
    copy = casting["ensemble"]["plate"]
    member = item.get("org_member")
    label = (copy["label_member"] if member
             else copy["label"] if member is False
             else copy["label_unknown"])
    entry = {"copy_source": "casting", "label": label,
             "name": item["display_name"]}
    if copy.get("title"):
        entry["title"] = copy["title"]
    return entry


def localise_avatar(key, copy):
    """Point a plate's ``avatar`` at the local cache, keeping the URL as source.

    Returns the copy unchanged when there is no avatar -- Karena has none,
    because no GitHub login for her is on record anywhere in this repo and a
    login is not an agent's to guess (issue #87). A wreath with no portrait to
    ring is a recorded gap, not a reason to invent one.
    """
    url = copy.get("avatar")
    if not url or not str(url).startswith("http"):
        return copy
    copy = dict(copy)
    copy["avatar"] = str(AVATAR_DIR / f"{key}.png")
    copy["avatar_url"] = url
    return copy


def fetch_avatars(manifest, verbose=True):
    """Download every avatar the manifest names. Degrade, never block."""
    import urllib.request

    dest_dir = REPO_ROOT / AVATAR_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    got, failed = 0, []
    for plate in manifest["plates"]:
        url = plate.get("avatar_url")
        if not url:
            continue
        dest = REPO_ROOT / plate["avatar"]
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "destiny-vids"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                dest.write_bytes(resp.read())
            got += 1
            if verbose:
                print(f"  {plate['id']}: {dest.relative_to(REPO_ROOT)}")
        except Exception as exc:                      # noqa: BLE001
            failed.append((plate["id"], exc))
    for pid, exc in failed:
        print(f"  {pid}: avatar fetch failed ({exc}) -- the drawn crest "
              "stands in (punch-list item)", file=sys.stderr)
    if verbose:
        print(f"fetched {got} avatar(s), {len(failed)} failed")
    return got, failed


def space_plates(plates):
    """Stop a credit running into the next one in the same frame position.

    Holds are set by how long a name wants to be readable; whether that fits is
    a property of the TIMELINE, not of the plate. Two cards in the same
    position with no gap between them read as one flicker, so each plate is
    shortened to clear ``PLATE_GAP`` before its successor.

    A plate is never shortened below ``MIN_HOLD`` -- if it does not fit, it
    keeps its readable minimum and is returned in the report, because a
    silently unreadable credit is worse than a visible scheduling problem.

    Positions are independent: the trio's left/center/right cards sit in
    different thirds of the frame and cannot collide with each other.
    """
    tight = []
    by_position = {}
    for p in plates:
        by_position.setdefault(p.get("position"), []).append(p)

    for lane in by_position.values():
        lane.sort(key=lambda p: p["at"])
        for cur, nxt in zip(lane, lane[1:]):
            room = round(nxt["at"] - cur["at"] - PLATE_GAP, 3)
            if cur["dur"] <= room:
                continue
            if room < MIN_HOLD:
                tight.append((cur, nxt, room))
                cur["dur"] = MIN_HOLD
            else:
                cur["dur"] = room
    return tight


def _at(shot_in, film_of):
    """When the plate arrives: after the cut has landed."""
    return round(film_of(shot_in) + LEAD_IN, 3)


def build():
    casting = load_casting()
    plan = build_efmb.build()
    lead = build_efmb.derive_lead()

    def film_of(src):
        return build_efmb.film_for_source(src, lead)

    plates = []

    # --- the trio, as one row ---------------------------------------------
    # The row assembles one card at a time and clears together: each Guardian
    # gets an entrance of their own (TRIO_STAGGER), and once up the three read
    # as the roll call they are. Owner instruction -- see TRIO_STAGGER.
    #
    # The row rides past TRIO_OUT, where the camera pushes in on the hooded
    # Hunter. That is deliberate and it is the owner's call: holding the names
    # only while all three figures are separate is what made them flash by.
    trio_at = _at(TRIO_IN, film_of)
    trio_out = round(trio_at + (len(TRIO) - 1) * TRIO_STAGGER + TRIO_HOLD, 3)
    for order, (key, where) in enumerate(TRIO):
        at = round(trio_at + order * TRIO_STAGGER, 3)
        dur = round(trio_out - at, 3)
        assert dur >= MIN_HOLD, (
            f"the trio's {key} card can only hold {dur:.3f}s, below the "
            f"{MIN_HOLD}s a plate needs to be read")
        plates.append({
            "id": f"trio_{key}",
            "at": at,
            "dur": dur,
            "position": where,
            "scale": TRIO_SCALE,
            "group": "trio_row",
            "order": order,
            "copy_source": "casting",
            "seen_at_src": TRIO_IN,
            **localise_avatar(key, authored_copy(key, casting)),
        })

    # --- one person, one shot ---------------------------------------------
    for b in SOLO:
        src_in, src_out = b["src"]
        at = (round(film_of(b["at_src"]), 3) if b.get("at_src")
              else _at(src_in, film_of))
        hold = clamp_hold(at, SOLO_HOLD, film_of)
        assert hold, (
            f"{b['key']}'s plate at {at:.3f}s cannot clear a no-plate zone and "
            "still be readable -- move the anchor to another shot")
        plates.append({
            "id": f"solo_{b['key']}",
            "at": at,
            "dur": hold,
            "position": "left",
            "copy_source": "casting",
            "shot_src": [src_in, src_out],
            "seen_at_src": b["seen"],
            "why": b["why"],
            **localise_avatar(b["key"], authored_copy(b["key"], casting)),
        })

    # --- named placeholders -----------------------------------------------
    for b in PLACEHOLDERS:
        src_in, src_out = b["src"]
        at = _at(src_in, film_of)
        hold = clamp_hold(at, SOLO_HOLD, film_of)
        assert hold, (
            f"{b['key']}'s badge at {at:.3f}s cannot clear a no-plate zone and "
            "still be readable -- move the anchor to another shot")
        plates.append({
            "id": f"placeholder_{b['key']}",
            "at": at,
            "dur": hold,
            "position": "right",
            "copy_source": "casting",
            "shot_src": list(b["src"]),
            "seen_at_src": b["seen"],
            "why": b["why"],
            **placeholder_copy(b["key"], casting),
        })

    # --- the blueberries ---------------------------------------------------
    # Deterministic: the roster is walked in its own order against the shot
    # list in timeline order, so a re-render never reshuffles who played whom.
    items = roster_items(casting)
    for i, shot in enumerate(BLUEBERRY_SHOTS):
        if i >= len(items):
            break
        src_in, src_out = shot["src"]
        item = items[i]
        plates.append({
            "id": f"blueberry_{item['login']}",
            "at": _at(src_in, film_of),
            "dur": SOLO_HOLD,
            "position": "right",
            "shot_src": [src_in, src_out],
            "seen_at_src": shot["seen"],
            "why": shot["why"],
            **localise_avatar(item["login"],
                              blueberry_entry(item, None, None, casting)),
        })

    # --- Cayde's sign-off --------------------------------------------------
    src_in, src_out = CAYDE["src"]
    room = round(film_of(src_out) - film_of(src_in), 3)
    assert room >= MIN_HOLD, (
        f"Cayde's shot is {room:.3f}s, under the {MIN_HOLD}s the card needs")
    # The card takes the whole shot up to the minimum hold and no more: at
    # 2.30 s of room against a 2.2 s hold there is no lead-in to spend, and
    # riding past the cut would put his line over the cathedral ending.
    real_name = authored_copy(CAYDE["reveals"], casting)["name"]
    plates.append({
        "id": "cayde_signoff",
        "kind": "chat",
        "at": round(film_of(src_in), 3),
        "dur": MIN_HOLD,
        "copy_source": "dialogue",
        "shot_src": [src_in, src_out],
        "seen_at_src": CAYDE["seen"],
        "why": CAYDE["why"],
        "speaker": CAYDE["redacted_speaker"],
        "redacts": real_name,
        "redaction_scope": "act II only -- he is revealed later in the programme",
        "text": "I'm so proud of you kids!",
        "text_source": "owner_supplied",
    })

    plates.sort(key=lambda p: (p["at"], p.get("order", 0), p["id"]))

    for cur, nxt, room in space_plates(plates):
        print(f"plate {cur['id']} has only {room:.3f}s before {nxt['id']} and "
              f"keeps the {MIN_HOLD}s minimum -- the two overlap on screen",
              file=sys.stderr)

    return {
        "_what": (
            "Act II's plate manifest. GENERATED by "
            "scripts/build_efmb_plates.py -- never hand-edited. Windows are "
            "derived from scripts/build_efmb.py (source time -> film time) and "
            "every word of copy is reproduced verbatim from vocab/casting.yaml."
        ),
        "_film_sec": plan["film_sec"],
        "_bed_lead_sec": plan["bed_lead_sec"],
        "act": "II",
        "title": plan["title"],
        "source_id": plan["source_id"],
        "chapters": [
            {"at": round(film_of(src), 3), "title": title, "src": src}
            for src, title in CHAPTERS
        ],
        "plates": plates,
    }


def render_text(manifest):
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="write the manifest")
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed manifest is out of date")
    ap.add_argument("--fetch-avatars", action="store_true",
                    help="download the avatars the manifest names into renders/")
    ap.add_argument("--chapters", action="store_true",
                    help="print act II's sub-chapters in film time")
    args = ap.parse_args(argv)

    manifest = build()
    text = render_text(manifest)

    if args.chapters:
        for c in manifest["chapters"]:
            m, s = divmod(c["at"], 60)
            print(f"{int(m):d}:{s:06.3f}  {c['title']}")
        return 0

    if args.fetch_avatars:
        fetch_avatars(manifest)
        return 0

    if args.check:
        if not MANIFEST.exists():
            print(f"{MANIFEST} is missing -- run --write", file=sys.stderr)
            return 1
        if MANIFEST.read_text() != text:
            print(f"{MANIFEST} is out of date -- regenerate with --write, "
                  "never hand-resolve", file=sys.stderr)
            return 1
        print(f"{MANIFEST.name} is up to date ({len(manifest['plates'])} plates)")
        return 0

    if args.write:
        MANIFEST.write_text(text)
        print(f"wrote {MANIFEST} ({len(manifest['plates'])} plates)")
        return 0

    for p in manifest["plates"]:
        end = p["at"] + p["dur"]
        who = p.get("name") or p.get("speaker", "?")
        print(f"  {p['at']:7.3f} -> {end:7.3f}  {p['id']:28s}  {who}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

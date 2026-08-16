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
from tools.plate import CHOICE_POINTER_CUT  # noqa: E402

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

# THE OWNER TIMED THIS ROW BY HAND, AND HIS CLOCK IS THE MEGACUT'S.
#
#   "02:57 only show joseph sandoval, we're going to stagger these, keep them
#    up for readability / 02:59 add ricardo / 3:03 add karena (Angel, one L)"
#
# Act II's film sits at +2:01.567 in the programme, so his 2:57 / 2:59 / 3:03
# are film 55.433 / 57.433 / 61.433. That conversion is not assumed: the marks
# in the same message name `blueberry_Giklab` at "03:16" and that plate is at
# film 73.400, which is megacut 3:14.97 -- the only reading that lands.
#
# It replaces the even TRIO_STAGGER cascade. He is no longer asking for three
# entrances 0.8 s apart; he is asking for Joseph ALONE for two seconds, then a
# pair, then the row -- and for the row to stay up long enough to read, which
# is what TRIO_HOLD after the LAST arrival buys.
MEGACUT_OFFSET = 121.567


def source_from_original_megacut(mark):
    """Turn a pre-interruption programme mark into a stable Act-II source time.

    The interruption changes final wall time after source 323.933. Owner
    marks 06:17/06:19/06:27 predate it, so subtracting a later output offset
    would silently bind cards to the wrong frame. The Act-II bed clock is the
    original programme clock; source is the only stable placement authority.
    """
    return build_efmb.source_from_original_megacut(mark)


INTERRUPTION_MARKS = {
    "in": 6 * 60 + 17,
    "resume": 6 * 60 + 19,
    "kolunmi": 6 * 60 + 27,
}
TRIO = [
    ("joseph_sandoval", "left", 177.0),
    ("rochaporto", "center", 179.0),
    ("mara_sov", "right", 183.0),
]

# ONE L. The README says "Karena Angel" and the owner said it again this round
# ("add karena (Angel, one L)"). vocab/casting.yaml spells it "Angell", and it
# is a committed input to six delivered acts (#167), so correcting it there
# marks every one of them stale. The correction is applied HERE, to the copy
# this act prints, and recorded in `unresolved` -- a person's name is not
# something to leave wrong while waiting for a freeze to lift.
NAME_CORRECTIONS = {"mara_sov": ("Karena Angell", "Karena Angel")}

# --- THE OG GUARDIANS (owner brief, this round) ----------------------------
#
#   "02:15 name plate github/dims - 'Comes in Peace'
#    02:20 name plate Catherine Paganini
#    02:28 name plate github/thockin - 'Does NOT Come in Peace'
#    02:38 name plate github/jbeda - 'Out of Retirement'
#    These are OG Guardians make them a proud bronze"
#
# All four times are megacut, like the trio's. Every authored string is the
# owner's, verbatim -- including the capitalised NOT, which is the joke and is
# reproduced rather than normalised.
#
# THE NAMES ARE THE GITHUB PROFILES' OWN. Owner, 2026-08-15: *"guardian plaques
# need to be filled in"*, and when asked how: *"jesus christ look up their
# github name."* Three of these cards were printing a LOGIN where a name
# belongs, because an earlier pass took the owner's `github/<name>` shorthand
# as the copy. Each `name` below is now that account's own `name` field, read
# with `gh api users/<login> --jq .name` on 2026-08-15:
#
#     dims    -> Davanum Srinivas      thockin -> Tim Hockin
#     jbeda   -> Joe Beda              CathPag -> Catherine Paganini
#
# A published profile is a FACT ABOUT A REAL PERSON, stated by that person,
# which is why this fill is allowed where writing a title would not be. Cathy's
# lookup CONFIRMS the string her card already carried rather than correcting
# it, and it gets her the pfp the other three had.
#
# THE ROW SHE DOES NOT HAVE IS STILL THE POINT. Catherine Paganini was given a
# name and no line, so her card carries no title: that is the "missing, so omit
# and record" case, and writing one for her would be inventing copy about a
# real person. Recorded in the manifest's `unresolved`.
OG_LABEL = "OG GUARDIAN"
OG_GUARDIANS = [
    {"id": "og_dims", "at_megacut": 135.0, "name": "Davanum Srinivas",
     "title": "Comes in Peace", "login": "dims"},
    {"id": "og_paganini", "at_megacut": 140.0, "name": "Catherine Paganini",
     "login": "CathPag"},
    {"id": "og_thockin", "at_megacut": 148.0, "name": "Tim Hockin",
     "title": "Does NOT Come in Peace", "login": "thockin"},
    {"id": "og_jbeda", "at_megacut": 158.0, "name": "Joe Beda",
     "title": "Out of Retirement", "login": "jbeda"},
]
OG_HOLD = 4.0

# --- THE TEAM BADGE --------------------------------------------------------
#
#   "Make a Team Badge: CNCF Community Leadership / Looking for Open Source's
#    Brightest Future"
#
# It lands after the trio's row clears, so it reads as the caption on the three
# people who just arrived rather than as a fourth name competing with them.
# `name` and `title` are the owner's two lines; there is no third row.
TEAM_BADGE = {
    "id": "team_cncf_leadership",
    "label": "TEAM",
    "name": "CNCF Community Leadership",
    "title": "Looking for Open Source's Brightest Future",
}
TEAM_BADGE_HOLD = 3.5
TEAM_BADGE_LEAD = 0.25

# --- THE KERNEL TRUSTEES (owner note, dictated 2026-08-13 01:09; #119) -----
#
#   "5:43 [redacted] To graduate you must impress / 2 Badges platinum, above
#    gold. greg-kh and shuah khan / TRUSTEE // KERNEL / Make them both
#    warlocks / Keep them up even when cutting to the raw recruits, their
#    names up while redacted is talking"
#
# Megacut marks again, from the 2026-08-12 ALPHA watch -- and act II's window
# has not moved since (MEGACUT_OFFSET is the same on the ALPHA builds), so
# 5:43 is film 221.433. Frame-verified: the note's 6:34 "famous titan shield
# throw" is Kyle's Sentinel plate (film 269.700) and "6:44 is eyecantCU" is
# his window (film 283.666) -- the note is THIS act, misfiled as act III.
#
# THE DICTATED ANCHOR IS OCCUPIED. Film 221.433 sits inside the #98 pill run
# (218.484 -> 230.766), which did not exist on the cut he watched -- ALPHA2
# held Ahmed Adan's badge there and nothing else. Two owner instructions,
# one window. The badges land at the first frame the pills clear and hold
# across the recruits, the scarred man's close-up (the 5:58 slot the note
# parks for Troy -- nothing renders there until the owner writes him), and
# Cayde's 6:01 shot, which is the "while redacted is talking" the note asks
# for; they clear for Tulip's shot. The 9.6 s displacement from the dictated
# anchor is recorded in `unresolved`, and which of the two instructions
# yields is the owner's call, not made here.
TRUSTEE_ROW_AT = 231.016      # Joseph's "LOL" pill ends 230.766 + PLATE_GAP
TRUSTEE_ROW_OUT = 247.217     # Tulip's shot starts 247.467, less PLATE_GAP
TRUSTEE_ROW = ["gregkh", "shuah_khan"]  # the pair, left to right

# --- TULIP, THE SOLAR WARLOCK (same note) ----------------------------------
#
#   "6:11 Nameplate: Tulip Blossom, whatever solar warlock is
#    https://github.com/tulilirockz/ 'Deliverer of DDI' / keep it up until
#    6:20"
#
# 6:11 is film 249.433 -- MID-SHOT: her leap through the cathedral window
# runs 247.467 -> 249.567 (measured, scdet over renders/efmb-hq.mp4, cuts at
# 247.467 and 249.567), so the plate anchors to the SHOT's first frame and
# is already up at the dictated second. "Keep it up until 6:20" (film
# 258.433) is NOT honoured: the shot ends 249.567 and the #98 pills (krook
# at 250.000, the bedazzle at 253.250) own everything through 255.850, so
# the longest possible hold that still names her on her own shot is
# 247.467 -> 249.750 -- 0.083 s over the readable minimum. Recorded in
# `unresolved`; the pills are the owner's to move if she should hold longer.
TULIP = {"key": "tulilirockz", "at": 247.467, "out": 249.750}

# --- THE NEW DIALOGUE (owner brief, this round) ----------------------------
#
#   "03:12 chat bubble for Joseph: Here comes the slop
#    03:19 karena: I love this job
#    03:39 joseph: Master your skills
#    03:40 joseph: You got this"
#
# Megacut marks again. 3:39 and 3:40 are ONE SECOND apart and a pill needs
# MIN_HOLD to be read, so the second is chained behind the first rather than
# stacked on it -- the ORDER is his and it is kept; only the gap is the
# timeline's. Recorded in `unresolved`.
NEW_CHATS = [
    {"id": "chat_joseph_slop", "key": "joseph_sandoval", "speaker": "Joseph",
     "text": "Here comes the slop", "at_megacut": 192.0, "hold": 2.6},
    {"id": "chat_karena_job", "key": "mara_sov", "speaker": "Karena",
     "text": "I love this job", "at_megacut": 199.0, "hold": 2.6},
    {"id": "chat_riaan_choices", "key": None, "speaker": "riaankleinhans",
     "text": "Your choices are:", "at_megacut": 206.0, "hold": 2.4,
     "login": "riaankleinhans"},
    {"id": "chat_joseph_master", "key": "joseph_sandoval", "speaker": "Joseph",
     "text": "Master your skills", "at_megacut": 219.0, "hold": 2.2},
    {"id": "chat_joseph_gotthis", "key": "joseph_sandoval", "speaker": "Joseph",
     "text": "You got this", "at_megacut": None, "hold": 2.2},
]

# --- THE CHOICE SCREEN -----------------------------------------------------
#
#   "then generate a graphic choice box for the team o Update your LFX Profile
#    o Do it the hard way ... Then just cut to the shot of them firing"
#   "make them 2 separate boxes"
#   "make the text MUCH larger like a video game choice screen"
#   "design it like a video game choice screen and 'pause' here to let the
#    player 'decide' then it cuts to the descent"
#   "design it like the destiny legendary campaign screen -- the fight one
#    should match 'legendary'"
#   "whip up a quick mouse pointer starting at the center and then moving
#    towards the fighting choice but have it cut so it's a teaser quick cut"
#
# So: a FULL-FRAME pause menu straight after riaankleinhans's line, the second
# option carrying Destiny's amber legendary chrome, and a cursor that leaves
# the centre of the screen heading for it and never arrives -- the film cuts
# first. It is animated the only way a still-plate pipeline can animate: a
# short run of frames, each one a plate, one group, back to back.
CHOICE_OPTIONS = [
    "Update your LFX Profile",
    {"text": "Do it the hard way", "tier": "legendary"},
]
CHOICE_HOLD = 1.5          # the whole teaser, cut to cut
CHOICE_FPS = 16            # the cursor's frame rate; the film's is 59.94.
                           # 16 x 1.5 s = 24 frames exactly, so the image2
                           # sequence has an integral rate and tpad does not
                           # have to round one.
CHOICE_LEAD = 0.2          # air between riaan's pill and the menu

# One person, one shot. Each verified by eye at the frame named in `seen`.
# REMOVED, owner instruction for "The Long Walk": William Rizzo's credit sat
# at source 185.233 -- inside the new chapter, whose whole brief is "No other
# guardians". His authored copy stays in vocab/casting.yaml; only the
# SCHEDULING is gone, so nothing about his identity was lost with it.
SOLO = [
    {
        # THE ARC HUNTER BEFORE KYLE. Owner, 2026-08-14: "the arc hunter
        # before kylegospo is https://github.com/kolunmi/ - add a nameplate."
        #
        # The shot bounds are MEASURED, not eyeballed: a scene-change pass
        # over source 320-342 puts cuts at 333.400 and 335.267, and 335.267 is
        # exactly where Kyle's shot already started -- the two lists agreeing
        # independently. 1.867 s of picture, the Guardian loosing an Arc bow.
        "key": "kolunmi",
        "src": (333.400, 335.267),
        "at_src": source_from_original_megacut(INTERRUPTION_MARKS["kolunmi"]),
        "seen": 334.300,
        "why": "the Arc Hunter loosing a bow, one cut before Kyle's Sentinel",
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
    # AHMED ADAN'S BADGE IS REMOVED, owner instruction: "get rid of the
    # hanthor plate, ahmed, etc. here". It sat at source 241.167 (film
    # 3:37.3), at the end of "The Long Walk" and directly after the villain
    # arrives. He was ALREADY re-anchored once, off 171.800 where the plate
    # came up under Bungie's burned-in "BECOME LEGEND"; this time the chapter
    # itself is what displaces him.
    #
    # He stays in ensemble.placeholders, which is the queue that owes him a
    # plate -- nothing about his standing changed, only where act II had room.
]

# The blueberries -- the month's contributors, in the anonymous slots. Copy is
# resolved by tools/plate.py's own ensemble path, so a contributor whose
# identity IS authored gets it verbatim and everyone else gets the generic
# blueberry plate with the eyebrow their org membership earns. Leads are
# excluded: castrojo is Cayde-6 and is credited only where Cayde is on screen.
# TWO SHOTS REMOVED, same instruction. 195.267 (HuntedRaven7, film 2:51.4)
# and 233.500 (hanthor, film 3:29.6) are both inside "The Long Walk". The
# roster is walked in order against this list, so dropping two shots does not
# reshuffle who played whom -- it shortens the list, and the two contributors
# it reached are reported in `unresolved` rather than silently dropped.
# EMPTY, owner instruction: "03:16 get rid of giklab". Megacut 3:16 is film
# 74.4, and the one blueberry plate in this act was `blueberry_Giklab` at film
# 73.400 -- the shot at source 90.767. The SHOT is what came out, so the roster
# is not reshuffled: nobody else moved into his slot, and Giklab stays on the
# roster for a later act. The window is now clear for the OG Guardians above.
BLUEBERRY_SHOTS = []
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

# --- THE MONTAGE ANNOUNCEMENTS (owner brief, issue #98) --------------------
#
# "Right after the smash at 1:38 ... Make an overlay with announcements spaced
# out over this montage until the 02:19 - try to space them out evenly. Rank
# them with bronze, silver, and gold, make them lower thirds with the
# heraldric style."
#
# ALL COPY BELOW IS OWNER-AUTHORED AND VERBATIM, including the bracket spacing
# (`[ NEW CONTRIBUTORS ]` but `[ALL CONTRIBUTORS]`) and `Ready to the
# #FIGHTFORCONTRIBUTORS?`. Authored copy is reproduced, never corrected.
#
# THE RANKS ESCALATE, and that is the joke: bronze greets the newcomer, silver
# flatters the incumbent, gold is kept for the people who already left and for
# the payoff line that agrees with all of them.
MONTAGE_IN, MONTAGE_OUT = 98.0, 139.0     # 1:38 -> 2:19, in film time

# The window is not empty: the Dylan Taylor badge already sits at 130.267.
# Six cues at MONTAGE_STEP land the last one clear of it rather than stacking
# a second card on top -- `space_plates` would catch the collision, but an
# announcement silently trimmed to 2.2s is not what "spaced out evenly" means.
MONTAGE_STEP = 5.5

# AN4-CH3CK-12 IS GONE. Owner: "Remove all this anacheck stuff for now."
#
# The announcer carried three blocks -- the four ranked montage cards, the two
# TOC payoff cards, and the label on Natewaddington's placard (the placard
# itself is out too now, see TIMED_KROOK below). All three are
# removed rather than re-voiced: the copy was written FOR that character, and
# putting somebody else's name on his lines would be a different joke nobody
# asked for. Every string survives in git and in `unresolved`, so bringing him
# back is a revert rather than a rewrite -- which is what "for now" means.
ANNOUNCER = None

# `kind: chat` -- the pfp-badge pill the other videos use, not heraldry. The
# owner's two lines are asides to camera, so they carry no rank.
#
# The SPEAKER string is the owner's own, from the brief ("[pfp] Jorge Castro:
# Enjoying the metal?"), not a casting.yaml lookup: nobody has authored plate
# copy for `castrojo`, and a chat pill needs a name to put on the pill. The
# login is carried only to find the pfp, which degrades to the drawn crest.
MONTAGE_CHATS = [
    ("castrojo", "Jorge Castro", "Enjoying the metal?"),
    ("castrojo", "Jorge Castro", "Ready to the #FIGHTFORCONTRIBUTORS?"),
]

# The heraldic lower thirds. `name` is who is being addressed, `title` is what
# is said to them -- the closed field set, no row invented.
MONTAGE_ANNOUNCEMENTS = [
    {
        "id": "announce_new",
        "rank": "bronze",
        "name": "TO [ NEW CONTRIBUTORS ]",
        "title": "It's totally like this. We promise.",
    },
    {
        "id": "announce_current",
        "rank": "silver",
        "name": "TO [ CURRENT CONTRIBUTORS ]",
        "title": "Look how good you look, it totally is like this!",
    },
    {
        "id": "announce_emeritus",
        "rank": "gold",
        "name": "[ EMERITUS CONTRIBUTORS ]",
        "title": "It's totally NOT like this. We promise.",
        # The owner's block for this one carries a SECOND line -- "Look how
        # good you look!" -- and the card has three rows, all spoken for. It
        # is recorded in `unresolved` rather than dropped or crammed into the
        # class row, which is a subclass and would be nonsense here.
        "orphan_copy": "Look how good you look!",
    },
    {
        "id": "announce_all",
        "rank": "gold",
        "name": "[ALL CONTRIBUTORS]",
        "title": "You are not wrong",
    },
]

# `trustee: true` IS the silver treatment (tools/plate.py `_variant_for`), so
# the middle rank is a flag rather than a `variant` -- same as every silver
# plate in the show.
RANK_CHROME = {
    "bronze": {"variant": "bronze"},
    "silver": {"trustee": True},
    "gold": {"variant": "leader"},
}

# --- "THE LONG WALK" (owner brief, this round) -----------------------------
#
# A chapter inside act II, in the jungle: GloriousEggroll walking with Nobara
# chrome, A1RM4X as his peer, and NOBODY ELSE -- "No other guardians", which is
# why Rizzo, HuntedRaven7, hanthor and Ahmed Adan came out of the lists above.
# HikariKnight was the third name here and the owner has since cut him too
# ("remove hikari from the eggroll scene"), so the walk is two Guardians.
#
# TWO CLOCKS AGAIN, AND THEY ARE NOT THE ONES ISSUE #98 USED. The owner gave
# this round's marks off the MEGACUT (`tools/megacut.py --locate`), where act
# II's film sits at +2:01.567; issue #98's marks were act II FILM time. The
# conversion was not assumed, it was proved on the frame: at megacut 5:35 the
# extracted frame still carries hanthor's plate, and act II's own 4:59 is
# black tail, so the standalone reading is impossible.
#
#   megacut 4:30 -> film 148.433 -> source 166.199   the walk
#   megacut 4:59 -> film 177.433 -> source 201.299   "turn the stream on"
#   megacut 5:08 -> film 186.433 -> source 210.299   the green-eyed enemies
#   megacut 5:28 -> film 206.433 -> source 230.299   he turns around
#   megacut 5:35 -> film 213.433 -> source 237.299   the villain
#
# Every anchor below is therefore a SOURCE timecode, like every other window
# in this file, and each one was snapped to a measured shot boundary and then
# looked at on a contact sheet.
# 163.799 is the walking shot's FIRST frame, measured (film 146.033). It used
# to be 165.567, which is 0.032 s before that shot's LAST frame -- off by a
# whole shot -- so the chapter card came up 0.4 s after the walk had already
# cut away and rode five seconds straight onto KARENA'S JUMP, captioning her
# dive into the sinkhole "Glorious Eggroll and the new kids ...". The owner
# caught it in the programme: "there's an erroneous long walk in the part with
# karena". The shot boundaries either side are measured, not eyeballed:
# 146.033 -> 147.833 is the walk, and 148.533 is the frame she jumps on.
WALK_IN = 163.799          # two Guardians walking, green forest -- the chapter
WALK_ENEMIES = 210.200     # the helmet close-up, teal eyes lit behind it
WALK_VILLAIN = 238.200     # the winged figure: "Say hello to ..."
WALK_OUT = 244.832         # run 4's last frame; nothing here may cross it

# The owner's own marks, where a cue is timed to one rather than to a shot.
WALK_MARK_STREAM = 201.299     # "4:59 Alright A1RMAX turn the stream on"
WALK_MARK_UPSTREAM = 210.299   # "5:08 he says ..."

# THE CHAPTER CARD. `kind: "title"` is the deck's own title card, so this adds
# no renderer: `title` over `subtitle`, and no third row.
#
# Both strings are the owner's, verbatim and from the same brief: he wrote the
# chapter in as "Glorious Eggroll and the new kids ..." and then named it --
# 'Make this one "The Long Walk"'. The name is the title and the line he wrote
# it in as is the subtitle; the ellipsis is his.
# TODO(owner): if the subtitle is not wanted, delete it -- it is reproduced,
# not required.
# The chapter card gets a SHORTER lead than everything else. Its shot is only
# 1.8 s long and Karena's jump is the next frame after it, so the ordinary
# 0.4 s of "let the cut land first" is 0.2 s the card cannot spare: at 0.4 it
# clears the jump zone with 2.1 s, under the readable minimum, and would be
# dropped entirely.
WALK_CARD_LEAD = 0.2

WALK_CARD = {
    "title": "The Long Walk",
    "subtitle": "Glorious Eggroll and the new kids ...",
}

# THE SCENE, IN ORDER. One lane, one card at a time: a plate arrives, then the
# lines that follow it, then the next plate.
#
# `src` anchors a cue to a measured shot boundary; `at_src` pins one to a mark
# the OWNER gave (see the conversion table above). A cue with neither simply
# follows the previous one -- the whole list is chained, so a boundary that
# moves slides the scene rather than reordering it.
#
# Copy for a `plate` comes from vocab/casting.yaml like every other credit
# here. Every `line` is the owner's, verbatim, including the swearing and his
# own spelling of "A1RMAX" inside his line -- his transcription of a name
# stays as he typed it, while the CARD carries the channel's own @A1RM4X.
WALK_SEQUENCE = [
    # NO NAMEPLATE FOR GloriousEggroll. Removed 2026-08-15 (#192): the cue was
    # anchored at src 180.533, which is film ~156.7 -- a ship, then a hangar
    # interior, then an EXTREME CLOSE-UP OF A WOMAN'S FACE at film 160.5. Its
    # own `why` claimed "he takes the frame after the title, walking", and he
    # does not; the walking shot the chapter card names is film 146.033 ->
    # 147.833, 1.8 s, which is under MIN_HOLD and cannot carry a plate at all.
    # So there is no shot in this chapter that can hold his credit, and what
    # shipped instead was a real person's name over a different person's face
    # -- AGENTS.md rule 3. Omission credits nobody, so the card comes out; he
    # keeps all seven lines below, which name him as the speaker.
    # TODO(owner): if he should carry a nameplate here, say which shot is him.
    # ANCHORED, not chained. With the plate gone this block would chain off the
    # chapter card and slide 4.65 s earlier -- straight into Karena's jump zone
    # (clamp_hold raises on it). 185.183 is the source frame that maps to film
    # 161.317, which is exactly where this line already plays, so removing the
    # nameplate above moves his dialogue not at all.
    {"cue": "line", "id": "walk_ge_1", "speaker": "GloriousEggroll",
     "at_src": 185.183,
     "text": "Watch how I do it", "hold": 2.6},
    {"cue": "line", "id": "walk_ge_2", "speaker": "GloriousEggroll",
     "text": "Half the trick is looking good", "hold": 2.6},
    {"cue": "line", "id": "walk_ge_3", "speaker": "GloriousEggroll",
     "text": "This Nobara Horse Armor Proton Edition will slay", "hold": 3.4},
    # HIKARIKNIGHT IS OUT, owner instruction: "remove hikari from the eggroll
    # scene". His plate sat at 193.800 (film 170.667). Only the SCHEDULING is
    # gone -- his authored copy stays in vocab/casting.yaml and he keeps every
    # other claim on the show, exactly as Rizzo and Ahmed Adan did when this
    # chapter took their shots. A1RM4X is pinned to his own anchor below, so
    # nothing slides up into the hole.
    # 195.267 is the shot HuntedRaven7's credit used to hold. It is free now,
    # and putting A1RM4X there is what lets the next line land ON the owner's
    # 4:59 instead of 1.3 s late behind a plate.
    {"cue": "plate", "key": "A1RM4X", "src": 195.267, "hold": 3.0,
     "why": "up before the line that talks to him"},
    {"cue": "line", "id": "walk_ge_stream", "speaker": "GloriousEggroll",
     "text": "Alright A1RMAX turn the stream on", "hold": 2.6,
     "at_src": WALK_MARK_STREAM},
    {"cue": "line", "id": "walk_a1rm4x", "speaker": "A1RM4X",
     "text": "When can we see Shuah and Greg?", "hold": 2.6},
    {"cue": "line", "id": "walk_ge_soundcard", "speaker": "GloriousEggroll",
     "text": "You picked the shittiest sound card to impress them with",
     "hold": 2.7},
    {"cue": "line", "id": "walk_ge_glorious", "speaker": "GloriousEggroll",
     "text": "There's nothing glorious about this job", "hold": 2.8,
     "at_src": WALK_MARK_UPSTREAM},
    {"cue": "line", "id": "walk_ge_upstream", "speaker": "GloriousEggroll",
     "text": "If we don't upstream these they keep coming back", "hold": 3.2},
]

# The line after the villain lands, which is why it is not in the list above.
# 2.2 s is the readable minimum and it is exactly what run 4 has left after
# the villain's bar clears: his line is the last thing in the chapter and the
# cut behind it is hard, so the card ends with the run rather than riding over
# it. DO NOT LENGTHEN IT without shortening the bar first.
WALK_LESSON = {"id": "walk_ge_lesson", "speaker": "GloriousEggroll",
               "text": "Here comes the lesson kids", "hold": 2.2}

# THE PATCH QUEUE. Owner: "When he sees the green eyed monsters have a status
# thing in the bottom say: UPSTREAM PATCH QUEUE". It is the site's own HUD
# card (`kind: "status"`), at the bottom because he said bottom, and it holds
# from the enemies' reveal until the villain arrives -- a queue that blinks
# once is a caption, a queue that stays up is a HUD.
WALK_HUD = {"detail": "UPSTREAM PATCH QUEUE", "label": "KERNEL 6.11-RC"}

# THE VILLAIN. `kind: "miniboss"` -- Destiny's boss-bar treatment, in the red
# the owner asked for. Both rows are his, verbatim.
#
# It names NOBODY: a kernel regression is not a person, which is the only
# reason this card may carry copy no identity was authored for.
WALK_VILLAIN_CARD = {
    "name": "KERNEL REGRESSION",
    "title": "Enslaver of Maintainers | Ruiner of User Experience",
}
# The bar and the line after it have to share what run 4 has left after the
# villain arrives: 2.97 s of his own shot plus the tail of the run. 3.5 s
# leaves the closing line its readable minimum, and the build asserts it
# rather than trusting this number.
WALK_VILLAIN_HOLD = 3.5

# THE ACHIEVEMENT GAG -- PROPOSED, NOT APPROVED, SO NOT EMITTED.
#
# Owner: "for every dramatic explosion in this segment add a Bazzite
# Achievement Unlocked gag designed after the XBox ... Give them jokes about
# upstreaming patches. The most dramatic should be 'Mailing List Bullshit'."
# He then chose, explicitly, to approve the strings before anything is burned.
#
# So the renderer exists (tools/plate.py `kind: "achievement"`), the explosions
# are measured, and the copy below is a PROPOSAL: only "Mailing List Bullshit"
# is his. `WALK_ACHIEVEMENTS_APPROVED` is the gate, and until he flips it the
# whole list is reported in `unresolved` and no card is scheduled.
#
# The four `src` values are measured explosion cuts inside the chapter,
# verified on the contact sheet. "Mailing List Bullshit" is on 213.200, the
# biggest blast in the segment, per his "the most dramatic should be".
WALK_ACHIEVEMENTS_APPROVED = False
WALK_ACHIEVEMENTS = [
    {"src": 213.200, "name": "Mailing List Bullshit", "score": "100 G",
     "copy": "owner_supplied"},
    {"src": 217.033, "name": "Sent It Upstream", "score": "10 G",
     "copy": "proposed"},
    {"src": 223.967, "name": "Maintainer Said NAK", "score": "25 G",
     "copy": "proposed"},
    {"src": 228.300, "name": "Carried Out of Tree Since 2019", "score": "50 G",
     "copy": "proposed"},
]
WALK_ACHIEVEMENT_HOLD = 3.0

# --- THE TOC EXCHANGE AND THE ENDGAME (owner brief, issue #98 §3-§4) --------
#
# §3's exchange is the trio talking about the CNCF; §4 is the endgame's timed
# cues. ALL COPY IS OWNER-AUTHORED AND VERBATIM, bracket spacing, casing and
# the asterisk emphasis markers included (the markers are emphasis, not words:
# the chat pill's message row is set in bold throughout, so `DO` and
# `powering up` ARE bold on screen -- preserved, not differentiated).
#
# THE CLOCK TRAP, AGAIN (#109): the brief's marks are ACT II FILM time, and
# one of them -- "JOSEPH at 5:07" -- lands in the 16.065 s of black tail
# (picture ends at 4:51.933). The owner has since ruled where the exchange
# plays: "this should be in the endless beautiful section, it's the only
# section with greenery in it". The greenery is the jungle, and the jungle is
# where The Long Walk already lives, so the exchange is laid out AROUND the
# walk, never on top of it:
#
#   * the three QUESTIONS go up in the pre-walk window (2:19 -> the walk's
#     first frame) -- with the trio itself on screen at 2:24;
#   * the ANSWER lands after the walk, in the run-5 window its credits leave
#     clear (220.967 -> Kyle's downbeat at 269.700), chained ahead of the two
#     owner-marked §4 cues at 4:10 and 4:20.
#
# KARENA'S JUMP CARRIES NO CARD. "Karena says nothing and jumps. No card on
# her here; the beat is the jump." So the beat is clear screen: JUMP_BEAT
# seconds between Joseph's DO line and Ricardo's answer. No shot here was
# verified as HER jump and picking one would be casting by inference -- the
# frame is the owner's eye, recorded in `unresolved`.
JUMP_BEAT = 1.5

# The speakers are the brief's own tags ([KARENA] / [JOSEPH] / [RICARDO]),
# not a casting.yaml lookup -- the same rule the montage applied to "Jorge
# Castro". The `key` rides along ONLY to find the pfp; a speaker with no
# recorded avatar (Karena, Joseph) gets the drawn crest, by omission rather
# than by accident.
TOC_PRE = [
    {"id": "toc_karena", "key": "mara_sov", "speaker": "Karena",
     "text": "One hundred thousand bootc volunteers, ready to power up",
     "hold": 3.2},
    {"id": "toc_joseph_worth", "key": "joseph_sandoval", "speaker": "Joseph",
     "text": "Is it worth it?", "hold": 2.2},
    {"id": "toc_ricardo", "key": "rochaporto", "speaker": "Ricardo",
     "text": "You really think they can save open source?",
     "hold": 2.4},
]
# THE EXCHANGE IS CHAINED BACKWARD FROM THE WALK, not forward from 2:19.
#
# It used to start at MONTAGE_OUT and give the last line "whatever is left"
# before the walk's first frame. That worked only while the walk was
# mis-anchored a shot late; correcting WALK_IN to the walking shot's real
# first frame (146.033) left 7.033 s for three cards that need 7.100, and
# Ricardo's question would have been squeezed under the readable minimum.
#
# Chaining backward keeps every authored hold and moves the whole exchange
# 1.07 s earlier instead -- into clear air, since Dylan Taylor's badge is out
# at 134.767. The scene it belongs to is the walk, so the walk is what it is
# pinned to.
TOC_PRE_TAIL_GAP = 0.2   # air between the last question and the chapter card
TOC_POST = [
    {"id": "toc_joseph_faith", "key": "joseph_sandoval", "speaker": "Joseph",
     "text": "Dunno, how much faith DO we have in the CNCF?", "hold": 3.0},
    {"id": "toc_ricardo_desktop", "key": "rochaporto", "speaker": "Ricardo",
     "text": "Cloud native desktop? ...", "hold": 2.6, "lead": JUMP_BEAT},
    {"id": "toc_joseph_lol", "key": "joseph_sandoval", "speaker": "Joseph",
     "text": "LOL", "hold": 2.2},
]

# The payoff pair from §3's announcement block. The first REPRISES the
# montage's emeritus card verbatim -- a callback, so the copy is identical,
# row for row, rank included. The second is the pivot it sets up; the brief's
# block gives it no addressee row, so the card carries none.
TOC_ANNOUNCEMENTS = [
    {"id": "toc_announce_emeritus", "rank": "gold",
     "name": "[ EMERITUS CONTRIBUTORS ]",
     "title": "It's totally NOT like this. We promise."},
    {"id": "toc_announce_ambassadors", "rank": None,
     "name": None,
     "title": "Have you met our Ambassadors?"},
]

# §4's owner-marked cues, pinned to his second. Like every window in this file
# the anchor is carried in SOURCE time (`src_of` below), so a cut that moves
# raises rather than slides.
#
# NOT HERE: the 4:01 cue -- "[pfp] Jorge Castro: They are not ready for Shua
# Khan and Greg KH", drawn as a speech bubble ON Cayde. Cayde's [ REDACTED ]
# card is at 287.933 (4:47.9), so a bubble anchored on him cannot also be at
# 4:01. Which moves is the owner's call (#98, Questions) -- recorded in
# `unresolved`, scheduled nowhere.
TIMED_KROOK = 250.0          # 4:10
# NATEWADDINGTON IS OUT, owner: "get rid of the nate wassington in the endless
# climax in endless". His placard sat at film 260.000 (4:20) for SOLO_HOLD,
# inside the run into the act's climax -- the song breaks down at 258.0 and the
# band re-enters on the 269.700 downbeat, so his card was the last thing on
# screen before the biggest musical event in the act.
#
# Only the SCHEDULING goes, exactly as it did for HikariKnight: the placard's
# two rows were the owner's copy and they stay in git, the drop is recorded in
# `unresolved`, and nothing slides up into the hole -- krook and the bedazzle
# pill keep their own anchors and Jorge stays pinned to 291.0.
TIMED_JORGE = 291.0          # 4:51 -- inside the cathedral shot, which ends
                             # 291.933; the pill rides the black tail
TIMED_JORGE_HOLD = 2.8

# The untimed §4 cue, in the order the brief lists it: after krook.
BEDAZZLE = {"speaker": "cncf marketing", "text": "Let's bedazzle this thing!"}

# The show callout lives in the TOP treatment lane. It is deliberately split
# into three owner-authored segments: tools/plate.py renders the glowing
# Bluefin `|` separators, rather than treating punctuation between authored
# phrases as authored copy. Chat pills remain the lower treatment lane.
TOP_BANNER_SEGMENTS = (
    "#FIGHTFORCONTRIBUTORS",
    "Support Open Gaming Collective",
    "#UPSTREAMFIRST",
)

# The interruption moves the already-authored Cortney hero treatment rather
# than recreating it. The brief's reaction words are placeholders supplied by
# the owner; speaker identity comes only from existing gold/leader cards.
CORTNEY_HERO_MANIFEST = (
    REPO_ROOT / "stories" / "megacut" / "megacut-hero-plates.json"
)
CORTNEY_PLATE_LEAD = 0.5
INTERRUPTION_REACTIONS = (
    ("joseph_sandoval", "Hell yeah!"),
    ("mara_sov", "YYES!"),
    ("joseph_sandoval", "Hell yeah!"),
)

# The closing montage: five quotes the brief leaves untimed. Its own proposal
# is 4:51 -> 5:07, and the preamble lands the last cue on the final second --
# so they are spread evenly from the gaslighting pill's out to the film's last
# frame, over the black outro the owner is keeping "for future flexibility".
#
# siosm's line carries authored emphasis (`**powering up**` in the brief). The
# asterisks are emphasis markup, not words -- burning them would put
# punctuation on screen nobody meant to say -- so they are stripped here and
# recorded in `unresolved`: the pill's message row is set in bold throughout
# (the site's own style), so the emphasis survives but is not differentiated.
CLOSING_QUOTES = [
    ("cgwalters", "Use open source responsibly!"),
    ("siosm", "I can feel Fedora powering up!"),
    ("jberkus", "I knew they could do it!"),
    ("preethi", "Great, more paperwork"),
    ("castrojo", "Just another day on the CNCF Projects team"),
]
QUOTE_HOLD = 2.2

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
    # "Rizzo" is gone with his plate: a chapter that drops the audience on a
    # credit that is no longer there is a marker pointing at nothing. The
    # chapter it is replaced by starts where the walk starts.
    (WALK_IN, "The Long Walk"),
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
    # KARENA'S JUMP. The brief has always said "Karena says nothing and jumps.
    # No card on her here; the beat is the jump" -- but that was a rule about
    # what to SCHEDULE, and the thing that broke it was a card scheduled
    # somewhere else RIDING onto her. A zone is the mechanism that already
    # exists for exactly that, and it protects the beat from every future cue
    # rather than from the one that happened to hit it.
    #
    # 166.299 -> 167.766 is her shot, measured (film 148.533 -> 150.000).
    (166.299, 167.766, "Karena's jump -- the beat is the jump, and no card "
                       "belongs on it"),
    # Bungie burns "BECOME LEGEND" over the cave at the end of run 2, fading in
    # around 172.5 and holding to the cut. The act removes a DIFFERENT instance
    # of this same title (build_efmb.REMOVED names 244.833 -> 246.100); this one
    # is inside picture the act keeps.
    (172.500, 174.433, "Bungie's burned-in 'BECOME LEGEND'"),
    (356.500, 358.200, "Bungie's burned-in 'NEW LEGENDS WILL RISE'"),
]


def _zones(film_of):
    return [(film_of(a), film_of(b - 0.001), why) for a, b, why in NO_PLATE_SRC]


# One frame at the act's 30 fps. A cue that ends exactly ON a zone's first
# frame is still ON the protected shot, so the clamp backs off by this much.
ZONE_GUARD = round(1.0 / 30.0, 3)


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
            # END BEFORE THE ZONE, NOT ON IT. `start - at` lands the cue's last
            # frame on the zone's FIRST frame -- which is the frame the zone
            # exists to protect. That off-by-one is why the Long Walk card kept
            # captioning Karena's jump (#184, #192): it was clamped to 2.300 s,
            # ending at 148.533, the exact frame she jumps on. _zones already
            # backs the zone's END off by a hair; the START needs the same.
            hold = round(start - at - ZONE_GUARD, 3)
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


def _corrected(key, copy):
    """Apply an owner-stated spelling of somebody's name to this act's copy.

    Reproducing authored copy is the rule; this is the one case where the
    AUTHOR has since corrected it and the file it lives in is frozen. The
    correction is keyed on the exact string it replaces, so if the vocab is
    ever fixed this silently stops applying instead of double-correcting.
    """
    want = NAME_CORRECTIONS.get(key)
    if not want or copy.get("name") != want[0]:
        return copy
    copy = dict(copy)
    copy["name"] = want[1]
    return copy


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


def chat_avatar(key, casting):
    """The pfp for a chat pill's badge, or nothing at all.

    The pill has an avatar slot (`tools/plate.py` CHAT_AVATAR) and its
    documented fallback is the drawn crest. `localise_avatar` only rewrites an
    avatar that is already in the copy, so handing it an empty dict -- which
    is what this file used to do for every chat -- silently produced a pill
    with no picture on it, every time. The avatar comes from the SAME authored
    entry as the plate copy, so a speaker with no recorded avatar (Karena, and
    anyone the owner has not given one) still gets the crest, by omission
    rather than by accident.
    """
    try:
        copy = authored_copy(key, casting)
    except KeyError:
        return {}
    if not copy.get("avatar"):
        return {}
    return localise_avatar(key, {"avatar": copy["avatar"]})


def cortney_authored_copy():
    """Read Cortney's approved plate, never compose a second identity."""
    hero = json.loads(CORTNEY_HERO_MANIFEST.read_text())
    entry = next(p for p in hero["plates"] if p["id"] == "cortney")
    return {
        field: entry[field]
        for field in ("position", "label", "name", "title")
    }


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
        # ANIMATION FRAMES ARE NOT CREDITS. A choice-screen frame is one
        # sixteenth of a second by design; MIN_HOLD exists so a NAME can be
        # read, and applying it to a frame stretches a 1.5 s teaser into a
        # 35 s stack of overlapping stills. They are contiguous by
        # construction, so there is nothing here to space.
        if p.get("animation"):
            continue
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
    trio_ats = [round(mc - MEGACUT_OFFSET, 3) for _, _, mc in TRIO]
    trio_out = round(max(trio_ats) + TRIO_HOLD, 3)
    for order, ((key, where, _), at) in enumerate(zip(TRIO, trio_ats)):
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
            **localise_avatar(key, _corrected(key, authored_copy(key, casting))),
        })

    # --- the OG Guardians, in bronze --------------------------------------
    for og in OG_GUARDIANS:
        at = round(og["at_megacut"] - MEGACUT_OFFSET, 3)
        hold = clamp_hold(at, OG_HOLD, film_of)
        assert hold, (
            f"{og['id']} at {at:.3f}s cannot clear a no-plate zone and still "
            "be readable -- the owner's mark has to move")
        entry = {
            "id": og["id"],
            "at": at,
            "dur": hold,
            "position": "left",
            "copy_source": "owner_supplied",
            "label": OG_LABEL,
            "name": og["name"],
            "variant": "bronze",
        }
        if og.get("title"):
            entry["title"] = og["title"]
        if og.get("login"):
            # The pfp comes from the account the owner named, and nothing else
            # about the person is read off it.
            entry["avatar"] = str(AVATAR_DIR / f"{og['login']}.png")
            entry["avatar_url"] = f"https://github.com/{og['login']}.png?size=256"
        plates.append(entry)

    # --- the team badge ----------------------------------------------------
    badge_at = round(trio_out + TEAM_BADGE_LEAD, 3)
    plates.append({
        **TEAM_BADGE,
        "at": badge_at,
        "dur": TEAM_BADGE_HOLD,
        "position": "center",
        "copy_source": "owner_supplied",
    })

    # --- the kernel trustees, one platinum pair held across the cuts -------
    for order, key in enumerate(TRUSTEE_ROW):
        dur = round(TRUSTEE_ROW_OUT - TRUSTEE_ROW_AT, 3)
        assert dur >= MIN_HOLD, (
            f"the trustee badge for {key} holds {dur:.3f}s, under the "
            f"{MIN_HOLD}s a plate needs to be read")
        plates.append({
            "id": f"trustee_{key}",
            "at": TRUSTEE_ROW_AT,
            "dur": dur,
            "position": ("left", "right")[order],
            "scale": TRIO_SCALE,
            "group": "kernel_trustees_row",
            "order": order,
            "copy_source": "casting",
            **localise_avatar(key, authored_copy(key, casting)),
        })

    # --- Tulip, on her own shot ---------------------------------------------
    tulip_dur = round(TULIP["out"] - TULIP["at"], 3)
    assert tulip_dur >= MIN_HOLD, (
        f"Tulip's plate holds {tulip_dur:.3f}s, under the {MIN_HOLD}s a "
        "plate needs to be read -- her shot is shorter than the note's hold")
    plates.append({
        "id": "solo_tulilirockz",
        "at": TULIP["at"],
        "dur": tulip_dur,
        "position": "left",
        "copy_source": "casting",
        **localise_avatar("tulilirockz", authored_copy("tulilirockz", casting)),
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

    # --- the new dialogue, and the choice screen ---------------------------
    #
    # These share the pill lane with the montage asides below, so they are
    # scheduled first and the montage takes what is left. Every mark is the
    # owner's own; only the pair he put one second apart is chained, because a
    # pill under MIN_HOLD cannot be read.
    montage_unresolved = []
    chat_cursor = 0.0
    choice_end = 0.0
    for spec in NEW_CHATS:
        if spec["at_megacut"] is not None:
            at = round(spec["at_megacut"] - MEGACUT_OFFSET, 3)
        else:
            at = round(chat_cursor + PLATE_GAP, 3)
        entry = {
            "id": spec["id"],
            "kind": "chat",
            "at": at,
            "dur": spec["hold"],
            "copy_source": "owner_supplied",
            "speaker": spec["speaker"],
            "text": spec["text"],
            "text_source": "owner_supplied",
        }
        if spec.get("key"):
            entry.update(chat_avatar(spec["key"], casting))
        elif spec.get("login"):
            entry["avatar"] = str(AVATAR_DIR / f"{spec['login']}.png")
            entry["avatar_url"] = (
                f"https://github.com/{spec['login']}.png?size=256")
        plates.append(entry)
        chat_cursor = round(at + spec["hold"], 3)

        # riaankleinhans asks, and the menu comes up on his line's tail.
        if spec["id"] == "chat_riaan_choices":
            frames = max(2, int(round(CHOICE_HOLD * CHOICE_FPS)))
            step = round(CHOICE_HOLD / frames, 4)
            start = round(chat_cursor + CHOICE_LEAD, 3)
            for n in range(frames):
                t = n / (frames - 1)
                plates.append({
                    "id": f"choice_lfx_{n:02d}",
                    "kind": "choice",
                    "at": round(start + n * step, 3),
                    "dur": step,
                    "position": "full",
                    "group": "choice_lfx",
                    "order": n,
                    "animation": True,
                    "copy_source": "owner_supplied",
                    "label": spec["text"],
                    "options": CHOICE_OPTIONS,
                    "pointer": round(t * CHOICE_POINTER_CUT, 4),
                })
            choice_end = round(start + frames * step, 3)
            chat_cursor = max(chat_cursor, choice_end)

    # --- the montage asides (owner brief #98) ------------------------------
    # The ranked announcement cards are GONE with AN4-CH3CK-12; the owner's own
    # two asides to camera stay. They start after the new dialogue has cleared
    # rather than at MONTAGE_IN, because 1:38 is now where Joseph is talking.
    cue_at = max(MONTAGE_IN, round(chat_cursor + PLATE_GAP, 3))
    for i, (login, speaker, text) in enumerate(MONTAGE_CHATS):
        plates.append({
            "id": f"montage_chat_{i + 1}",
            "kind": "chat",
            "at": round(cue_at, 3),
            "dur": SOLO_HOLD,
            "copy_source": "owner_supplied",
            "speaker": speaker,
            "text": text,
            "text_source": "owner_supplied",
            **chat_avatar(login, casting),
        })
        cue_at += MONTAGE_STEP

    last_out = cue_at - MONTAGE_STEP + SOLO_HOLD
    assert last_out <= MONTAGE_OUT, (
        f"the montage cues run to {last_out:.3f}s, past the {MONTAGE_OUT}s "
        "lead-in banner they are supposed to hand off to")

    # --- "The Long Walk" (owner brief, this round) -------------------------
    # One lane, in order: the chapter card, then a plate or a line at a time,
    # each landing on its shot and never before the previous card has cleared.
    # Nothing here types a film timecode -- `at` is either a shot boundary
    # converted from source, or the previous cue's out plus the gap.
    walk_unresolved = []
    walk = []
    cursor = [0.0]

    def walk_cue(entry, src=None, at_src=None, hold=None, lead=LEAD_IN):
        """Schedule one cue in the walk's single lower-third lane."""
        want = round(film_of(at_src), 3) if at_src else (
            round(film_of(src) + lead, 3) if src else 0.0)
        at = round(max(want, cursor[0]), 3)
        room = clamp_hold(at, hold, film_of)
        if room is None:
            walk_unresolved.append(
                f"{entry['id']}: no readable hold at {at:.3f}s once the "
                "no-plate zone is cleared -- the cue is not scheduled")
            return None
        entry = {**entry, "at": at, "dur": room, "position": "left"}
        cursor[0] = round(at + room + PLATE_GAP, 3)
        walk.append(entry)
        return entry

    walk_cue({
        "id": "walk_chapter",
        "kind": "title",
        "copy_source": "owner_supplied",
        "seen_at_src": WALK_IN,
        "why": "the chapter card, on the walk it names",
        **WALK_CARD,
    }, src=WALK_IN, hold=5.0, lead=WALK_CARD_LEAD)

    for spec in WALK_SEQUENCE:
        if spec["cue"] == "plate":
            walk_cue({
                "id": f"walk_{spec['key']}",
                "copy_source": "casting",
                "seen_at_src": spec["src"],
                "why": spec["why"],
                **localise_avatar(spec["key"],
                                  authored_copy(spec["key"], casting)),
            }, src=spec["src"], hold=spec["hold"])
        else:
            walk_cue({
                "id": spec["id"],
                "kind": "chat",
                "copy_source": "owner_supplied",
                "speaker": spec["speaker"],
                "text": spec["text"],
                "text_source": "owner_supplied",
                **chat_avatar(spec["speaker"], casting),
            }, at_src=spec.get("at_src"), hold=spec["hold"])

    # The villain, then the line that answers him.
    villain_at = _at(WALK_VILLAIN, film_of)
    walk.append({
        "id": "walk_villain",
        "kind": "miniboss",
        "at": villain_at,
        "dur": WALK_VILLAIN_HOLD,
        "position": "boss",
        "copy_source": "owner_supplied",
        "seen_at_src": WALK_VILLAIN,
        "why": "the winged figure arrives: 'Say hello to ...'",
        **WALK_VILLAIN_CARD,
    })
    cursor[0] = max(cursor[0], round(villain_at + WALK_VILLAIN_HOLD
                                     + PLATE_GAP, 3))
    # The last card in the chapter ends WITH run 4, never over it: the cut
    # behind it is hard and lands in a different sequence entirely. So its
    # hold is what the run has left, floored at the readable minimum -- a
    # typed number here would ride over the join the next time a boundary
    # moves.
    lesson_room = round(film_of(WALK_OUT) - cursor[0], 3)
    assert lesson_room >= MIN_HOLD, (
        f"only {lesson_room:.3f}s left in run 4 for "
        f"{WALK_LESSON['text']!r}, under the {MIN_HOLD}s minimum -- shorten "
        "the villain's bar")
    walk_cue({
        "id": WALK_LESSON["id"],
        "kind": "chat",
        "copy_source": "owner_supplied",
        "speaker": WALK_LESSON["speaker"],
        "text": WALK_LESSON["text"],
        "text_source": "owner_supplied",
        **chat_avatar(WALK_LESSON["speaker"], casting),
    }, hold=min(WALK_LESSON["hold"], lesson_room))

    # The patch queue: up on the enemies, down when the villain lands.
    hud_at = round(film_of(WALK_ENEMIES), 3)
    walk.append({
        "id": "walk_patch_queue",
        "kind": "status",
        "at": hud_at,
        "dur": round(villain_at - hud_at, 3),
        "position": "status-bottom",
        "copy_source": "owner_supplied",
        "seen_at_src": WALK_ENEMIES,
        "why": "the green-eyed enemies are on screen from here",
        **WALK_HUD,
    })

    if WALK_ACHIEVEMENTS_APPROVED:
        for i, gag in enumerate(WALK_ACHIEVEMENTS):
            walk.append({
                "id": f"walk_achievement_{i + 1}",
                "kind": "achievement",
                "at": _at(gag["src"], film_of),
                "dur": WALK_ACHIEVEMENT_HOLD,
                "position": "toast",
                "copy_source": gag["copy"],
                "seen_at_src": gag["src"],
                "why": "a dramatic explosion",
                "name": gag["name"],
                "score": gag["score"],
            })
    else:
        proposed = "; ".join(
            f"{g['name']} ({g['score']}, {g['copy']})"
            for g in WALK_ACHIEVEMENTS)
        walk_unresolved.append(
            "the Bazzite/Xbox achievement gag is BUILT BUT NOT SCHEDULED: the "
            "owner asked to approve the strings before anything is burned. "
            f"Proposed, one per measured explosion -- {proposed}. Only "
            "'Mailing List Bullshit' is his. Flip "
            "WALK_ACHIEVEMENTS_APPROVED in scripts/build_efmb_plates.py once "
            "he has said yes.")

    walk_end = max(p["at"] + p["dur"] for p in walk)
    assert walk_end <= film_of(WALK_OUT) + 1e-6, (
        f"the walk runs to {walk_end:.3f}s, past run 4's out point at "
        f"{film_of(WALK_OUT):.3f}s -- a card would ride over the hard cut")
    plates.extend(walk)

    # --- the TOC exchange (owner brief #98, section 3) ---------------------
    # One screen, one card: the exchange shares the lower third with
    # everything else, so it is scheduled on ONE cursor even where the card's
    # lane changes -- load_manifest_entries is position-blind, and two cards
    # in different thirds of the frame still read as two cards at once.
    toc = []

    def src_of(film_sec):
        """A pre-interruption film mark, anchored once in stable source time."""
        return build_efmb.source_for_bed(film_sec, lead)

    def toc_chat(spec, at, hold):
        entry = {
            "id": spec["id"],
            "kind": "chat",
            "at": round(at, 3),
            "dur": round(hold, 3),
            "position": "left",
            "copy_source": "owner_supplied",
            "speaker": spec["speaker"],
            "text": spec["text"],
            "text_source": "owner_supplied",
            **chat_avatar(spec["key"], casting),
        }
        return entry

    # The questions, in the pre-walk window. The scene starts at 2:19 -- the
    # lead-in banner that was to open it has no copy yet (#98, Questions), so
    # the first line takes its slot.
    span = (sum(spec["hold"] for spec in TOC_PRE)
            + PLATE_GAP * (len(TOC_PRE) - 1) + TOC_PRE_TAIL_GAP)
    cursor = round(film_of(WALK_IN) - span, 3)
    assert cursor >= 134.767, (
        f"the pre-walk exchange would start at {cursor:.3f}s, on top of Dylan "
        "Taylor's badge -- a hold has to come down")
    for spec in TOC_PRE:
        hold = spec["hold"]
        assert hold >= MIN_HOLD, (
            f"{spec['id']} holds {hold:.3f}s, under the {MIN_HOLD}s a card "
            "needs to be read")
        toc.append(toc_chat(spec, cursor, hold))
        cursor = round(cursor + hold + PLATE_GAP, 3)

    # The answer, after the walk's last card has cleared. `lead` is the TOTAL
    # clear screen before the card -- the jump beat is measured in clear air,
    # not in clear air plus a gap nobody asked for.
    cursor = round(film_of(WALK_OUT) + PLATE_GAP, 3)
    for spec in TOC_POST:
        at = round(cursor - PLATE_GAP + spec.get("lead", PLATE_GAP), 3)
        toc.append(toc_chat(spec, at, spec["hold"]))
        cursor = round(at + spec["hold"] + PLATE_GAP, 3)
    # TOC_ANNOUNCEMENTS are NOT scheduled: they are AN4-CH3CK-12's payoff pair,
    # and he is out this round. See the ANNOUNCER note.

    # --- the timed cues (owner brief #98, section 4) -----------------------
    # krook and the placard are pinned to the owner's marks (4:10, 4:20); the
    # bedazzle line is untimed and takes the gap between them in the order he
    # listed them. All three are over run 5's end fight.
    krook_at = round(film_of(src_of(TIMED_KROOK)), 3)
    assert krook_at >= cursor, (
        f"krook's 4:10 mark lands at {krook_at:.3f}s but the TOC exchange "
        f"runs to {cursor:.3f}s -- one of them has to move")
    timed = [{
        "id": "timed_krook",
        "kind": "chat",
        "at": krook_at,
        "dur": 3.0,
        "position": "left",
        "copy_source": "owner_supplied",
        "seen_at_src": round(src_of(TIMED_KROOK), 3),
        "speaker": "krook",
        "text": "Generational talent detected, call in the best",
        "text_source": "owner_supplied",
    }, {
        "id": "timed_bedazzle",
        "kind": "chat",
        # Its owner mark is untimed. It is shortened to the readable minimum
        # so the 06:17 source interruption starts on a clear frame instead of
        # inheriting a chat from the preceding shot.
        "at": round(krook_at + 3.2, 3),
        "dur": MIN_HOLD,
        "position": "left",
        "copy_source": "owner_supplied",
        "speaker": BEDAZZLE["speaker"],
        "text": BEDAZZLE["text"],
        "text_source": "owner_supplied",
    }]
    # NATEWADDINGTON'S PLACARD IS NOT HERE. Owner: "get rid of the nate
    # wassington in the endless climax in endless." It stood at film 260.000
    # for SOLO_HOLD, centre frame, the last card before the 269.700 downbeat.
    # Nothing takes its slot -- the run into the climax plays clean now.

    # The gaslighting pill and the closing quotes: his 4:51, then an even
    # spread whose last card ENDS on the film's final frame, over the black
    # outro. None of them are casting lookups -- the speakers are the brief's
    # own handles, and every one without a recorded login renders the drawn
    # crest (recorded in `unresolved`).
    jorge_at = round(film_of(src_of(TIMED_JORGE)), 3)
    timed.append({
        "id": "timed_jorge",
        "kind": "chat",
        "at": jorge_at,
        "dur": TIMED_JORGE_HOLD,
        "copy_source": "owner_supplied",
        "seen_at_src": round(src_of(TIMED_JORGE), 3),
        "speaker": "jorge",
        "text": "Well shut my gaslighting mouth ....",
        "text_source": "owner_supplied",
        **chat_avatar("castrojo", casting),
    })
    film_sec = plan["film_sec"]
    quotes_start = round(jorge_at + TIMED_JORGE_HOLD + PLATE_GAP, 3)
    quote_step = round(
        (film_sec - QUOTE_HOLD - quotes_start) / (len(CLOSING_QUOTES) - 1), 3)
    for i, (speaker, text) in enumerate(CLOSING_QUOTES):
        timed.append({
            "id": f"quote_{speaker}",
            "kind": "chat",
            "at": round(quotes_start + i * quote_step, 3),
            "dur": QUOTE_HOLD,
            "copy_source": "owner_supplied",
            "speaker": speaker,
            "text": text,
            "text_source": "owner_supplied",
            **chat_avatar(speaker, casting),
        })
    last_quote = timed[-1]
    assert abs(last_quote["at"] + last_quote["dur"] - film_sec) < 0.01, (
        "the preamble lands the last cue on the final second")

    # The callout occupies the top treatment lane. It no longer ducks the
    # bottom-right patch queue because chat and HUD chrome own lower lanes.
    toc.append({
        "id": "top_banner",
        "kind": "banner",
        "at": MONTAGE_OUT,
        "dur": round(film_sec - MONTAGE_OUT, 3),
        "position": "banner-top",
        "copy_source": "owner_supplied",
        "segments": list(TOP_BANNER_SEGMENTS),
        "text_source": "owner_supplied",
    })

    plates.extend(toc)
    plates.extend(timed)

    # --- Cortney's moved interruption ------------------------------------
    # These are final wall positions derived from source, not a copy of the
    # old Act-VI timestamps. The source resumes after the black reaction, so
    # every later source-bound card moves with this block automatically.
    interruption = plan["interruption"]
    plate_at = interruption["wall_in"] + CORTNEY_PLATE_LEAD
    plates.append({
        "id": "interruption_cortney",
        "at": round(plate_at, 3),
        "dur": round(build_efmb.CORTNEY_PLATE_SEC - CORTNEY_PLATE_LEAD, 3),
        "copy_source": "stories/megacut/megacut-hero-plates.json",
        "source_pointer": interruption["source_in"],
        "why": "Cortney's existing authored plate, moved from Act VI",
        **cortney_authored_copy(),
    })

    black_at = round(
        interruption["wall_in"] + build_efmb.CORTNEY_PLATE_SEC
        + (build_efmb.HERO_OUT - build_efmb.HERO_IN), 3)
    plates.append({
        "id": "interruption_ready",
        "kind": "chat",
        "at": black_at,
        "dur": build_efmb.OWNER_TEXT_SEC,
        "position": "left",
        "copy_source": "owner_supplied",
        "text": "Well ... are they ready?",
        "text_source": "owner_supplied",
    })
    reaction_at = black_at + build_efmb.OWNER_TEXT_SEC + build_efmb.REACTION_GAP_SEC
    for index, (key, text) in enumerate(INTERRUPTION_REACTIONS, start=1):
        copy = _corrected(key, authored_copy(key, casting))
        plates.append({
            "id": f"interruption_reaction_{index}",
            "kind": "chat",
            "at": round(reaction_at, 3),
            "dur": build_efmb.REACTION_HOLD_SEC,
            "position": "left",
            "copy_source": "owner_supplied",
            "speaker": copy["name"],
            "text": text,
            "text_source": "owner_supplied",
            **chat_avatar(key, casting),
        })
        reaction_at += build_efmb.REACTION_HOLD_SEC + build_efmb.REACTION_GAP_SEC
    assert abs(reaction_at - build_efmb.REACTION_GAP_SEC
               - interruption["wall_out"]) < 1e-3

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
            "every word of copy is reproduced verbatim from vocab/casting.yaml "
            "or, for the montage cues, from the owner's brief in issue #98."
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
        # What the brief authored but this manifest could not place. Recorded
        # so it is visible rather than buried: degrade, never block.
        "unresolved": montage_unresolved + walk_unresolved + [
            "og_paganini HAS NO `title` ROW. The owner filled the OG Guardian "
            "plaques on 2026-08-15 by pointing at GitHub, which gets every one "
            "of them a verified NAME and a pfp -- but a title is authored copy "
            "and no profile carries one. The other three have the owner's own "
            "lines ('Comes in Peace', 'Does NOT Come in Peace', 'Out of "
            "Retirement'); Catherine Paganini has none, so the row is OMITTED "
            "and her card degrades to name and pfp. A lorem placeholder is NOT "
            "available here: placeholder prose credits the vocab's uncast "
            "speaker, and this card names a real person -- AGENTS.md, 'Lorem "
            "under a real name is still putting words in a colleague's mouth.' "
            "One line from the owner closes it",
            "AN4-CH3CK-12 IS OUT, owner: 'Remove all this anacheck stuff for "
            "now.' Three blocks went with him -- the four ranked montage "
            "cards, the two TOC payoff cards ('It's totally NOT like this' "
            "and 'Have you met our Ambassadors?'), and the eyebrow on "
            "Natewaddington's placard. Every string is still in git; 'for "
            "now' means this is a revert, not a rewrite",
            "NATEWADDINGTON IS OUT, owner: 'get rid of the nate wassington "
            "in the endless climax in endless'. His placard stood at film "
            "260.000 (4:20) -- centre frame, the last card before the "
            "269.700 downbeat the act climaxes on. Only the scheduling went: "
            "his two authored rows are still in git, nothing moved into the "
            "slot, and he is owed a credit somewhere nobody has decided yet",
            "the owner marked Joseph's last two lines one second apart "
            "(megacut 3:39 and 3:40) and a pill needs 2.2s to be read, so "
            "'You got this' is chained behind 'Master your skills' at 99.883 "
            "rather than stacked on it. The ORDER is his and is kept",
            "the choice screen is a full-frame PAUSE MENU over MOVING "
            "picture: the owner asked to 'pause here to let the player "
            "decide', and a real freeze-frame has to be cut into the film "
            "itself, which moves every timecode after it. TODO(owner): "
            "whether the 1.5s teaser is enough or the picture should stop",
            "'Then just cut to the shot of them firing' / 'then it cuts to "
            "the descent' is an EDIT instruction, not a plate: the menu ends "
            "at 88.533 and whatever the film already cuts to is what plays. "
            "TODO(owner): confirm the shot after it is the one meant",
            "Catherine Paganini's OG Guardian card carries NO title row -- "
            "the owner named her and wrote no line, and the other three OG "
            "cards have one. Omitted rather than composed",
            "dims, thockin and jbeda are printed as the LOGINS the owner "
            "wrote ('github/dims'), not as their real names, and their pfps "
            "come from those accounts. Whether the cards should carry real "
            "names instead is the owner's call",
            "vocab/casting.yaml spells Karena's surname 'Angell'; the README "
            "and the owner both say 'Angel', one L. Act II prints the "
            "correction (NAME_CORRECTIONS) rather than editing the vocab, "
            "which is a committed input to six delivered acts (#167)",
            "the two contributors who held the shots 'The Long Walk' took "
            "(HuntedRaven7 at source 195.267 and hanthor at 233.500) are no "
            "longer credited in act II. The owner's instruction for the "
            "chapter is 'No other guardians'; they are owed a credit "
            "elsewhere and nobody has decided where",
            "William Rizzo and Ahmed Adan lose their act II badges to the "
            "same instruction. Rizzo's authored copy stays in "
            "vocab/casting.yaml and Ahmed stays in ensemble.placeholders, so "
            "only the scheduling went",
            "GloriousEggroll's name row is the handle he was written in as; "
            "GitHub records him as Thomas Crider. Which goes on the card is "
            "the owner's call",
            "no title row is authored for GloriousEggroll or A1RM4X -- their "
            "affiliation rides as chrome and the row is omitted rather than "
            "composed",
            "HikariKnight is no longer credited in act II, owner: 'remove "
            "hikari from the eggroll scene'. His plate sat at source 193.800 "
            "(film 2:50.667). His authored copy stays in vocab/casting.yaml "
            "and only the scheduling went -- he is owed a credit elsewhere "
            "and nobody has decided where",
            "the owner's own chat pills still have no pfp: `castrojo` is a "
            "lead, his identity lives on the `cayde_6` binding, and no avatar "
            "is recorded on it. The drawn crest stands in on the montage's "
            "two pills, the 4:51 gaslighting pill, and his closing quote",
            "the 2:19 lead-in banner (owner: \"setting up this scene it's "
            "important\") has no authored copy, so nothing is emitted for it "
            "-- the TOC exchange's first line takes its slot",
            "the CNCF logo the brief marks as [CNCF LOGO] on each announcement "
            "has no asset in this repo; the cards render without it",
            "AN4-CH3CK-12 is not in vocab/casting.yaml -- it is reproduced as "
            "the announcer's label, and casts nobody",
            "the 4:01 cue ('They are not ready for Shua Khan and Greg KH', "
            "a speech bubble ON Cayde) is NOT scheduled: Cayde's "
            "[ REDACTED ] card is at 287.933 (4:47.9), so a bubble anchored "
            "on him cannot also be at 4:01. TODO(owner): which moves -- the "
            "bubble to ~4:48, or the anchor (#98, Questions)",
            "the #119 note's dictated badge anchor (megacut 5:43 = film "
            "221.433) sits inside the #98 pill run (218.484 -> 230.766), "
            "which did not exist on the ALPHA2 cut the owner was watching "
            "-- the pills are the NEWER instruction. The kernel-trustee "
            "badges land at 231.016 instead, the first clear frame, and "
            "still hold across the recruits, the Troy slot and Cayde's 6:01 "
            "shot as the note asks. TODO(owner): badges at 5:43 over the "
            "pills, or the pills keep the window",
            "the #119 note's 6:27 (film 265.433) names github.com/m2 for "
            "the Arc Hunter -- the same shot #198 gave kolunmi the day "
            "AFTER the note was dictated. One shot, two owner-given names: "
            "kolunmi's plate stands (the newer instruction), and m2's "
            "authored copy is in vocab/casting.yaml (he is owed a plate "
            "wherever the owner points). TODO(owner): which name the Arc "
            "Hunter keeps",
            "Troy renders NOTHING: 'Nameplate - Troy (I'll fill in later) "
            "Stormbreaker Titan' (megacut 5:58 = film 236.433) is an "
            "explicit owner placeholder, so he is queued in "
            "ensemble.placeholders and his slot sits empty inside the "
            "trustee badges' hold. The class words are his; every other "
            "row is his to write",
            "Tulip's 'keep it up until 6:20' (film 258.433) is not "
            "honoured: her window-leap shot ends 249.567 and the #98 pills "
            "own 250.000 -> 255.850, so she holds 247.467 -> 249.750 -- up "
            "at the dictated 6:11, gone with her shot. TODO(owner): move "
            "the pills or accept the shot-length hold",
            "krook, cgwalters, siosm, jberkus and preethi are "
            "not in vocab/casting.yaml -- their pills render "
            "as placeholder badges with the drawn crest, and their GitHub "
            "logins are the owner's to confirm before any avatar is fetched "
            "(a login is not guessed). 'cncf marketing' as a speaker and the "
            "Open Gaming Collective callout are reproduced as written; "
            "neither casts anybody",
            "the brief names the same person three ways -- 'Jorge Castro' in "
            "the montage, 'jorge' at 4:51, 'castrojo' in the closing quotes. "
            "All three are reproduced verbatim; the pill's own chrome "
            "uppercases the speaker row",
            "Karena's jump carries no card ('the beat is the jump'): it is "
            f"{JUMP_BEAT}s of clear screen between Joseph's DO line and "
            "Ricardo's answer. No shot was verified as HER jump and picking "
            "one would be casting by inference -- TODO(owner): the frame",
            "the closing five quotes play over the black outro (picture ends "
            "4:51.933): the brief's own schedule put them 4:51 -> 5:07 and "
            "its preamble lands the last cue on the final second. The tail "
            "is black by the owner's standing decision",
            "Joseph's 'DO' and siosm's 'powering up' carry authored emphasis; "
            "the pill's message row is set bold throughout (the site's own "
            "style), so both ARE bold on screen but not differentiated. "
            "siosm's asterisks are emphasis markup and are stripped, not "
            "burned. An accent-colour emphasis would be chrome nobody "
            "authored",
            "the letterbox callout runs 2:19 -> the last frame, where the "
            "brief's scene starts, ducking only the patch-queue HUD's 28.4 s "
            "(its card already occupies the bar's bottom-right; measured, not "
            "aesthetic). 'The whole song' could also mean from 0:00, from the "
            "pill that first asks it (1:43.5), or with NO duck -- that costs "
            "shrinking it to ticker height for the whole film. TODO(owner)",
            "the TOC payoff REPRISES the montage's emeritus card verbatim -- "
            "a callback, not a second credit; the double-credit guard was "
            "taught that a verbatim reprise is not two faces",
        ],
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

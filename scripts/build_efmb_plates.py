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
from tools.plate import CHOICE_POINTER_CUT, CHROME_ROWS  # noqa: E402
from tools import chapter_md  # noqa: E402
from tools import placeholder  # noqa: E402

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
# The owner's 2026-08-17 Endless pass was marked against the then-current
# programme, where Act II starts at 4:26.500. This is a different clock from
# the earlier ALPHA notes above; mixing the two is what pushed 5:59 copy into
# the 8:41 window.
OWNER_PASS_OFFSET = 266.5
TRIO = [
    ("joseph_sandoval", "left", 177.0),
    ("rochaporto", "center", 179.0),
    ("mara_sov", "right", 183.0),
]

# --- THE OPENING BLACK-HEAD CARD ------------------------------------------
#
# The first 10.65 s of Act II are DERIVED black head: there is no picture yet,
# only the bed coming in under black until the first kept frame of the moon
# battle. The owner has now authored that silent-visual seat instead of
# skipping it in the megacut. The card uses the existing title-card treatment:
# title, subtitle, then one authored line per body row.
OPENING_HEAD_CARD = {
    "id": "opening_black_head",
    "kind": "title",
    "position": "center",
    "title": "Eons later",
    "subtitle": "Open Source has led us to the stars",
    "body": [
        "Maintainer-Guardians hold the line for humanity",
        "Fighting against the Toilmaster and his Legion of Clankers",
        "It all started with Kubernetes.",
    ],
}

# ONE L. The README says "Karena Angel" and the owner said it again this round
# ("add karena (Angel, one L)"). vocab/casting.yaml spells it "Angell", and it
# is a committed input to six delivered acts (#167), so correcting it there
# marks every one of them stale. The correction is applied HERE, to the copy
# this act prints, and recorded in `unresolved` -- a person's name is not
# something to leave wrong while waiting for a freeze to lift.
NAME_CORRECTIONS = {"mara_sov": ("Karena Angell", "Karena Angel")}

# --- THE OPENING NAMEPLATES -------------------------------------------------
#
#   "02:15 name plate Sarah Novotny
#    02:20 name plate Brent Burns
#    02:28 name plate github/thockin - 'Does NOT Come in Peace'
#    02:38 name plate github/jbeda - 'Out of Retirement'
#    The last two are OG Guardians; make them a proud bronze"
#
# The opening slot introduces RICARDO ROCHA, owner order 2026-08-20, while
# watching the v4.2 build: "move rochoporto's nameplate introduction to where
# novotny is, this hunter is now rochaporto, lock it in". The hunter in that
# shot is him; his full authored identity (label/class/name/title/wreath)
# rides the plate. Sarah Novotny's record STAYS in casting.yaml -- the order
# named a seat, not her removal (contrast Brent Burns, "remove him
# entirely", same day). She is owed a seat and that is recorded in
# `unresolved`.
#
# BRENT BURNS IS OUT ENTIRELY, owner order 2026-08-20: "remove him entirely".
# He held the second opening slot (02:20) until then; the slot stays empty --
# nobody is promoted into an owner's mark.
OPENING_NAMEPLATES = [
    {"key": "rochaporto", "at_megacut": 135.0},
]

OG_LABEL = "OG GUARDIAN"
OG_GUARDIANS = [
    {"id": "og_thockin", "at_megacut": 148.0, "name": "Tim Hockin",
     "title": "Does NOT Come in Peace", "login": "thockin",
     "seen_at_src": 32.800,
     "why": "the hooded Hunter raising the revolver into frame"},
    # JOE BEDA IS OUT ENTIRELY, owner order 2026-08-20: "Remove jbeda as
    # well" -- as well as Brent Burns, who was "remove him entirely". The
    # 02:38 'Out of Retirement' mark stays empty; nobody inherits an owner's
    # mark. The dictation quoted above keeps his line as history.
]
OG_HOLD = 4.0

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

# --- THE LATER OWNER PASS (megacut 5:13 -> 6:56) --------------------------
#
# Owner note, 2026-08-17: Act II's later programme-time pass is timed off the
# MEGACUT again, so the same 121.567 s offset applies:
#
#   "TITLE OVERLAY SIMILAR TO THE OUTRO / 5:13 PRESENT DAY"
#   "5:59 [mfahlandt] K1 Logistics is clean / [kfaseela] ... /
#    [markmandel] Agones Cluster - ONLINE"
#   "[[github.com/riaankleinhans]] You're getting close"
#   "[github.com/brandtkeller]"
#   "There are two shots with people's faces, add this:
#      6:06 [jrsapi] They learn quickly
#      6:07 [rochaporto] We need to move!
#      6:11 [jrsapi] Projects Teams Metrics are strong
#            They just need mentoring in the right skills
#      6:14 [karena] Like cardio!"
#   "6:23 Mars"
#   "6:29 red miniboss flashing / Your Bad Decisions"
#   "6:30 [karena] Hit 'em with your lessons learned
#    6:32 [rochaporto] One CERN Special coming up!
#    6:41 [jrsapi] Shit are you taking notes?
#    6:45 Move the banner to the top
#    6:56 Do we even know who they are?
#    #UPSTREAMFIRST | Support the Open Gaming Collective(OGC) | #UPSTREAMFIRST"
#
# TWO TIMING CONSTRAINTS MATTER:
# 1. The 5:59 block is a conversation, not a title card. It begins immediately
#    after the choice animation and flows as four standard GitHub-PFP pills;
#    the 6:06 cue still keeps its owner-timed seat.
# 2. The 6:29 "red miniboss flashing" cue is a visual treatment, not a title,
#    chat or banner. This batch is limited to the existing three kinds, so that
#    one stays recorded rather than faked.
PRESENT_DAY = {"at_megacut": 313.0, "hold": 2.6, "title": "PRESENT DAY"}
LATE_PASS = [
    {
        "id": "late_mfahlandt_clean",
        "kind": "chat",
        "position": "left",
        "at_film": 88.883,
        "hold": 2.2,
        "login": "mfahlandt",
        "speaker": "mfahlandt",
        "text": "K1 Logistics is clean",
    },
    {
        "id": "late_kfaseela_gamers",
        "kind": "chat",
        "position": "left",
        "hold": 2.2,
        "login": "kfaseela",
        "speaker": "kfaseela",
        "text": "The gamers were here alright",
    },
    {
        "id": "late_markmandel_online",
        "kind": "chat",
        "position": "left",
        "hold": 2.2,
        "login": "markmandel",
        "speaker": "markmandel",
        "text": "Agones Cluster - ONLINE",
    },
    {
        "id": "late_riaankleinhans_close",
        "kind": "chat",
        "position": "left",
        "hold": 2.2,
        "login": "riaankleinhans",
        "speaker": "riaankleinhans",
        "text": "You're getting close",
    },
    {
        "id": "late_jrsapi_learn",
        "kind": "chat",
        "position": "left",
        "login": "jrsapi",
        "speaker": "jrsapi",
        "text": "They learn quickly",
        "at_megacut": 366.0,
        "hold": 2.2,
    },
    {
        "id": "late_rochaporto_move",
        "kind": "chat",
        "position": "left",
        "login": "rochaporto",
        "speaker": "rochaporto",
        "text": "We need to move!",
        "at_megacut": 367.0,
        "hold": 2.2,
    },
    {
        "id": "late_metrics_cluster",
        "kind": "chat",
        "position": "left",
        "at_megacut": 371.0,
        "hold": 2.75,
        "login": "jrsapi",
        "speaker": "jrsapi",
        "text": (
            "Projects Teams Metrics are strong "
            "They just need mentoring in the right skills"),
    },
    {
        "id": "late_karena_cardio",
        "kind": "chat",
        "position": "left",
        "speaker": "karena",
        "text": "Like cardio!",
        "at_megacut": 374.0,
        "hold": 2.2,
    },
    {
        "id": "late_mars_title",
        "kind": "title",
        "position": "boss",
        "at_megacut": 383.0,
        "hold": 2.2,
        "title": "Mars",
    },
    {
        "id": "late_clankers_context",
        "kind": "context",
        "position": "context",
        "at_film": 45.2,
        "hold": 6.0,
        "title": "Clankers and Contributors",
        "subtitle": "2026",
        "body": [
            "The Community fights its way",
            "Through the Chaos",
            "To Find the Kube of Destiny",
        ],
    },
    # THE RED FLASH IS AUTHORED IN chapters/II-endless-forms.md NOW --
    # `! [late_poor_technical_decisions] POOR TECHNICAL DECISIONS |` under
    # `## 6:45`. Deleting it here would strand the evidence; editing it here
    # would fork the copy. The chapter file owns seat and wording.
    {
        "id": "late_karena_lessons",
        "kind": "chat",
        "position": "left",
        "speaker": "karena",
        "text": "Hit 'em with your lessons learned",
        "at_megacut": 390.0,
        "hold": 2.2,
    },
    {
        "id": "late_rochaporto_cern",
        "kind": "chat",
        "position": "left",
        "login": "rochaporto",
        "speaker": "rochaporto",
        "text": "One reference architecture coming up!",
        "at_megacut": 392.0,
        "hold": 2.6,
    },
    {
        "id": "late_jrsapi_notes",
        "kind": "chat",
        "position": "left",
        "login": "jrsapi",
        "speaker": "jrsapi",
        "text": "Shit are you taking notes?",
        "at_megacut": 401.0,
        "hold": 2.6,
    },
    {
        "id": "late_final_question",
        "kind": "title",
        "position": "center",
        "scale": 0.9,
        "at_megacut": 416.0,
        "at_film": 150.0,
        "hold": 2.6,
        "title": "Do we even know who they are?",
    },
]
TOP_BANNER = {
    "id": "top_banner_ogc",
    "kind": "banner",
    # Owner, 2026-08-20: banners and CTAs with #hashtags ride the TOP
    # letterbox bar, never the picture -- the boss lane is for boss bars.
    "position": "letterbox_top",
    "at_megacut": 405.0,
    "text": "#UPSTREAMFIRST | Support the Open Gaming Collective(OGC) | #UPSTREAMFIRST",
}
LATE_PASS_REPLACEMENTS = {
    "chat_joseph_master",
    "chat_joseph_gotthis",
    "montage_chat_1",
    "montage_chat_2",
    "walk_ge_upstream",
    "trustee_gregkh",
    "trustee_shuah_khan",
    "solo_tulilirockz",
    "timed_krook",
    "timed_bedazzle",
    "solo_kolunmi",
    "quote_cgwalters",
    "quote_siosm",
    "quote_jberkus",
    "quote_preethi",
    "quote_castrojo",
}

# --- THE MAPPED 8:28 -> 9:31 OWNER PASS -----------------------------------
#
# The next mapped megacut block starts at act-II film 4:01.5. The complete
# owner-authored copy was recovered from the original session record after the
# first implementation incorrectly claimed it was unavailable. The picture
# freeze, Amber insert, and music treatment are mirrored by build_efmb.py;
# missing picture never licenses dropping the words.
MAPPED_TAIL_REPLACEMENTS = {
    "solo_EyeCantCU",
    "solo_KyleGospo",
    "solo_p5",
    "timed_jorge",
}
MAPPED_TAIL_PASS = [
    {
        "id": "mapped_redacted_blow",
        "kind": "chat",
        "position": "left",
        "at_film": 242.4,
        "hold": 2.6,
        "speaker": "[redacted]",
        "text": "Or go blow some shit up",
    },
    {
        "id": "mapped_amber_reveal",
        "kind": "guardian",
        "position": "left",
        "at_film": build_efmb.AMBER_AT,
        "hold": 4.0,
        "key": "akgraner",
        "seen_at_src": 48.0,
        "seen_in_video": build_efmb.AMBER_SOURCE_ID,
        "shot_src": [build_efmb.AMBER_CLIP_IN, build_efmb.AMBER_CLIP_OUT],
        "why": "the owner identified this gameplay clip as Amber's sequence",
    },
    {
        "id": "mapped_kyle_reveal",
        "kind": "guardian",
        "position": "left",
        "at_film": build_efmb.KYLE_REVEAL_AT,
        "hold": build_efmb.KYLE_REVEAL_SEC,
        "key": "KyleGospo",
        "seen_at_src": build_efmb.SYNC_ANCHOR_SRC,
        "shot_src": [335.267, 339.767],
        "why": "the Sentinel raising the Void shield in the authored reveal",
    },
    # HATERS IS AUTHORED IN chapters/II-endless-forms.md NOW --
    # `! [mapped_haters] HATERS |` under `## 10:00`. The seat's evidence
    # (the red-lit face shot, film 315.267 -> 316.967 by scene detection)
    # is recorded beside the line there. This spec's old seen_at_src pointed
    # at the hallway frame, which is NOT that shot; the card now carries no
    # seen_at_src rather than a wrong one.
    {
        "id": "mapped_kyle_sup",
        "kind": "chat",
        # RIGHT lane, not the default left -- see the bond note below.
        "position": "right",
        # OWNER-PLACED, DO NOT MOVE. 310.4 is where the owner had it.
        #
        # He asked for it on the Titan close-up ("sup is a purple titan ...
        # put it when it's zoomed into his face") -- that frame is film 317.0.
        # It CANNOT be seated there: KYLE_REVEAL_AT is 318.737, so a 2.2s hold
        # from 317.0 overlaps his own nameplate and the builder refuses it.
        #
        # An agent then slid it to 316.287 to make the assertion pass, which
        # put it AFTER kolunmi's "Disco!" (313.2) and reordered the authored
        # exchange. That is the fourth class in AGENTS.md: a gate refusing a
        # seat is not permission to move an authored beat. Reverted.
        #
        # The conflict is the owner's to settle -- move the reveal, shorten the
        # hold, or keep 310.4. Until he does, his number stands.
        "at_film": 316.967,
        # OWNER, verbatim: "sup is a purple titan", "put it when it's
        # zoomed into his face". 316.967 is the first frame of that
        # close-up, measured by scene detection (the shot runs
        # 316.967 -> 317.733). The pill OPENS on his face, which is what
        # he asked for. Nothing else moves.
        "hold": 2.2,
        "speaker": "kylegospo",
        "text": "Sup",
        "avatar_login": "KyleGospo",
        # BONDED to his own nameplate, in the deck's bonded-pair shape:
        # nameplate holds the left, the pill takes the RIGHT. The owner
        # locked both TIMES ("lock the plate"; the pill on the close-up's
        # first frame) -- the lane was never his instruction, and stacking
        # both on the left drew them on top of each other for the pill's
        # last 0.43 s (the nameplate arrives at 318.737). Right lane, same
        # seats: the pair reads as the site's GUARDIAN BOND composition.
        "bond_of": "mapped_kyle_reveal",
    },
    {
        "id": "mapped_kolunmi_disco",
        "kind": "chat",
        "position": "left",
        "at_film": 313.2,
        "hold": 2.2,
        "speaker": "kolunmi",
        "text": "Disco!",
        "avatar_login": "kolunmi",
    },
    {
        "id": "mapped_eyecantcu_reveal",
        "kind": "guardian",
        "position": "left",
        "at_film": build_efmb.EYECANTCU_AT,
        "hold": 3.2,
        "key": "EyeCantCU",
        "seen_at_src": build_efmb.EYECANTCU_SRC,
        "shot_src": [353.533, 355.167],
        "why": "the evidenced Warlock frame held in the authored 9:31 seat",
    },
]

BLACK_CONVERSATION = [
    ("mapped_akgraner_kyle", "akgraner", "Hi sugar, I'm looking for Kyle", 2.2,
     "akgraner"),
    ("mapped_hikari_ouch", "HikariKnight", "Ouch man wtf!", 2.2,
     "HikariKnight"),
    ("mapped_owen_sorry", "Owen", "Oh sorry my bad", 2.2, None),
    ("mapped_kolunmi_pvp", "kolunmi", "Who turned PvP on?", 2.2, "kolunmi"),
    ("mapped_karena_pve", "karena",
     "Don't look at me I only put PvE on Legendary", 3.0, "karena"),
    ("mapped_cam_noone", "cam", "Mom no one plays this game", 2.2, None),
    ("mapped_hikari_wait", "HikariKnight", "Hey wait?!", 2.2,
     "HikariKnight"),
    ("mapped_kolunmi_users", "kolunmi",
     "Are those ... other linux users?", 2.6, "kolunmi"),
]

AFTER_AMBER_CONVERSATION = [
    ("mapped_owen_slay", "Owen", "Slay out, Queen!", 2.2, None, 1.0),
    ("mapped_akgraner_kindness_1", "akgraner",
     "Kindness is doing what's right", 2.2, "akgraner", 1.18),
    ("mapped_akgraner_kindness_2", "akgraner",
     "For the ecosystem.", 2.2, "akgraner", 1.18),
    ("mapped_akgraner_kindness_3", "akgraner",
     "For our users.", 2.2, "akgraner", 1.18),
    ("mapped_akgraner_kindness_4", "akgraner",
     "And for our maintainers.", 2.2, "akgraner", 1.18),
    ("mapped_akgraner_kindness_5", "akgraner",
     "Don't be nice.", 2.2, "akgraner", 1.18),
    ("mapped_akgraner_kindness_6", "akgraner",
     "Be kind.", 2.2, "akgraner", 1.18),
    ("mapped_which_kyle", "akgraner", "Which one of you is Kyle?", 2.6,
     "akgraner", 1.0),
]

# --- THE MAPPED 7:03 -> 8:26 OWNER PASS -----------------------------------
#
# The later owner notes past 7:03 are NOT Act II standalone time. They were
# mapped against the actual megacut plan and land here on Act II's FILM clock:
#
#   7:03 -> 2:36.5   7:42 -> 3:15.5   8:08 -> 3:41.5
#   7:06 -> 2:39.5   7:52 -> 3:25.5   8:11 -> 3:44.5
#   7:09 -> 2:42.5   7:59 -> 3:32.5   8:18 -> 3:51.5
#   7:12 -> 2:45.5   8:03 -> 3:36.5   8:26 -> 3:59.5
#   7:16 -> 2:49.5
#
# Every record below is the owner's own words. Anything that was only an
# effect note ("rare drop", "flashing") is rendered with the nearest existing
# chrome and recorded in `unresolved` rather than invented as a new treatment.
MAPPED_PASS_REPLACEMENTS = {
    "walk_ge_1",
    "walk_ge_2",
    "walk_ge_3",
    "walk_A1RM4X",
    "walk_ge_stream",
    "walk_a1rm4x",
    "walk_ge_soundcard",
    "walk_ge_glorious",
    "walk_ge_lesson",
    "toc_joseph_faith",
    "toc_ricardo_desktop",
    "toc_joseph_lol",
}
MAPPED_PASS = [
    {
        "id": "mapped_saturn_title",
        "kind": "title",
        "position": "boss",
        "at_film": 156.666,
        "hold": 2.2,
        "title": "SATURN",
        "subtitle": "Nobara Contributor LionHeartP and A1RMAX",
    },
    {
        "id": "mapped_kernel_bump",
        "kind": "chat",
        "position": "left",
        "at_film": 159.5,
        "hold": 2.2,
        "speaker": "[redacted]",
        "text": "Time to bump the kernel",
    },
    {
        "id": "walk_lionheartp",
        "kind": "plate",
        "position": "right",
        "at_film": 162.5,
        "hold": 2.75,
        "avatar_login": "LionHeartP",
        "variant": "nobara",
        "label": "NOBARA CONTRIBUTOR",
        "class": "Sunbreaker Titan",
        "name": "LionHeartP",
        "title": "Nessus of Nobara",
        "why": "the centered Guardian against Saturn, one shot before pastaq's cue",
    },
    {
        "id": "mapped_pastaq_tests",
        "kind": "chat",
        "position": "left",
        "at_film": 165.5,
        "hold": 2.2,
        "avatar_login": "pastaq",
        "speaker": "pastaq",
        "text": "All your tests passed right?",
    },
    {
        "id": "mapped_lionheartp_what_tests",
        "kind": "chat",
        "position": "left",
        "at_film": 169.5,
        "hold": 2.2,
        "avatar_login": "LionHeartP",
        "speaker": "LionHeartP",
        "text": "What tests?",
    },
    {
        "id": "walk_A1RM4X",
        "kind": "ghost",
        "position": "left",
        "at_src": 195.267,
        "hold": 3.0,
        "avatar_login": "A1RM4X",
        "variant": "youtube",
        "label": "NEW CONTRIBUTOR",
        "name": "A1RM4X",
        "title": "Useful Youtuber (UNCOMMON)",
        "why": "the freed-up ghost seat before GloriousEggroll speaks to him",
    },
    {
        "id": "mapped_a1rmax_intro",
        "kind": "chat",
        "position": "left",
        "at_film": 175.5,
        "hold": 2.5,
        "avatar_login": "A1RM4X",
        "speaker": "A1RM4X",
        "text": (
            "Thank you I never thought I could help! "
            "I'm not like you I'm just a lowly user"),
    },
    {
        "id": "walk_ge_stream",
        "kind": "chat",
        "position": "left",
        "at_film": 178.5,
        "hold": 2.2,
        "speaker": "GloriousEggroll",
        "text": "It's your patch, turn the stream on",
    },
    {
        "id": "walk_a1rm4x",
        "kind": "chat",
        "position": "left",
        "hold": 2.2,
        "avatar_login": "LionHeartP",
        "speaker": "LionHeartP",
        "text": "Let's get these numbers up",
    },
    {
        "id": "mapped_lionheartp_hardware",
        "kind": "chat",
        "position": "left",
        "at_film": 183.5,
        "hold": 2.7,
        "avatar_login": "LionHeartP",
        "speaker": "LionHeartP",
        "text": "Why spend the extra dollar to support Linux hardware",
    },
    {
        "id": "walk_ge_glorious",
        "kind": "chat",
        "position": "left",
        "at_film": 187.5,
        "hold": 2.8,
        "speaker": "GloriousEggroll",
        "text": "There's nothing glorious about this job",
    },
    {
        "id": "mapped_lionheartp_together",
        "kind": "chat",
        "position": "left",
        "at_film": 195.5,
        "hold": 3.8,
        "avatar_login": "LionHeartP",
        "speaker": "LionHeartP",
        "text": "When we work together This gets easier",
    },
    {
        "id": "mapped_eggroll_title",
        "kind": "chat",
        "position": "left",
        "at_film": 205.5,
        "hold": 4.5,
        "speaker": "GloriousEggroll",
        "text": (
            "Nice work testing that patch "
            "Usually Blueberries just "
            "Send me a bunch of crap"),
    },
    {
        "id": "mapped_eggroll_didyou",
        "kind": "chat",
        "position": "left",
        "at_film": 212.5,
        "hold": 2.2,
        "speaker": "GloriousEggroll",
        "text": "You didn't test any of this did you.",
    },
    {
        "id": "mapped_pastaq_what_tests",
        "kind": "chat",
        "position": "left",
        "at_film": 216.5,
        "hold": 2.2,
        "gap_after": 0.0,
        "avatar_login": "pastaq",
        "speaker": "pastaq",
        "text": "Hey man WHAT tests?",
    },
    {
        "id": "walk_ge_lesson",
        "kind": "chat",
        "position": "right",
        "at_film": 218.766,
        "hold": 2.2,
        "avatar_login": "LionHeartP",
        "speaker": "LionHeartP",
        "text": "Let's go!",
    },
    {
        "id": "mapped_redacted_unlearning",
        "kind": "chat",
        "position": "left",
        "at_film": 221.5,
        "hold": 2.75,
        "speaker": "[redacted]",
        "text": "Unlearning bad habits takes time",
    },
    {
        "id": "mapped_redacted_options",
        "kind": "chat",
        "position": "left",
        "at_film": 224.5,
        "hold": 6.75,
        "speaker": "[redacted]",
        "text": (
            "Your options are success "
            "Or a lifetime of servitude in the Toilmaster's Packaging Mines"),
    },
    {
        "id": "mapped_kyle_titanfall",
        "kind": "chat",
        "position": "left",
        "at_film": 239.95,
        "hold": 2.2,
        "avatar_login": "KyleGospo",
        "speaker": "KyleGospo",
        "text": "FOR TITANFALL!",
    },
]
OWNER_CONVO = [
    ("owner_convo_karena", "karena",
     "The Kube always seeks open source potential"),
    ("owner_convo_joseph", "joseph",
     "We can't let The Toilmaster enslave another generation"),
]
OWNER_CONVO_AT = 231.5

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
# So: a FULL-FRAME pause menu that carries riaankleinhans's question in its
# heading, the second option carrying Destiny's amber legendary chrome, and a
# cursor that leaves the centre of the screen heading for it and never arrives
# before the film cuts. It is animated the only way a still-plate pipeline can
# animate: a short run of frames, each one a plate, one group, back to back.
CHOICE_OPTIONS = [
    "Update your LFX Profile",
    {"text": "Do it the hard way", "tier": "legendary"},
]
CHOICE_HOLD = 4.2          # Riaan's prompt and the decision screen, one window
CHOICE_FPS = 16            # the cursor's frame rate; the film's is 59.94.
                           # Rounded to 67 frames, long enough to read.
                           # sequence has an integral rate and tpad does not
                           # have to round one.

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

# Dylan Taylor and Ahmed Adan remain recorded in `ensemble.placeholders`, but
# neither has a scheduled Act II nameplate. The owner removed Dylan's card;
# Ahmed's had already been removed when The Long Walk displaced it.
PLACEHOLDERS = []

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

# Cayde's sign-off ("I'm so proud of you kids!") is RETIRED -- owner,
# 2026-08-20: "I don't want it in the movie." The card left the manifest in
# the v3.9 converge; the emission code and the one-line
# dialogue/yt_destiny_all_live_action_trailers/ record followed it out. His
# hero pose at source 358.200 -> 360.500 plays clean, then three figures
# walk into the cathedral light. The redaction joke itself is untouched: the
# `cayde_6` binding in vocab/casting.yaml still carries it, and act VIII's
# "Directed by" card is still his one reveal.

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

# The letterbox callout. "Keep it up for the whole song": it comes up where
# the brief's own scene starts (2:19, the montage's hand-off) and holds to
# the last frame. It never shares the lower third's row -- it lives on the
# bottom letterbox bar, below the picture.
#
# ONE DUCK, AND IT IS MEASURED, NOT AESTHETIC. The walk's patch-queue HUD is
# bottom-right and its card dips 90px onto the bar (y 922-1030 in the shipped
# geometry); no position on the bar clears it while it holds. So the callout
# ducks exactly the HUD's window -- 28.4 s in a 169 s hold -- rather than
# shrink to ticker height for the whole song to fix half a minute. The
# alternative is the owner's to call (#98, Questions); recorded in
# `unresolved`.
LETTERBOX_BANNER = (
    "#FIGHTFORCONTRIBUTORS - Support Open Gaming Collective - #UPSTREAMFIRST")

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


def github_avatar(login):
    """A direct GitHub avatar binding for owner-seated login copy."""
    return {
        "avatar": str(AVATAR_DIR / f"{login}.png"),
        "avatar_url": f"https://github.com/{login}.png?size=256",
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
        if p.get("kind") in CHROME_ROWS:
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
        return build_efmb.edited_film_for_source(src, lead)

    plates = []
    opening_head_dur = round(plan["bed_lead_sec"], 3)
    plates.append({
        "at": 0.0,
        "dur": opening_head_dur,
        "copy_source": "owner_supplied",
        **OPENING_HEAD_CARD,
    })

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

    # --- the opening nameplates (Brent's and Joe's slots stay empty) -------
    for spec in OPENING_NAMEPLATES:
        at = round(spec["at_megacut"] - MEGACUT_OFFSET, 3)
        hold = clamp_hold(at, OG_HOLD, film_of)
        assert hold, (
            f"{spec['key']} at {at:.3f}s cannot clear a no-plate zone and "
            "still be readable -- the owner's mark has to move")
        plates.append({
            "id": f"opening_{spec['key']}",
            "at": at,
            "dur": hold,
            "position": "left",
            "copy_source": "casting",
            "why": "owner-seated opening nameplate replacing a retired credit",
            **localise_avatar(spec["key"], authored_copy(spec["key"], casting)),
        })

    # --- the remaining OG Guardians, in bronze ----------------------------
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
        if og.get("seen_at_src") is not None:
            entry["seen_at_src"] = og["seen_at_src"]
        if og.get("why"):
            entry["why"] = og["why"]
        plates.append(entry)

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
        if f"solo_{b['key']}" in (
                LATE_PASS_REPLACEMENTS | MAPPED_PASS_REPLACEMENTS
                | MAPPED_TAIL_REPLACEMENTS):
            continue
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

        # The full-frame choice screen owns Riaan's question. Rendering a
        # separate chat pill spends the same text twice and delays the graphic.
        if spec["id"] == "chat_riaan_choices":
            frames = max(2, int(round(CHOICE_HOLD * CHOICE_FPS)))
            step = round(CHOICE_HOLD / frames, 4)
            start = at
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
            continue

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

    # --- the later owner pass's opening title -----------------------------
    present_day_at = round(PRESENT_DAY["at_megacut"] - OWNER_PASS_OFFSET, 3)
    plates.append({
        "id": "late_present_day",
        "kind": "title",
        "at": present_day_at,
        "dur": PRESENT_DAY["hold"],
        "position": "boss",
        "copy_source": "owner_supplied",
        "seen_at_src": round(build_efmb.source_for_film(present_day_at, lead), 3),
        "title": PRESENT_DAY["title"],
    })

    # --- the TOC exchange (owner brief #98, section 3) ---------------------
    # One screen, one card: the exchange shares the lower third with
    # everything else, so it is scheduled on ONE cursor even where the card's
    # lane changes -- load_manifest_entries is position-blind, and two cards
    # in different thirds of the frame still read as two cards at once.
    toc = []

    def src_of(film_sec):
        """An owner mark is given in FILM time; anchor it in SOURCE time."""
        return build_efmb.edited_source_for_film(film_sec, lead)

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

    # --- the mapped 7:03 -> 8:26 owner pass -------------------------------
    mapped_unresolved = []
    mapped = []
    mapped_cursor = 0.0
    for spec in MAPPED_PASS:
        if spec.get("at_src") is not None:
            want = round(film_of(spec["at_src"]) + LEAD_IN, 3)
        elif spec.get("at_film") is not None:
            want = round(spec["at_film"], 3)
        else:
            want = round(mapped_cursor + PLATE_GAP, 3)
        at = round(max(want, mapped_cursor), 3)
        if ((spec.get("at_src") is not None or spec.get("at_film") is not None)
                and at > want + 1e-6):
            mapped_unresolved.append(
                f"{spec['id']} is owner-timed to Act II film {want:.3f}, but "
                f"the previous mapped card clears at {mapped_cursor:.3f}, so "
                f"it lands at {at:.3f} instead. The order is the owner's; "
                "only the gap is the timeline's")
        entry = {
            "id": spec["id"],
            "at": at,
            "dur": spec["hold"],
            "position": spec["position"],
            "copy_source": "owner_supplied",
        }
        if spec["kind"] in {"plate", "ghost"}:
            if spec["kind"] == "ghost":
                entry["kind"] = "ghost"
            entry.update({
                "label": spec["label"],
                "name": spec["name"],
                "title": spec["title"],
            })
            if spec.get("class"):
                entry["class"] = spec["class"]
            if spec.get("variant"):
                entry["variant"] = spec["variant"]
            if spec.get("bond_of"):
                entry["bond_of"] = spec["bond_of"]
            if spec.get("avatar_login"):
                entry.update(github_avatar(spec["avatar_login"]))
            if at <= plan["picture_sec"]:
                entry["seen_at_src"] = round(src_of(at), 3)
                entry["why"] = spec["why"]
        elif spec["kind"] == "chat":
            entry.update({
                "kind": "chat",
                "speaker": spec["speaker"],
                "text": spec["text"],
                "text_source": "owner_supplied",
            })
            if spec.get("avatar_login"):
                entry.update(github_avatar(spec["avatar_login"]))
            elif spec["speaker"] in ("GloriousEggroll",):
                entry.update(chat_avatar(spec["speaker"], casting))
            if at <= plan["picture_sec"]:
                entry["seen_at_src"] = round(src_of(at), 3)
        elif spec["kind"] == "title":
            entry.update({
                "kind": "title",
                "title": spec["title"],
            })
            if spec.get("subtitle"):
                entry["subtitle"] = spec["subtitle"]
            if spec.get("body"):
                entry["body"] = list(spec["body"])
            if spec.get("scale") is not None:
                entry["scale"] = spec["scale"]
            if at <= plan["picture_sec"]:
                entry["seen_at_src"] = round(src_of(at), 3)
        mapped.append(entry)
        mapped_cursor = round(at + spec["hold"] + spec.get("gap_after", PLATE_GAP), 3)

    convo_cursor = OWNER_CONVO_AT
    for pid, speaker, txt in OWNER_CONVO:
        hold = round(max(MIN_HOLD, len(txt) / 15), 3)
        at = round(convo_cursor, 3)
        entry = {
            "id": pid,
            "kind": "chat",
            "at": at,
            "dur": hold,
            "position": "left",
            "copy_source": "owner_supplied",
            "speaker": speaker,
            "text": txt,
            "text_source": "owner_supplied",
        }
        if speaker == "karena":
            entry.update(github_avatar("karena"))
        if at <= plan["picture_sec"]:
            entry["seen_at_src"] = round(src_of(at), 3)
        mapped.append(entry)
        convo_cursor = round(at + hold + PLATE_GAP, 3)
    mapped_unresolved.append(
        "the owner conversation at 231.500 now keeps only karena and joseph; "
        "krook and both rochaporta lines were removed by the owner. Karena's "
        "chat uses github.com/karena, as explicitly supplied this round")

    # --- the later owner pass (megacut 5:59 -> 6:56) ----------------------
    late_unresolved = []
    late = []
    late_cursor = 0.0
    for spec in LATE_PASS:
        if spec.get("at_film") is not None:
            want = round(spec["at_film"], 3)
        elif spec.get("at_megacut") is not None:
            want = round(spec["at_megacut"] - OWNER_PASS_OFFSET, 3)
        else:
            want = round(late_cursor + PLATE_GAP, 3)
        at = round(want if spec["kind"] == "context" else max(want, late_cursor), 3)
        if spec.get("at_megacut") is not None and at > want + 1e-6:
            mm = int(spec["at_megacut"] // 60)
            ss = spec["at_megacut"] % 60
            late_unresolved.append(
                f"{spec['id']} is owner-timed to megacut "
                f"{mm}:{ss:04.1f} "
                f"(film {want:.3f}) but the previous card clears at "
                f"{late_cursor:.3f}, so it lands at {at:.3f} instead. The "
                "order is the owner's; only the gap is the timeline's")
        entry = {
            "id": spec["id"],
            "kind": spec["kind"],
            "at": at,
            "dur": spec["hold"],
            "position": spec["position"],
            "copy_source": "owner_supplied",
        }
        if spec["kind"] == "chat":
            entry.update({
                "speaker": spec["speaker"],
                "text": spec["text"],
                "text_source": "owner_supplied",
            })
            if spec.get("login"):
                entry["avatar"] = str(AVATAR_DIR / f"{spec['login']}.png")
                entry["avatar_url"] = (
                    f"https://github.com/{spec['login']}.png?size=256")
        elif spec["kind"] == "warning":
            entry["text"] = spec["text"]
            entry["text_source"] = "owner_supplied"
        elif spec["kind"] == "miniboss":
            # The kernel boss bar's closed pair. `title` is omitted when
            # nobody has authored one -- _render_miniboss draws the name row
            # alone rather than inventing a second line.
            entry["name"] = spec["name"]
            entry["text_source"] = "owner_supplied"
            if spec.get("title"):
                entry["title"] = spec["title"]
                if spec.get("title_placeholder"):
                    entry["title_source"] = "placeholder"
        else:
            entry["title"] = spec["title"]
            if spec.get("subtitle"):
                entry["subtitle"] = spec["subtitle"]
            if spec.get("body"):
                entry["body"] = list(spec["body"])
            if spec.get("scale") is not None:
                entry["scale"] = spec["scale"]
        if spec.get("at_megacut") is not None and at <= plan["picture_sec"]:
            entry["seen_at_src"] = round(src_of(at), 3)
        late.append(entry)
        if spec["kind"] != "context":
            late_cursor = round(at + spec["hold"] + PLATE_GAP, 3)

    top_banner_at = round(TOP_BANNER["at_megacut"] - OWNER_PASS_OFFSET, 3)
    # The OGC banner rides the TOP letterbox bar now (owner, 2026-08-20:
    # hashtag banners and CTAs live in the letterbox, not on the content).
    # Its windows are unchanged: it still ducked the old skill-banner zone at
    # 231.5 -> 239.5, even though that lane is now lower-third chat.
    ogc_resume_at = 239.5
    for i, (start, end) in enumerate((
            (top_banner_at, OWNER_CONVO_AT),
            (ogc_resume_at, build_efmb.HALLWAY_AT)), 1):
        late.append({
            "id": f"{TOP_BANNER['id']}_{i}",
            "kind": "banner",
            "at": start,
            "dur": round(end - start, 3),
            "position": TOP_BANNER["position"],
            "copy_source": "owner_supplied",
            "text": TOP_BANNER["text"],
            "text_source": "owner_supplied",
        })

    mapped_tail = []
    black_cursor = round(build_efmb.HALLWAY_AT + 0.5, 3)
    for pid, speaker, text, hold, avatar_login in BLACK_CONVERSATION:
        entry = {
            "id": pid,
            "kind": "chat",
            "at": black_cursor,
            "dur": hold,
            "position": "left",
            "copy_source": "owner_supplied",
            "speaker": speaker,
            "text": text,
            "text_source": "owner_supplied",
        }
        if avatar_login:
            entry.update(github_avatar(avatar_login))
        mapped_tail.append(entry)
        black_cursor = round(black_cursor + hold + PLATE_GAP, 3)
    assert black_cursor <= build_efmb.AMBER_AT

    after_cursor = round(build_efmb.HALLWAY_AFTER_AMBER_AT + 0.5, 3)
    for pid, speaker, text, hold, avatar_login, scale in AFTER_AMBER_CONVERSATION:
        entry = {
            "id": pid,
            "kind": "chat",
            "at": after_cursor,
            "dur": hold,
            "position": "left",
            "copy_source": "owner_supplied",
            "speaker": speaker,
            "text": text,
            "text_source": "owner_supplied",
            "scale": scale,
        }
        if avatar_login:
            entry.update(github_avatar(avatar_login))
        mapped_tail.append(entry)
        after_cursor = round(after_cursor + hold + PLATE_GAP, 3)
    assert after_cursor <= build_efmb.HALLWAY_RETURN_AT

    for spec in MAPPED_TAIL_PASS:
        entry = {
            "id": spec["id"],
            "kind": spec["kind"],
            "at": round(spec["at_film"], 3),
            "dur": spec["hold"],
            "position": spec["position"],
            "copy_source": "owner_supplied",
        }
        seen_at_src = (
            spec["seen_at_src"] if spec.get("seen_at_src") is not None
            else src_of(spec["at_film"])
        )
        entry["seen_at_src"] = round(seen_at_src, 3)
        if spec.get("seen_in_video"):
            entry["seen_in_video"] = spec["seen_in_video"]
        if spec["kind"] == "chat":
            entry.update({
                "speaker": spec["speaker"],
                "text": spec["text"],
                "text_source": "owner_supplied",
            })
            if spec.get("avatar_login"):
                entry.update(github_avatar(spec["avatar_login"]))
            if spec.get("bond_of"):
                entry["bond_of"] = spec["bond_of"]
        elif spec["kind"] == "title":
            entry["title"] = spec["title"]
            if spec.get("body"):
                entry["body"] = list(spec["body"])
            if spec.get("scale") is not None:
                entry["scale"] = spec["scale"]
        elif spec["kind"] == "warning":
            entry["text"] = spec["text"]
            entry["text_source"] = "owner_supplied"
        elif spec["kind"] == "miniboss":
            # The kernel boss bar's closed pair. `title` is omitted when
            # nobody has authored one -- _render_miniboss draws the name row
            # alone rather than inventing a second line.
            entry["name"] = spec["name"]
            entry["text_source"] = "owner_supplied"
            if spec.get("title"):
                entry["title"] = spec["title"]
                if spec.get("title_placeholder"):
                    entry["title_source"] = "placeholder"
        elif spec["kind"] == "guardian":
            entry.pop("kind")
            entry["copy_source"] = "casting"
            entry["shot_src"] = list(spec["shot_src"])
            entry["why"] = spec["why"]
            entry.update(localise_avatar(
                spec["key"],
                _corrected(spec["key"], authored_copy(spec["key"], casting))))
        mapped_tail.append(entry)

    # The newer 8:28 pass replaces the old gaslighting pill. Its authored copy
    # remains above in TIMED_JORGE; no stale plate is built on the shifted film.
    timed = []
    film_sec = plan["film_sec"]

    # The letterbox callout: up where the brief's scene starts, down on the
    # last frame -- "keep it up for the whole song". Two windows: it ducks the
    # patch-queue HUD, the one card that already owns a piece of the bar. The
    # HUD holds from the enemies' reveal until the villain lands (see the
    # walk's own schedule above), so those are the duck's edges.
    # The owner's newer pass moves this banner to the top at film 2:18.5.
    # The old bottom-letterbox windows are superseded rather than layered.

    plates.extend(toc)
    plates.extend(timed)
    plates.extend(late)
    plates.extend(mapped_tail)
    plates = [p for p in plates if p["id"] not in (
        LATE_PASS_REPLACEMENTS | MAPPED_PASS_REPLACEMENTS
        | MAPPED_TAIL_REPLACEMENTS)]
    plates.extend(mapped)

    # The owner-authored conversations in chapters/II-endless-forms.md. Same
    # entry shape as everything above; whatever its scheduler cannot honour
    # is recorded in `unresolved`, never raised -- and every note is printed,
    # because the owner's rule is "always inform the operator of
    # improvements", not file them away.
    chapter_entries, chapter_unresolved = chapter_md.entries("II")
    for note in chapter_unresolved:
        print(f"chapter: {note}", file=sys.stderr)
    plates.extend(chapter_entries)

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
        "unresolved": (montage_unresolved + walk_unresolved + mapped_unresolved
                        + late_unresolved + chapter_unresolved + [
            "AN4-CH3CK-12 IS OUT, owner: 'Remove all this anacheck stuff for "
            "now.' Three blocks went with him -- the four ranked montage "
            "cards, the two TOC payoff cards ('It's totally NOT like this' "
            "and 'Have you met our Ambassadors?'), and the eyebrow on "
            "Natewaddington's placard. Every string is still in git; 'for "
            "now' means this is a revert, not a rewrite",
            "SARAH NOVOTNY'S SEAT WENT TO RICARDO ROCHA, owner 2026-08-20: "
            "'move rochoporto's nameplate introduction to where novotny is, "
            "this hunter is now rochaporto'. Unlike Brent Burns and Joe Beda "
            "the same day, she was NOT ordered out -- her authored record "
            "stays in vocab/casting.yaml and she is owed a seat nobody has "
            "named yet",
            "NATEWADDINGTON IS OUT, owner: 'get rid of the nate wassington "
            "in the endless climax in endless'. His placard stood at film "
            "260.000 (4:20) -- centre frame, the last card before the "
            "269.700 downbeat the act climaxes on. Only the scheduling went: "
            "his two authored rows are still in git, nothing moved into the "
            "slot, and he is owed a credit somewhere nobody has decided yet",
            "the choice screen is a full-frame PAUSE MENU over MOVING "
            "picture: the owner asked to 'pause here to let the player "
            "decide', and a real freeze-frame has to be cut into the film "
            "itself, which moves every timecode after it. TODO(owner): "
            "whether the 1.5s teaser is enough or the picture should stop",
            "'Then just cut to the shot of them firing' / 'then it cuts to "
            "the descent' is an EDIT instruction, not a plate: the menu ends "
            "at 88.533 and whatever the film already cuts to is what plays. "
            "TODO(owner): confirm the shot after it is the one meant",
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
            "HikariKnight's Guardian plate remains removed from the Eggroll "
            "scene on the owner's instruction. His later black-screen chat "
            "lines are a separate owner-authored conversation, not a restored "
            "credit on that shot",
            "the owner's own chat pills still have no pfp: `castrojo` is a "
            "lead, his identity lives on the `cayde_6` binding, and no avatar "
            "is recorded on it. The drawn crest stands in on the montage's "
            "two pills and the 4:51 gaslighting pill",
            "the 2:19 lead-in banner (owner: \"setting up this scene it's "
            "important\") has no authored copy, so nothing is emitted for it "
            "-- the TOC exchange's first line takes its slot",
            "the CNCF logo the brief marks as [CNCF LOGO] on each announcement "
            "has no asset in this repo; the cards render without it",
            "AN4-CH3CK-12 is not in vocab/casting.yaml -- it is reproduced as "
            "the announcer's label, and casts nobody",
            "the later owner-timed 5:59 -> 6:56 pass REPLACES the earlier "
            "#119 trustee/Tulip block and the #98 krook/bedazzle/closing "
            "quotes in this window. Greg Kroah-Hartman, Shuah Khan, Tulip "
            "Blossom, krook and kolunmi no longer render in act "
            "II on those earlier seats; if any of those credits still belong "
            "in this act they need new owner-seated windows rather than "
            "quietly colliding with the later pass",
            "the owner supplied only a bare `[github.com/brandtkeller]` in "
            "the 5:59 -> 6:56 pass -- no text, no plate fields, no timing "
            "beyond its place in the note. Nothing is emitted for it; one "
            "authored line or one authored card closes it",
            "the prior mapped 8:26 Kyle line clears at film 241.700, so the "
            "next mapped redacted clue cannot also start on 241.500. It lands "
            "at 241.950 instead: the order is the owner's; only the gap is the "
            "timeline's",
            "the SATURN title's mapped 2:36.5 mark lands inside Bungie's "
            "burned-in 'BECOME LEGEND' copy. The card therefore starts on the "
            "first clean frame after that publisher title clears (film 156.666) "
            "rather than over the burned-in words",
            "the owner asked to 'stylize it like a rare drop in a game' for "
            "A1RM4X's ghost card. This batch stays inside the existing plate "
            "renderer, so the card uses the verified YouTube ghost chrome and "
            "the rarer drop treatment stays unrendered rather than faked",
            "the 6:29 cue is 'red miniboss flashing / Your Bad Decisions'. "
            "This deterministic batch is limited to the existing title/chat/"
            "banner kinds, and none of them is a flashing red miniboss bar, "
            "so the line stays recorded rather than faked with the wrong "
            "chrome",
            "the mapped hallway edit uses the owner-supplied source-323.933 "
            "hallway-and-dogs frame, Amber's owner-identified gameplay "
            "sequence, and the cleared Local Forecast - Slower bed. Source "
            "resumes at 325.933 after the readable black-screen conversation",
            "EyeCantCU's owner-timed megacut 9:31 seat uses a freeze of the "
            "evidenced source-354.600 Warlock frame; the stale old 283.666 "
            "plate seat remains removed",
            "the 9:10 HATERS title renders through existing title chrome. The "
            "requested flashing red boss treatment is still missing; the copy "
            "ships without that effect rather than being dropped",
            "the Kyle and kolunmi pills land at film 335.650 and 338.100 "
            "after Amber's conversation and Bungie's burned-in "
            "'NEW LEGENDS WILL RISE' zone. The order and copy are the owner's; "
            "the protected publisher-title gap moves the seats",
            "KyleGospo's mapped reveal sits on his verified source-335.267 "
            "Sentinel shot at film 314.237, after Amber's sequence",
            "the brief names the same person two ways -- 'Jorge Castro' in "
            "the montage and 'jorge' at 4:51. Both are reproduced verbatim; "
            "the pill's own chrome uppercases the speaker row",
            "Karena's jump carries no card ('the beat is the jump'): it is "
            f"{JUMP_BEAT}s of clear screen between Joseph's DO line and "
            "Ricardo's answer. No shot was verified as HER jump and picking "
            "one would be casting by inference -- TODO(owner): the frame",
            "the later owner-timed 6:56 question replaces the earlier five "
            "closing quotes on the black tail. The tail still plays black by "
            "the owner's standing decision; the new seat is the question, "
            "not the quote spread",
            "the 6:56 question maps to film 149.500 inside Karena's protected "
            "jump. It lands at the first clean frame, 150.000, rather than "
            "captioning the beat",
            "the newer 5:59 -> 6:14 owner pass replaces the older Joseph "
            "master/got-this pair and the two montage asides on the same face "
            "shots. Their authored strings remain in this generator, but only "
            "the newer dialogue reaches the frame",
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
        ]),
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

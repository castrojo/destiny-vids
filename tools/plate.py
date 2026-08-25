#!/usr/bin/env python3
"""Guardian nameplates -> RGBA stills -> burned into a rendered cut.

The index names the cast; this is what puts the name on screen. A plate is the
Project Bluefin Guardian nameplate from the website's Wolves intro overlay,
rendered as a transparent PNG and composited over a cut for a timed window.

Two subcommands:

    python3 tools/plate.py render --manifest plates.json --out-dir renders/plates
    python3 tools/plate.py burn  --video renders/cut.mp4 --manifest plates.json \
                                 --out renders/cut-plated.mp4

A manifest entry follows the authoring contract in the
``authoring-interview-chat-plates`` skill -- timed, authored metadata, never
improvised text:

    {"id": "osiris", "at": 12.4, "dur": 6.0, "position": "left",
     "label": "TRUSTEE // GUARDIAN", "class": "Voidwalker Warlock",
     "name": "Bob Killen", "title": "Reconciler of the Plane", "trustee": true}

The four text fields plus ``trustee`` are exactly the vocabulary of the
reference deck (``~/Videos/nameplates.json``); nothing is invented on top of it.
The owner-authored chrome rides as flags, never copy: ``variant`` (``leader``
gold, ``rust`` iron, ``bazzite`` purple), ``avatar`` (a PFP composited into
the crest, degrading to the drawn crest when the file is not there), and
``wreath`` (the struck laurel around it). See docs/skills/plates/SKILL.md.

``kind: "ghost"`` drops the class line (a Ghost is not a Guardian, so a subclass
would be nonsense on it) and shrinks the plate. ``kind: "title"`` is the deck's
other card -- ``title`` / ``subtitle`` / ``body`` -- used here to credit the
month's ensemble.

Before a month's roster exists, ``plan --placeholders N`` plates ensemble shots
with the uncast blueberry copy from ``vocab/casting.yaml``. It names nobody: a
placeholder is for timing and review, and a real contributor replaces it.

``plan`` writes ``{"plates": [...], "unresolved": [...]}``: the manifest the
other two subcommands read, plus a punch-list of everyone the cut could not
credit -- a lead, or a contributor even the tail roster card had no room for --
and why. It never blocks on one -- an uncast character and a binding with no
plate copy are owner decisions -- but it never swallows one either.

Styling is ported from ``projectbluefin/website``
``src/components/wolves/WolvesIntroOverlay.vue`` -- ``.wolves-guardian-plate``
and friends. The CSS is the source of truth; the constants below name the rule
each value came from so the two can be diffed by eye. Entrance animation is
deliberately NOT reproduced: a still plate that cuts in cleanly reads better at
this length than a 0.6s CSS transform ported by hand, and it keeps the burn a
single ffmpeg overlay rather than an image sequence.

The cinematic chrome kinds are rendered by the same primitives:
``kind: "caption"`` is a top-safe narrative rail; ``kind: "context"`` is a
restrained lower-left stack; ``kind: "warning"`` is a full-frame deployment
card. ``caption`` supports structured glyphs that replace individual
characters with a mark image while reserving the mark's real width during
layout, so adjacent text stays visible.
"""

from __future__ import annotations

import argparse
import json
import os
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import conform  # noqa: E402  (needs REPO_ROOT on sys.path first)

FRAME_W, FRAME_H = 1920, 1080

# The site sizes everything in rem. 1rem = 16px reproduces the desktop layout
# at 1080p, which is what these plates are composited over.
REM = 16.0

# --- palette (WolvesIntroOverlay.vue, as baked by wolves-*/render/reveal.html) -
INK = (8, 12, 20, 209)          # background: rgb(8 12 20 / 82%)
CREST_FILL = (8, 12, 20, 242)   # .wolves-guardian-plate-crest-inner
TEXT = (245, 245, 245, 255)     # .wolves-guardian-plate-name color
# .name's gradient has a MIDDLE stop: #fff 0%, #e2e8f0 60%, #a0aec0 100%.
NAME_MID = (226, 232, 240, 255)      # #e2e8f0 at 60%
NAME_BOTTOM = (160, 174, 192, 255)   # #a0aec0

# text-shadow: 0 2px 10px rgb(0 0 0 / 80%) -- a CSS blur radius of 10px is
# roughly a Gaussian sigma of 5. Without it the type sits flat on a translucent
# plate that has footage showing through it.
SHADOW = (0, 0, 0, 204)
SHADOW_OFFSET = (0, 2)
SHADOW_BLUR = 5

# Default (blue) chrome vs the burnished-silver trustee treatment.
VARIANTS = {
    "default": {
        "border": (147, 197, 253, 115),   # rgb(147 197 253 / 45%)
        "accent": (147, 197, 253, 255),   # #93c5fd
        "label": (147, 197, 253, 255),
        "klass": (203, 213, 245, 255),    # #cbd5f5 (reveal.html .class)
        "title": (147, 197, 253, 255),    # #93c5fd (reveal.html .title)
    },
    "trustee": {
        "border": (203, 213, 225, 140),   # rgb(203 213 225 / 55%)
        "accent": (209, 213, 219, 255),   # #d1d5db
        "label": (229, 231, 235, 255),    # #e5e7eb
        "klass": (226, 232, 240, 255),
        "title": (203, 213, 225, 255),    # #cbd5e1
    },
    "leader": {
        "border": (250, 204, 21, 140),    # rgb(250 204 21 / 55%)
        "accent": (250, 204, 21, 255),    # #facc15
        "label": (250, 204, 21, 255),
        # The leader block overrides the label and the title but NOT the class
        # row, so the subclass keeps the default colour on the gold plate.
        # Christoph Blecker's "Broodweaver Warlock" renders exactly this way.
        "klass": (203, 213, 245, 255),    # #cbd5f5, as default
        "title": (253, 230, 138, 255),    # #fde68a
    },
    # Bronze, the third rank. `leader` is already the gold and `trustee` the
    # silver, so a medal set only needed its lowest step -- owner instruction:
    # "Rank them with bronze, silver, and gold, make them lower thirds with the
    # heraldric style". #cd7f32 is the classical bronze, deliberately more
    # golden than `rust`'s oxide (#c25b20) so the two do not read as the same
    # metal: rust is a Foundation's herald, bronze is a rank.
    "bronze": {
        "border": (205, 127, 50, 140),    # rgb(205 127 50 / 55%) — #cd7f32
        "accent": (205, 127, 50, 255),    # #cd7f32
        "label": (231, 178, 124, 255),    # #e7b27c, struck bronze highlight
        # As `leader`, the rank never recolours the class row.
        "klass": (203, 213, 245, 255),    # #cbd5f5, as default
        "title": (222, 164, 110, 255),    # #dea46e
    },
    # Oxidised iron, for the Rust Foundation herald. Same geometry and the same
    # closed field set as every other plate — only the chrome changes, so this
    # stays a variant rather than a second kind of card.
    "rust": {
        "border": (180, 83, 9, 140),      # rgb(180 83 9 / 55%) — #b45309
        "accent": (194, 91, 32, 255),     # #c25b20, oxide edge
        "label": (251, 146, 60, 255),     # #fb923c
        "klass": (253, 186, 116, 255),    # #fdba74
        "title": (168, 121, 92, 255),     # #a8795c, weathered iron
    },
    # Bazzite purple, for the three end-fight plates. The brand colours are
    # VERIFIED from the official logo (ublue-os/bazzite,
    # repo_content/Bazzite.svg): the logomark's gradient runs cobalt #0047AB
    # -> blue-violet #8A2BE2, and the wordmark sets its type in #5835ce. The
    # wordmark purple is too dark to set type in on the translucent plate, so
    # the text rows take Tailwind violet tints -- the palette family the rest
    # of the site's ramp is built from. The brief is a HUM, not a glow: the
    # type stays legible, and the card says nothing about why they are special.
    "bazzite": {
        "border": (138, 43, 226, 140),    # rgb(138 43 226 / 55%) — #8A2BE2
        "accent": (138, 43, 226, 255),    # #8A2BE2, logomark gradient end stop
        "label": (196, 181, 253, 255),    # #c4b5fd (Tailwind violet-300)
        "klass": (221, 214, 254, 255),    # #ddd6fe (Tailwind violet-200)
        "title": (167, 139, 250, 255),    # #a78bfa (Tailwind violet-400)
    },
    # Nobara indigo, for GloriousEggroll -- the peer of Kyle's bazzite purple,
    # and for the same reason: the affiliation is CHROME, and the card says
    # nothing about it in words. The colours are VERIFIED from the official
    # icon at https://nobaraproject.org/img/nobara-icon.png, sampled rather
    # than recalled: #3E3FC5 is the dominant fill (and the brand's own
    # "Governor Bay"), and the mark's gradient runs #2431A5 -> #664FF8 across
    # it. As with bazzite, the wordmark indigo is too dark to set type in on a
    # translucent plate, so the text rows take the same family's tints.
    "nobara": {
        "border": (62, 63, 197, 140),     # rgb(62 63 197 / 55%) — #3E3FC5
        "accent": (62, 63, 197, 255),     # #3E3FC5, the icon's dominant fill
        "label": (165, 180, 252, 255),    # #a5b4fc (Tailwind indigo-300)
        "klass": (199, 210, 254, 255),    # #c7d2fe (Tailwind indigo-200)
        "title": (129, 140, 248, 255),    # #818cf8 (Tailwind indigo-400)
    },
    # YouTube red, for a creator whose affiliation IS their channel. Same
    # rule: the platform is chrome, and #FF0000 is YouTube's own logo red,
    # which is too hot to set small type in -- the rows take red tints.
    "youtube": {
        "border": (255, 0, 0, 140),       # rgb(255 0 0 / 55%) — #FF0000
        "accent": (255, 0, 0, 255),       # #FF0000, the YouTube logo red
        "label": (252, 165, 165, 255),    # #fca5a5 (Tailwind red-300)
        "klass": (254, 202, 202, 255),    # #fecaca (Tailwind red-200)
        "title": (248, 113, 113, 255),    # #f87171 (Tailwind red-400)
    },
}

# The Bazzite logomark's gradient stops (ublue-os/bazzite repo_content/Bazzite.svg,
# paint0_linear: cobalt -> blue-violet across the tile's diagonal).
BAZZITE_COBALT = (0, 71, 171)      # #0047AB, gradient start (top-left)
BAZZITE_VIOLET = (138, 43, 226)    # #8A2BE2, gradient end (bottom-right)

# Which chrome variants put a brand mark in the crest instead of the hex.
# `bazzite` is drawn from traced SVG geometry; the rest are cached raster
# artwork, downloaded by scripts/fetch_brand_marks.py into gitignored
# renders/. A missing file degrades to the drawn crest, never a crash.
#
# `youtube` is deliberately NOT here: a creator's own channel avatar is their
# brand, so A1RM4X's crest carries HIS picture and the red is the platform.
# Putting YouTube's own logo on somebody's credit would name the platform
# louder than the person.
BRAND_MARKS = {
    "bazzite": "bazzite",
    "nobara": "renders/marks/nobara.png",
}

# --- type ramp (clamp() upper bounds, i.e. the desktop sizes) ---------------
FS_LABEL = 1.8 * REM     # .wolves-guardian-plate-label
FS_CLASS = 2.1 * REM     # .wolves-guardian-plate-class
FS_NAME = 3.6 * REM      # .wolves-guardian-plate-name
FS_TITLE = 1.9 * REM     # .wolves-guardian-plate-title

LS_LABEL = 0.35          # letter-spacing: 0.35em
LS_CLASS = 0.05
LS_TITLE = 0.08          # reveal.html .title; the site leaves the title untracked

PAD_X = 2.0 * REM        # padding: 1.75rem 2rem 1.5rem
PAD_TOP = 1.75 * REM
PAD_BOTTOM = 1.5 * REM
CHAMFER = 16             # clip-path: polygon(16px ...)
CORNER_RADIUS = 12       # border-radius: 0.75rem, on the two corners not cut
CREST = 2.5 * REM        # .wolves-guardian-plate-crest

# --- owner-authored chrome: the laurel wreath -------------------------------
# `wreath: true` strikes a laurel around the crest in the plate's own accent
# metal -- the ring a game draws around a max-level portrait. Exactly two
# people in the show carry it, and that scarcity is the point; the renderer
# never adds one by itself. The canvas is wider than the crest so the leaves
# clear the hex, and the header rules shorten around it (the card's box and
# every row of type stay exactly where they were).
WREATH_SPAN = 1.5        # the laurel's canvas, as a multiple of the crest
WREATH_LEAVES = 7        # per branch -- restraint is the brief
WREATH_GAP = 35          # degrees left open at the bottom, where a laurel ties

# --- status nameplate (the site's own top-of-frame chrome) -------------------
# A DIFFERENT card from the reveal plate: the Wolves app's persistent HUD
# nameplate (src/components/wolves/cinematic/Nameplate.vue, on the tokens in
# src/style/wolves-cinematic.scss), which the intro overlay re-labels per cue.
# It carries two authored lines -- a small `detail` eyebrow over a large
# `label` -- and nothing else, so it is added to the data model deliberately
# rather than bent out of the Guardian plate's field set.
#
# Note `--wc-gold` is the token's NAME, not its value: it resolves to #60a5fa,
# a blue. Reproducing the name instead of the value would have made this card
# gold and wrong.
STATUS_PANEL = (14, 16, 20, 224)     # --wc-panel: rgb(14 16 20 / 88%)
STATUS_LINE = (96, 165, 250, 71)     # --wc-line: rgb(96 165 250 / 28%)
STATUS_ACCENT = (96, 165, 250, 255)  # --wc-gold: #60a5fa
STATUS_WHITE = (233, 233, 229, 255)  # --wc-white: #e9e9e5

FS_STATUS_DETAIL = 1.1 * REM   # .wc-label
FS_STATUS_LABEL = 2.2 * REM    # .wc-nameplate-label
LS_STATUS_DETAIL = 0.32        # letter-spacing: 0.32em
LS_STATUS_LABEL = 0.06

STATUS_PAD_TOP = 1.2 * REM     # padding: 1.2rem 2.4rem 1.2rem 1.6rem
STATUS_PAD_RIGHT = 2.4 * REM
STATUS_PAD_LEFT = 1.6 * REM
STATUS_RULE = 2                # border-left: 2px solid var(--wc-gold)
STATUS_CHAMFER = int(0.9 * REM)  # .wc-plate clip-path: 0.9rem
STATUS_GAP = 0.35 * REM
# .wc-intro-nameplate { position: fixed; top: 3rem; left: 3rem }
STATUS_INSET = 3.0 * REM
# .wolves-guardian-plate-raised { bottom: auto; top: 28% }
RAISED_TOP = 0.28

# --- letterbox banner (owner brief, issue #98) -------------------------------
# "a huge callout along the bottom of the letterbox ... Keep it up for the
# whole song". One tracked line on the bottom bar of a letterboxed frame --
# cinema-subtitle territory, BELOW the picture, so it can hold for a whole
# film without ever sharing the lower third's row. There is no deck component
# for it; it is chrome, not copy: the words are owner-authored and the shape
# is one line of the deck's own tracked type.
BANNER_FS_MAX = 2.6 * REM    # "huge" -- bounded by the bar's ~140px
BANNER_FS_MIN = 1.2 * REM    # below this it is not a callout; render whole anyway
BANNER_LS = 0.18             # letter-spacing, em
BANNER_MAX_W = 0.94          # of the frame's width

# --- cinematic caption / context / warning (owner brief, Task 1) -------------
# A wrapped bold-white top rail for narrative cues; a restrained lower-left
# context stack; and a full-frame red deployment warning. Each owns its own
# chrome row, so they may share the screen with Guardian plates while a
# second card of the same kind remains an error.
CAPTION_FS = 2.4 * REM
CAPTION_PAD = 1.25 * REM
CAPTION_LINE_GAP = 0.4 * REM
CAPTION_MAX_W = FRAME_W * 0.88
CAPTION_TOP = 0.06
CAPTION_RULE = 3

CONTEXT_FS_TITLE = 2.0 * REM
CONTEXT_FS_LINE = 1.5 * REM
CONTEXT_PAD = 1.25 * REM
CONTEXT_LINE_GAP = 0.5 * REM
CONTEXT_TOP = 0.36

WARNING_RED = (220, 38, 38, 255)          # the owner's deployment-warning red
WARNING_PANEL = (153, 27, 27, 235)
WARNING_STRIPE = (0, 0, 0, 220)
WARNING_TEXT = (245, 245, 245, 255)
WARNING_FS = 4.5 * REM
WARNING_STRIPE_H = 20

# --- chat card (wolves-*/render/plate.html -- the baked dialogue pill) -------
# The other videos' talking card is neither the reveal plate nor the site's
# .wc-nameplate: it is the one-line pill plate.html bakes -- [crest] SPEAKER |
# message, shrink-to-fit, never wrapped. plate.html renders at 2x for the 4K
# master, so every constant here is the 1x half, named after the rule it came
# from. Where plate.html and the site disagree (pill vs chamfered box, one
# line vs stacked rows, gradient message vs solid uppercase label) the baked
# reference wins: it is what the videos were actually rendered from
# (docs/skills/plates/SKILL.md: where the site and the videos disagree, the videos win).
CHAT_AVATAR = 42         # .avatar/.pfp: 84px circle; the crest is the no-pfp fallback
CHAT_GAP = 13            # .plate { gap: 26px }
CHAT_PAD_L = 12          # .plate { padding: 20px 44px 20px 24px }
CHAT_PAD_R = 22
CHAT_PAD_Y = 10
CHAT_MAX_W = 1550        # .plate { max-width: 3100px }
CHAT_FS_SPEAKER = 17     # .eyebrow { font-size: 34px }
CHAT_LS_SPEAKER = 0.28   # .eyebrow { letter-spacing: 0.28em }
CHAT_FS_TEXT_MAX = 28    # render script MAX_FONT 56px -- the preferred size
CHAT_FS_TEXT_MIN = 19    # ...MIN_FONT 38px -- the shrink-to-fit floor
CHAT_RULE_W = 2          # .rule { width: 3px } -- 1.5px at 1x, rounded up
CHAT_RULE_H = 23         # .rule { height: 46px }
K8S_CENSOR_TOKEN = "{k8s}"
K8S_CENSOR_MARK = REPO_ROOT / "renders" / "marks" / "kubernetes.png"

# --- companion plate (the site's GUARDIAN BOND card) ------------------------
# A DIFFERENT card again: `.wolves-companion-plate` in WolvesIntroOverlay.vue,
# the bonded dinosaur split out beside the Guardian's own lower third. It is
# the row's other half -- the site anchors it `right: 5%; bottom: 10%` while
# the name plate holds the left -- so a companion shares its Guardian's `group`
# rather than contending with it for the lower third.
#
# Its three rows are the site's, reproduced: the fixed `GUARDIAN BOND` label
# (chrome, not a per-person line), the dinosaur's authored name, and the
# species' scientific name. Where no character sheet names the bonded animal
# the name row is OMITTED, exactly as `v-if` does it on the site -- an unnamed
# bond is a real state, and inventing a name for somebody's companion is the
# same class of mistake as inventing their subclass.
COMPANION_LABEL = "GUARDIAN BOND"
COMPANION_W = 24.0 * REM          # width: clamp(17rem, 14rem + 5vw, 24rem)
COMPANION_PAD_TOP = 4.2 * REM     # padding: 4.2rem 1.6rem 1.4rem
COMPANION_PAD_X = 1.6 * REM
COMPANION_PAD_BOTTOM = 1.4 * REM
COMPANION_ART_DROP = 3.4 * REM    # .art { margin-bottom: -3.4rem } -- the
                                  # artwork breaks out of the chamfered box
FS_COMPANION_LABEL = 1.5 * REM    # .wolves-companion-plate-label
FS_COMPANION_NAME = 2.8 * REM     # .wolves-companion-plate-name
FS_COMPANION_SPECIES = 1.6 * REM  # .wolves-companion-plate-species
LS_COMPANION_LABEL = 0.35         # letter-spacing: 0.35em
LS_COMPANION_SPECIES = 0.05
COMPANION_LABEL_COLOUR = (147, 197, 253, 255)   # #93c5fd
COMPANION_SPECIES_COLOUR = (148, 163, 184, 255)  # #94a3b8
# "Size each visible silhouette, not each source canvas" -- the per-species
# corrections the site carries, reproduced rather than re-judged. A species
# with no entry renders at the base width, which is what the base rule does.
COMPANION_ART_WIDTH = {
    "bob-torosaurus": 1.08,
    "karl": 1.18,
    "kentrosaurus": 1.04,
    "alamosaurus": 1.242,
}
COMPANION_ART_BASE = 1.08         # .wolves-companion-plate-art { width: 108% }

# --- the miniboss badge (Destiny's own boss-bar treatment) ------------------
# `kind: "miniboss"` -- the card a Destiny raid or strike puts at the TOP of
# the screen when a named enemy arrives: a rank icon, the name in large
# tracked caps, its title beneath, and the health bar under both.
#
# Destiny's own tiers are colour-coded: an orange/yellow bar is a Major (what
# players call a miniboss) and an Ultra gets the big bar with a skull. The
# owner asked for a RED badge, so the red is his and the LAYOUT is the game's.
# It carries the deck's own `name` and `title` and adds no new row.
MINIBOSS_RED = (220, 38, 38, 255)         # #dc2626, the owner's red badge
MINIBOSS_RED_DIM = (127, 29, 29, 255)     # #7f1d1d, the bar's unfilled track
MINIBOSS_PANEL = (10, 6, 8, 196)
FS_MINIBOSS_NAME = 2.6 * REM
FS_MINIBOSS_TITLE = 1.35 * REM
LS_MINIBOSS_NAME = 0.14                   # the game sets the name wide
LS_MINIBOSS_TITLE = 0.24
MINIBOSS_PAD_X = 2.2 * REM
MINIBOSS_PAD_Y = 1.0 * REM
MINIBOSS_BAR_H = 7                        # the health bar under the type
MINIBOSS_ICON = 2.2 * REM                 # the rank diamond on the left
MINIBOSS_TOP = 0.08                       # the game puts the bar near the top

# --- the achievement toast (the Xbox gag) -----------------------------------
# `kind: "achievement"` -- the unlock notification, top-centre, in the official
# Xbox brand green #107C10. Three rows: the fixed ACHIEVEMENT UNLOCKED eyebrow,
# the achievement's `name`, and its gamerscore.
#
# EVERY STRING ON THIS CARD IS A JOKE ABOUT UPSTREAMING PATCHES, which makes it
# authored copy like any other. The builder holds a PROPOSED list and does not
# emit it until the owner approves the words -- see build_efmb_plates.py.
XBOX_GREEN = (16, 124, 16, 255)           # #107C10
ACHIEVEMENT_PANEL = (18, 22, 18, 224)
FS_ACHIEVEMENT_EYEBROW = 1.0 * REM
FS_ACHIEVEMENT_NAME = 1.7 * REM
FS_ACHIEVEMENT_SCORE = 1.2 * REM
LS_ACHIEVEMENT_EYEBROW = 0.3
ACHIEVEMENT_PAD_X = 1.4 * REM
ACHIEVEMENT_PAD_Y = 0.9 * REM
ACHIEVEMENT_ORB = 3.0 * REM               # the green sphere on the left
ACHIEVEMENT_TOP = 0.06
ACHIEVEMENT_EYEBROW = "ACHIEVEMENT UNLOCKED"

# --- the choice box (owner brief, act II) -----------------------------------
#
# "[github.com/riaankleinhans] - Your choices are: then generate a graphic
# choice box for the team o Update your LFX Profile o Do it the hard way"
#
# A dialogue-tree box: a prompt row, then one row per option behind the
# owner's own `o` bullet, which is drawn as a ring rather than typeset as the
# letter. NOTHING is selected -- no highlight, no cursor -- because the joke is
# that the choice is not a choice, and lighting one up would answer it.
#
# Its fields are `label` and `options`, closed like every other card kind's:
# a third row here would be an invented line in somebody's mouth.
CHOICE_PANEL = (10, 14, 22, 232)
# VIDEO-GAME SCALE, owner instruction: *"make the text MUCH larger like a video
# game choice screen"*. A dialogue-tree option is not a lower third -- it is the
# thing the player is being asked to press, so it is set at 3rem (48px at
# 1080p), roughly double a Guardian plate's name, with the padding and the
# bullet scaled with it so the box stays a button rather than a banner.
FS_CHOICE_LABEL = 1.6 * REM
FS_CHOICE_OPTION = 3.0 * REM
LS_CHOICE_LABEL = 0.3
CHOICE_PAD_X = 2.4 * REM
CHOICE_PAD_Y = 1.5 * REM
CHOICE_ROW_GAP = 1.0 * REM      # the prompt's air above the first box
CHOICE_BOX_GAP = int(0.9 * REM)  # the clear air BETWEEN the two boxes
CHOICE_BULLET = 1.1 * REM
CHOICE_BULLET_GAP = 1.2 * REM
CHOICE_RULE = 4
CHOICE_MAX_W = 0.66              # the widest a button may get, as a fraction of frame
CHOICE_SCRIM = (4, 7, 12, 178)   # the pause dim over the whole picture

# THE LEGENDARY TIER.
#
# Owner: *"design it like the destiny legendary campaign screen -- the fight
# one should match 'legendary'."* Destiny's campaign difficulty select puts the
# two options side by side and gives the hard one AMBER chrome, a diamond in
# place of the plain marker, and its name spelled out above it. So the fighting
# option gets that treatment and the other keeps the deck's blue.
#
# LEGENDARY is the only word added, and it is the owner's own. No modifier
# rows, no "recommended power", no flavour line -- Destiny's card carries all
# three and every one of them would be copy nobody wrote.
CHOICE_LEGENDARY_TAG = "LEGENDARY"
CHOICE_LEGENDARY_ACCENT = (240, 191, 92, 255)   # the campaign card's amber
CHOICE_LEGENDARY_LINE = (240, 191, 92, 80)
CHOICE_LEGENDARY_PANEL = (26, 19, 7, 236)
FS_CHOICE_TAG = 1.0 * REM
LS_CHOICE_TAG = 0.34

# THE CURSOR, AND WHY IT NEVER ARRIVES.
#
# Owner: *"whip up a quick mouse pointer starting at the center and then moving
# towards the fighting choice but have it cut so it's a teaser quick cut."*
#
# So the pointer starts dead centre and travels toward the SECOND option -- the
# fighting one, "Do it the hard way" -- and the film cuts while it is still in
# transit. `CHOICE_POINTER_CUT` is how far along it gets: short of the button,
# on purpose. A pointer that lands has made the choice, and the gag is that
# nobody gets to.
CHOICE_POINTER_TARGET = 1        # index into `options`: the fighting one
CHOICE_POINTER_CUT = 0.80        # fraction of the way there when the cut lands
CHOICE_POINTER_H = 4.2 * REM     # the arrow's height -- game-menu scale
CHOICE_POINTER_FILL = (255, 255, 255, 255)
CHOICE_POINTER_EDGE = (8, 12, 20, 235)
# The site's own accent (`--wc-gold`, which resolves to #60a5fa and is blue).
CHOICE_ACCENT = STATUS_ACCENT
CHOICE_LINE = STATUS_LINE


MARGIN_X = 0.05
MARGIN_BOTTOM = 0.10

# The full-frame cards -- the cinematic act slide, the intro's comic title
# card, and the full-bleed photo card. They are the site's own components,
# reproduced by `cards/render-cards.mjs`
# in a real browser rather than ported into Pillow, so this module only ever
# BURNS them: `render` skips them and `render_plate` refuses one outright.
CARD_KINDS = ("act", "comic", "photo", "ending")

# The card kinds that own a row of their own rather than the lower third: the
# site's top-left HUD, Destiny's boss bar at the top of frame, the console
# toast under it, and the letterbox banner on the bottom bar of a letterboxed
# frame. Each may share the screen with a lower third and with a different
# chrome row; two of the SAME kind at once are still an error.
#
# `warning` is deliberately NOT here: it renders a full 1920x1080 panel over
# the picture, so it contends for the whole screen like any full-frame card
# and gets no coexistence exemption.
CHROME_ROWS = ("status", "miniboss", "achievement", "banner", "caption", "context")

# --- group rows (the reference deck's roll call, ~/Videos/nameplates.json) ---
# The deck's gp_* entries are one row of credits, doubly staggered: spatially,
# each card carries an absolute `x` measured against the picture; temporally,
# entrances cascade GROUP_STAGGER seconds apart and every card ends together.
# They are deliberately NOT aimed at individual bodies: the casting model says
# the anonymous crowd is fillable by anyone (vocab/casting.yaml `ensemble`), so
# an even spread reads as a row of credits rather than arrows at people.
GROUP_SCALE = 0.78      # the deck's gp_* scale
GROUP_MIN_SCALE = 0.4   # below this the type is too small to be a credit
GROUP_GAP = 24          # px between cards in a row
GROUP_STAGGER = 0.4     # the cascade between entrances; the row ends together
# The roll call spans nearly the whole picture width (the deck's row runs
# x=51 -> ~1920, ~2.7% margins), wider than a corner plate's 5%.
GROUP_MARGIN_X = 0.03

# The CSS stack is `ui-monospace, 'SFMono-Regular', 'Cascadia Mono', monospace`
# (wolves-*/render/reveal.html, and --wc-font-mono on the site). Neither Apple's
# SF Mono nor Cascadia Mono ships on a Fedora atomic host, so the browser that
# baked the reference plates fell through to the fontconfig generic -- which is
# DejaVu Sans Mono. Match that resolution order exactly.
#
# Adwaita Mono is deliberately NOT first: it is the desktop's mono and it is
# installed here, so preferring it silently rendered every plate in a typeface
# that appears nowhere in the stack, and none of the other videos.
FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationMono-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationMono-Bold.ttf",
    ],
    # `font-style: italic` on .wolves-companion-plate-species -- the only
    # italic row anywhere in the deck. The same family's oblique, and the
    # regular faces as the last resort: a scientific name set upright is a
    # missing slant, not a wrong word.
    "italic": [
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono-Oblique.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono-Oblique.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationMono-Italic.ttf",
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    ],
}


def _font(weight, size):
    for path in FONT_CANDIDATES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, int(round(size)))
    raise RuntimeError(
        f"no {weight} monospace font found; tried {FONT_CANDIDATES[weight]}"
    )


def _tracked_width(draw, text, font, tracking_em):
    """Width of ``text`` with CSS-style letter-spacing applied."""
    extra = tracking_em * font.size
    return sum(draw.textlength(ch, font=font) + extra for ch in text)


def _draw_tracked(draw, xy, text, font, fill, tracking_em):
    """Letter-spaced text. Pillow has no tracking, so glyphs are placed by hand."""
    x, y = xy
    extra = tracking_em * font.size
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + extra


def _gradient_text(size, text, font, stops, tracking_em=0.0):
    """The name's vertical gradient (background-clip: text).

    ``stops`` is ``[(offset, rgba), ...]`` with offsets in 0..1, mirroring the
    CSS: `#fff 0%, #e2e8f0 60%, #a0aec0 100%`. The middle stop matters -- a
    straight white->slate ramp washes the centre of the name out.
    """
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    if tracking_em:
        _draw_tracked(ImageDraw.Draw(mask), (0, 0), text, font, 255,
                      tracking_em)
    else:
        ImageDraw.Draw(mask).text((0, 0), text, font=font, fill=255)
    grad = Image.new("RGBA", size)
    for y in range(size[1]):
        t = y / max(1, size[1] - 1)
        lower = max(i for i, (offset, _) in enumerate(stops) if offset <= t) \
            if any(offset <= t for offset, _ in stops) else 0
        upper = min(lower + 1, len(stops) - 1)
        (o0, c0), (o1, c1) = stops[lower], stops[upper]
        k = 0.0 if o1 == o0 else (t - o0) / (o1 - o0)
        grad.paste(
            tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(4)),
            (0, y, size[0], y + 1),
        )
    layer.paste(grad, (0, 0), mask)
    return layer


def _with_text_shadow(layer):
    """`text-shadow: 0 2px 10px rgb(0 0 0 / 80%)` under a text layer.

    The plate is translucent, so footage shows through it; without the shadow
    the type has no separation from whatever is moving behind the card.
    """
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    shadow.paste(SHADOW, (0, 0), layer.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(shadow, SHADOW_OFFSET)
    out.alpha_composite(layer)
    return out


def _chamfered(size, fill, border, radius=CHAMFER, corner=CORNER_RADIUS):
    """The plate box: two chamfered corners, two rounded, one hairline rule.

    The CSS applies `border-radius` *and* a `clip-path`, so the polygon wins on
    the top-left and bottom-right (diagonal cuts) while the other two corners
    keep their radius. Built from a supersampled mask because Pillow will not
    antialias a polygon edge, and a hard-aliased diagonal is exactly the sort of
    thing that reads as "not the same card" next to a browser-rendered plate.
    """
    w, h = size
    scale = 4
    big = (w * scale, h * scale)
    r, c = radius * scale, corner * scale

    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big[0] - 1, big[1] - 1],
                                           radius=c, fill=255)
    # Cut the two chamfers back out of the rounded box.
    cut = ImageDraw.Draw(mask)
    cut.polygon([(0, 0), (r, 0), (0, r)], fill=0)
    cut.polygon([(big[0] - 1, big[1] - 1 - r), (big[0] - 1, big[1] - 1),
                 (big[0] - 1 - r, big[1] - 1)], fill=0)
    mask = mask.resize(size, Image.LANCZOS)

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    img.paste(fill, (0, 0, w, h), mask)

    # The 1px rule is the mask minus its own inset, so it follows every corner.
    inner = mask.filter(ImageFilter.MinFilter(3))
    edge = ImageChops.subtract(mask, inner)
    rule = Image.new("RGBA", size, (0, 0, 0, 0))
    rule.paste(border, (0, 0, w, h), edge)
    img.alpha_composite(rule)
    return img


def _resolve(path):
    """A manifest image path -> an absolute Path (relative to the repo root)."""
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def _load_avatar(path, size):
    """A PFP file -> a ``size``-px square RGBA crop, or None.

    GitHub avatars are the source (e.g. avatars.githubusercontent.com/u/<id>),
    fetched and cached AHEAD of time -- this renderer never touches the
    network, so ``avatar`` is always a local path. A ``~``-rooted path is
    expanded, matching the delivery map's own rule that a path outside the
    repo is ``~``-rooted or absolute and never relative to a worktree;
    relative paths resolve against the repo root. The crop is CSS
    `object-fit: cover`: scaled to fill, centre-cropped.

    A missing or unreadable file is a punch-list item, never a crash
    (degrade, never block): the caller falls back to the drawn crest.
    """
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = REPO_ROOT / p
    try:
        img = Image.open(p).convert("RGBA")
        if not img.width or not img.height:
            raise ValueError("empty image")
        scale = max(size / img.width, size / img.height)
        img = img.resize((max(1, round(img.width * scale)),
                          max(1, round(img.height * scale))), Image.LANCZOS)
        x = (img.width - size) // 2
        y = (img.height - size) // 2
        return img.crop((x, y, x + size, y + size))
    except (OSError, ValueError):
        print(f"plate: avatar {path!r} is missing or unreadable -- "
              "the drawn crest stands in (punch-list item)", file=sys.stderr)
        return None


# The crest's own geometry (inline SVG in the Vue component), in its box.
CREST_OUTER = [(50, 5), (85, 20), (95, 55), (50, 95), (5, 55), (15, 20)]
CREST_INNER = [(50, 12), (78, 25), (87, 52), (50, 85), (13, 52), (22, 25)]
CREST_CHEVRON = [(35, 45), (50, 60), (65, 45)]


def _cubic(p0, p1, p2, p3):
    """Flatten a cubic Bezier to polygon points (excluding ``p0``)."""
    steps = 24
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        out.append((
            mt ** 3 * p0[0] + 3 * mt ** 2 * t * p1[0]
            + 3 * mt * t ** 2 * p2[0] + t ** 3 * p3[0],
            mt ** 3 * p0[1] + 3 * mt ** 2 * t * p1[1]
            + 3 * mt * t ** 2 * p2[1] + t ** 3 * p3[1],
        ))
    return out


def _bazzite_tile(s, accent, photo):
    """The Bazzite logomark, ``s`` px square, supersampled: the gradient tile
    with its D-pad glyph, or ``photo`` masked to the tile's silhouette.

    Traced from the official logo (ublue-os/bazzite repo_content/Bazzite.svg).
    The tile (path1) lives in a 408x408 box at (100,100) of the viewBox: a
    circle of radius 204 centred on (304,304) with the top-left squared off
    into an 81.6px rounded corner. The glyph is a controller D-pad -- two
    fully-rounded bars (path3, white at 70%) with four button ticks around it
    (paths 4-7) -- over the "b" stem and bowl (path2, white at 50%).

    With a ``photo`` the tile keeps only its silhouette and hairline: the PFP
    masked into it IS the logo's shape, and the glyph is never drawn over a
    face.
    """
    def m(pt):  # svg coords -> pixels: the mark's 408x408 box maps onto s
        return ((pt[0] - 100) / 408 * s, (pt[1] - 100) / 408 * s)

    outline = [(100, 181.6)]
    outline += _cubic((100, 181.6), (100, 136.534), (136.534, 100), (181.6, 100))
    outline.append((304, 100))
    outline += _cubic((304, 100), (416.666, 100), (508, 191.334), (508, 304))
    outline += _cubic((508, 304), (508, 416.666), (395.334, 508), (304, 508))
    outline += _cubic((304, 508), (191.334, 508), (100, 416.666), (100, 304))
    poly = [m(p) for p in outline]

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    if photo is not None:
        img.paste(photo, (0, 0), mask)
    else:
        # paint0_linear: userSpaceOnUse from (100,100) to (508,508) -- the
        # tile's diagonal, so t is the mean of the two axes.
        grad = Image.new("RGBA", (s, s))
        px = grad.load()
        for yy in range(s):
            for xx in range(s):
                t = ((xx + yy) / 2) / s
                px[xx, yy] = tuple(
                    int(BAZZITE_COBALT[i] + (BAZZITE_VIOLET[i] - BAZZITE_COBALT[i]) * t)
                    for i in range(3)) + (255,)
        img.paste(grad, (0, 0), mask)

        d = ImageDraw.Draw(img)
        # path2, the "b": an outer shape with the bowl punched back out of it
        # (the SVG's fill-rule="evenodd").
        stem = [(204.448, 100), (256.672, 100), (256.672, 204.448),
                (366.167, 204.448)]
        stem += _cubic((366.167, 204.448), (412.051, 204.448),
                       (449.248, 241.645), (449.248, 287.529))
        stem += _cubic((449.248, 287.529), (449.248, 376.844),
                       (376.844, 449.248), (287.529, 449.248))
        stem += _cubic((287.529, 449.248), (241.645, 449.248),
                       (204.448, 412.051), (204.448, 366.167))
        stem += [(204.448, 256.672), (100, 256.672), (100, 204.448),
                 (204.448, 204.448)]
        bowl = [(256.672, 256.672), (256.672, 366.167)]
        bowl += _cubic((256.672, 366.167), (256.672, 383.209),
                       (270.487, 397.024), (287.529, 397.024))
        bowl += _cubic((287.529, 397.024), (348.001, 397.024),
                       (397.024, 348.001), (397.024, 287.529))
        bowl += _cubic((397.024, 287.529), (397.024, 270.487),
                       (383.209, 256.672), (366.167, 256.672))
        b_mask = Image.new("L", (s, s), 0)
        b_draw = ImageDraw.Draw(b_mask)
        b_draw.polygon([m(p) for p in stem], fill=128)   # white at ~50%
        b_draw.polygon([m(p) for p in bowl], fill=0)     # the even-odd punch
        img.paste(Image.new("RGBA", (s, s), (255, 255, 255, 255)), (0, 0),
                  b_mask)

        # path3, the D-pad: two fully-rounded bars crossing at (230.56, 230.56),
        # white at 70%.
        cross = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(cross)
        arm_r = 26.112
        c_draw.rounded_rectangle(
            [m((204.448, 124.48)), m((256.672, 336.64))],
            radius=arm_r / 408 * s, fill=(255, 255, 255, 179))
        c_draw.rounded_rectangle(
            [m((124.48, 204.448)), m((336.64, 256.672))],
            radius=arm_r / 408 * s, fill=(255, 255, 255, 179))
        img.alpha_composite(cross)
        # paths 4-7: the four button ticks around the pad, full white.
        for tri in (
            [(312.82, 230.56), (298.444, 243.19), (290.944, 238.86),
             (290.944, 222.26), (298.444, 217.93)],
            [(230.56, 312.82), (217.93, 298.444), (222.26, 290.944),
             (238.86, 290.944), (243.19, 298.444)],
            [(230.56, 148.3), (243.19, 162.676), (238.86, 170.176),
             (222.26, 170.176), (217.93, 162.676)],
            [(148.3, 230.56), (162.676, 217.93), (170.176, 222.26),
             (170.176, 238.86), (162.676, 243.19)],
        ):
            d.polygon([m(p) for p in tri], fill=(255, 255, 255, 255))

    # The silhouette's hairline, in the plate's accent -- the same job the
    # hex crest's own rule does, so the crest slot keeps its geometry.
    ImageDraw.Draw(img).polygon(poly, outline=accent, width=max(1, s // 100))
    return img


def _mark_tile(s, path, photo):
    """Official brand artwork as the crest, ``s`` px square.

    The generic form of ``_bazzite_tile``: where Bazzite's logomark is traced
    from its SVG's path geometry, a brand whose only published asset is a
    raster is REPRODUCED from that raster instead of being redrawn by hand --
    a hand-drawn approximation of somebody's logo is an invented mark.

    The artwork's own alpha is the silhouette, so a ``photo`` masks into the
    logo's shape exactly as it does on the Bazzite tile, and the glyph is
    never drawn over a face. A missing file degrades to ``None`` and the
    caller falls back to the drawn hex crest.
    """
    try:
        art = Image.open(_resolve(path)).convert("RGBA")
    except (OSError, ValueError):
        print(f"plate: brand mark {path!r} is missing or unreadable -- "
              "the drawn crest stands in (punch-list item)", file=sys.stderr)
        return None
    # Crop to the artwork's own ink first. A published icon carries whatever
    # transparent padding its author gave it, and scaling the padded canvas
    # into the crest renders the mark visibly smaller than the traced Bazzite
    # tile beside it -- the same logo at two sizes reads as two ranks.
    box = art.getbbox()
    if box:
        art = art.crop(box)
    side = max(art.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.alpha_composite(art, ((side - art.width) // 2,
                                 (side - art.height) // 2))
    art = square.resize((s, s), Image.LANCZOS)
    if photo is None:
        return art
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.paste(photo, (0, 0), art.getchannel("A"))
    return img


def _crest(size, accent, avatar=None, mark=None):
    """The hex crest with its chevron (inline SVG in the Vue component).

    ``avatar`` is the path to a PFP image: the photo is cover-fit and masked
    to the crest's inner hex, with the hex rules kept drawn over it so the
    card's geometry is unchanged. A missing or unreadable file degrades to
    the drawn crest -- a punch-list item, never a crash.

    ``mark="bazzite"`` replaces the hex with the Bazzite logomark (see
    ``_bazzite_tile``); an avatar there masks to the tile's silhouette. Any
    other ``mark`` is a path to cached brand artwork and behaves the same way
    (``_mark_tile``).
    """
    scale = 4  # supersampled, then downscaled: Pillow has no antialiased strokes
    s = int(size * scale)
    if mark == "bazzite":
        return _bazzite_tile(s, accent, _load_avatar(avatar, s)).resize(
            (int(size), int(size)), Image.LANCZOS)
    if mark:
        tile = _mark_tile(s, mark, _load_avatar(avatar, s))
        if tile is not None:
            return tile.resize((int(size), int(size)), Image.LANCZOS)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def pts(coords):
        return [(x / 100 * s, y / 100 * s) for x, y in coords]

    photo = _load_avatar(avatar, s)
    if photo is not None:
        # The portrait takes the inner hex; both rules stay drawn over it.
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).polygon(pts(CREST_INNER), fill=255)
        img.paste(photo, (0, 0), mask)
        d.polygon(pts(CREST_OUTER), outline=accent, width=int(2 * scale))
        d.polygon(pts(CREST_INNER), outline=TEXT, width=int(1 * scale))
    else:
        d.polygon(pts(CREST_OUTER), outline=accent, width=int(2 * scale))
        d.polygon(pts(CREST_INNER), fill=CREST_FILL, outline=TEXT,
                  width=int(1 * scale))
        d.line(pts(CREST_CHEVRON), fill=accent, width=int(4 * scale),
               joint="curve")
    return img.resize((int(size), int(size)), Image.LANCZOS)


def _leaf(cx, cy, r, theta, lean, length, half_w):
    """One laurel leaf: a pointed oval grown from the stem ring at ``theta``.

    The axis tilts ``lean`` radians off the tangent toward outward, the way a
    laurel's leaves angle toward the branch tip. Returns (outline, tip_base)
    polygons in pixels -- the leaf and the midrib line that strikes it.
    """
    base = (cx + r * math.cos(theta), cy + r * math.sin(theta))
    tangent = (-math.sin(theta), math.cos(theta))
    outward = (math.cos(theta), math.sin(theta))
    axis = (tangent[0] * math.cos(lean) + outward[0] * math.sin(lean),
            tangent[1] * math.cos(lean) + outward[1] * math.sin(lean))
    perp = (-axis[1], axis[0])
    steps = 10
    fwd, back = [], []
    for i in range(steps + 1):
        t = i / steps
        w = half_w * math.sin(math.pi * t) ** 0.8
        px = base[0] + axis[0] * length * t
        py = base[1] + axis[1] * length * t
        fwd.append((px + perp[0] * w, py + perp[1] * w))
        back.append((px - perp[0] * w, py - perp[1] * w))
    rib = [(base[0] + axis[0] * length * 0.15, base[1] + axis[1] * length * 0.15),
           (base[0] + axis[0] * length * 0.85, base[1] + axis[1] * length * 0.85)]
    return fwd + back[::-1], rib


def _wreath(size, accent):
    """A struck laurel around the crest, in the plate's own accent metal.

    Owner-briefed chrome for the show's two maxed-out characters: the ring a
    game draws around a max-level portrait. "Struck" means ONE metal, like a
    medallion -- no glow, no bloom, no second light source, nothing fighting
    the type. Two branches rise from an open bottom and stop short of the
    top. Scarcity and restraint are the brief: if it reads as gaudy, it is
    overdone.
    """
    scale = 4  # supersampled like the crest, for antialiased leaf edges
    s = int(size * scale)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = s / 2
    r_stem = s * 0.335
    r_leaf = s * 0.365
    leaf_len = s * 0.19
    leaf_w = s * 0.034
    metal = (accent[0], accent[1], accent[2], 232)
    # The struck relief: the SAME metal darkened, an engraved shadow -- not a
    # second light source.
    shade = tuple(int(c * 0.55) for c in accent[:3]) + (232,)

    # Two branches, open at the bottom where a laurel ties, just short of
    # meeting at the top. Angles are screen degrees: 0 is right, 90 is down.
    gap = math.radians(WREATH_GAP)
    top = math.radians(12)
    branches = [
        (math.pi / 2 + gap, math.pi * 1.5 - top),   # left, rising
        (-math.pi / 2 + top, math.pi / 2 - gap),    # right, rising (theta falls)
    ]
    for start, end in branches:
        d.arc([cx - r_stem, cy - r_stem, cx + r_stem, cy + r_stem],
              math.degrees(min(start, end)), math.degrees(max(start, end)),
              fill=shade, width=max(1, int(1.1 * scale)))
        step = (end - start) / (WREATH_LEAVES - 1)
        for i in range(WREATH_LEAVES):
            theta = start + i * step
            # Leaves grow toward the middle of the branch, as a laurel's do.
            grow = 0.8 + 0.4 * math.sin(math.pi * i / (WREATH_LEAVES - 1))
            lean = math.radians(28) * (1 if step > 0 else -1)
            outline, rib = _leaf(cx, cy, r_leaf, theta, lean,
                                 leaf_len * grow, leaf_w * grow)
            d.polygon(outline, fill=metal)
            d.line(rib, fill=shade, width=max(1, int(0.7 * scale)))
    return img.resize((int(size), int(size)), Image.LANCZOS)


def _horizon(width, height, accent, to_left=False):
    """A header rule: transparent -> accent -> white, with a soft glow."""
    img = Image.new("RGBA", (max(1, int(width)), max(1, int(height))), (0, 0, 0, 0))
    w = img.width
    for x in range(w):
        t = (w - 1 - x) / max(1, w - 1) if to_left else x / max(1, w - 1)
        if t < 0.6:
            k = t / 0.6
            px = (*accent[:3], int(255 * k))
        else:
            k = (t - 0.6) / 0.4
            px = tuple(int(accent[i] + (255 - accent[i]) * k) for i in range(3)) + (255,)
        img.paste(px, (x, 0, x + 1, img.height))
    return img


def _pill(size, fill, border):
    """plate.html's `.plate`: `border-radius: 999px` under a 1px (2px at 2x) rule.

    The fill is a supersampled mask so the round caps antialias. The hairline
    is STROKED, not mask-minus-eroded: `_chamfered`'s erosion trick only shows
    where its mask slopes, but a pill is all straight runs between the caps and
    the browser's border is visible the whole way around.
    """
    w, h = size
    scale = 4
    big = (w * scale, h * scale)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big[0] - 1, big[1] - 1],
                                           radius=big[1] // 2, fill=255)
    mask = mask.resize(size, Image.LANCZOS)

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    img.paste(fill, (0, 0, w, h), mask)

    ring = Image.new("RGBA", big, (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle([0, 0, big[0] - 1, big[1] - 1],
                                           radius=big[1] // 2,
                                           outline=border, width=scale)
    img.alpha_composite(ring.resize(size, Image.LANCZOS))
    return img


def _render_chat(spec):
    """The dialogue pill from wolves-*/render/plate.html: `[crest] SPEAKER | message`.

    One horizontal line on a pill -- the small talking card the other videos
    use, not the Guardian reveal's centered stack. The reveal names the person
    once; every line after that rides in this. Both fields are recovered copy:
    `speaker` from vocab/casting.yaml, `text` from dialogue/<id>/dialogue.json.

    A pill with NO text is not skipped and no longer renders empty: it is
    filled with lorem ipsum and credited to nobody, so the cut can be watched
    and timed before its words exist (``tools/placeholder.py``). The speaker is
    replaced along with the text -- a placeholder line under a real login is
    how act IV once had three colleagues "saying" lorem.
    """
    from tools.placeholder import fill

    spec = fill(spec)
    chrome = VARIANTS["default"]  # plate.html bakes only the blue chrome
    # .eyebrow { text-transform: uppercase } -- the speaker is chrome.
    speaker = (spec.get("speaker") or "").upper()
    # NOT uppercased. The site's .wc-nameplate-label shouts its label, but
    # plate.html's .message carries no text-transform and the baked plates
    # prove it ("I guess I'm taking the long way around."): recovered dialogue
    # is real speech, and shouting it would put an emphasis on it nobody said.
    text = spec.get("text") or ""
    for censor in spec.get("censor", []):
        source = censor["find"]
        replacement = censor["replace"]
        occurrences = text.count(source)
        if occurrences != 1:
            raise ValueError(
                f"chat plate {spec.get('id')!r} must contain its censorship "
                f"source {source!r} exactly once; found {occurrences}")
        text = text.replace(source, replacement)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    f_speaker = _font("regular", CHAT_FS_SPEAKER)
    speaker_w = _tracked_width(probe, speaker, f_speaker, CHAT_LS_SPEAKER)

    def censor_size(f_text):
        height = max(1, int(round(f_text.size * 0.72)))
        mark = Image.open(K8S_CENSOR_MARK)
        return int(round(mark.width * height / mark.height)), height

    def message_width(f_text):
        width = 0
        for part in text.split(K8S_CENSOR_TOKEN):
            if width:
                width += censor_size(f_text)[0]
            width += probe.textlength(part, font=f_text)
        return width

    def pill_width(f_text):
        # the flex row: pad, avatar, gap, eyebrow, gap, rule, gap, message, pad
        return (CHAT_PAD_L + CHAT_AVATAR + CHAT_GAP + speaker_w + CHAT_GAP
                + CHAT_RULE_W + CHAT_GAP
                + message_width(f_text) + CHAT_PAD_R)

    # plate.html's shrink-to-fit: start at MAX_FONT and step down until the
    # pill fits max-width -- one wide line, never a wrap ("Prefer one wide
    # line", authoring-interview-chat-plates). The loop stops at MIN_FONT just
    # like the browser's, so a line that still overflows renders whole rather
    # than clipping recovered dialogue.
    size = CHAT_FS_TEXT_MAX
    f_text = _font("bold", size)
    while size > CHAT_FS_TEXT_MIN and pill_width(f_text) > CHAT_MAX_W:
        size -= 1
        f_text = _font("bold", size)

    box_w = int(math.ceil(pill_width(f_text)))
    # border-box: the avatar is the tallest item, padding above and below.
    box_h = int(round(CHAT_AVATAR + 2 * CHAT_PAD_Y))
    img = _pill((box_w, box_h), INK, chrome["border"])
    mid = box_h / 2

    # The avatar slot holds a pfp in the videos (.avatar/.pfp: an 84px
    # circle); with no pfp, the crest is plate.html's own fallback. A pfp
    # that will not load falls back the same way -- degrade, never block.
    photo = _load_avatar(spec.get("avatar"), CHAT_AVATAR * 4)
    if photo is not None:
        s = CHAT_AVATAR * 4
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
        badge = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        badge.paste(photo, (0, 0), mask)
        img.alpha_composite(
            badge.resize((CHAT_AVATAR, CHAT_AVATAR), Image.LANCZOS),
            (CHAT_PAD_L, int(mid - CHAT_AVATAR / 2)))
    else:
        img.alpha_composite(_crest(CHAT_AVATAR, chrome["accent"]),
                            (CHAT_PAD_L, int(mid - CHAT_AVATAR / 2)))

    # Text goes on its own layer so one text-shadow sits under all of it
    # (plate.html: text-shadow: 0 4px 20px at 2x == 0 2px 10px here). The rule
    # is chrome, not type, so it stays out from under the shadow layer.
    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    x = CHAT_PAD_L + CHAT_AVATAR + CHAT_GAP
    if speaker:
        a, d = f_speaker.getmetrics()
        _draw_tracked(draw, (x, mid - (a + d) / 2), speaker, f_speaker,
                      chrome["label"], CHAT_LS_SPEAKER)
    x += speaker_w + CHAT_GAP
    img.alpha_composite(
        Image.new("RGBA", (CHAT_RULE_W, CHAT_RULE_H), chrome["border"]),
        (int(x), int(mid - CHAT_RULE_H / 2)))
    x += CHAT_RULE_W + CHAT_GAP

    if text:
        a, d = f_text.getmetrics()
        y = int(mid - (a + d) / 2)
        message_x = int(x)
        for index, part in enumerate(text.split(K8S_CENSOR_TOKEN)):
            if index:
                mark_w, mark_h = censor_size(f_text)
                with Image.open(K8S_CENSOR_MARK) as mark:
                    text_layer.alpha_composite(
                        mark.convert("RGBA").resize((mark_w, mark_h), Image.LANCZOS),
                        (message_x, int(mid - mark_h / 2)))
                message_x += mark_w
            if part:
                part_w = int(math.ceil(probe.textlength(part, font=f_text)))
                layer = _gradient_text(
                    (part_w + 4, int(f_text.size * 1.4)), part, f_text,
                    [(0.0, (255, 255, 255, 255)),
                     (0.6, NAME_MID), (1.0, NAME_BOTTOM)])
                text_layer.alpha_composite(layer, (message_x, y))
                message_x += part_w

    img.alpha_composite(_with_text_shadow(text_layer))
    return img


def _variant_for(spec):
    """The reference deck flags chrome with `trustee`; `variant` adds `leader`.

    `leader` is checked first because the CSS does the same:
    `.wolves-guardian-plate-trustee:not(.wolves-guardian-plate-leader)` means
    the gold leader treatment takes precedence over burnished silver, so a
    binding can carry both flags and be plated as the leader.
    """
    if spec.get("variant"):
        return VARIANTS[spec["variant"]]
    if spec.get("kind") == "title":
        return VARIANTS["trustee"]  # the title card uses the silver treatment
    return VARIANTS["trustee" if spec.get("trustee") else "default"]


def _render_status(spec, glitch=False):
    """The site's top-of-frame HUD nameplate: a `detail` eyebrow over a `label`.

    Reproduces `.wc-nameplate` (Nameplate.vue) on the `.wc-plate` surface: a
    chamfered translucent panel with a 2px accent rule down its left edge.

    The component's rotating dinosaur avatar badge is deliberately NOT drawn.
    It is animated brand artwork rather than copy, it cycles on a 20s timer
    that no still can represent honestly, and inventing a frozen stand-in for
    it would put a picture on the card that the deck never authored. Recorded
    as a gap instead, in the act's plate manifest under ``unresolved``.
    """
    detail = (spec.get("detail") or "").upper()   # text-transform: uppercase
    label = (spec.get("label") or "").upper()

    f_detail = _font("regular", FS_STATUS_DETAIL)
    f_label = _font("bold", FS_STATUS_LABEL)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    inner = max(
        _tracked_width(probe, detail, f_detail, LS_STATUS_DETAIL),
        _tracked_width(probe, label, f_label, LS_STATUS_LABEL),
    )
    box_w = int(round(inner + STATUS_PAD_LEFT + STATUS_PAD_RIGHT + STATUS_RULE))
    rows = [t for t in (detail, label) if t]
    text_h = sum(f.size * 1.25 for t, f in ((detail, f_detail), (label, f_label)) if t)
    text_h += STATUS_GAP * (len(rows) - 1) if len(rows) > 1 else 0
    box_h = int(round(STATUS_PAD_TOP * 2 + text_h))

    img = _chamfered((box_w, box_h), STATUS_PANEL, STATUS_LINE,
                     radius=STATUS_CHAMFER, corner=0)
    # border-left: the accent rule runs the full height of the plate.
    ImageDraw.Draw(img).rectangle(
        [0, 0, STATUS_RULE - 1, box_h - 1], fill=STATUS_ACCENT)

    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    x = STATUS_RULE + STATUS_PAD_LEFT
    y = STATUS_PAD_TOP
    if detail:
        _draw_tracked(draw, (x, y), detail, f_detail, STATUS_ACCENT,
                      LS_STATUS_DETAIL)
        y += f_detail.size * 1.25 + STATUS_GAP
    if label:
        _draw_tracked(draw, (x, y), label, f_label, STATUS_WHITE,
                      LS_STATUS_LABEL)

    if glitch:
        text_layer = _rgb_split(text_layer)
    img.alpha_composite(_with_text_shadow(text_layer))
    if glitch:
        img = _tear(img)
    return img


def _render_banner(spec):
    """The letterbox callout: one tracked line, sized to the frame's width.

    NOT uppercased, for the same reason the chat pill's message is not: the
    string is owner-authored copy (`copy_source: owner_supplied`) and shouting
    the mixed-case part ("Support Open Gaming Collective") would put an
    emphasis on it nobody wrote. Shrink-to-fit like the chat pill: one wide
    line, never a wrap, and at the floor it renders whole rather than clip.
    """
    text = spec.get("text") or ""
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    max_w = FRAME_W * BANNER_MAX_W

    size = BANNER_FS_MAX
    f_text = _font("bold", int(size))
    while (int(size) > int(BANNER_FS_MIN)
           and _tracked_width(probe, text, f_text, BANNER_LS) > max_w):
        size -= 1
        f_text = _font("bold", int(size))

    w = int(math.ceil(_tracked_width(probe, text, f_text, BANNER_LS))) + 4
    a, d = f_text.getmetrics()
    img = Image.new("RGBA", (w, int((a + d) * 1.3)), (0, 0, 0, 0))
    layer = _gradient_text((w, int(f_text.size * 1.4)), text, f_text,
                           [(0.0, (255, 255, 255, 255)),
                            (0.6, NAME_MID), (1.0, NAME_BOTTOM)],
                           tracking_em=BANNER_LS)
    img.alpha_composite(_with_text_shadow(layer), (0, 0))
    return img



def _wrap_text_to_width(text, font, max_width):
    """Wrap text to a pixel width, preserving explicit newlines."""
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            if probe.textlength(trial, font=font) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def _render_caption(spec):
    """Top-safe narrative cue: wrapped bold white text on a dark rail.

    Glyph-aware layout: each active glyph reserves its actual mark width in
    line measurement, wraps based on that visual width, and shifts the text
    after it by the accumulated width delta. A missing mark falls back to the
    plain letter, leaving the line width unchanged.
    """
    text = spec.get("text") or ""
    f_text = _font("bold", CAPTION_FS)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    inner_w = CAPTION_MAX_W - 2 * CAPTION_PAD
    line_h = f_text.size * 1.25

    # Resolve active glyphs and the exact character offset each replaces in
    # the raw authored text. Missing/unreadable marks are silently ignored so
    # the original letter renders instead.
    active = {}
    for glyph in spec.get("glyphs") or []:
        token = glyph.get("token", "")
        if not token:
            continue
        word = glyph.get("word") or ""
        idx = int(glyph.get("index", 0))
        src = glyph.get("src") or str(K8S_CENSOR_MARK)
        try:
            mark = Image.open(_resolve(src)).convert("RGBA")
        except (OSError, ValueError):
            continue
        mark_h = int(round(f_text.size * 0.85))
        mark_w = int(round(mark.width * mark_h / mark.height))
        resized = mark.resize((mark_w, mark_h), Image.LANCZOS)

        if word:
            wstart = text.find(word)
            if wstart == -1:
                continue
            occurrences = [
                i for i, ch in enumerate(text[wstart:wstart + len(word)])
                if ch == token
            ]
            if not occurrences or idx >= len(occurrences):
                continue
            char_offset = wstart + occurrences[idx]
        else:
            occurrences = [i for i, ch in enumerate(text) if ch == token]
            if not occurrences or idx >= len(occurrences):
                continue
            char_offset = occurrences[idx]
        if char_offset in active:
            continue
        active[char_offset] = {"token": token, "mark": resized,
                               "mark_w": mark_w, "mark_h": mark_h}

    class TextSeg:
        __slots__ = ("text", "width")
        def __init__(self, text_):
            self.text = text_
            self.width = probe.textlength(text_, font=f_text)

    class GlyphSeg:
        __slots__ = ("mark", "mark_w", "mark_h")
        def __init__(self, info):
            self.mark = info["mark"]
            self.mark_w = info["mark_w"]
            self.mark_h = info["mark_h"]
        @property
        def width(self):
            return self.mark_w

    class WordPiece:
        __slots__ = ("segments", "width")
        def __init__(self, segments):
            self.segments = segments
            self.width = sum(s.width for s in segments)

    class SpacePiece:
        __slots__ = ("text", "width")
        def __init__(self, text_):
            self.text = text_
            self.width = probe.textlength(text_, font=f_text)

    def pieces_for(paragraph, base_offset):
        pieces = []
        for m in re.finditer(r"\S+|\s+", paragraph):
            piece_text = m.group()
            start = m.start()
            if piece_text.isspace():
                pieces.append(SpacePiece(piece_text))
                continue
            segments = []
            i = start
            end = m.end()
            while i < end:
                global_i = base_offset + i
                info = active.get(global_i)
                if info is not None and text.startswith(info["token"], global_i):
                    segments.append(GlyphSeg(info))
                    i += len(info["token"])
                    continue
                next_glyph = min(
                    (off - base_offset for off in active
                     if start <= off - base_offset < end and off - base_offset > i),
                    default=end,
                )
                chunk = paragraph[i:min(next_glyph, end)]
                if chunk:
                    segments.append(TextSeg(chunk))
                    i += len(chunk)
                else:
                    # Defensive: should only happen if a glyph offset <= i.
                    i += 1
            pieces.append(WordPiece(segments))
        return pieces

    def trim_line(line):
        while line and isinstance(line[-1], SpacePiece):
            line.pop()
        while line and isinstance(line[0], SpacePiece):
            line.pop(0)
        return line

    all_lines = []
    base_offset = 0
    for paragraph in text.split("\n"):
        pieces = pieces_for(paragraph, base_offset)
        cur_line = []
        cur_w = 0.0
        for p in pieces:
            if isinstance(p, SpacePiece) and not cur_line:
                continue
            if not cur_line or cur_w + p.width <= inner_w:
                cur_line.append(p)
                cur_w += p.width
            else:
                all_lines.append(trim_line(cur_line))
                cur_line = []
                cur_w = 0.0
                if isinstance(p, SpacePiece):
                    continue
                cur_line.append(p)
                cur_w = p.width
        if cur_line:
            all_lines.append(trim_line(cur_line))
        base_offset += len(paragraph) + 1
    if not all_lines:
        all_lines = [[]]

    line_widths = [sum(p.width for p in line) for line in all_lines]
    box_w = int(round(min(CAPTION_MAX_W, max(line_widths) + 2 * CAPTION_PAD)))
    text_h = len(all_lines) * line_h + (len(all_lines) - 1) * CAPTION_LINE_GAP
    box_h = int(round(
        CAPTION_PAD + text_h + CAPTION_PAD + CAPTION_RULE + CAPTION_PAD))

    img = _chamfered((box_w, box_h), INK, VARIANTS["default"]["border"],
                     radius=CHAMFER, corner=CORNER_RADIUS)
    rule_y = int(round(box_h - CAPTION_PAD - CAPTION_RULE / 2))
    img.alpha_composite(_horizon(box_w - 2 * CAPTION_PAD, CAPTION_RULE,
                                 VARIANTS["default"]["accent"]),
                        (int(CAPTION_PAD), rule_y))

    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    glyph_placements = []

    for ln_idx, line in enumerate(all_lines):
        line_w = line_widths[ln_idx]
        x = (box_w - line_w) / 2
        y = int(round(CAPTION_PAD + ln_idx * (line_h + CAPTION_LINE_GAP)))
        for p in line:
            if isinstance(p, WordPiece):
                for seg in p.segments:
                    if isinstance(seg, TextSeg):
                        draw.text((int(round(x)), y), seg.text,
                                  font=f_text, fill=TEXT)
                    else:
                        my = y - (seg.mark_h - f_text.size) // 2
                        glyph_placements.append(
                            (seg.mark, int(round(x)), int(round(my))))
                    x += seg.width
            else:
                x += p.width

    img.alpha_composite(_with_text_shadow(text_layer))
    for mark, mx, my in glyph_placements:
        img.alpha_composite(mark, (mx, my))
    return img

def _render_context(spec):
    """Restrained lower-left context stack: title, subtitle, body lines.

    Sits above the Guardian-plate plaque lane; no crest, because this is
    scene-setting metadata rather than a named identity.
    """
    title = spec.get("title") or ""
    subtitle = spec.get("subtitle") or ""
    body = list(spec.get("body") or [])

    f_title = _font("bold", CONTEXT_FS_TITLE)
    f_line = _font("bold", CONTEXT_FS_LINE)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    widths = [probe.textlength(title, font=f_title)]
    if subtitle:
        widths.append(probe.textlength(subtitle, font=f_line))
    for line in body:
        widths.append(probe.textlength(line, font=f_line))
    inner_w = max(widths) if widths else 0
    box_w = int(round(inner_w + 2 * CONTEXT_PAD))

    rows = []
    if title:
        rows.append((title, f_title, TEXT))
    if subtitle:
        rows.append((subtitle, f_line, VARIANTS["default"]["label"]))
    for line in body:
        rows.append((line, f_line, TEXT))
    line_h_title = f_title.size * 1.3
    line_h_body = f_line.size * 1.25
    text_h = 0.0
    for i, (_, f, _) in enumerate(rows):
        text_h += (line_h_title if f is f_title else line_h_body)
        if i < len(rows) - 1:
            text_h += CONTEXT_LINE_GAP
    box_h = int(round(CONTEXT_PAD + text_h + CONTEXT_PAD))

    img = _chamfered((box_w, box_h), INK, VARIANTS["default"]["border"],
                     radius=CHAMFER, corner=CORNER_RADIUS)
    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    y = int(round(CONTEXT_PAD))
    for line, f, colour in rows:
        draw.text((int(round(CONTEXT_PAD)), int(round(y))), line, font=f, fill=colour)
        y += (line_h_title if f is f_title else line_h_body) + CONTEXT_LINE_GAP

    img.alpha_composite(_with_text_shadow(text_layer))
    return img


def _render_warning(spec):
    """Full-frame deployment warning: red panel, two warning stripes, text."""
    text = spec.get("text") or ""
    f_text = _font("bold", WARNING_FS)

    frame = Image.new("RGBA", (FRAME_W, FRAME_H), WARNING_PANEL)
    # Diagonal deployment hazard bars at top and bottom: the warning red cuts
    # through a near-black track instead of reading as a plain divider.
    stripe = Image.new("RGBA", (FRAME_W, WARNING_STRIPE_H), WARNING_STRIPE)
    stripe_draw = ImageDraw.Draw(stripe)
    step = WARNING_STRIPE_H * 4
    slash = WARNING_STRIPE_H * 2
    for x in range(-slash, FRAME_W + step, step):
        stripe_draw.polygon([
            (x, 0), (x + slash, 0),
            (x + slash - WARNING_STRIPE_H, WARNING_STRIPE_H),
            (x - WARNING_STRIPE_H, WARNING_STRIPE_H),
        ], fill=WARNING_RED)
    frame.alpha_composite(stripe, (0, 0))
    frame.alpha_composite(stripe, (0, FRAME_H - WARNING_STRIPE_H))

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w = probe.textlength(text, font=f_text)
    a, d = f_text.getmetrics()
    text_layer = Image.new("RGBA", (int(w + 4), int(a + d + 4)), (0, 0, 0, 0))
    ImageDraw.Draw(text_layer).text((2, 0), text, font=f_text, fill=WARNING_TEXT)
    shadowed = _with_text_shadow(text_layer)
    x = (FRAME_W - shadowed.width) // 2
    y = (FRAME_H - shadowed.height) // 2
    frame.alpha_composite(shadowed, (x, y))
    return frame


def _render_companion(spec):
    """The site's GUARDIAN BOND card: species artwork over a three-row plate.

    Ported from `.wolves-companion-plate` and friends (WolvesIntroOverlay.vue).
    The artwork is the hero: it rides above the card and overflows the
    chamfered box (the site puts the clip-path on the card, never the wrapper),
    so this composites onto a canvas taller and wider than the card itself.

    `name` is omitted when no character sheet names the bonded dinosaur -- the
    site's own `v-if`. `art` is a local image path, cached ahead of time the
    way avatars are; a missing file degrades to the card alone with a stderr
    note, because a bond that renders without its picture still credits the
    bond, and a crash credits nobody.
    """
    label = COMPANION_LABEL
    name = spec.get("name") or ""
    species = spec.get("species") or ""

    f_label = _font("regular", FS_COMPANION_LABEL)
    f_name = _font("bold", FS_COMPANION_NAME)
    f_species = _font("italic", FS_COMPANION_SPECIES)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    inner = max(
        _tracked_width(probe, label, f_label, LS_COMPANION_LABEL),
        probe.textlength(name, font=f_name),
        _tracked_width(probe, species, f_species, LS_COMPANION_SPECIES),
    )
    # The site fixes the card's width and lets the browser wrap; nothing here
    # wraps, so the card grows past its clamp rather than clipping a name.
    card_w = int(round(max(COMPANION_W, inner + 2 * COMPANION_PAD_X)))

    gap = 0.3 * REM   # .name { margin-top: 0.3rem }, .species { 0.35rem }
    rows = [(label, f_label), (name, f_name), (species, f_species)]
    text_h = sum(f.size * 1.25 for text, f in rows if text)
    text_h += gap * (max(1, len([1 for text, _ in rows if text])) - 1)
    card_h = int(round(COMPANION_PAD_TOP + text_h + COMPANION_PAD_BOTTOM))

    art = None
    art_path = spec.get("art")
    if art_path:
        try:
            art = Image.open(_resolve(art_path)).convert("RGBA")
        except (OSError, ValueError) as exc:
            print(f"companion {spec.get('id')!r}: no artwork at {art_path} "
                  f"({exc}); rendering the card alone", file=sys.stderr)

    art_w = art_h = 0
    if art is not None:
        ratio = COMPANION_ART_WIDTH.get(spec.get("species_id"),
                                        COMPANION_ART_BASE)
        art_w = int(round(card_w * ratio))
        art_h = max(1, int(round(art.height * art_w / art.width)))
        # `art_max_h` caps how far the artwork rises, for the one place where
        # a full-height animal would climb into another card. It is a FRAME
        # JUDGEMENT and never a default: the site's art is the hero and this
        # shrinks it, so an entry that sets it has to say why in its note.
        cap = spec.get("art_max_h")
        if cap and art_h > int(cap):
            art_w = max(1, int(round(art_w * int(cap) / art_h)))
            art_h = int(cap)
        art = art.resize((art_w, art_h), Image.LANCZOS)

    # The art overflows the card on both sides and rises above it, less the
    # negative bottom margin that tucks it behind the card's top padding.
    overhang = max(0, (art_w - card_w) // 2)
    rise = max(0, art_h - int(round(COMPANION_ART_DROP))) if art is not None else 0
    img = Image.new("RGBA", (card_w + 2 * overhang, card_h + rise), (0, 0, 0, 0))

    card = _chamfered((card_w, card_h), INK, VARIANTS["default"]["border"],
                      radius=CHAMFER, corner=CORNER_RADIUS)
    img.alpha_composite(card, (overhang, rise))
    if art is not None:
        img.alpha_composite(art, ((img.width - art_w) // 2, 0))

    text_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    cx = img.width / 2
    y = rise + COMPANION_PAD_TOP
    if label:
        w = _tracked_width(draw, label, f_label, LS_COMPANION_LABEL)
        _draw_tracked(draw, (cx - w / 2, y), label, f_label,
                      COMPANION_LABEL_COLOUR, LS_COMPANION_LABEL)
        y += f_label.size * 1.25 + gap
    if name:
        w = int(math.ceil(draw.textlength(name, font=f_name)))
        layer = _gradient_text((w + 4, int(f_name.size * 1.4)), name, f_name,
                               [(0.0, (255, 255, 255, 255)),
                                (0.6, NAME_MID),
                                (1.0, NAME_BOTTOM)])
        text_layer.alpha_composite(layer, (int(cx - w / 2), int(y)))
        y += f_name.size * 1.25 + gap
    if species:
        w = _tracked_width(draw, species, f_species, LS_COMPANION_SPECIES)
        _draw_tracked(draw, (cx - w / 2, y), species, f_species,
                      COMPANION_SPECIES_COLOUR, LS_COMPANION_SPECIES)

    img.alpha_composite(_with_text_shadow(text_layer))
    return img


def _render_miniboss(spec):
    """Destiny's boss bar, as a card: rank diamond, NAME, title, health bar.

    The layout is the game's -- the thing it puts at the top of frame when a
    named enemy arrives -- and the red is the owner's ("Name Plate for the
    Villan in Red Badge"). Destiny's own Majors run orange-yellow and its
    Ultras get the skull, so this is not a reproduction of a specific bar; it
    is that treatment in his colour, and the rows are still the deck's closed
    set: `name` and `title`, nothing invented.

    It names a VILLAIN, not a person. That is why it is the one card here that
    may carry copy nobody's identity had to be authored for.
    """
    name = (spec.get("name") or "").upper()
    title = (spec.get("title") or "").upper()

    f_name = _font("bold", FS_MINIBOSS_NAME)
    f_title = _font("regular", FS_MINIBOSS_TITLE)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    inner = max(_tracked_width(probe, name, f_name, LS_MINIBOSS_NAME),
                _tracked_width(probe, title, f_title, LS_MINIBOSS_TITLE))
    gap = 0.3 * REM
    text_h = f_name.size * 1.25 + (f_title.size * 1.25 + gap if title else 0)
    box_w = int(round(inner + 2 * MINIBOSS_PAD_X + MINIBOSS_ICON + gap))
    box_h = int(round(2 * MINIBOSS_PAD_Y + text_h + gap + MINIBOSS_BAR_H))

    img = _chamfered((box_w, box_h), MINIBOSS_PANEL, MINIBOSS_RED,
                     radius=CHAMFER, corner=0)
    d = ImageDraw.Draw(img)

    # The rank diamond: the game marks a named enemy before it names it.
    cy = MINIBOSS_PAD_Y + text_h / 2
    r = MINIBOSS_ICON / 2
    cxi = MINIBOSS_PAD_X + r
    d.polygon([(cxi, cy - r), (cxi + r, cy), (cxi, cy + r), (cxi - r, cy)],
              fill=MINIBOSS_RED)
    d.polygon([(cxi, cy - r * 0.5), (cxi + r * 0.5, cy),
               (cxi, cy + r * 0.5), (cxi - r * 0.5, cy)], fill=MINIBOSS_PANEL)

    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    x = MINIBOSS_PAD_X + MINIBOSS_ICON + gap
    y = MINIBOSS_PAD_Y
    _draw_tracked(draw, (x, y), name, f_name, TEXT, LS_MINIBOSS_NAME)
    y += f_name.size * 1.25 + gap
    if title:
        _draw_tracked(draw, (x, y), title, f_title, MINIBOSS_RED,
                      LS_MINIBOSS_TITLE)
    img.alpha_composite(_with_text_shadow(text_layer))

    # The health bar, full: the enemy has just arrived and has taken nothing.
    bar_y = box_h - MINIBOSS_PAD_Y / 2 - MINIBOSS_BAR_H
    d.rectangle([MINIBOSS_PAD_X, bar_y, box_w - MINIBOSS_PAD_X,
                 bar_y + MINIBOSS_BAR_H - 1], fill=MINIBOSS_RED_DIM)
    d.rectangle([MINIBOSS_PAD_X, bar_y, box_w - MINIBOSS_PAD_X,
                 bar_y + MINIBOSS_BAR_H - 1], fill=MINIBOSS_RED)
    return img


def _render_achievement(spec):
    """The Xbox achievement toast: green orb, ACHIEVEMENT UNLOCKED, name, score.

    Owner's gag, one per dramatic explosion: "make this look like a real
    person unlocking a bunch of achievements". #107C10 is Xbox's own brand
    green. The eyebrow is fixed chrome; `name` and `score` are authored copy
    and the builder will not emit one the owner has not approved.
    """
    eyebrow = ACHIEVEMENT_EYEBROW
    name = spec.get("name") or ""
    score = spec.get("score") or ""

    f_eyebrow = _font("regular", FS_ACHIEVEMENT_EYEBROW)
    f_name = _font("bold", FS_ACHIEVEMENT_NAME)
    f_score = _font("regular", FS_ACHIEVEMENT_SCORE)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    gap = 0.75 * REM
    text_w = max(_tracked_width(probe, eyebrow, f_eyebrow,
                                LS_ACHIEVEMENT_EYEBROW),
                 probe.textlength(name, font=f_name))
    score_w = probe.textlength(score, font=f_score) + gap if score else 0
    box_w = int(round(ACHIEVEMENT_PAD_X * 2 + ACHIEVEMENT_ORB + gap
                      + text_w + score_w))
    text_h = f_eyebrow.size * 1.25 + f_name.size * 1.25
    box_h = int(round(ACHIEVEMENT_PAD_Y * 2 + max(text_h, ACHIEVEMENT_ORB)))

    img = _chamfered((box_w, box_h), ACHIEVEMENT_PANEL, XBOX_GREEN,
                     radius=CORNER_RADIUS, corner=CORNER_RADIUS)
    d = ImageDraw.Draw(img)

    # The orb: the green sphere the console pops with its own tick inside it.
    ox = ACHIEVEMENT_PAD_X
    oy = (box_h - ACHIEVEMENT_ORB) / 2
    d.ellipse([ox, oy, ox + ACHIEVEMENT_ORB, oy + ACHIEVEMENT_ORB],
              fill=XBOX_GREEN)
    cx, cy = ox + ACHIEVEMENT_ORB / 2, oy + ACHIEVEMENT_ORB / 2
    q = ACHIEVEMENT_ORB * 0.22
    d.line([(cx - q, cy), (cx - q * 0.2, cy + q * 0.8), (cx + q, cy - q * 0.8)],
           fill=(255, 255, 255, 255), width=max(2, int(ACHIEVEMENT_ORB * 0.09)),
           joint="curve")

    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    x = ox + ACHIEVEMENT_ORB + gap
    y = (box_h - text_h) / 2
    _draw_tracked(draw, (x, y), eyebrow, f_eyebrow, XBOX_GREEN,
                  LS_ACHIEVEMENT_EYEBROW)
    y += f_eyebrow.size * 1.25
    draw.text((x, y), name, font=f_name, fill=TEXT)
    if score:
        sw = draw.textlength(score, font=f_score)
        draw.text((box_w - ACHIEVEMENT_PAD_X - sw, (box_h - f_score.size) / 2),
                  score, font=f_score, fill=XBOX_GREEN)
    img.alpha_composite(_with_text_shadow(text_layer))
    return img


def _render_choice(spec):
    """The **video-game choice screen**: the film stops and asks the player.

    Owner: *"design it like a video game choice screen and 'pause' here to let
    the player 'decide' then it cuts to the descent."*

    So this is not a lower third at all -- it is a FULL-FRAME card, placed with
    ``position: "full"``. A scrim goes over the whole picture, the way a pause
    menu dims the game behind it, and the two options sit in the middle at
    button scale. The picture is still moving underneath: a true freeze would
    have to be cut into the film itself, which moves every timecode after it,
    so it is recorded as a punch-list item rather than faked here.

    NOTHING IS HIGHLIGHTED -- no cursor, no selected row, no confirm prompt --
    because the joke is that neither option is a choice, and lighting one up
    would answer it. The `o` the owner typed is drawn as a ring rather than
    typeset as the letter: it is a marker, not a lowercase o.

    `label` is the prompt and `options` are the boxes. Both are authored copy,
    and the field set is closed like every other card kind's.
    """
    label = (spec.get("label") or "").upper()
    # An option is either a string or ``{"text": ..., "tier": "legendary"}``.
    options = []
    for raw in spec.get("options") or []:
        entry = {"text": str(raw)} if isinstance(raw, str) else dict(raw)
        if str(entry.get("text", "")).strip():
            options.append(entry)

    f_label = _font("regular", FS_CHOICE_LABEL)
    f_option = _font("bold", FS_CHOICE_OPTION)
    f_tag = _font("regular", FS_CHOICE_TAG)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    row_w = CHOICE_BULLET + CHOICE_BULLET_GAP
    widest = max([probe.textlength(o["text"], font=f_option) for o in options]
                 or [0])
    # Every box is cut to the widest option, so the stack is a column of
    # buttons rather than a ragged edge -- two separate boxes, owner's call.
    box_w = int(round(CHOICE_RULE + CHOICE_PAD_X * 2 + row_w + widest))
    box_w = min(box_w, int(FRAME_W * CHOICE_MAX_W))
    box_h = int(round(CHOICE_PAD_Y * 2 + f_option.size * 1.25))
    # The legendary card is taller: Destiny's puts the difficulty's NAME above
    # its title, so the amber box carries a tag row the plain one does not.
    tag_h = int(round(f_tag.size * 1.5))
    heights = [box_h + (tag_h if o.get("tier") == "legendary" else 0)
               for o in options]

    label_h = int(round(f_label.size * 1.25 + CHOICE_ROW_GAP)) if label else 0
    stack_h = (label_h + sum(heights)
               + max(0, len(options) - 1) * CHOICE_BOX_GAP)

    # The pause scrim: the whole frame goes down so the menu reads as chrome
    # over a stopped game rather than as a caption on a moving shot.
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), CHOICE_SCRIM)

    top = int((FRAME_H - stack_h) / 2)
    left = int((FRAME_W - box_w) / 2)

    if label:
        layer = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        lw = _tracked_width(probe, label, f_label, LS_CHOICE_LABEL)
        _draw_tracked(ImageDraw.Draw(layer),
                      ((FRAME_W - lw) / 2, top), label, f_label,
                      CHOICE_ACCENT, LS_CHOICE_LABEL)
        frame.alpha_composite(_with_text_shadow(layer))

    y = top + label_h
    centres = []
    for option, height in zip(options, heights):
        legendary = option.get("tier") == "legendary"
        panel = CHOICE_LEGENDARY_PANEL if legendary else CHOICE_PANEL
        line = CHOICE_LEGENDARY_LINE if legendary else CHOICE_LINE
        accent = CHOICE_LEGENDARY_ACCENT if legendary else CHOICE_ACCENT

        box = _chamfered((box_w, height), panel, line,
                         radius=CORNER_RADIUS, corner=CORNER_RADIUS)
        ImageDraw.Draw(box).rectangle(
            [0, 0, CHOICE_RULE - 1, height - 1], fill=accent)
        layer = Image.new("RGBA", (box_w, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        x = CHOICE_RULE + CHOICE_PAD_X
        ty = CHOICE_PAD_Y
        if legendary:
            _draw_tracked(draw, (x + row_w, ty), CHOICE_LEGENDARY_TAG, f_tag,
                          accent, LS_CHOICE_TAG)
            ty += tag_h
        # The marker: Destiny's legendary card uses a diamond, the plain one a
        # simple ring.
        cy = ty + f_option.size * 0.62
        r = CHOICE_BULLET / 2
        if legendary:
            draw.polygon([(x + r, cy - r), (x + CHOICE_BULLET, cy),
                          (x + r, cy + r), (x, cy)], outline=accent, width=3)
        else:
            draw.ellipse([x, cy - r, x + CHOICE_BULLET, cy + r],
                         outline=accent, width=3)
        draw.text((x + row_w, ty), option["text"], font=f_option, fill=TEXT)
        box.alpha_composite(_with_text_shadow(layer))
        frame.alpha_composite(box, (left, int(round(y))))
        # Aimed at the MARKER, not at the words: a cursor sitting on the text
        # reads as a typo, and the marker is what you would click.
        centres.append((left + x + CHOICE_BULLET / 2, y + cy))
        y += height + CHOICE_BOX_GAP

    progress = spec.get("pointer")
    if progress is not None and centres:
        target = centres[min(CHOICE_POINTER_TARGET, len(centres) - 1)]
        t = max(0.0, min(1.0, float(progress)))
        # Ease-IN: the hand is still winding up. Ease-out would put the
        # pointer almost on the button by the time the cut lands, which reads
        # as having chosen. It has not chosen -- that is the whole gag.
        k = t ** 1.5
        px = FRAME_W / 2 + (target[0] - FRAME_W / 2) * k
        py = FRAME_H / 2 + (target[1] - FRAME_H / 2) * k
        frame.alpha_composite(_cursor(), (int(px), int(py)))
    return frame


_CURSOR = None


def _cursor():
    """The arrow pointer, drawn once and cached.

    The classic seven-point cursor: tip at the origin, so a caller places it by
    the point it is actually pointing with rather than by a bounding box. White
    with a dark edge, at game-menu scale -- a 24px desktop cursor is invisible
    at a distance on a 1080p film.
    """
    global _CURSOR
    if _CURSOR is not None:
        return _CURSOR
    h = CHOICE_POINTER_H
    # Proportions of the standard arrow, in units of its height.
    pts = [(0.00, 0.00), (0.00, 0.74), (0.19, 0.57), (0.31, 0.86),
           (0.45, 0.80), (0.33, 0.52), (0.55, 0.52)]
    scale = 4  # drawn oversized and downsampled: Pillow does not antialias
    poly = [(x * h * scale, y * h * scale) for x, y in pts]
    big = Image.new("RGBA", (int(h * 0.6 * scale) + 8, int(h * scale) + 8),
                    (0, 0, 0, 0))
    ImageDraw.Draw(big).polygon(poly, fill=CHOICE_POINTER_FILL,
                                outline=CHOICE_POINTER_EDGE)
    ImageDraw.Draw(big).line(poly + [poly[0]], fill=CHOICE_POINTER_EDGE,
                             width=3 * scale, joint="curve")
    ImageDraw.Draw(big).polygon(poly, fill=CHOICE_POINTER_FILL)
    _CURSOR = big.resize((big.width // scale, big.height // scale),
                         Image.LANCZOS)
    return _CURSOR


def _rgb_split(text):
    """The glitch's red/cyan `text-shadow` split.

    In the CSS this is a *text-shadow*, so it applies to the type and not to
    the panel behind it -- splitting the whole card instead fringes the plate's
    edges and leaves the words looking untouched.

        text-shadow: 2px 0 0 rgb(255 0 64 / 75%), -2px 0 0 rgb(0 220 255 / 75%)
    """
    out = Image.new("RGBA", text.size, (0, 0, 0, 0))
    alpha = text.getchannel("A").point(lambda a: int(a * 0.75))
    for colour, dx in (((255, 0, 64), 2), ((0, 220, 255), -2)):
        layer = Image.new("RGBA", text.size, (*colour, 0))
        layer.putalpha(alpha)
        shifted = Image.new("RGBA", text.size, (0, 0, 0, 0))
        # alpha_composite takes no negative offset, so each copy is pasted onto
        # its own full-size canvas at the shift and then composited.
        shifted.paste(layer, (dx, 0))
        out.alpha_composite(shifted)
    out.alpha_composite(text)
    return out


def _tear(img):
    """The glitch's clip-path tear: the band from 42% to 58% is cut away.

        clip-path: polygon(0 0, 100% 0, 100% 42%, 0 42%, 0 58%, 100% 58%, ...)
    """
    out = img.copy()
    ImageDraw.Draw(out).rectangle(
        [0, int(img.height * 0.42), img.width, int(img.height * 0.58)],
        fill=(0, 0, 0, 0))
    return out


def render_plate(spec):
    """One plate spec -> a tight RGBA image (no frame padding).

    Three card shapes. Two come straight from ~/Videos/nameplates.json: the
    Guardian plate (`label` / `class` / `name` / `title`) and the title card
    (`title` / `subtitle` / `body`). The third is the chat card (`speaker` /
    `text`), added to the data model deliberately so a cut can show a recovered
    conversation without a plate line anybody had to invent. The chat card is
    a different component -- the plate.html dialogue pill -- so it dispatches
    to `_render_chat` instead of sharing the reveal's centered stack. So are
    the site's own two: the top-of-frame `status` HUD, and the `companion`
    card that names a Guardian's bonded dinosaur beside their lower third.

    The FULL-FRAME cards (`act`, `comic`, `photo`) are not rendered here at all. They are
    the site's own components, and they are reproduced the way every other
    Wolves card is -- the real CSS in a browser (`cards/render-cards.mjs`),
    never a second implementation in Pillow. Rendering one here would silently
    produce an empty Guardian plate, so it is refused instead.
    """
    if spec.get("kind") in CARD_KINDS:
        raise ValueError(
            f"plate {spec.get('id')!r} is a {spec['kind']} card: render it with "
            "`node cards/render-cards.mjs --manifest <manifest> --out-dir <dir>`, "
            "which uses the website's own CSS. tools/plate.py burns them, it "
            "does not draw them."
        )
    if spec.get("kind") == "interstitial":
        raise ValueError(
            f"plate {spec.get('id')!r} is an interstitial card: render it with "
            "its own builder (scripts/build_scream_card.py). tools/plate.py "
            "neither draws nor burns it."
        )
    if spec.get("kind") == "logowall":
        raise ValueError(
            f"plate {spec.get('id')!r} is a logo wall: render it with its own "
            "builder (scripts/build_cncf_wall.py), which draws from the "
            "landscape record. tools/plate.py burns it, it does not draw it."
        )
    if spec.get("kind") == "chat":
        return _render_chat(spec)
    if spec.get("kind") == "companion":
        return _render_companion(spec)
    if spec.get("kind") == "miniboss":
        return _render_miniboss(spec)
    if spec.get("kind") == "achievement":
        return _render_achievement(spec)
    if spec.get("kind") == "status":
        return _render_status(spec, glitch=bool(spec.get("glitch")))
    if spec.get("kind") == "banner":
        return _render_banner(spec)
    if spec.get("kind") == "caption":
        return _render_caption(spec)
    if spec.get("kind") == "context":
        return _render_context(spec)
    if spec.get("kind") == "warning":
        return _render_warning(spec)
    if spec.get("kind") == "choice":
        return _render_choice(spec)
    variant = _variant_for(spec)
    ghost = spec.get("kind") == "ghost"
    card = spec.get("kind") == "title"
    scale = 0.82 if ghost else 1.0
    # Chrome, not copy: a PFP in the crest, the laurel around it, and the
    # bazzite logomark. None of it adds a row the deck has no field for.
    avatar = spec.get("avatar")
    wreath = bool(spec.get("wreath"))
    # The crest's mark follows the chrome: Bazzite's is traced from its SVG,
    # and a brand published only as a raster is reproduced from the cached
    # artwork (scripts/fetch_brand_marks.py). A variant with no mark keeps
    # the drawn hex crest, which is the default everywhere else.
    mark = BRAND_MARKS.get(spec.get("variant"))

    f_label = _font("regular", FS_LABEL * scale)
    f_class = _font("regular", FS_CLASS * scale)
    f_name = _font("bold", FS_NAME * scale)
    f_title = _font("regular", FS_TITLE * scale)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    if card:
        # The title card has no eyebrow and no class: its `title` is the display
        # line and `subtitle` sits under it, with `body` beneath both.
        label, klass = "", ""
        name = spec.get("title") or ""
        title = spec.get("subtitle") or ""
        body = list(spec.get("body") or [])
    else:
        label = (spec.get("label") or "").upper()
        # NOT uppercased. The site stylesheet puts `text-transform: uppercase`
        # on .wolves-guardian-plate-class, but the baked reveal that the other
        # videos actually use does not -- "Behemoth Titan", not "BEHEMOTH
        # TITAN". The videos are the thing being matched.
        klass = "" if ghost else (spec.get("class") or "")
        name = spec.get("name") or ""
        title = spec.get("title") or ""
        body = []

    widths = [
        _tracked_width(probe, label, f_label, LS_LABEL),
        _tracked_width(probe, klass, f_class, LS_CLASS),
        probe.textlength(name, font=f_name),
        _tracked_width(probe, title, f_title, LS_TITLE),
        *(probe.textlength(line, font=f_class) for line in body),
        CREST * scale * 3,  # the header never collapses below crest + two rules
    ]
    # The CSS caps the plate at 44rem and lets the browser wrap; nothing here
    # wraps, so the box sizes to its longest line instead of clipping it.
    inner = max(widths)
    box_w = int(round(inner + 2 * PAD_X * scale))

    gap = 0.35 * REM * scale
    crest_h = CREST * scale
    stack = [(label, f_label), (klass, f_class), (name, f_name), (title, f_title)]
    stack += [(line, f_class) for line in body]
    text_h = sum(f.size * 1.25 + gap for text, f in stack if text)
    box_h = int(round(PAD_TOP * scale + crest_h + gap + text_h + PAD_BOTTOM * scale))

    img = _chamfered((box_w, box_h), INK, variant["border"])

    # Text goes on its own layer so one text-shadow can sit under all of it,
    # matching CSS (the shadow applies to type, not to the crest or the rules).
    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    # Header: rule, crest, rule. A wreath's canvas is wider than the crest,
    # so the rules shorten around it -- the box and every row stay put.
    y = PAD_TOP * scale
    cx = box_w / 2
    crest_w = crest_h * (WREATH_SPAN if wreath else 1)
    rule_w = (inner - crest_w - 2 * gap) / 2
    rule_y = int(y + crest_h / 2 - 1)
    if rule_w > 8:
        img.alpha_composite(_horizon(rule_w, 2, variant["accent"]),
                            (int(PAD_X * scale), rule_y))
        img.alpha_composite(_horizon(rule_w, 2, variant["accent"], to_left=True),
                            (int(box_w - PAD_X * scale - rule_w), rule_y))
    img.alpha_composite(
        _crest(crest_h, variant["accent"], avatar=avatar,
               mark=mark),
        (int(cx - crest_h / 2), int(y)))
    if wreath:
        laurel = _wreath(crest_w, variant["accent"])
        img.alpha_composite(laurel, (int(cx - laurel.width / 2),
                                     int(y + crest_h / 2 - laurel.height / 2)))
    y += crest_h + gap

    for text, font, colour, tracking in (
        (label, f_label, variant["label"], LS_LABEL),
        (klass, f_class, variant["klass"], LS_CLASS),
    ):
        if not text:
            continue
        w = _tracked_width(draw, text, font, tracking)
        _draw_tracked(draw, (cx - w / 2, y), text, font, colour, tracking)
        y += font.size * 1.25 + gap

    if name:
        w = int(math.ceil(draw.textlength(name, font=f_name)))
        layer = _gradient_text((w + 4, int(f_name.size * 1.4)), name, f_name,
                               [(0.0, (255, 255, 255, 255)),
                                (0.6, NAME_MID),
                                (1.0, NAME_BOTTOM)])
        text_layer.alpha_composite(layer, (int(cx - w / 2), int(y)))
        y += f_name.size * 1.25 + gap

    if title:
        w = _tracked_width(draw, title, f_title, LS_TITLE)
        _draw_tracked(draw, (cx - w / 2, y), title, f_title, variant["title"],
                      LS_TITLE)
        y += f_title.size * 1.25 + gap

    # The title card's body copy: one authored line per row.
    for line in body:
        w = draw.textlength(line, font=f_class)
        draw.text((cx - w / 2, y), line, font=f_class, fill=variant["klass"])
        y += f_class.size * 1.25 + gap

    img.alpha_composite(_with_text_shadow(text_layer))
    return img


def place(plate, position="left", picture=None, x=None, scale=1.0, raised=False):
    """Composite a plate onto a full 1920x1080 transparent frame.

    ``picture`` is the real image area ``(x, y, w, h)`` inside the frame. The
    row margins are measured against *it*, not the frame, so on a letterboxed
    2.39:1 cinematic the plate sits on the picture instead of hanging onto the
    black bar. Defaults to the whole frame.

    ``position: "group"`` is the reference deck's roll call: the card carries
    an absolute ``x`` measured from the *picture's* left edge (never the raw
    frame's, so it cannot drift onto a letterbox bar) and a ``scale`` that
    shrinks the rendered card, the same lever ``render_plate``'s ghost scale
    pulls. A group plate without an ``x`` is a bug, not a default.
    """
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    if scale != 1.0:
        plate = plate.resize((max(1, int(round(plate.width * scale))),
                              max(1, int(round(plate.height * scale)))),
                             Image.LANCZOS)
    px, py, pw, ph = picture or (0, 0, FRAME_W, FRAME_H)
    y = py + int(ph * (1 - MARGIN_BOTTOM)) - plate.height
    if raised:
        # .wolves-guardian-plate-raised { bottom: auto; top: 28% } -- for a
        # Guardian who towers above the frame's lower third.
        y = py + int(ph * RAISED_TOP)
    if position == "top-right":
        # Title-card sign in the picture's top-right safe area. Measure both
        # edges against the picture so letterboxed footage keeps the card on
        # the image rather than on a matte.
        x = px + int(pw * (1 - MARGIN_X)) - plate.width
        y = py + int(ph * MARGIN_X)
        frame.alpha_composite(plate, (x, y))
        return frame
    if position == "caption":
        # Top-safe rail, horizontally centred on the picture.
        x = px + (pw - plate.width) // 2
        y = py + int(ph * CAPTION_TOP)
        frame.alpha_composite(plate, (x, y))
        return frame
    if position == "context":
        # Lower-left stack, above the Guardian-plaque lane.
        x = px + int(pw * MARGIN_X)
        y = py + int(ph * CONTEXT_TOP)
        frame.alpha_composite(plate, (x, y))
        return frame
    if position == "warning":
        frame.alpha_composite(plate, (0, 0))
        return frame
    if position == "slide":
        # A card with NO PICTURE BEHIND IT -- a slide in a deck that plays
        # between acts. Every other placement here measures a row against the
        # frame the plate sits over, which is right when there is one: a
        # lower third belongs in the lower third. On black there is nothing
        # to sit under, and the same measurement reads as a card that missed
        # its mark, so a slide is centred on both axes instead.
        #
        # It is NOT `center`, and the distinction cost a delivered act. This
        # branch first shipped as `center`, which silently shadowed the
        # `center` fallthrough at the bottom of this function -- a lane that
        # centres a card horizontally and leaves it in the lower third, and
        # the lane every act III dialogue pill has always been emitted in.
        # Adding a slide moved a whole two-hander conversation into the dead
        # middle of the picture, over the faces. An early return that reuses
        # a live position name is not a new placement, it is a hijack of the
        # old one.
        frame.alpha_composite(plate, ((FRAME_W - plate.width) // 2,
                                      (FRAME_H - plate.height) // 2))
        return frame
    if position == "full":
        # A FULL-FRAME card: the pause menu draws its own scrim over the whole
        # picture, so it is composited at the origin rather than measured into
        # a row. It is the only position that ignores `picture` -- a menu that
        # respects a letterbox is a menu with black bars through it.
        frame.alpha_composite(plate, (0, 0))
        return frame
    if position == "status":
        # .wc-intro-nameplate { top: 3rem; left: 3rem }. Measured against the
        # PICTURE, like every other placement here, so it cannot land on a
        # letterbox bar.
        frame.alpha_composite(plate, (px + int(STATUS_INSET),
                                      py + int(STATUS_INSET)))
        return frame
    if position == "status-bottom":
        # The same HUD card, at the bottom. Owner instruction for act II's
        # patch queue: "have a status thing in the bottom". It goes bottom
        # RIGHT because the dialogue pills hold the bottom left, and a status
        # card is already exempt from the one-plate-at-a-time rule -- that
        # exemption assumes the two are not in the same corner.
        frame.alpha_composite(
            plate, (px + pw - int(STATUS_INSET) - plate.width,
                    py + ph - int(STATUS_INSET) - plate.height))
        return frame
    if position == "letterbox":
        # The banner's strip is the bottom BAR of a letterboxed frame: below
        # the picture entirely, so it can hold for a whole film and never
        # share the lower third's row (issue #98: "a huge callout along the
        # bottom of the letterbox ... keep it up for the whole song"). When
        # the picture rect IS the frame -- detection probed an un-letterboxed
        # stretch, or the source mixes aspect ratios (act II's opening is
        # full-frame, the rest is not) -- it sits just off the bottom edge.
        bar_top = py + ph
        x = (FRAME_W - plate.width) // 2
        if FRAME_H - bar_top >= plate.height:
            y = bar_top + (FRAME_H - bar_top - plate.height) // 2
        else:
            y = FRAME_H - plate.height - int(0.02 * FRAME_H)
        frame.alpha_composite(plate, (x, y))
        return frame
    if position == "letterbox_top":
        # Hashtag banners and CTAs ride the TOP bar of a letterboxed frame:
        # above the picture entirely, never on the content. Owner,
        # 2026-08-20: "upstream first and other banners and CTAs with
        # #hashtags should be in the letterbox area up top, not on the
        # content." When the picture rect IS the frame -- an un-letterboxed
        # stretch, or a source that mixes aspect ratios (act II's opening is
        # full-frame, the rest is not) -- it sits just inside the top edge.
        x = (FRAME_W - plate.width) // 2
        if py >= plate.height:
            y = (py - plate.height) // 2
        else:
            y = int(0.02 * FRAME_H)
        frame.alpha_composite(plate, (x, y))
        return frame
    if position == "boss":
        # Destiny puts a named enemy's bar at the top of frame, centred.
        frame.alpha_composite(plate, (px + (pw - plate.width) // 2,
                                      py + int(ph * MINIBOSS_TOP)))
        return frame
    if position == "toast":
        # The console's own notification slot: top centre, clear of the lower
        # third and of the bottom-right HUD.
        frame.alpha_composite(plate, (px + (pw - plate.width) // 2,
                                      py + int(ph * ACHIEVEMENT_TOP)))
        return frame
    if position == "group":
        if x is None:
            raise ValueError("a group plate needs an absolute x")
        x = px + int(round(x))
    elif position == "right":
        x = px + int(pw * (1 - MARGIN_X)) - plate.width
    elif position == "center":
        x = px + (pw - plate.width) // 2
    else:
        x = px + int(pw * MARGIN_X)
    frame.alpha_composite(plate, (x, y))
    return frame


# --- Planning a cut's plates -------------------------------------------------

# A plate the viewer cannot finish reading is worse than no plate: below this
# hold the shot is skipped and the person waits for their next appearance.
MIN_HOLD = 2.2
# ...but a plate still has to be anchored to a shot the viewer can tie it to.
MIN_ANCHOR = 1.5
LEAD_IN = 0.4     # let the cut land before the plate arrives
TAIL_OUT = 0.25   # ...and clear before the next one
DEFAULT_HOLD = 5.0
# The roster card is a credit, not an end board: on a long final shot the
# remaining room can be half a minute, which reads as a stuck frame.
MAX_ROSTER_HOLD = 10.0
# A reveal reads better on the character's hero move than on the static insert
# they happen to appear in first -- Osiris's name arriving as he climbs the
# stairwell, not while the camera sits on his mask. `traversal_hero` is already
# derived (wide, stable, in motion), so the index says which shot that is.
#
# Bounded, though: a lead the audience has been watching for this long is not
# being revealed any more, they are being belatedly captioned. Past it, the
# reveal goes back to the first appearance that can hold it.
MAX_REVEAL_DEFERRAL = 30.0

# The fields schema/brief.schema.json allows in a brief plate's `copy` -- the
# reference deck's closed on-screen vocabulary, the same set a lead binding's
# `plate:` block carries. brief.py's schema validation is optional (it no-ops
# without jsonschema installed), so the planner defends the set itself: a
# field outside it is an invented row on a card that names a real person, and
# that is an error, never something to accommodate.
BRIEF_COPY_FIELDS = {"label", "class", "name", "title", "trustee", "kind",
                     "variant"}


def _tc_seconds(tc):
    """``mm:ss`` or ``HH:MM:SS`` -> seconds (the shape the brief schema pins)."""
    parts = [int(p) for p in str(tc).split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def _source_moment_on_timeline(timeline, at_sec, video_id=None):
    """A source-time moment -> (its time on the rendered cut, the shot), or
    (None, None) when the moment is not in the cut.

    A brief's `at` is in SOURCE time ("drop her nameplate right after she
    removes her helmet, 0:14"); the plate has to land on the CUT's clock, so
    the moment is mapped through the shot that carries it. A moment no
    selected shot covers -- or one the render's hold cap trimmed away --
    returns None, and the caller reports rather than relocates it: the owner
    pointed at a moment, and quietly moving their credit to a moment they did
    not choose is the same failure as inventing the copy.
    """
    for start, duration, shot in timeline:
        if video_id and shot.get("video_id") != video_id:
            continue
        s0, s1 = shot.get("start_sec"), shot.get("end_sec")
        if s0 is None or s1 is None or not (s0 <= at_sec < s1):
            continue
        if at_sec - s0 > duration:  # trimmed by the render's max_shot_sec cap
            continue
        return round(start + (at_sec - s0), 3), shot
    return None, None


def _plan_brief_plates(brief, timeline, total, hold, leads, busy, log):
    """A brief's `plates[]` -> fixed manifest entries, before anything derived.

    Returns ``(entries, plated_characters, reveal_copy)``: the fixed plates,
    the characters they already credit (so the reveal pass does not plate them
    again), and copy to hand the reveal pass for a character whose binding has
    no `plate:` block of its own.

    The owner authored these, so they pin the timeline: each entry with an
    `at` takes its window first and everything derived routes around it. Three
    rules keep that safe:

    * **Copy is closed.** A field outside BRIEF_COPY_FIELDS is refused.
    * **The vocab wins a conflict.** When the character's binding in
      vocab/casting.yaml already has a `plate:` block, that copy is used and
      the brief's copy is reported as deferred -- the vocab is the project's
      durable record of claims about real people, changed by reviewed PR,
      while a brief is one video's request in an editable issue body. Letting
      a brief override it would let two videos disagree about a person's
      credit, which is the drift the vocab exists to prevent. A brief that
      disagrees with the record is a signal the record needs an edit, so the
      conflict is logged rather than adjudicated silently.
    * **The owner's `at` is honoured, not re-derived.** The moment is mapped
      from source time onto the cut; when it is not in the cut (or lands on a
      shot the character's constraints exclude) that is reported, and a plate
      naming a character falls back to the derived reveal rather than
      vanishing.

    Every entry carries `copy_source` -- "brief" or "casting" -- so a reader
    of the manifest can tell owner-authored copy from the vocab's.
    """
    entries, plated, reveal_copy = [], set(), {}

    def note(msg):
        if log:
            log(msg)

    requested = {}  # character -> placed fixed?
    for index, req in enumerate(brief.get("plates") or [], start=1):
        copy = dict(req.get("copy") or {})
        extra = sorted(set(copy) - BRIEF_COPY_FIELDS)
        if extra:
            raise ValueError(
                f"brief plate #{index} has copy field(s) outside the "
                f"reference deck's closed set: {', '.join(extra)}. The deck "
                "has no row for them, and inventing one puts unauthored text "
                "on a card that names a real person -- see "
                "docs/skills/plates/SKILL.md."
            )
        character = req.get("character")
        if not character and not copy:
            note(f"  brief plate #{index}: no character and no copy -- "
                 f"direction, not a plate ({(req.get('note') or '').strip()}); "
                 "nothing to plan. An ensemble credit at a moment is a beat "
                 "with `ensemble: true`, not a plate.")
            continue

        binding = (leads.get(character) or {}) if character else {}
        binding_copy = binding.get("plate")
        if binding_copy:
            if copy and copy != binding_copy:
                note(f"  {character:<10} brief copy differs from the binding's "
                     "plate: block -- the vocab's copy wins (it is the durable "
                     "record; edit vocab/casting.yaml if the brief is right)")
            use, provenance = binding_copy, "casting"
        else:
            use, provenance = copy, "brief"
        if character:
            requested.setdefault(character, False)

        at_tc = req.get("at")
        placed = False
        if at_tc and use:
            t, shot = _source_moment_on_timeline(timeline, _tc_seconds(at_tc),
                                                 req.get("video_id"))
            if (t is not None and character
                    and (shot.get("casting") or {}).get("character") == character
                    and not (shot.get("casting") or {}).get("usable", True)):
                note(f"  {character:<10} the owner's moment {at_tc} lands on a "
                     "shot the binding's constraints exclude -- not a reveal; "
                     "falling back to the derived one")
                t = None
            if t is None:
                note(f"  {character or copy.get('name', index):<10} the owner's "
                     f"moment {at_tc} is not in this cut -- reported, not moved")
            else:
                dur = round(min(hold, total - t), 3)
                if dur < MIN_HOLD:
                    note(f"  {character or copy.get('name', index):<10} the "
                         f"owner's moment {at_tc} leaves {dur:.1f}s -- less "
                         "than a readable hold; honouring it anyway, it is "
                         "their call")
                if character:
                    plate_id = character
                    if plate_id in plated:
                        plate_id = f"{character}_2"  # "again here" -- the owner
                else:                                # may repeat a plate
                    from tools.derive import snake_case
                    plate_id = snake_case(copy.get("name") or "") or f"brief_{index}"
                    while plate_id in plated:
                        plate_id += "_2"
                entries.append({"id": plate_id, "at": t, "dur": dur,
                                "position": "left", "copy_source": provenance,
                                **use})
                busy.append((t, t + dur))
                plated.add(plate_id)
                if character:
                    requested[character] = True
                placed = True
                if log:
                    whose = ("owner-authored" if provenance == "brief"
                             else "the binding's")
                    log(f"  {plate_id:<10} {t:6.2f}s +{dur:.1f}s  "
                        f"{use.get('name')} (brief plate, {whose} copy, at "
                        f"the owner's moment {at_tc})")
        if placed:
            continue
        if character and not binding_copy and copy:
            reveal_copy[character] = copy  # the reveal pass plates them with it

    # A character the owner asked to plate who never (usably) appears is
    # reported, never dropped: the brief asked for them by name. A character
    # whose fixed placement failed above is NOT reported again here -- their
    # reveal falls back to the derived path, which is about to run.
    in_cut = {(s.get("casting") or {}).get("character")
              for _, _, s in timeline
              if (s.get("casting") or {}).get("role") == "lead"
              and (s.get("casting") or {}).get("usable", True)}
    for character, was_placed in requested.items():
        if not was_placed and character not in in_cut:
            note(f"  {character:<10} the brief asks to plate them, but they "
                 "are not in this cut -- reported, not dropped")
    return entries, plated, reveal_copy


def _brief_ensemble_beats(brief, timeline, log):
    """A brief's ensemble direction -> fixed moments on the cut.

    ``beats[].ensemble`` is the owner asking for a contributor credit at a
    particular moment -- "4:03 put a bluefin maintainer in here". It requests a
    SLOT, not a person: who fills it is the month's rotation in
    tools/ensemble.py, and the note stays direction rather than becoming plate
    copy. That is the whole reason this is safe to execute -- an ensemble
    credit says "one of the anonymous Guardians in this film", which is true
    wherever it lands, while naming who is in a frame would be a casting
    decision the brief does not get to make.

    Returns ``[(timeline_seconds, note, shot)]`` for the moments that can take
    a pin, earliest first. A moment outside the cut is reported and dropped,
    the same way a lead plate's is: the direction is about a frame this cut
    does not contain. So is a moment inside a shot with no ensemble role: the
    round-robin and the re-home pass both require ``casting.role ==
    "ensemble"``, and a pin may not anchor a credit anywhere they could not.
    """
    out = []
    for index, beat in enumerate(brief.get("beats") or [], start=1):
        if not beat.get("ensemble"):
            continue
        note = (beat.get("note") or "").strip()
        at_tc = beat.get("at")
        if not at_tc:
            if log:
                log(f"  brief beat #{index}: asks for an ensemble credit but "
                    f"carries no `at` -- nothing to pin it to ({note})")
            continue
        t, shot = _source_moment_on_timeline(timeline, _tc_seconds(at_tc),
                                             beat.get("video_id"))
        if t is None:
            if log:
                log(f"  {'ensemble':<10} the owner's moment {at_tc} is not in "
                    f"this cut -- reported, not moved ({note})")
            continue
        if (shot.get("casting") or {}).get("role") != "ensemble":
            if log:
                log(f"  {'ensemble':<10} the owner's moment {at_tc} lands on "
                    "a shot with no ensemble role -- an ensemble credit "
                    f"cannot anchor there; reported, not moved ({note})")
            continue
        out.append((t, note, shot))
    return sorted(out)

# Why a lead who made the cut carries no plate. A credit that disappears without
# a word is how a real person goes uncredited, so an unplated lead is REPORTED,
# never dropped -- and reporting is all it does, because the two copy-shaped
# reasons are owner decisions that no derivation can make.
UNPLATED = {
    "uncast": {
        "reason": "uncast",
        "detail": "no person is bound to this character in vocab/casting.yaml",
        "automatable": False,
        "blocked_on": "an owner casting decision (leads.<character>.person)",
    },
    "no_plate_copy": {
        "reason": "no_plate_copy",
        "detail": "the binding carries no `plate:` copy, and plate copy is never invented",
        "automatable": False,
        "blocked_on": "owner-authored plate copy (leads.<character>.plate)",
    },
    "no_window": {
        "reason": "no_window",
        "detail": "no appearance in the cut was long enough, or free, to hold a plate",
        "automatable": True,
        "blocked_on": None,
    },
}

# Not an unplated reason: the person IS credited. What could not be honoured is
# the moment, and only the owner can choose between the earlier reveal, a
# longer cut, and footage nobody has indexed yet.
REVEAL_FLOOR_MISSED = {
    "reason": "reveal_floor_missed",
    "detail": ("the cut holds no appearance of this character at or after the "
               "requested reveal point, so the reveal was placed on their "
               "latest appearance instead -- never on a shot they are not in"),
    "automatable": False,
    "blocked_on": ("an owner decision: accept the earlier reveal, or index "
                   "footage of them past the requested point"),
}


def cut_timeline(shots, max_shot_sec=None):
    """Cut list -> [(start_on_timeline, duration, shot)] on the rendered cut.

    Mirrors what render.py actually produced, including its hold cap, so plate
    timings land on the finished file rather than on the source timeline.
    """
    out, t = [], 0.0
    for shot in shots:
        duration = shot.get("duration") or (shot["end_sec"] - shot["start_sec"])
        if max_shot_sec:
            duration = min(duration, float(max_shot_sec))
        out.append((t, duration, shot))
        t += duration
    return out


def _window(start, duration, hold=DEFAULT_HOLD, room=None):
    """A readable plate window anchored to a shot.

    The plate is *anchored* to the shot that reveals the subject, but it is not
    confined to it: a lower third routinely rides across a cut, and Destiny
    cinematics are full of two-second shots that could otherwise never carry a
    reveal. What must hold is that the shot is long enough to register as the
    anchor, and that the plate has room to be read before the cut ends.
    """
    if duration < MIN_ANCHOR:
        return None
    room = duration if room is None else room
    usable = room - LEAD_IN - TAIL_OUT
    if usable < MIN_HOLD:
        return None
    return round(start + LEAD_IN, 3), round(min(hold, usable), 3)


def _first_free_window(start, duration, hold, total, busy, cursor=None):
    """First readable window inside a shot that nothing else has taken.

    Walks forward from the shot's head: if dialogue or an earlier plate holds
    it, the next candidate starts as soon as the *blocking* window clears --
    not a whole plate-length later, which used to step straight over the gap it
    was looking for. Leads, ensemble slots and re-homed contributors all share
    this, so "the head of the shot is busy" never means "not credited at all".
    """
    cursor = start if cursor is None else cursor
    while True:
        candidate = _window(cursor, duration - (cursor - start), hold,
                            room=total - cursor)
        if not candidate:
            return None
        at, dur = candidate
        blockers = [b_end for b_start, b_end in busy
                    if at < b_end and at + dur > b_start]
        if not blockers:
            return candidate
        cursor = max(blockers) + TAIL_OUT


def _ensemble_entry(item, at, dur, copy):
    """One contributor's credit plate.

    The eyebrow distinguishes a maintainer from a passing contributor, because
    a credit that flattens the two says something untrue about a real person.
    Which one applies comes from the roster's ``org_member``; the words come
    from vocab/casting.yaml, never from here.

    A contributor whose Guardian identity is genuinely authored -- recorded
    under ``ensemble.titles`` in vocab/casting.yaml, straight from the
    reference deck -- gets that plate verbatim instead of the generic copy.
    """
    from tools.derive import ensemble_label, load_ensemble_titles

    authored = load_ensemble_titles().get(item["login"])
    if authored:
        return {"id": f"ensemble_{item['login']}", "at": at, "dur": dur,
                "position": "right", "copy_source": "casting", **authored}
    entry = {
        "id": f"ensemble_{item['login']}", "at": at, "dur": dur,
        "position": "right", "copy_source": "casting",
        "label": ensemble_label(copy, item.get("org_member")),
        "name": item["display_name"],
    }
    if copy.get("title"):
        entry["title"] = copy["title"]
    return entry


def _ensemble_group_rows(items, start, duration, hold, total, busy, copy):
    """A shot's ensemble slots as staggered rows of credits across the frame.

    The reference deck's roll call (~/Videos/nameplates.json gp_*) is staggered
    twice: spatially, each card gets an absolute ``x``; temporally, entrances
    cascade GROUP_STAGGER apart and every card in the row ends together. ``x``
    here is an EVEN SPREAD across the frame width, never a pointer at a body:
    the casting model says the anonymous crowd is fillable by anyone, so a
    plate that appears to single out a specific Guardian overclaims it. Each
    row is centred on the frame -- ``place()`` anchors that ``x`` to the
    picture's left edge, and Bungie's letterboxed cinematics are full-width, so
    the two coincide.

    The layout is computed from the actual rendered card widths (``render`` is
    deterministic, so what ``plan`` measures is what ``burn`` draws): a row
    starts at GROUP_SCALE and shrinks until it fits inside the row margins.
    When one row of all the shot's slots would have to shrink past
    GROUP_MIN_SCALE, the slots split into the fewest balanced rows that each
    fit (six cards is still one row; an unusually wide mix may go 3+3). Rows
    after the first take the next free window, and a row whose last,
    latest-arriving card could not be read stops the cascade -- anything
    unplaced is returned for the caller's sequential fallback, so nobody is
    dropped over a layout.
    """
    n = len(items)
    if n < 2:
        return [], items
    cards = [_ensemble_entry(item, 0.0, 0.0, copy) for item in items]
    widths = [render_plate(card).width for card in cards]
    usable_w = FRAME_W * (1 - 2 * GROUP_MARGIN_X)

    def chunk_scale(i, j):
        """The scale a row of cards ``i..j`` needs to fit the row margins."""
        k = j - i
        fit = (usable_w - (k - 1) * GROUP_GAP) / sum(widths[i:j])
        return math.floor(min(GROUP_SCALE, fit) * 100) / 100  # never wider than fits

    def balanced_chunks(r):
        """``r`` contiguous rows, sizes differing by at most one card."""
        base, extra = divmod(n, r)
        spans, i = [], 0
        for row_i in range(r):
            j = i + base + (1 if row_i < extra else 0)
            spans.append((i, j))
            i = j
        return spans

    layout = None
    for r in range(1, n):
        spans = balanced_chunks(r)
        scales = [chunk_scale(i, j) for i, j in spans]
        if all(s >= GROUP_MIN_SCALE for s in scales):
            layout = list(zip(spans, scales))
            break
    if layout is None:
        return [], items

    entries, cursor = [], start
    for row_i, ((i, j), scale) in enumerate(layout):
        stagger = (j - i - 1) * GROUP_STAGGER
        window = _first_free_window(start, duration, hold + stagger, total,
                                    busy, cursor)
        if not window or window[1] - stagger < MIN_HOLD:
            break  # the last card in would arrive too late to be read
        at, dur = window
        end = round(at + dur, 3)
        scaled = [int(round(w * scale)) for w in widths[i:j]]
        row_w = sum(scaled) + (j - i - 1) * GROUP_GAP
        x = (FRAME_W - row_w) / 2
        row_id = f"ensemble_row:{items[i]['segment_id']}:{row_i}"
        for k, (card, w) in enumerate(zip(cards[i:j], scaled)):
            card_at = round(at + k * GROUP_STAGGER, 3)
            card.update({"at": card_at, "dur": round(end - card_at, 3),
                         "position": "group", "group": row_id,
                         "x": int(round(x)), "scale": scale})
            x += w + GROUP_GAP
        entries.extend(cards[i:j])
        busy.append((at, end))
        cursor = end + TAIL_OUT
    return entries, items[len(entries):]


def plan(shots, leads, roster=None, max_shot_sec=None, hold=DEFAULT_HOLD, log=None,
         busy=None, only="all", soft_busy=None, brief=None,
         placeholders=0, placeholder_copy=None, unresolved=None,
         reveal_after=None):
    """Cut list -> plate manifest.

    Leads are plated on their first appearance long enough to read, using the
    `plate:` copy in vocab/casting.yaml. Ensemble contributors are plated from
    the deterministic assignment in tools/ensemble.py; anyone whose assigned
    shot is too short to hold a plate is credited over the final shot instead,
    so the month's contributors are never silently dropped.

    ``brief`` is a parsed brief (tools/brief.py) whose ``plates[]`` are
    planned FIRST, as fixed owner-authored credits -- see
    ``_plan_brief_plates`` for the precedence and timing rules. They are part
    of THIS pass, not a post-hoc `merge` step, for two reasons: a brief's
    `at` is in source time and only the shot list here can map it onto the
    cut's clock, and a brief plate that names a character IS that character's
    one plate -- planned anywhere else it would double-plate the reveal or die
    on merge's overlap check. Brief plates are lead-tier: with
    ``only="ensemble"`` they are expected to arrive via ``busy`` (the
    ``--around`` manifest), the same way dialogue does.

    A brief's ``beats[].ensemble`` direction is the ensemble-tier equivalent --
    "put a bluefin maintainer in here" -- and is planned in the ensemble pass,
    so it is honoured under ``only="ensemble"`` too. See
    ``_brief_ensemble_beats``.

    Every entry carries ``copy_source`` -- "brief" for owner-authored copy,
    "casting" for vocab/casting.yaml -- so the manifest says where each claim
    about a real person came from.

    ``busy`` seeds the occupied windows with something already fixed on the
    timeline. ``soft_busy`` is a *preference*: windows a plate should avoid if
    it can (in practice a dialogue pre-pass), but which it may take rather than
    not being placed at all. A reveal that yields until it disappears is worse
    than a reveal that costs one line -- so the preference is tried first for
    every shot, and only then the fallback.

    ``only`` (``leads`` / ``ensemble`` / ``all``) runs one tier at a time,
    which is what lets a scored cut be planned in priority order: the lead
    reveals are placed first because they are the credit the whole index exists
    to get right, the dialogue is fitted around them, and the ensemble then
    takes what is left.

    A reveal also prefers the character's first ``traversal_hero`` beat over
    their literal first appearance -- see ``MAX_REVEAL_DEFERRAL``.

    ``reveal_after`` is a floor on the CUT's clock -- "do not reveal him until
    1:50" -- and it outranks that preference: no lead reveal is placed before
    it. It is deliberately not a brief ``plates[].at``, which pins ONE credit
    to one moment in SOURCE time; this holds EVERY derived lead reveal until a
    point on the finished video, which is the clock an owner watching the cut
    is reading off. Brief plates are owner-authored fixed points and are not
    moved by it. When no appearance of a character lies at or after the floor,
    the reveal degrades to their latest appearance and the shortfall is
    reported (``REVEAL_FLOOR_MISSED``) -- the floor never buys itself a plate
    on a shot the character is not in.

    ``placeholders`` plates that many ensemble shots with the UNCAST blueberry
    copy from vocab/casting.yaml instead — for a cut being timed and reviewed
    before a roster exists. It is mutually exclusive with ``roster``: once real
    contributors are known, they are who the plate is for.

    Anyone the cut could not credit gets the same treatment: pass a list as
    ``unresolved`` and it is appended a punch-list entry saying who went
    unplated and why (see ``UNPLATED``) -- a lead, and also a contributor whom
    even the tail roster card had no room for. Nothing blocks -- an uncast
    character and a binding with no plate copy are both owner decisions, so the
    manifest is written either way and the punch-list is what asks for the
    decision. An empty ``unresolved`` therefore means exactly what it says:
    nobody on screen went uncredited. A shot that fails its binding's
    constraints is not an appearance at all: it is already excluded from that
    character's retrieval, so it is not a reveal.
    """
    if roster and placeholders:
        raise ValueError("pass a roster or placeholders, not both: a cut with a "
                         "roster credits real contributors, not placeholders")
    timeline = cut_timeline(shots, max_shot_sec)
    total = sum(duration for _, duration, _ in timeline)
    entries, plated = [], set()
    busy = list(busy or [])  # occupied windows, so nothing double-books the screen
    soft_busy = list(soft_busy or [])

    # The brief's owner-authored plates take their windows first; everything
    # derived routes around them.
    brief_reveal_copy = {}
    if brief and only != "ensemble":
        brief_entries, brief_plated, brief_reveal_copy = _plan_brief_plates(
            brief, timeline, total, hold, leads, busy, log)
        entries.extend(brief_entries)
        plated |= brief_plated

    unplated = {}  # character -> UNPLATED key, in first-appearance order

    def free(start, duration):
        end = start + duration
        return all(end <= b_start or start >= b_end for b_start, b_end in busy)

    def first_appearance():
        """Timeline start of each character's first plateable shot."""
        first = {}
        for start, duration, shot in timeline:
            casting = shot.get("casting") or {}
            character = casting.get("character")
            if (casting.get("role") == "lead" and character
                    and casting.get("usable", True)
                    and character not in first):
                first[character] = start
        return first

    debut = first_appearance()

    def place_leads(avoid, hero_only=False, floor=None, latest=False):
        for start, duration, shot in (reversed(timeline) if latest else timeline):
            casting = shot.get("casting") or {}
            character = casting.get("character")
            if casting.get("role") != "lead" or not character or character in plated:
                continue
            if not casting.get("usable", True):
                continue  # a shot failing its binding's constraints is no reveal
            if hero_only:
                # Hold the reveal for the character's hero move -- but only if
                # it lands close enough to their debut to still read as an
                # introduction rather than a late caption. An owner-set floor
                # has already overridden that judgement, so it does not apply.
                if not shot.get("traversal_hero"):
                    continue
                if (floor is None
                        and start - debut.get(character, start) > MAX_REVEAL_DEFERRAL):
                    continue
            # The reportable reasons, in order: nobody cast, no copy to plate,
            # no window to plate it in. The first two are owner decisions; the
            # third a re-plan can fix. The hero filter above is none of these --
            # it defers to a later pass, it does not report.
            binding = leads.get(character) or {}
            if not binding.get("person"):
                unplated[character] = "uncast"
                continue
            copy = binding.get("plate")
            provenance = "casting"
            if not copy:
                copy = brief_reveal_copy.get(character)
                provenance = "brief" if copy else provenance
            if not copy:
                unplated[character] = "no_plate_copy"
                continue
            # Walk forward through the shot: if dialogue (or an earlier plate)
            # holds its head, the reveal waits for the next opening inside its
            # own anchor rather than being lost for the whole cut. A floor
            # starts that walk at the owner's moment instead of the shot's
            # head, so the plate lands at or after it while still anchored to
            # a shot the character is actually in.
            cursor = None if floor is None else max(start, floor)
            window = _first_free_window(start, duration, hold, total, avoid,
                                        cursor=cursor)
            if not window:
                unplated.setdefault(character, "no_window")
                continue
            at, dur = window
            entries.append({"id": character, "at": at, "dur": dur,
                            "position": "left", "copy_source": provenance,
                            **copy})
            busy.append((at, at + dur))
            plated.add(character)
            unplated.pop(character, None)  # a later appearance carried it after all
            if log:
                notes = "".join([
                    " (on the hero move)" if hero_only else "",
                    " (clear of dialogue)" if avoid is not busy else "",
                    " (held for the reveal point)" if floor is not None else "",
                    " (latest appearance)" if latest else "",
                ])
                log(f"  {character:<10} {at:6.2f}s +{dur:.1f}s  "
                    f"{copy.get('name')}{notes}")

    if only != "ensemble":
        # Preference order, most wanted first. A reveal that yields until it
        # disappears is worse than one that costs a line of dialogue, so every
        # preference is tried across the whole timeline before its fallback.
        for hero_only in (True, False):
            if soft_busy:
                place_leads(busy + soft_busy, hero_only=hero_only,
                            floor=reveal_after)
            place_leads(busy, hero_only=hero_only, floor=reveal_after)

    if reveal_after is not None and only != "ensemble":
        # The floor is a request about the CUT, and the footage may simply not
        # reach it. Held back rather than credited is how a real person goes
        # uncredited, so the reveal degrades to their LATEST appearance -- the
        # closest the footage comes to the moment asked for -- and the
        # shortfall is reported. What is never done is honouring the floor by
        # plating them over a shot they are not in: that is a false claim
        # about a real person, and no timing request outranks it.
        held = set(unplated)
        if soft_busy:
            place_leads(busy + soft_busy, latest=True)
        place_leads(busy, latest=True)
        for character in [c for c in held if c not in unplated]:
            at = next(e["at"] for e in entries if e.get("id") == character)
            binding = leads.get(character) or {}
            if unresolved is not None:
                unresolved.append({
                    "id": character,
                    "person": binding.get("person"),
                    "display_name": binding.get("display_name"),
                    "requested_reveal_after": round(reveal_after, 3),
                    "revealed_at": at,
                    **REVEAL_FLOOR_MISSED,
                })
            if log:
                log(f"  REVEAL     {character:<10} the cut has no appearance at "
                    f"or after {reveal_after:.2f}s; revealed at {at:.2f}s "
                    f"instead -- reported, not moved onto another shot")

    # Every lead the passes above could not plate is REPORTED, never dropped:
    # a credit that disappears without a word is how a real person goes
    # uncredited. (Under --only ensemble the leads pass never ran, so this
    # list is empty and the loop says nothing.)
    for character, why in unplated.items():
        binding = leads.get(character) or {}
        if unresolved is not None:
            unresolved.append({
                "id": character,
                "person": binding.get("person"),
                "display_name": binding.get("display_name"),
                **UNPLATED[why],
            })
        if log:
            log(f"  UNPLATED   {character:<10} {why}: {UNPLATED[why]['detail']}")

    if not roster or only == "leads":
        # These paths never run the ensemble pass, so a brief's pinned
        # ensemble beats cannot be honoured here. That is reported, never
        # silently dropped: the direction was the owner's.
        if brief and log:
            pins = [b for b in (brief.get("beats") or []) if b.get("ensemble")]
            if pins:
                why = ("no roster was given" if not roster
                       else "--only leads plans no ensemble tier")
                log(f"  {'ensemble':<10} the brief pins {len(pins)} ensemble "
                    f"moment(s), but {why} -- reported, not honoured")
        if placeholders:
            # No roster yet: the blueberry plates hold the ensemble's places so
            # a cut can be timed and reviewed before anybody is credited.
            entries.extend(_placeholder_entries(
                timeline, total, placeholders, placeholder_copy, hold, free, busy, log))
        return sorted(entries, key=lambda e: e["at"])

    from tools.derive import load_ensemble_plate
    from tools.ensemble import assign

    ensemble_copy = load_ensemble_plate()
    result = assign(roster, [s for _, _, s in timeline])
    by_segment = {}
    for item in result["assignments"]:
        by_segment.setdefault(item["segment_id"], []).append(item)

    credited, pending = set(), []

    # The owner's ensemble direction is a FIXED POINT: "put a bluefin
    # maintainer in here" pins one slot to one moment, and the rotation below
    # routes around it exactly as it routes around a lead reveal or a line of
    # dialogue. It is honoured before the round-robin runs, because a moment
    # the owner chose outranks a moment the assignment happened to produce --
    # and because taking its window first is what makes the rest route around
    # it at all.
    #
    # WHO fills the slot still comes from the rotation, never from the note.
    # The note is direction ("a bluefin maintainer"), and turning it into copy
    # would put words on whichever real contributor landed there.
    #
    # Fixed does not mean above the one-plate-at-a-time rule: the pin takes
    # only windows nothing earlier claimed (brief plates, lead reveals,
    # --around dialogue, earlier pins). It is shortened to fit ahead of the
    # next plate when it can be, and reported and skipped when it cannot --
    # it is never MOVED, because the owner pointed at a frame.
    if brief:
        rotation = list({item["login"]: item
                         for item in result["assignments"]}.values())
        for t, note, _ in _brief_ensemble_beats(brief, timeline, log):
            item = next((i for i in rotation if i["login"] not in credited), None)
            if item is None:
                if log:
                    log(f"  {'ensemble':<10} the owner asks for a credit at "
                        f"{t:.2f}s, but every contributor in the rotation is "
                        f"already credited -- reported, not duplicated ({note})")
                continue
            dur = round(min(hold, total - t), 3)
            if dur < MIN_HOLD:
                # A pin on the trim boundary maps to the cut's final instant
                # (dur == 0), and one near it to an unreadable flash. Neither
                # may be emitted -- validation rejects a non-positive dur, and
                # a plate below MIN_HOLD cannot be read.
                if log:
                    log(f"  {'ensemble':<10} the owner's moment {t:.2f}s "
                        f"leaves {dur:.1f}s on the cut -- no readable hold "
                        f"remains; reported, not emitted ({note})")
                continue
            # The moment is a fixed point, but the screen may already be
            # booked: an earlier pin, a brief plate, a lead reveal, or
            # dialogue via --around. The pin never MOVES -- the owner pointed
            # at this frame -- so a moment already covered is reported and
            # skipped, and a partly free window is shortened to end where the
            # next plate begins (when what remains can still be read).
            overlapping = sorted(
                (b_start, b_end) for b_start, b_end in busy
                if t < b_end and b_start < t + dur)
            if overlapping and overlapping[0][0] <= t:
                if log:
                    log(f"  {'ensemble':<10} the owner's moment {t:.2f}s is "
                        "already covered by another plate -- reported, not "
                        f"moved ({note})")
                continue
            if overlapping:
                trimmed = round(overlapping[0][0] - t, 3)
                if trimmed < MIN_HOLD:
                    if log:
                        log(f"  {'ensemble':<10} the owner's moment {t:.2f}s "
                            f"has only {trimmed:.1f}s before the next plate "
                            f"-- reported, not moved ({note})")
                    continue
                if log:
                    log(f"  {'ensemble':<10} the owner's moment {t:.2f}s "
                        f"holds {dur:.1f}s, shortened to {trimmed:.1f}s ahead "
                        f"of the next plate ({note})")
                dur = trimmed
            entries.append(_ensemble_entry(item, t, dur, ensemble_copy))
            busy.append((t, t + dur))
            credited.add(item["login"])
            if log:
                log(f"  {'ensemble':<10} {t:6.2f}s +{dur:.1f}s  "
                    f"{item['display_name']} (the owner's moment: {note})")

    for start, duration, shot in timeline:
        items = [item for item in by_segment.get(shot.get("segment_id"), [])
                 if item["login"] not in credited]
        # One credit per person per shot: a pool smaller than the slot count
        # assigns the same login twice, and a row cannot name someone twice.
        items = list({item["login"]: item for item in items}.values())
        if not items:
            continue
        # A shot with several ensemble slots credits them as staggered rows
        # spread across the frame -- the reference deck's roll call -- instead
        # of a queue of right-hand plates arriving one at a time in the same
        # corner. Each row shares one busy window, so the rest of the cut
        # still sees one plate at a time outside the row.
        row, leftover = _ensemble_group_rows(items, start, duration, hold,
                                             total, busy, ensemble_copy)
        if row:
            entries.extend(row)
            for item in items[:len(row)]:
                credited.add(item["login"])
            if log:
                for card, item in zip(row, items):
                    log(f"  {'ensemble':<10} {card['at']:6.2f}s +{card['dur']:.1f}s  "
                        f"{item['display_name']} (group row x={card['x']})")
        # Single slot, or a row that cannot fit/readably stagger: the plates
        # ride across the cut one after another instead, so a six-Guardian
        # firefight can still name six contributors rather than burning five of
        # them onto the roster card for want of a start time.
        cursor = start
        for item in leftover:
            window = _first_free_window(start, duration, hold, total, busy, cursor)
            if not window:
                pending.append(item)
                continue
            at, dur = window
            cursor = at + dur + TAIL_OUT
            entries.append(_ensemble_entry(item, at, dur, ensemble_copy))
            busy.append((at, at + dur))
            credited.add(item["login"])
            if log:
                log(f"  {'ensemble':<10} {at:6.2f}s +{dur:.1f}s  {item['display_name']}")

    # Second pass: anyone their own shot could not hold is re-homed onto another
    # ensemble shot that still has room. An ensemble credit is not a claim about
    # a particular body in a particular frame the way a lead binding is -- the
    # slot formula says the crowd is fillable, and vocab/casting.yaml assigns it
    # programmatically -- so "one of the anonymous Guardians in this film" stays
    # true wherever the plate lands. It is still a real credit, and a named
    # contributor reads better than a line on a roster card.
    #
    # Whoever the body of the cut still could not hold is credited together on
    # one roster plate over the tail, in rotation order. The month's
    # contributors are the ensemble; dropping them silently would be the one
    # unacceptable outcome -- so when even the tail has no room, every name the
    # cut could not credit goes on the punch-list, not just into a log line.
    pending = [item for item in pending if item["login"] not in credited]
    still_pending = []
    for item in pending:
        placed = False
        for start, duration, shot in timeline:
            if (shot.get("casting") or {}).get("role") != "ensemble":
                continue
            window = _first_free_window(start, duration, hold, total, busy)
            if not window:
                continue
            at, dur = window
            entries.append(_ensemble_entry(item, at, dur, ensemble_copy))
            busy.append((at, at + dur))
            credited.add(item["login"])
            placed = True
            if log:
                log(f"  {'ensemble':<10} {at:6.2f}s +{dur:.1f}s  "
                    f"{item['display_name']} (re-homed)")
            break
        if not placed:
            still_pending.append(item)

    # The sign-off card over the tail. It has two jobs, and they are separable:
    #
    #   1. It is the cut's LAST BEAT -- the card's headline (roster_title in
    #      vocab/casting.yaml) is how the video says goodbye, so it plays
    #      whether or not anyone is left to credit. Gating it on leftovers
    #      meant that crediting everyone in the body silently deleted the
    #      ending.
    #   2. Its `body` credits whoever the body of the cut could not hold, in
    #      rotation order. That list may be empty; the card still plays.
    #
    # Dropping a contributor silently remains the one unacceptable outcome.
    pending = [item for item in still_pending if item["login"] not in credited]
    if timeline:
        tail_start, tail_dur, _ = timeline[-1]
        cursor = max([tail_start + LEAD_IN] + [b_end + TAIL_OUT for b_start, b_end in busy
                                               if b_end > tail_start])
        # A contributor whose Guardian identity is authored (ensemble.titles in
        # vocab/casting.yaml) is never reduced to a name line on the card while
        # the cut still has room for the real plate: they get first claim on
        # the tail the card was about to occupy -- but not at the price of
        # pushing anyone else off the card, since dropping a contributor is the
        # one unacceptable outcome. When the tail cannot hold both, the card
        # credits everyone and the authored plate waits for a cut with room.
        from tools.derive import load_ensemble_titles
        titled = load_ensemble_titles()

        def card_waiting(extra_credited=()):
            seen, waiting = set(), []
            for item in pending:
                if (item["login"] not in seen and item["login"] not in credited
                        and item["login"] not in extra_credited):
                    seen.add(item["login"])
                    waiting.append(item)
            return waiting

        def card_names(extra_credited=()):
            return [item["display_name"] for item in card_waiting(extra_credited)]

        def tail_room(at_cursor):
            return min(tail_start + tail_dur - TAIL_OUT - at_cursor,
                       MAX_ROSTER_HOLD)

        for item in pending:
            if item["login"] in credited or item["login"] not in titled:
                continue
            window = _first_free_window(tail_start, tail_dur, hold, total, busy, cursor)
            if not window:
                continue  # no room for the real plate; the card carries them
            at, dur = window
            would_cursor = at + dur + TAIL_OUT
            rest = card_names(extra_credited={item["login"]})
            if rest and tail_room(would_cursor) < MIN_HOLD <= tail_room(cursor):
                continue  # plating them would strand the rest off the card
            cursor = would_cursor
            entries.append(_ensemble_entry(item, at, dur, ensemble_copy))
            busy.append((at, at + dur))
            credited.add(item["login"])
            if log:
                log(f"  {'ensemble':<10} {at:6.2f}s +{dur:.1f}s  "
                    f"{item['display_name']} (authored plate)")
        remaining = tail_room(cursor)
        waiting = card_waiting()
        names = [item["display_name"] for item in waiting]
        if remaining >= MIN_HOLD:
            card = {
                "id": "ensemble_roster", "at": round(cursor, 3),
                "dur": round(remaining, 3), "position": "right", "kind": "title",
                "copy_source": "casting",
                "title": ensemble_copy["roster_title"],
                "subtitle": f"Project Bluefin contributors, {result['month']}",
            }
            if names:
                card["body"] = names
            entries.append(card)
            if log:
                log(f"  {'sign-off':<10} {cursor:6.2f}s +{remaining:.1f}s  "
                    f"{', '.join(names) if names else '(everyone credited in the cut)'}")
        elif names:
            # Even the tail had no room: every name the cut could not credit
            # goes on the punch-list, not just into a log line nobody reads.
            if unresolved is not None:
                for item in waiting:
                    unresolved.append({
                        "id": f"ensemble_{item['login']}",
                        "person": item["login"],
                        "display_name": item["display_name"],
                        **UNPLATED["no_window"],
                    })
            if log:
                log(f"  UNCREDITED (no room in the cut): {', '.join(names)}")
        elif log:
            log("  NO SIGN-OFF: the tail has no room for the card")

    return sorted(entries, key=lambda e: e["at"])


def _placeholder_entries(timeline, total, wanted, copy, hold, free, busy, log=None):
    """Blueberry plates: the first ``wanted`` ensemble shots that can hold one.

    A placeholder credits nobody, so there is no assignment to be deterministic
    about — it just proves the plate lands, reads, and clears before the next
    one, on a cut whose cast is not decided yet.
    """
    if not copy:
        from tools.derive import load_placeholder_plate

        copy = load_placeholder_plate()
    if not copy:
        raise ValueError("no ensemble.placeholder_plate copy in vocab/casting.yaml")

    entries = []
    for start, duration, shot in timeline:
        if len(entries) >= wanted:
            break
        if (shot.get("casting") or {}).get("role") != "ensemble":
            continue
        window = _window(start, duration, hold, room=total - start)
        if not window or not free(*window):
            continue
        at, dur = window
        entries.append({"id": f"ensemble_placeholder_{len(entries) + 1:02d}",
                        "at": at, "dur": dur, "position": "right", **copy})
        busy.append((at, at + dur))
        if log:
            log(f"  {'placeholder':<10} {at:6.2f}s +{dur:.1f}s  {copy.get('name')}")
    if log and len(entries) < wanted:
        log(f"  only {len(entries)}/{wanted} placeholder(s) fit — the rest of the "
            f"ensemble shots are too short or already busy")
    return entries


def check_copy_against_bindings(entries, leads=None):
    """A hand-authored manifest must not silently contradict `vocab/casting.yaml`.

    `plan` already enforces this: when a brief's copy differs from a character's
    binding, the **vocab wins**, because it is the reviewed durable record and an
    issue body is editable. `plates/SKILL.md` lists "the owner wrote it today" as
    a rationalization, not an exception.

    A manifest written by hand skips `plan` entirely, so nothing was checking it
    — which is exactly how act VI's tail shipped two cards that disagree with
    their bindings (issue #111). This closes that path: a card whose `name`
    matches an authored identity must either reproduce that identity's copy or
    carry an explicit `copy_override` recording who decided otherwise.

    The override is deliberately noisy. It cannot be added by accident, it names
    the deciding issue, and it makes the divergence greppable instead of
    invisible.
    """
    if leads is None:
        from tools.derive import load_leads
        leads = load_leads()

    by_name = {}
    for character, binding in (leads or {}).items():
        copy = (binding or {}).get("plate") or {}
        if copy.get("name"):
            by_name.setdefault(copy["name"], (character, copy))

    problems = []
    for e in entries:
        name = e.get("name")
        if not name or name not in by_name:
            continue
        character, bound = by_name[name]
        differs = [f for f in ("label", "class", "title")
                   if f in e and e[f] != bound.get(f)]
        if not differs:
            continue
        override = e.get("copy_override")
        if not (isinstance(override, dict) and override.get("decided_by")):
            problems.append(
                f"plate {e['id']!r} credits {name!r} with copy that differs from "
                f"the `{character}` binding in vocab/casting.yaml ({', '.join(differs)}). "
                "The vocab wins a conflict. Either fix the manifest, edit the "
                "binding, or record the decision with a `copy_override` carrying "
                "a `decided_by` issue URL."
            )
    if problems:
        raise ValueError("\n".join(problems))
    return entries


def load_manifest(path):
    """A plate manifest, brought current with the chapter file that owns it.

    THE WORDS LIVE IN ``chapters/<act>.md``. A manifest an act has migrated is
    an output of that file, so it is synced here rather than trusted: this is
    the single place every burn reads its plates from, which makes it the
    single place a plate can be caught carrying copy the owner has already
    replaced. Rendering a card from superseded words is the "never stale"
    rule in AGENTS.md, and a render is where it would go unnoticed.

    A manifest nobody has migrated syncs nothing and reports nothing.
    """
    from tools import chapter_md
    for note in chapter_md.sync_manifest(path):
        print(f"chapter: {note}", file=sys.stderr)
    with Path(path).open(encoding="utf-8") as fh:
        entries = json.load(fh)
    if isinstance(entries, dict):
        entries = entries["plates"]
    return load_manifest_entries(entries)


def load_manifest_entries(entries):
    """Validate plate entries: unique ids, real durations, one plate at a time."""
    seen, windows = set(), []
    for e in entries:
        if e["id"] in seen:
            raise ValueError(f"duplicate plate id {e['id']!r}")
        seen.add(e["id"])
        if float(e["dur"]) <= 0:
            raise ValueError(f"plate {e['id']!r} has non-positive dur")
        start = float(e["at"])
        windows.append((start, start + float(e["dur"]), e["id"],
                        e.get("group"), e.get("kind"), e.get("bond_of")))

    # One plate at a time (authoring-interview-chat-plates): overlapping visible
    # windows are a bug, not a style choice. Three narrow exceptions:
    #
    #   * members of the same group row share a `group` key and are one row by
    #     construction -- the reference deck's roll call is *meant* to be
    #     visible together;
    #   * the status nameplate is the site's top-of-frame HUD, a different row
    #     from the lower third entirely. On the site it is persistent chrome
    #     that Guardian plates appear *underneath*, so a status card and a
    #     lower third are never in contention for the same space. Two status
    #     cards still are, and are still an error. The same holds for the two
    #     other cards that own a row of their own -- the `miniboss` bar at the
    #     top of frame and the `achievement` toast under it (`CHROME_ROWS`):
    #     each may share the screen with a lower third and with a DIFFERENT
    #     chrome row, and never with a second card of its own kind.
    #   * a `companion` card naming the Guardian it is bonded to, via
    #     `bond_of: "<that plate's id>"`. The site renders the pair as one row
    #     -- the name plate holding the left, the GUARDIAN BOND card anchored
    #     bottom-right -- so they are the same exemption as a group, but
    #     NAMED: the companion has to say whose bond it is, which means it can
    #     never quietly overlap somebody else's plate the way a shared group
    #     string could. The same named bond covers an owner-instructed
    #     pill/nameplate pair (act II's "Sup" on Kyle's locked reveal), and it
    #     keeps the deck's shape there too: left and right lanes, never two
    #     cards stacked on one.
    #
    # A group member overlapping anything outside its own row is still an
    # error, so the check is pairwise rather than the old adjacent-pair scan
    # (an exempt pair must not shield a later collider behind it).
    ordered = sorted(windows)
    # Windows that merely TOUCH are adjacent, not overlapping. Without a
    # tolerance, a back-to-back pair whose boundary is computed in floating
    # point (58.6 + 0.45 == 59.050000000000004, against a next cue at 59.05)
    # trips the check by 4e-15 of a second.
    EPS = 1e-6
    for i, (a_start, a_end, a_id, a_group, a_kind, a_bond) in enumerate(ordered):
        for b_start, b_end, b_id, b_group, b_kind, b_bond in ordered[i + 1:]:
            if b_start >= a_end - EPS:
                break
            if a_group and a_group == b_group:
                continue
            if (a_kind in CHROME_ROWS) != (b_kind in CHROME_ROWS):
                continue
            # Two chrome cards may share the screen only when they do not
            # share a row. The status HUD sits alone at the bottom; the boss
            # bar and the console toast BOTH live at the top of frame, so
            # they are held to the one-at-a-time rule against each other. The
            # letterbox banner is below the picture entirely, on the bar, so
            # it shares a row with nothing -- only a second banner collides.
            if a_kind in CHROME_ROWS and b_kind in CHROME_ROWS \
                    and a_kind != b_kind \
                    and {"status", "banner"}.intersection((a_kind, b_kind)):
                continue
            if a_bond == b_id or b_bond == a_id:
                continue
            raise ValueError(
                f"plates {a_id!r} and {b_id!r} are visible at the same time "
                f"({b_start:.2f}s < {a_end:.2f}s)"
            )
    return entries


def render_all(entries, out_dir, picture=None):
    """Render every plate in a manifest -- except the full-frame cards.

    A manifest may mix the two: the megacut's hero segment carries six Guardian
    plates and the full-frame title card. The cards come from `cards/render-cards.mjs`
    and land in the same directory under the same `plate_<id>.png` name, so
    both renderers fill one plates-dir and `burn` reads it without caring which
    tool drew which file. Skipped cards are returned so a caller can report
    them rather than assume they were drawn.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []
    for e in entries:
        if e.get("kind") in CARD_KINDS:
            skipped.append(e["id"])
            continue
        if e.get("kind") == "interstitial":
            # Owned by its own builder (scripts/build_scream_card.py); neither
            # full-frame renderer draws it, exactly like the site's cards.
            skipped.append(e["id"])
            continue
        if e.get("kind") == "logowall":
            # Owned by scripts/build_cncf_wall.py, which draws from the
            # landscape record. Same arrangement as the interstitial.
            skipped.append(e["id"])
            continue
        dest = out_dir / f"plate_{e['id']}.png"
        place(render_plate(e), e.get("position", "left"), picture,
              x=e.get("x"), scale=float(e.get("scale", 1.0)),
              raised=bool(e.get("raised"))).save(dest)
        written.append(dest)
    if skipped:
        print(f"skipped {len(skipped)} full-frame card(s) -- render them with "
              f"cards/render-cards.mjs: {', '.join(skipped)}")
    return written


def _probe_duration(path, ffmpeg=None):
    """Seconds of ``path``, for bounding the looped plate inputs.

    Uses the ffprobe beside whichever ffmpeg was resolved, so a containerized
    toolchain probes the same file it is about to read.
    """
    probe = ["ffprobe"]
    if ffmpeg and ffmpeg[-1].endswith("ffmpeg"):
        probe = [*ffmpeg[:-1], "ffprobe"]
    out = subprocess.run(
        [*probe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        raise RuntimeError(f"could not read the duration of {path}: {out.stderr}")


def _burn_units(entries):
    """One overlay unit per still, and one per ANIMATION GROUP.

    An animation group is a contiguous run of plates carrying ``animation:
    true`` and the same ``group``. They are ``plate_<group>_NN.png`` on disk,
    which is an image2 sequence, so the whole run becomes a single input at
    ``1 / step`` frames a second. Everything else is unchanged.
    """
    units, seen = [], set()
    for e in entries:
        group = e.get("group") if e.get("animation") else None
        if not group:
            units.append({"animation": False, "id": e["id"],
                          "at": float(e["at"]), "dur": float(e["dur"])})
            continue
        if group in seen:
            continue
        seen.add(group)
        frames = [x for x in entries
                  if x.get("animation") and x.get("group") == group]
        frames.sort(key=lambda x: float(x["at"]))
        start = float(frames[0]["at"])
        end = float(frames[-1]["at"]) + float(frames[-1]["dur"])
        step = (end - start) / len(frames)
        width = max(2, len(str(len(frames) - 1)))
        units.append({
            "animation": True,
            "id": group,
            "pattern": f"plate_{group}_%0{width}d.png",
            "fps": 1.0 / step if step else 1.0,
            "at": start,
            "dur": end - start,
        })
    return units


def burn(video, entries, plates_dir, out_path, ffmpeg=None, runner=None,
         encode_args=None):
    """Composite every plate onto ``video`` in one ffmpeg pass.

    Audio is stream-copied: this stage titles a cut, it does not re-cut it, and
    re-encoding audio here would be a second generation for no reason.

    ``runner`` defaults to a memory-capped local subprocess
    (``tools.farm.run_capped_local``); a caller (the farm path in
    ``scripts/build_act1.py``) may pass one that runs the same argv elsewhere
    and fetches ``out_path`` back.

    ``encode_args`` is the x264 argv for the burn. Pass
    ``conform.video_encode_args()`` to get the repo's DELIVERY rung and the
    BT.709 VUI; ``None`` keeps the legacy ``crf 18``/``medium``/untagged argv
    that acts not yet rebuilt were delivered with, so their masters stay
    byte-identical and do not go stale. See the note at the argv itself.
    """
    if ffmpeg is None:
        from tools.render import find_ffmpeg

        ffmpeg = find_ffmpeg()
    video = Path(video).resolve()
    out_path = Path(out_path).resolve()
    plates_dir = Path(plates_dir).resolve()

    # HOW LONG THE PLATES HAVE TO EXIST FOR.
    #
    # A PNG is a ONE-FRAME input. Fed to overlay as-is it reaches EOF almost
    # immediately, and while `eof_action=repeat` holds the last frame for a
    # while, it does not hold it for five minutes: a plate gated to t=5 draws
    # and the identical plate gated to t=269 does not, on the same file, with
    # the same filtergraph. That is how act II came out fully credited on paper
    # and completely unplated on screen.
    #
    # So each image input is LOOPED for the length of the video. `-loop 1`
    # alone is an infinite input and the encode never terminates; bounding it
    # with `-t` makes it finite, so the frame is available at every timestamp
    # the enable expression might name and the muxer still stops.
    #
    # `-framerate 1` is the cheap part: the looped stream is the SAME still
    # frame at every timestamp, so decoding it 30 times a second buys nothing.
    # One frame a second cut this burn from ten minutes back to about one.
    duration = _probe_duration(video, ffmpeg)

    # AN ANIMATION IS ONE INPUT, NOT ONE INPUT PER FRAME.
    #
    # Act II's choice screen is 24 plates a sixteenth of a second apart. Fed
    # to this graph as 24 more stills it took the burn from 52 inputs to 74,
    # and ffmpeg died on `Failed initializing scaling graph (Resource
    # temporarily unavailable)` -- one rgba->yuva420p scaler per input, and
    # the box ran out. It did not fail fast either: it span for thirty
    # minutes and wrote a zero-byte file.
    #
    # A contiguous run of frames is exactly what the image2 demuxer reads
    # natively, so a whole animation costs ONE input at its own frame rate.
    # `tpad` then holds transparent frames in front of it so the stream spans
    # the timeline from t=0 -- overlay's framesync wants a secondary frame to
    # pair with every primary one, and a stream that simply starts late is
    # how a graph stalls.
    units = _burn_units(entries)

    cmd = [*ffmpeg, "-nostdin", "-y", "-i", str(video)]
    for unit in units:
        if unit["animation"]:
            cmd += ["-framerate", f"{unit['fps']:.6f}", "-start_number", "0",
                    "-i", str(plates_dir / unit["pattern"])]
        else:
            cmd += ["-loop", "1", "-framerate", "1", "-t", f"{duration:.3f}",
                    "-i", str(plates_dir / f"plate_{unit['id']}.png")]

    steps, last = [], "0:v"
    for i, unit in enumerate(units, start=1):
        start = unit["at"]
        end = start + unit["dur"]
        label = f"v{i}"
        if unit["animation"]:
            steps.append(
                f"[{i}:v]tpad=start_duration={start:.3f}:start_mode=add:"
                f"color=black@0[a{i}]")
            steps.append(
                f"[{last}][a{i}]overlay=0:0:eof_action=pass:"
                f"enable=between(t\\,{start:.3f}\\,{end:.3f})[{label}]")
            last = label
            continue
        # NO SHELL QUOTES HERE, AND THE COMMAS ARE ESCAPED.
        #
        # `enable='between(t,269.7,272.9)'` is the form the ffmpeg docs show,
        # and it is correct -- on a COMMAND LINE, where the shell strips the
        # quotes. This command is built as an argv list and never sees a shell,
        # so ffmpeg received the quote characters as part of the expression,
        # failed to parse it, disabled the overlay, and exited 0. The result
        # was a video that looked finished and carried no plates at all.
        #
        # Unquoted, the commas must be escaped instead, or the filtergraph
        # parser reads them as argument separators.
        steps.append(
            f"[{last}][{i}:v]overlay=0:0:"
            f"enable=between(t\\,{start:.3f}\\,{end:.3f})[{label}]"
        )
        last = label
    if not steps:
        raise ValueError("no plates to burn")

    cmd += [
        "-filter_complex", ";".join(steps),
        "-map", f"[{last}]", "-map", "0:a?",
        # The looped plate inputs are the same length as the picture, so the
        # muxer has no unambiguous shortest stream to stop at and the output
        # runs long -- act II came out 318.767 s against a 307.998 s cut.
        # Naming the length is deterministic where `-shortest` is not.
        "-t", f"{duration:.3f}",
        # The burn is the LAST picture generation before an act is delivered,
        # so its argv decides what the standalone master's bitstream says.
        # Rolling a private one is how acts II and VI shipped with
        # color_space/transfer/primaries all `unknown`: the BT.709 VUI is
        # written by `conform.video_encode_args` and by nothing else, and
        # untagged SDR is only *assumed* 709 by a player (tools/megacut.py
        # records why "most players" is not good enough). It also encoded a
        # delivery master at crf 18/medium against the repo's own crf 16/slow
        # DELIVERY spec.
        #
        # The legacy argv is still the DEFAULT, and that is deliberate rather
        # than lazy: every act declaring tools/plate.py as a delivery source
        # goes stale the moment this changes, and an act only stops being stale
        # by being re-rendered. Flipping the default therefore forces a rebuild
        # of acts nobody asked for. Callers opt in as they are rebuilt; act II
        # is the first (issue #86's picture upgrade). See #271 to retire it.
        *(encode_args if encode_args is not None else
          ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p"]),
        "-c:a", "copy",
        str(out_path),
    ]
    print("ffmpeg:", " ".join(ffmpeg))
    # NEVER WRITE STRAIGHT AT THE MASTER -- not locally, and not through a
    # runner. `out_path` is routinely a hardlink into ~/Videos/Wolves/Prod/,
    # so opening it for writing truncates the DELIVERED act before a single
    # frame is encoded -- and an interrupted burn then leaves the film with
    # no copy anywhere. Act II was destroyed exactly that way (#286); the
    # only surviving copy was the megacut. A farm runner is the same hazard
    # one network cut closer: kubectl cp fetches INTO the path the argv
    # names, so the argv names the tmp here too, and only a completed fetch
    # replaces the master. tools/peaks.py already writes-then-replaces, so
    # this is that pattern.
    tmp = out_path.with_name(out_path.stem + ".burntmp" + out_path.suffix)
    cmd[-1] = str(tmp)
    try:
        if runner is not None:
            runner(cmd)
        else:
            # No runner means a LOCAL encode, and a local encode is capped
            # and states its reason (AGENTS.md: remote by default) -- the
            # CLI routes through a runner for exactly this; a direct caller
            # gets the same protection here.
            from tools import farm as _farm
            proc = _farm.run_capped_local(
                cmd, reason="plate burn with no runner -- a caller asked for "
                "a local encode", capture_output=True, text=True)
            if proc.returncode != 0:
                tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
                raise RuntimeError(f"plate burn failed:\n{tail}")
        # A stubbed encoder (the tests') and a failed fetch alike return
        # having written nothing; only a file that actually exists may
        # replace the master.
        if tmp.exists():
            os.replace(tmp, out_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return out_path


def parse_picture(text):
    """``"X,Y,W,H"`` -> the picture rect ``place`` measures its margins against.

    The measured alternative to probing footage. ``detect_picture`` reads the
    letterbox off the video, which needs the film to be on this machine and
    silently returns ``None`` when its probe lands past the end of a short cut
    -- so a 34 s act gets no rect at all and its plates seat against the raw
    frame. An act that has already measured its own matte records the rect in
    its manifest and passes it here, which is both reproducible and offline.
    """
    parts = [p.strip() for p in str(text).split(",")]
    if len(parts) != 4:
        raise ValueError(f"--picture wants X,Y,W,H -- got {text!r}")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError:
        raise ValueError(f"--picture wants four integers -- got {text!r}") from None
    if w <= 0 or h <= 0:
        raise ValueError(f"--picture needs a positive width and height -- got {text!r}")
    return x, y, w, h


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render and burn Guardian nameplates.")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("render", help="manifest -> transparent PNG per plate")
    r.add_argument("--manifest", required=True)
    r.add_argument("--out-dir", default=str(REPO_ROOT / "renders" / "plates"))
    r.add_argument("--fit-video", default=None,
                   help="keep plates on the picture of this letterboxed video "
                        "instead of the raw 16:9 frame")
    r.add_argument("--picture", default=None, metavar="X,Y,W,H",
                   help="the picture area, given rather than probed. Use when "
                        "the letterbox was MEASURED and recorded in the "
                        "manifest: the rect is then committed with the act "
                        "instead of being re-derived from footage this repo "
                        "does not carry, and rendering needs no video at all. "
                        "Wins over --fit-video when both are given")

    b = sub.add_parser("burn", help="composite rendered plates onto a cut")
    b.add_argument("--video", required=True)
    b.add_argument("--manifest", required=True)
    b.add_argument("--plates-dir", default=str(REPO_ROOT / "renders" / "plates"))
    b.add_argument("--out", required=True)
    b.add_argument("--fit-picture", action="store_true",
                   help="re-render the plates onto the video's picture area first, "
                        "so nothing sits on a letterbox bar")
    b.add_argument("--delivery-spec", action="store_true",
                   help="encode the burn at the repo's DELIVERY rung (crf 16, "
                        "preset slow) with the BT.709 VUI, instead of the legacy "
                        "crf 18/medium/untagged argv. Opt-in per act: turning it "
                        "on marks every act built without it as stale")
    b.add_argument("--farm", action="store_true",
                   help="encode the burn on the farm cluster. This is ALREADY "
                        "the default whenever the cluster is reachable "
                        "(owner's ruling: always prefer remote encoding); the "
                        "flag only pins the posture. An unreachable cluster "
                        "falls back to a memory-capped local encode with the "
                        "reason printed -- degrade, never block.")
    b.add_argument("--local", action="store_true",
                   help="force a local burn even when the cluster is "
                        "reachable (the escape hatch; the encode runs under "
                        "tools.farm.run_capped_local's memory cap)")

    p = sub.add_parser("plan", help="cut list (+ roster) -> timed plate manifest")
    p.add_argument("shotlist", help="JSON shot list from tools/story.py --format json")
    who = p.add_mutually_exclusive_group()
    who.add_argument("--roster", default=None, help="roster.json from tools/ensemble.py")
    who.add_argument("--placeholders", type=int, default=0, metavar="N",
                     help="plate N ensemble shots with the uncast blueberry copy "
                          "from vocab/casting.yaml, for a cut with no roster yet")
    p.add_argument("--max-shot-sec", type=float, default=None,
                   help="the same hold cap render.py was given, so timings line up")
    p.add_argument("--hold", type=float, default=DEFAULT_HOLD)
    p.add_argument("--around", default=None,
                   help="a manifest of already-fixed windows (e.g. dialogue) that "
                        "the plates must not collide with")
    p.add_argument("--prefer-clear-of", default=None,
                   help="a manifest (e.g. a dialogue pre-pass) that plates should "
                        "avoid if they can, but may overlap rather than be dropped")
    p.add_argument("--only", choices=("all", "leads", "ensemble"), default="all",
                   help="plan one tier at a time, so a scored cut can be planned "
                        "in priority order: leads, then dialogue, then ensemble")
    p.add_argument("--brief", default=None,
                   help="issue number or brief YAML file: the brief's plates[] "
                        "are planned first as fixed, owner-timed credits (see "
                        "docs/skills/plates/SKILL.md). Lead-tier: with --only ensemble "
                        "they are expected via --around, like dialogue")
    p.add_argument("--reveal-after", default=None, metavar="MM:SS",
                   help="hold every derived lead reveal until this point on the "
                        "FINISHED cut (mm:ss, HH:MM:SS or seconds). A character "
                        "the cut never shows again after it is revealed on their "
                        "latest appearance instead, and reported")
    p.add_argument("--out", required=True)

    m = sub.add_parser("merge", help="combine planned manifests into one, validated")
    m.add_argument("manifests", nargs="+")
    m.add_argument("--out", required=True)

    args = parser.parse_args(argv)

    if args.command == "merge":
        entries = []
        for path in args.manifests:
            entries.extend(load_manifest(path))
        entries.sort(key=lambda e: float(e["at"]))
        load_manifest_entries(entries)  # rejects overlaps across the whole deck
        with Path(args.out).open("w", encoding="utf-8") as fh:
            json.dump(entries, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.out} ({len(entries)} plate(s))")
        return 0

    if args.command == "plan":
        from tools.derive import load_leads
        from tools.render import load_shots

        roster = None
        if args.roster:
            with Path(args.roster).open(encoding="utf-8") as fh:
                roster = json.load(fh)
        busy = []
        if args.around:
            busy = [(float(e["at"]), float(e["at"]) + float(e["dur"]))
                    for e in load_manifest(args.around)]
        soft = []
        if args.prefer_clear_of:
            soft = [(float(e["at"]), float(e["at"]) + float(e["dur"]))
                    for e in load_manifest(args.prefer_clear_of)]
        brief = None
        if args.brief:
            from tools.brief import (BriefError, fetch_issue, has_block,
                                     parse_brief, parse_issue_body)
            try:
                if args.brief.isdigit():
                    brief = parse_issue_body(
                        fetch_issue(int(args.brief)).get("body"))
                else:
                    text = Path(args.brief).read_text(encoding="utf-8")
                    brief = (parse_issue_body(text) if has_block(text)
                             else parse_brief(text))
            except BriefError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
        unresolved = []
        reveal_after = None
        if args.reveal_after is not None:
            try:
                reveal_after = (_tc_seconds(args.reveal_after)
                                if ":" in args.reveal_after
                                else float(args.reveal_after))
            except ValueError:
                print(f"error: --reveal-after wants mm:ss or seconds, got "
                      f"{args.reveal_after!r}", file=sys.stderr)
                return 2
        entries = plan(load_shots(args.shotlist), load_leads(), roster,
                       max_shot_sec=args.max_shot_sec, hold=args.hold, log=print,
                       busy=busy, only=args.only, soft_busy=soft, brief=brief,
                       placeholders=args.placeholders, unresolved=unresolved,
                       reveal_after=reveal_after)
        load_manifest_entries(entries)  # same validation the burn path applies
        with Path(args.out).open("w", encoding="utf-8") as fh:
            json.dump({"plates": entries, "unresolved": unresolved}, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.out} ({len(entries)} plate(s), "
              f"{len(unresolved)} unresolved)")
        return 0

    entries = load_manifest(args.manifest)
    # `render` and `burn` are where a HAND-AUTHORED manifest enters the
    # pipeline without ever passing through `plan`, which is the only other
    # place the vocab-wins rule is enforced. Checked here rather than inside
    # load_manifest so the loader stays a parsing helper.
    check_copy_against_bindings(entries)

    if args.command == "render":
        picture = None
        if args.picture:
            picture = parse_picture(args.picture)
            print(f"picture area: {picture[2]}x{picture[3]} at "
                  f"+{picture[0]}+{picture[1]} (given, not probed)")
        elif args.fit_video:
            from tools.render import detect_picture

            picture = detect_picture(args.fit_video)
            if picture:
                print(f"picture area: {picture[2]}x{picture[3]} at "
                      f"+{picture[0]}+{picture[1]}")
            else:
                print("picture area: cropdetect found nothing -- plates are "
                      "placed against the RAW FRAME. On a letterboxed cut "
                      "that seats them wrong; pass --picture with the "
                      "measured rect instead", file=sys.stderr)
        written = render_all(entries, args.out_dir, picture)
        for path in written:
            print(f"wrote {path}")
        return 0

    picture = None
    if getattr(args, "fit_picture", False):
        from tools.render import detect_picture

        picture = detect_picture(args.video)
    render_all(entries, args.plates_dir, picture)
    encode_args = (conform.video_encode_args()
                   if getattr(args, "delivery_spec", False) else None)

    from tools import farm

    if getattr(args, "farm", False) and getattr(args, "local", False):
        raise SystemExit("--farm and --local are mutually exclusive: the farm "
                         "is already the default when the cluster is "
                         "reachable; --local is the escape hatch from it")
    if getattr(args, "local", False):
        use_farm, farm_why = False, "--local given"
    else:
        use_farm, farm_why = farm.cluster_available()
    if use_farm:
        # The farm stages exact argv tokens, so the inputs are the video plus
        # each plate PNG itself, not their directory (same pattern as the
        # burn leg in scripts/build_act1.py). An animation unit's argv token
        # is its %0Nd PATTERN, not a file -- farm.sequence_frames expands it,
        # so the staged token must be the pattern too (38e221b).
        burn_inputs = [Path(args.video).resolve()] + [
            (Path(args.plates_dir) / (
                u["pattern"] if u["animation"] else f"plate_{u['id']}.png")
             ).resolve()
            for u in _burn_units(entries)
        ]
        expected = _probe_duration(args.video)

        # 48Gi, not the farm's 16Gi default: act II's burn is ~78 overlay
        # inputs, and the 16Gi pod was OOMKilled (exit 137) 52 s in -- the
        # cgroup version of the local "Failed initializing scaling graph"
        # failure _burn_units' comment describes. exo-0 has 65Gi.
        #
        # The fetch target is read off the ARGV, never from `args.out`. burn()
        # rewrites the final token to a `.burntmp` sibling so an interrupted
        # encode cannot truncate the delivered master (#286), and the farm
        # refuses an `out` that the argv does not name verbatim -- so passing
        # the master here made every `--farm` burn fail before it started.
        # Fetching into the tmp is also what the write-then-replace wants: the
        # master is only replaced by a completed fetch.
        def runner(argv, _inputs=burn_inputs, _dur=expected):
            farm.run_ffmpeg_on_cluster(argv, inputs=_inputs,
                                       out=Path(argv[-1]),
                                       expected_duration=_dur,
                                       limit_memory="48Gi")
    else:
        # Local is the fallback, never the silent default, and never
        # unbounded: the burn is the heaviest encode in the repo (act II's
        # ~78 overlay inputs), so it runs under the memory cap with the
        # reason printed -- the same failure tail the bare path reported.
        def runner(argv, _why=farm_why):
            proc = farm.run_capped_local(
                argv, reason=f"plate burn on this host -- {_why}",
                capture_output=True, text=True)
            if proc.returncode != 0:
                tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
                raise RuntimeError(f"plate burn failed:\n{tail}")

    out = burn(Path(args.video).resolve(), entries, args.plates_dir,
               str(Path(args.out).resolve()),
               encode_args=encode_args, runner=runner)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

---
act: VI
manifest: stories/06-wolves-cayde-plates.json
# Programme start measured from `python3 tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-25. The programme item-duration rule is authoritative.
programme_start: 1109.9
# This act's manifest holds BOTH kinds of plate: the pills below, and four
# `copy_source: brief` nameplates that resolve from the roster. This file
# authors only its own -- `sync` carries the nameplates through in place.
owns_plates: true
field_order: id, kind, position, speaker, avatar, detail, label, text, copy_source, at, dur, fade_in, fade_out_at, fade_out, seen_at_film, _note
defaults:
  kind: chat
  position: letterbox
  copy_source: owner_supplied
  avatar: auto
  fade_in: 0.6
  fade_out: 0.25
  # This act's pills start fading 0.6 s before their window closes, not
  # 0.25 s: the fade is a fade-IN's length long on the way out. That is what
  # is on the delivered master, so it is stated rather than re-derived.
  fade_out_at: derived 0.6
  text_source: null
  avatar_url: null
---

# Act VI — the wolves, and what is asked of you

Jorge Castro's six lines over his own close-up, and the Ghost's welcome an
act earlier. Act II plates him as `[ REDACTED ]`; this act is the reveal, so
these are the first words on screen carrying his name.

Every line here is **owner-supplied verbatim**, including two the owner
corrected himself: "For fives years" → "For five years", and "Lead the way,
open source will follow" → "Lead the way, we will follow". Reproduce them as
written; never tidy them.

Four gold nameplates sit between the welcome and the pills — the Cayde-6
reveal and three credits. They are **not here on purpose**: they carry
`copy_source: brief` and resolve from the roster, which is the one place
those names live. Edit them there.

## 19:30.027

* [ghost_welcome] status @ 19:30.027 +6.0
  - position: status
  # The Ghost's welcome is a hard cut on and off; it carries none of the
  # pills' fades.
  - fade_in: null
  - fade_out: null
  - fade_out_at: null
  - detail: AN4-CH4K-12
  - label: Welcome to KubeCon + Cloud Native Con
  - seen_at_film: 60.127
  - _note: Programme 16:30.1 maps to Act VI 1:00.127 -- owner note 2026-08-16: "the 'Welcome to KubeCon' text line goes here". The owner asked for the Ghost to welcome the audience, so this uses the top-of-frame status treatment rather than a normal lower-third chat; the seat is the Ghost's own shot (the Ghost over the Moon), confirmed on an extracted frame. Moved from 36.127, the star-map HUD shot.

## 24:23.557

[castrojo_line_1] castrojo @ 24:23.557 +2.8: For five years you've trusted us

[castrojo_line_2] castrojo @ 24:26.715 +2.8: Mastered your tools

[castrojo_line_3] castrojo @ 24:29.873 +2.8: Honed your craft

[castrojo_line_4] castrojo @ 24:33.031 +2.8: Depended on your friends

[castrojo_line_5] castrojo @ 24:36.189 +2.8: Now you're one of us, you are the dream

* [gold_robertsirc] - @ 24:39.347 +2.8
  - position: left
  - label: "#HIREAWOLF // MAINTAINER"
  - class: Harbinger Titan
  - name: robertsirc
  - title: Protector of the Helm
  - variant: leader
  - why: >
      SEAT UNVERIFIED. The owner asked for this on "the guardian lifting the
      other one", which is the shot under "Depended on your friends" at film
      363.131 -- but a pill already holds the left lane there for its whole
      2.8 s, and this act is one-plate-at-a-time. This is the nearest clear
      air, film 369.289, immediately before Jorge's own reveal at 374.041.
      It reads: depended on your friends -> robertsirc -> now you're one of
      us -> Jorge. Whether it is still the lifting shot is a judgement about
      a picture, so it is flagged rather than claimed.
  - _note: >
      OWNER-AUTHORED, 2026-08-23, verbatim: `#HIREAWOLF // MAINTAINER
      HARBRINGER TITAN "Protector of the Helm"`. Split into the four plate
      fields as written -- HARBRINGER is reproduced, not corrected to
      "Harbinger", because authored copy is never tidied. `name` is his own
      GitHub login: vocab/casting.yaml records `display_name: null` with a
      note that a plate must not invent one, and a login is the person
      naming himself rather than this repo naming him.

>> THE FREEZE IS STILL OPEN. The owner asked to "freeze this section" for
this plate. Not done yet, deliberately: act VI is rebuildable, so a
freeze-frame is reachable, but lengthening the act shifts every pill after
it, acts VII and VIII's programme starts, and every chapter marker. The
plate plays over the moving shot until he has watched it and said. <<

>> THE MENTOR LINES PLAY AFTER THE PLATES, NOT ON THEM, and that is the one
thing here the owner asked for that could not be done. He wrote, 2026-08-23:
"their plates are up, add my dialogue to match their plates, I am
introducing them narratively." The plates are real and already in this act's
manifest -- gold_kelsey_hightower at film 382.349, gold_brian_ketelsen at
386.349, gold_angie_jones at 388.349 -- but they hold the left lane, which
is where a pill sits, and act VI is one-plate-at-a-time. Kelsey's clears
0.4 s before Ketelsen's opens; there is no window for a pill between them
and none over them.

So the reveals roll past / present / future in silence, and the seven lines
take the free BARS of the bed after them, in his order. If he wants a line
ON a plate, the plate has to shorten or the pill has to share the lane --
both are his calls, not mine.

THE BAR IS WHY THE SEATS LOOK ODD. Every pill in this act lands on a
multiple of 3.157914 s from line 1, which is the bed's own bar, and the
reveals occupy bars 6, 7, 9, 10 and 11. That leaves bar 8 and bars 12 to 17
-- exactly seven, for exactly seven lines. So "I follow my mentors of the
past" gets bar 8, immediately before Kelsey's plate, which is the line
doing the introducing anyway; "Present" and "and Future" take the first two
bars after Angie's clears. <<

[castrojo_line_6] castrojo @ 24:48.821 +2.8: I follow my mentors of the past

[castrojo_line_7] castrojo @ 25:01.452 +2.8: Present

[castrojo_line_8] castrojo @ 25:04.610 +2.8: and Future

[castrojo_line_9] castrojo @ 25:07.768 +2.8: The only winning move is not to play

[castrojo_line_10] castrojo @ 25:10.926 +2.8: Think like a dinosaur

[castrojo_line_11] castrojo @ 25:14.084 +2.8: When you fall, rise.

[castrojo_line_12] castrojo @ 25:17.242 +2.8: We've got your back

    THE OWNER REWROTE THIS TAIL ON 2026-08-23. Three lines went: "Made
    Lifelong Friends" (line 4), "And now it's up to you, guardian" (line 5)
    and "Lead the way, we will follow" (line 6, which used to close the act).
    They are recorded here because a deleted line is easy to miss in a diff,
    and they are in git if he wants one back.

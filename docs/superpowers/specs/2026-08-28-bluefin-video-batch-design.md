# Bluefin standalone video batch

## Goal

Produce four reproducible standalone Bluefin videos and matching YouTube
thumbnails as one parallel batch. Reuse the approved Linux Foundation training
CTA and the visual language of `Bluefin - The Law of the Jungle` rather than
creating a second treatment.

## Architecture

One committed batch manifest is the source of truth for:

- source YouTube ID and URL;
- display title, description, and filesystem-safe output name;
- source excisions;
- identity, status, title, and chat card windows;
- full-frame CTA takeover time;
- source-audio preservation;
- thumbnail title and selected source frame;
- output video and thumbnail paths.

All user-supplied timestamps are source-video marks. The builder maps those
marks through earlier excisions when it creates the output timeline; it never
reinterprets a later source mark as an already-shortened output mark.

One generic standalone-video builder consumes a single manifest entry. It:

1. fetches the requested source in the best supported picture and native audio
   formats;
2. applies source excisions without shifting authored card marks incorrectly;
3. renders existing plate and card kinds through `tools/plate.py`;
4. replaces picture from a configured takeover mark through end of file while
   preserving the source audio timeline;
5. renders a Jungle-family thumbnail from an evidenced source frame;
6. trims the finished file to the project's delivered true-peak ceiling; and
7. writes the master and thumbnail to the declared delivery paths.

The builder has no Linux Foundation-specific branch. The approved CTA remains
a reusable local skill and asset recipe: full-frame picture replacement from a
declared mark to EOF, unchanged source audio, and no fade unless a future brief
asks for one.

After the shared manifest, builder, and CTA skill exist, four fleet workers run
one manifest entry each. They write unique media and thumbnail paths and do not
edit shared repository files. Encoding uses the remote farm whenever it is
reachable.

## Shared visual treatment

### Thumbnails

Every thumbnail follows the established `Bluefin - The Law of the Jungle`
grammar:

- an evidenced hero frame from that video's source;
- a centered `BLUEFIN` eyebrow with a blue divider;
- the video's title in large uppercase white type with a black outline;
- no additional badge, CTA, or metadata clutter;
- 1920x1080 output under YouTube's 2 MB limit;
- readability checked at 336x189.

The selected frame is chosen so the title lockup lands on background, not on
the subject. The title ink occupies a fixed band of the fitted 1920x1080 card,
so the mark is evidence-checked against that band: no part of the subject's
head under the lockup, and no burned-in publisher copy beneath it either.

### Identity plates

A `Jorge Castro` plate credits a real person, so it is seated on the first
clear window that supports the full readable hold -- not on the character's
first clear frame. Every frame the plate is on screen for must support the
credit: the character stays in frame, or the picture stays in unbroken
continuity with them (their own hand, their own weapon). A window whose shot
ends before the hold does is not a seat; the next supported window is. A plate
that cannot be seated that way is omitted and recorded, never ridden onto
footage that does not support it.

The four thumbnails form one family while retaining a distinct source image for
each video.

### Linux Foundation training CTA

All three CTA takeovers use the same approved artwork and copy:

> FARM THE FREE LINUX FOUNDATION TRAINING FOREST

The card includes `training.projectbluefin.io` and its existing supporting
copy. Each use is visually byte-identical. Only the takeover time differs.
Source audio continues unchanged under the card through EOF.

## Video specifications

### Bluefin and the Blueberries

- Source: `https://www.youtube.com/watch?v=ZJLAJVmggt0`
- Delete source `0:46-0:54` and join the surrounding material.
- Show a standard plain-blue, name-only plate reading `Jorge Castro` on the
  first clear window that supports the full readable hold. Do not add a label,
  class, or title.
- At source `1:37`, replace picture with the approved LF training CTA through
  EOF. The earlier excision places this takeover at output `1:29`.
- Preserve source audio under the CTA.
- Deliver the video and matching Jungle-family thumbnail beside the existing
  Jungle standalone deliverable in `~/Videos/`.

### Bluefin: Care for a Drink?

- Source: `https://www.youtube.com/watch?v=rQ4i0AT8c-M`
- Show the same standard plain-blue, name-only `Jorge Castro` plate on the first
  clear window that supports the full readable hold.
- At `0:56`, replace picture with the approved LF training CTA through EOF.
- Preserve source audio under the CTA.
- Deliver the video and matching Jungle-family thumbnail in `~/Videos/`.

### Bluefin: Your Final Trial

- Source: `https://www.youtube.com/watch?v=_OvgGtnN_Ts`
- Treat this as the payoff to the player identity introduced in
  `Bluefin and the Witness`.
- Keep Cayde's `Jorge Castro` identity humble: the standard plain-blue,
  name-only finale treatment.
- Celebrate the player separately with the Excision status-HUD shape:
  - detail: `FIRETEAM // EXPERT`;
  - label: `John Bazzite`;
  - official Bazzite tile crest;
  - the selected promoted treatment: Bazzite gradient, luminous purple rule and
    glow, and a larger official tile crest;
  - top-right from the first full gameplay frame through the last gameplay
    frame, with the measured source marks committed in the manifest.
- "Highest tier" does not borrow the gold leader rank or the laurel reserved
  for named people. The Bazzite crest and promoted purple HUD are the complete
  rank statement.
- The status HUD and Cayde plate occupy independent rails so both characters
  can be celebrated without turning Cayde's card into a Bazzite card.
- At `0:33`, show these `castrojo` chat pills in order:
  1. `You knew this would happen`
  2. `Stay _sharp_!`
- Add only the minimal chat emphasis needed by the authored second line: one
  balanced underscore pair selects the renderer's existing italic mono face.
  This is not a general Markdown parser, and the stored source string remains
  verbatim.
- At `1:34`, show these `castrojo` chat pills in order:
  1. `I don't hate nix users`
  2. `That's your character to play, not mine`
  3. `Because I did just beat you, but that's a 50/50 call every time`
  4. `You need to carry me through Duality`
- Give every pill a readable hold. A pill may ride across a shot cut, but the
  picture and authored anchor times do not move to make room.
- Deliver the video and matching Jungle-family thumbnail in `~/Videos/`.

### Bluefin and Saint 14

- Source: `https://www.youtube.com/watch?v=iVZ-G88rOYg`
- Display title: `Bluefin and Saint 14`
- Description: `The Standard for others to Follow`
- Show a top-right title plate reading `Activating CNCF Community` from
  `1:46` through `1:51`.
- At `2:03`, replace picture with the approved LF training CTA through EOF.
- Preserve source audio under the CTA.
- Deliver the video and matching Jungle-family thumbnail in `~/Videos/`.

## Degradation and errors

The builder always emits the best supported cut:

- an optional plate that cannot be seated on evidenced picture is omitted and
  recorded in `unresolved`, never moved onto a false frame;
- colliding authored card windows are reported rather than silently retimed;
- missing optional brand artwork degrades to the renderer's documented crest
  fallback;
- source fetch and encode failures are explicit because no valid video exists
  without source media or a completed encode;
- footage, extracted frames, and rendered videos remain outside git.

The approved CTA asset is a committed non-footage production asset, so a normal
checkout can reproduce every takeover without depending on an untracked
workspace copy.

## Verification

For each output:

- `ffprobe` confirms the expected duration and stream layout;
- the Blueberries duration reflects exactly eight seconds removed;
- audio correlation before and after each CTA mark confirms that source audio
  continues without a reset, replacement, or fade;
- extracted frames inside every plate, card, chat, and CTA window confirm the
  requested visual is actually present;
- all CTA frames use the same approved source artwork;
- the delivered true peak passes the project's `-0.9 dBTP` ceiling;
- the thumbnail is 1920x1080, below 2 MB, and readable at 336x189;
- no media, keyframes, thumbnails, or rendered videos appear in git status.

# Standalone nameplate quality pass

## Goal

Correct two delivered standalone videos without changing their authored
dialogue, audio, thumbnails, or source edits:

- move Jorge Castro's Cayde-6 credit into the opening section of
  `Bluefin and the Blueberries`, restore his established series identity, and
  remove the source trailer's publisher text from the ending;
- replace the persistent John Bazzite status HUD in
  `Bluefin: Your Final Trial` with one normal lower-third on the player landing.

## Authoritative copy

Finished series nameplates use the established identity record. They are not
replaced with placeholders, compact approximations, or newly invented fields.

The Cayde-6 plate resolves through `vocab/casting.yaml` to:

- `TRUSTEE // GUARDIAN`
- `Harbinger Titan`
- `Jorge Castro`
- `Upender of Antipatterns | The First Disciple`
- trustee chrome

John Bazzite has no Guardian identity in `vocab/casting.yaml`. The only
owner-authored identity string is `John Bazzite`, and Bazzite chrome is already
an approved rendering flag. The normal landing plate therefore carries only
`name: John Bazzite` with `variant: bazzite`; it does not invent a label, class,
or title.

## Bluefin and the Blueberries

The current compact Jorge pill at source 69.6 seconds is replaced by the full
established Cayde-6 identity. Its new seat is source/output 33.55 seconds with
a 1.95-second hold. Visual frame review establishes Cayde-6 cleanly visible
from source 33.533 through 35.533, with the dissolve to the destruction wide
beginning at 35.567; the segment records
(`seg_yt_destiny_2_rally_the_troops_worldwide_reveal_trailer_0033-0037`,
"Cayde-6 reaches toward a red figure", 33.300-37.767) are coarser than the
picture, and the preceding segment (30.800-33.300, "Guardians fighting amid
debris") identifies no character. The standalone renderer hard-overlays the
static plate only from source_at through source_at+dur — it does not render
plate.py's lead-in/tail-out envelope — so the overlay interval 33.55-35.50
itself sits inside the measured visible bounds, satisfying the owner's
"around the first ~30 seconds" ask without crediting Jorge over the
destruction wide. The 1.95-second hold is an explicit short-hold exception to
the 2.2-second minimum because no 2.2-second continuous Cayde shot exists
near 30 seconds; the complete established four-row identity is kept.

The CTA takeover moves from source 97.0 seconds to 91.7 seconds (output 83.7
after the 8-second excision). The source's `NEW LEGENDS WILL RISE` title
segment begins at 91.767
(`seg_yt_destiny_2_rally_the_troops_worldwide_reveal_trailer_0091-0096`), so
91.7 starts the approved CTA before that title, its legal-card flash, and the
hard transition. Source audio continues unchanged beneath the CTA.

## Bluefin: Your Final Trial

The `john-bazzite-expert` status overlay that currently spans source
3.35-109.70 seconds is removed. A normal left lower-third appears at source
16.2 seconds for the standard 2.2-second hold, after the player's feet contact
the ground and while the landing shot remains stable.

The existing Jorge/Cayde plate and all authored chat remain unchanged. Its
manifest explanation is updated only where it incorrectly depends on the
retired persistent HUD.

## Implementation

`stories/standalone/bluefin-video-batch.json` remains the source of truth.
Focused tests pin the complete literal overlay records and the earlier CTA
seat. No delivered H.264 file is patched: both outputs are rebuilt from their
pinned source formats through the farm-first standalone builder.

The plates skill records the durable rule that finished identity plates must
use their established authored identity and must not degrade to placeholders.
Missing identity metadata is omitted and recorded rather than invented.

## Verification

- schema and focused standalone/plate tests pass;
- review frames show the complete Castrojo plate at the hold midpoint (34.5
  seconds) and no publisher title before the Blueberries CTA;
- Final Trial has no persistent top-right HUD and shows the John Bazzite
  lower-third only on the 16.2-second landing;
- delivered duration, audio correlation, stream shape, thumbnail, and true-peak
  checks remain valid;
- no footage, extracted frames, thumbnails, or rendered videos enter git.

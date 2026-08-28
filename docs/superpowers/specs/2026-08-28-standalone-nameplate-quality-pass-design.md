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
established Cayde-6 identity. Its new seat is source/output 31.2 seconds with a
2.2-second hold. The complete animation envelope, 30.8 through 33.65 seconds,
stays inside the measured 30.797-37.771 Cayde-visible battlefield advance.

The CTA takeover moves from source 97.0 seconds to 93.5 seconds. This starts the
approved CTA before the source's `NEW LEGENDS WILL RISE` title, legal-card
flash, and hard transition. Source audio continues unchanged beneath the CTA.

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
- review frames show the complete Castrojo plate at 31.2 seconds and no
  publisher title before the Blueberries CTA;
- Final Trial has no persistent top-right HUD and shows the John Bazzite
  lower-third only on the 16.2-second landing;
- delivered duration, audio correlation, stream shape, thumbnail, and true-peak
  checks remain valid;
- no footage, extracted frames, thumbnails, or rendered videos enter git.

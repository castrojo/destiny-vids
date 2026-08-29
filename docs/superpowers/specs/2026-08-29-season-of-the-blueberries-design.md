# Season of the Blueberries

## Goal

Turn the 12 publisher-authored chapters in
`https://www.youtube.com/watch?v=jlzQnXcUxqI` into weekly episodes under
`~/Videos/Hive/Season-of-the-Blueberries/`, plus one full-season cut.

## Episode shape

Every episode uses the same sequence:

1. the Expansion Pack opening CTA;
2. a title slide with the source chapter title and one copyedited lore subtitle;
3. up to three GitHub-sourced contributor dossier cards;
4. the source chapter with only visually supported character plates;
5. the existing `training.projectbluefin.io` CTA.

There is no added music. Opening and closing cards use silence; source audio is
preserved through the chapter.

## Identity and casting

Weekly contributor dossiers use GitHub as the factual source of truth:
numeric account ID, login, public display name when present, profile URL, and
the full profile image. Missing profile fields are omitted rather than
invented.

The dossier layout is the selected **Guardian dossier A** treatment: a large,
uncropped square profile image beside a dark KubeStellar panel with a
blue-purple edge. It shows factual GitHub identity and contribution evidence,
not generated biography or lore.

Character plates are fixed and source-evidenced:

- Ikora Rey: Angie Jones, using the existing Wolves gold identity.
- Eris Morn: Shellea Williams (`Swil78`), using the owner-authored gold plate.
- The recurring player Guardian: `CortNick`, using the owner-authored player
  plate.

No other body receives a named identity. Unsupported plates are omitted.

## Contributor rotation

A scheduled GitHub Action runs every seven days. It gathers commit authors
from the configured public KubeStellar repositories since the previous
snapshot, resolves each candidate through the GitHub Users API, excludes bots,
fixed cast, and every numeric GitHub ID credited before, then selects at most
three contributors by:

1. commit delta descending;
2. normalized login ascending.

The Action opens a pull request containing the next episode record and updated
no-repeat ledger. Merging the PR is the human approval for putting real people
on screen. A period with no eligible contributor still produces an episode
with no dossier cards.

## Lore authority

`projectbluefin/hive-lore` owns title-slide lore policy and candidate
generation. It does not generate person-facing fields. The selected subtitle is
frozen in the episode record; released slides never rotate.

## Build interface

`just hive-episode <number>` builds one episode.

`just hive-cut` builds all episodes and concatenates the full-season cut.

The source is fetched once and reused by every episode. Cards and profile
images are cached. Each final episode is encoded once through the existing
farm-first policy; local fallback remains memory-capped.

## Delivery

- Episodes:
  `~/Videos/Hive/Season-of-the-Blueberries/s01eNN-<chapter>.mp4`
- Thumbnails:
  `~/Videos/Hive/Season-of-the-Blueberries/s01eNN-<chapter>-thumbnail.jpg`
- Full cut:
  `~/Videos/Hive/Season-of-the-Blueberries/season-01-full.mp4`

The repository stores records, timestamps, generated card assets, and tooling,
never source footage or delivered video.


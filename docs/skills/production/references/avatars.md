# The credits' avatar cache

Part of the [production skill](../SKILL.md).

Act VIII puts a face beside about five hundred logins. The renderer never
touches the network — `tools/credits.avatar()` reads
`renders/avatars/<login>.png` and degrades a missing face to a ring — so the
only question is how that directory gets filled without hammering github.com.

`tools/avatars.py` is the whole answer, and the Actions job and the workstation
run the same code.

## Fill it from CI, not from your laptop

```bash
python3 -m tools.avatars --from-actions   # Act VIII default: unpack CI's artifact, then fill gaps
python3 -m tools.avatars --manifest stories/02-endless-forms-plates.json --from-actions
python3 -m tools.avatars --manifest stories/02-endless-forms-plates.json \
    --prepare renders/02-endless-forms-burn-manifest.json
python3 -m tools.avatars --manifest renders/yt_curse_of_osiris_opening_cinematic-plates.json \
    --from-actions
python3 -m tools.avatars --manifest renders/yt_curse_of_osiris_opening_cinematic-plates.json \
    --prepare renders/yt_curse_of_osiris_opening_cinematic-burn-manifest.json
python3 -m tools.avatars --revalidate     # re-check every cached face
python3 scripts/build_credits.py --avatars-from-actions   # both, then render
```

[`.github/workflows/avatars.yml`](../../../../.github/workflows/avatars.yml)
does the fetching on a runner with **`${{ github.token }}`** — the built-in
token, `contents: read`, and **no PAT and no repository secret of any kind**. It
warms an `actions/cache` entry keyed on the login set and uploads
`renders/avatars/` as the `avatars` artifact; `pull_from_actions()` brings that
back with `gh run download`. The artifact name is `tools.avatars.ARTIFACT`,
asserted against the workflow by `tests/test_avatars.py` so the upload and the
download cannot drift.

It runs on `workflow_dispatch` and on a push that touches
`stories/02-endless-forms-plates.json`,
`dialogue/yt_curse_of_osiris_opening_cinematic/dialogue.json`,
`stories/08-credits.json`, `vocab/casting.yaml` or `tools/avatars.py` — the
committed inputs that decide which portraits acts II, III and VIII can ask
for. Nothing is scheduled, because nothing here needs to run when nobody
changed the cast.

`--manifest` asks only for entries carrying `avatar_required: true`, and
`--dialogue` resolves the live cue speakers through `tools.identity.person_for_character`.
The workflow unions those exact sources in one call:

```bash
python3 -m tools.avatars \
  --manifest stories/02-endless-forms-plates.json \
  --dialogue yt_curse_of_osiris_opening_cinematic \
  --credits-manifest stories/08-credits.json
```

## What makes a re-run nearly free

`renders/avatars/index.json` is a **cache, not a record**: gitignored with the
rest of `renders/`, safe to delete, rebuilt by the next run. It holds one row
per login — `etag`, `status`, `checked`, `bytes` — and it is what buys all
three:

| | |
|---|---|
| **Conditional requests** | A cached face is revalidated with `If-None-Match`. A `304` is a header exchange: no image, no decode, nothing rewritten. |
| **Negative caching** | A `404` is an answer, not a failure. It is recorded and not asked again for `GONE_TTL` (30 days). |
| **Backoff that reads the response** | On `403`/`429`, `Retry-After` first, then `x-ratelimit-reset` — which is an **epoch, not a duration**, so it is subtracted from now. No instruction is not permission to retry immediately: it still waits. |

A cached face is left alone for `FRESH_FOR` (14 days) before it is revalidated
at all. A PFP is not urgent.

## Running out of patience is not a failure

`Budget` caps the total time a run will spend sleeping (`MAX_SLEEP_TOTAL`).
When it is gone the run **stops and reports how many faces are still missing**
instead of firing five hundred more requests at a server that just said no. The
build continues: an unfetched face is a ring, which is what the renderer already
draws.

Everything about the CI path degrades the same way — no `gh`, not logged in, no
successful run yet, artifact expired — and the direct fetch still works.

## Required portraits omit the card; optional artwork keeps the fallback

`prepare_manifest_avatars()` writes the persistent burn manifest each act burns
from. A canonical real-person entry carries `avatar_required: true`; when its
cached portrait is missing, the entry is omitted from the prepared manifest and
recorded in `unresolved` as `omitted_missing_required_avatar`. The renderer then
never gets the wrong fallback crest for that person.

Optional artwork stays on the old rule: if an entry does **not** claim a real
person's required portrait, a missing file may still degrade to the existing
crest or ring fallback.

## Never ask github.com for a name

`avatar_logins()` in `scripts/build_credits.py` is the one definition of who is
asked about, because the build and the runner must agree. Two traps are pinned
there by tests:

- **A GitLab section carries display names, not logins.** Asking for
  `Harald Sitter.png` is not a missing avatar, it is a category error — and
  whatever answered would be a stranger's face beside somebody's name.
- **`cast_logins._comment` is prose about the overlay, not a person.** Keys
  starting with `_` are skipped.

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
python3 -m tools.avatars --from-actions   # unpack CI's artifact: one request
python3 -m tools.avatars                  # fetch what is still missing
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
`stories/08-credits.json`, `vocab/casting.yaml` or `tools/avatars.py` — the
three files that decide which logins exist. Nothing is scheduled, because
nothing here needs to run when nobody changed the cast.

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

## Never ask github.com for a name

`avatar_logins()` in `scripts/build_credits.py` is the one definition of who is
asked about, because the build and the runner must agree. Two traps are pinned
there by tests:

- **A GitLab section carries display names, not logins.** Asking for
  `Harald Sitter.png` is not a missing avatar, it is a category error — and
  whatever answered would be a stranger's face beside somebody's name.
- **`cast_logins._comment` is prose about the overlay, not a person.** Keys
  starting with `_` are skipped.

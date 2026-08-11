# Epic B — Identity: GitHub is the source of truth

**Parent:** #9 · **Depends on:** A · **Blocks:** C, D, E, F, G
**Design:** [`docs/plans/wolves/design.md` §2](../design.md)

Everything on screen about a person — their name, their face, their employer,
their badges — is resolved from their public GitHub profile and written to a
committed metadata record. Nothing about a person is typed into `WOLVES.md`, and
nothing is guessed.

**Done looks like:** `python3 tools/identity.py sync` writes `people/<login>.json`
for every login in the comm log and the month's roster, caches their avatar into
gitignored `avatars/`, and the rest of the pipeline reads only those records —
so a render works with the network unplugged.

**Invariants for every sub-issue here**

- Public profile fields only. Never an email, never a private field.
- A person record is metadata. Images live in `avatars/`, which is gitignored,
  exactly as footage lives in `media/`.
- `withhold` is honored everywhere, immediately, and reported.

---

## B1 — The person record and its schema

**Labels:** `enhancement` · **Depends on:** —

Add `schema/person.schema.json` (Draft 2020-12, matching the style of
`schema/video.schema.json`) and commit `people/` with one hand-written example.
Fields: `login`, `display_name`, `avatar_url`, `avatar_sha256`, `company_raw`,
`affiliation`, `project`, `title`, `badges[]`, `withhold[]`, plus
`fetched_at`.

**Acceptance**

- [ ] Schema validates the example; the suite validates every `people/*.json`
      the way it already validates every `examples/*.json`.
- [ ] `affiliation`, `project` and `title` are nullable. An unresolved person is
      a valid person.
- [ ] `withhold` is an array with an enum of `avatar | affiliation | badges`.
- [ ] No field can hold an email address, and a test asserts it.

---

## B2 — `tools/identity.py sync`

**Labels:** `enhancement` · **Depends on:** B1

Fetch `GET /users/{login}` through `gh api` — the same approach
`tools/ensemble.py` already uses for the roster, so authentication and rate
limits work the way the repo already works. Write one record per login. A login
that 404s is a `fatal` reported by name; a request that fails for any other
reason leaves the existing record untouched and warns.

Take logins from `WOLVES.md` and from `tools/ensemble.py roster`.

**Acceptance**

- [ ] `--offline` (or an injected fetcher) makes the whole thing testable without
      the network; no test may hit GitHub.
- [ ] Re-running with no upstream change produces a byte-identical file — the
      diff is the review, so churn in `fetched_at` alone must not rewrite it.
- [ ] `company_raw` is stored verbatim, including the leading `@`.
- [ ] Bot logins are filtered with the existing `ensemble.is_bot()`.

**Tests:** `tests/test_identity.py`, with a fake fetcher returning a canned
GitHub payload.

---

## B3 — Avatar cache

**Labels:** `enhancement` · **Depends on:** B2

Download each avatar at `?s=460` (GitHub's ceiling) into `avatars/<login>.png`,
record its SHA-256 in the person record, and never commit the image. Add
`avatars/` and `emblems/` to `.gitignore` next to `media/`.

**Acceptance**

- [ ] A cached avatar whose hash matches is not re-downloaded.
- [ ] A changed avatar changes `avatar_sha256`, and that is the only signal the
      renderer needs to redraw.
- [ ] A missing avatar is a `warn`, and the chatter block falls back to the
      login's initials in the plate chrome — never a blank hole, never a
      stand-in face.
- [ ] `git status` is clean after a sync on a repo that has already synced.

---

## B4 — Consent: `withhold`, end to end

**Labels:** `enhancement`, `documentation` · **Depends on:** B2

Wire `withhold` through every consumer: a withheld `avatar` renders initials, a
withheld `affiliation` renders no emblem, withheld `badges` render no ribbons.
Sync must never overwrite a `withhold` array. Document the opt-out in one
paragraph: open a pull request adding the field, no reason required, honored on
the next render.

**Acceptance**

- [ ] `sync` preserves `withhold` across refreshes — a test asserts this, because
      losing it silently is the failure that matters.
- [ ] Each withheld field has a fallback that reads as deliberate.
- [ ] The report lists who withheld what, so a missing face is never mistaken
      for a bug.
- [ ] The opt-out is documented where a contributor will actually find it.

**Do not** add a reason field, an approval step, or an expiry. It is one array.

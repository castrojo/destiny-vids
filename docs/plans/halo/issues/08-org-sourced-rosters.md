# H-08 — Roster the squad from arbitrary GitHub orgs, not the Bluefin repo list

**What:** `tools/ensemble.py` builds its pool from a hardcoded list of five
Project Bluefin repositories (`tools/ensemble.py:41–47`), one `gh api
repos/{repo}/commits` call each, filtered by a calendar month. #11 wants the
squad sourced from the **contributor base of several orgs**, and wants that list
swapped per run.

**Scope:**
- Add org sourcing: `--org` (repeatable) walks `GET /orgs/{org}/repos` and then
  each repo's contributors/commits, deduplicating by login across orgs. Keep
  `--repo` working — it is how a single-repo pool is expressed today.
- Read the org list from the cast file (H-12) so a re-run swaps casts, not flags.
- Keep the properties the tool already guarantees, because they are the reason it
  is trustworthy: bots filtered, a failing repo costs a few names rather than the
  month, assignment deterministic and month-seeded, and contributors who do not
  fit a slot reported in `uncredited` rather than dropped.
- Budget the API. `ublue-os` alone is ~93 repos, so an org walk is ~100 requests
  before any commit query; authenticated limit is 5,000/hour. Cache the repo
  list per run and page at `per_page=100`.
- Org **membership** is not the contributor base — `GET /orgs/{org}/members`
  returns public members only and misses everyone who contributes without joining.
  Use contributions, which is also what the existing pool means.
- Record roster provenance: which orgs, which window, how many names, which repos
  errored. A squad that quietly shrank should be visible in the roster file.

**Acceptance:**
- [ ] `python3 tools/ensemble.py roster --org OpenGamingCollective --org FyraLabs
      --month YYYY-MM` produces a roster with per-org provenance.
- [ ] A non-existent org is reported and skipped, not fatal — and is visible in
      the output, because H-04 exists precisely because two of the named orgs
      were not real.
- [ ] Determinism test: the same (month, org list, shot list) yields identical
      assignments.

**Depends on:** H-04

**Automatable:** yes.

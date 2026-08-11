# Epic C — Affiliation and emblems: the bling matches the org

**Parent:** #9 · **Depends on:** B · **Blocks:** F · **Blocked by:** J1 (for C4)
**Design:** [`docs/plans/wolves/design.md` §3](../design.md)

An affiliation is a claim about where a real person works. It comes from what
that person published on their own GitHub profile, it is normalized through a
checked-in vocabulary, and when it does not resolve, **nothing renders**. Tiers
decorate the organization's band and nothing else — individuals are never tiered.

**Done looks like:** a nameplate carries a large org mark with its tier's chrome
when the person's self-declared company resolves, and carries no band at all when
it does not — with the unrecognized string reported so someone can add an alias.

**Invariants for every sub-issue here**

- Never fuzzy-match a company string. Exact alias, or `null`.
- The tier palette is only ever passed to the org band's draw call.
- Org marks are trademarks, not assets: gitignored, unmodified, never composited.

---

## C1 — `vocab/affiliation.yaml`

**Labels:** `enhancement` · **Depends on:** —

A new controlled vocabulary in the shape of the existing ones: org id → display
name, `tier`, `aliases[]`, `mark` (the path in the owner's official artwork repo,
not a URL to hotlink). Tiers are CNCF's real levels — `platinum`, `gold`,
`silver`, `end_user` — plus `none`. Seed it with the orgs that Bluefin
contributors actually declare today, and no others.

Per `AGENTS.md`, a new enum means editing `vocab/*.yaml` **and** the schema:
add the tier enum to `schema/person.schema.json` and assert the two agree.

**Acceptance**

- [ ] `vocab/README.md` gains a row for the file (one line; that table is the
      index of vocabularies).
- [ ] Every alias is lowercase-normalized and unique across all orgs — an alias
      that matches two orgs is a bug, and a test proves it cannot exist.
- [ ] The tier enum in the vocab and in the schema are asserted equal, the way
      the existing vocab/schema pairs are.
- [ ] A comment records where a tier came from (`cncf_membership_level` in
      `cncf/landscape`'s `landscape.yml`), so a refresh has a source.

---

## C2 — Resolve `company_raw` → org id

**Labels:** `enhancement` · **Depends on:** C1, B2

A pure function: strip `@`, lowercase, collapse whitespace and punctuation, look
up the alias table, return the org id or `None`. That is the whole algorithm, and
its restraint is the feature.

**Acceptance**

- [ ] `"@github"`, `"GitHub"`, `"GitHub, Inc."` → `github` when all three are
      aliases; `"the internet"` → `None`.
- [ ] No edit distance, no substring matching, no "contains the word Red Hat".
      A test asserts a near-miss string resolves to `None`.
- [ ] Unresolved strings are reported once per person, with the raw string.
- [ ] A person with `affiliation` in `withhold` resolves to `None` regardless.

---

## C3 — Tier chrome, and the rule that it stops at the band

**Labels:** `enhancement` · **Depends on:** C1, F1

Extend `tools/plate.py`'s `VARIANTS` with the tier palettes, reusing the existing
`leader` gold and `trustee` silver rather than inventing new colors. Draw an org
band: mark (or org name) plus a tier rule, in the tier's palette. Everything else
on the plate keeps the person's own chrome.

**Acceptance**

- [ ] The tier palette is passed only to the band's draw call — a test renders
      the same person at `platinum` and at `none` and asserts every pixel outside
      the band is identical.
- [ ] `end_user` and an unrecognized tier both fall back to the default blue.
- [ ] No affiliation → no band, and the plate's height shrinks accordingly.
- [ ] The band never changes the name's size, weight, or color.

**Do not** add a tier to the person, the avatar ring, the title, or the ribbons.

---

## C4 — Org marks: fetch, cache, degrade

**Labels:** `enhancement` · **Blocked by:** J1

Mark files live in gitignored `emblems/`, fetched from the owner's official
artwork repository (for CNCF and its projects, `cncf/artwork`). The renderer
draws the mark **unmodified and uncropped, with clear space, on a neutral field
beside the chrome**, at a size the mark's own brand guide permits. A missing mark
degrades to the org's name set in the tier chrome — which is also the fallback
when J1 says a mark may not ship.

**Acceptance**

- [ ] `emblems/` is gitignored; a test asserts no image file is tracked under it.
- [ ] The renderer never scales a mark non-uniformly, never recolors it, and
      never draws chrome over it.
- [ ] Text fallback is exercised by a test — the offline suite must render a
      plate for an affiliated person with no mark on disk.
- [ ] A short `NOTICE`-style note records each mark's source and terms.

**Do not** commit a logo, place a mark inside the hex crest, or ship this before
J1 closes. The Linux Foundation's terms prohibit composite marks and implied
endorsement, and issue #6 is what settling that after the design costs.

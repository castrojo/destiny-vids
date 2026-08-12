# Epic E — Heraldry: the Credly ribbon rack

**Parent:** #9 · **Depends on:** B · **Blocks:** F · **Blocked by:** J2
**Design:** [`docs/plans/wolves/design.md` §5](../design.md)

Badges become a service ribbon rack along the bottom of the nameplate: rows of
small stripes that encode a career at a glance, the way a military rack does and
for the same reason. We render heraldry *about* a badge; we never redistribute
the badge artwork.

**Done looks like:** a contributor who has published Credly badges and linked
Credly from their GitHub profile gets two rows of ribbons under their name, in a
stable order, generated entirely from checked-in metadata.

**Invariants for every sub-issue here**

- Opt-in by construction: no GitHub → Credly link means no ribbons.
- The badge *image* is never fetched, cached, or drawn.
- Deterministic ordering and deterministic colorways. Ribbons are a record.

---

## E1 — Badge metadata in the person record

**Labels:** `enhancement` · **Depends on:** B2 · **Blocked by:** J2

Read the Credly handle only from a `credly.com` link the person published on
their own GitHub profile (`blog`, or a profile social link). Fetch their public
badge list, store `{issuer, name, issued_on}` per badge in `people/<login>.json`,
and nothing else.

The endpoint (`https://www.credly.com/users/<handle>/badges.json`) is public and
key-free but **undocumented and unsupported** — a side effect of profile
rendering, not a product. Treat it accordingly: cache what you read, and treat a
failure as "no new badges", never as an error that fails a render.

**Acceptance**

- [ ] No GitHub → Credly link, or `badges` in `withhold`, means the fetch never
      happens at all.
- [ ] A failed or changed endpoint degrades to the cached list with a `warn`; a
      render never depends on Credly being up.
- [ ] Only `issuer`, `name`, `issued_on` are stored. No image URL, no badge id
      that only serves to fetch an image, no description.
- [ ] Tests use a canned payload; no test touches the network.

---

## E2 — Ribbon geometry and colorway

**Labels:** `enhancement` · **Depends on:** E1

One ribbon: a small chamfered bar (matching the plate's 16 px chamfer language)
carrying two or three vertical stripes. `H(issuer, name)` selects the stripe
pattern and colors from a checked-in palette that harmonizes with the plate
chrome — the same trick the sparkline uses, for the same reason.

Repeats of the same badge name collapse into one ribbon carrying **N−1 pips**,
the way a repeat award takes an oak-leaf cluster instead of a second ribbon.

**Acceptance**

- [ ] Same badge → same ribbon, forever; a test pins a known badge's colorway.
- [ ] Two different badges are visually distinct at nameplate scale — assert a
      minimum color distance between adjacent ribbons in a rack.
- [ ] Ribbons read at 10 feet: at least 12 px of stripe width at 1080p.
- [ ] The palette is checked in, documented, and derived from the plate's
      existing palette rather than invented alongside it.

---

## E3 — Rack layout

**Labels:** `enhancement` · **Depends on:** E2

Rows of three, most recent first (then by name), **two rows maximum**, overflow
collapsing into a `+N` device on the last ribbon. The rack hangs below the
title line and inside the plate's padding.

**Acceptance**

- [ ] 0 badges → no rack and no height cost.
- [ ] 7+ badges → exactly 6 ribbons and a `+N`; a test pins the arithmetic.
- [ ] Ordering is deterministic and stable when two badges share a date.
- [ ] The rack never widens the plate past its existing max, and never pushes
      the plate out of the title-safe area.

**Do not** let a rack grow to a third row "just this once". A rack that fills the
plate is a rack nobody reads, and the plate is a claim about a person, not a
trophy case.

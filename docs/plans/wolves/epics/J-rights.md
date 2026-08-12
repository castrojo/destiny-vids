# Epic J — Rights, Code of Conduct, and consent

**Parent:** #9 · **Blocks:** C4, D1, E1, H1 · **Depends on:** —
**Design:** [`docs/plans/wolves/design.md`](../design.md)

Four questions that are cheaper to answer now than to discover in a finished
video. Issue [#6](https://github.com/castrojo/destiny-vids/issues/6) is the
precedent: a licence that was checked after the treatment was designed cost the
whole treatment.

None of these are code. Each closes with a written answer in the repo and a
decision recorded in the design doc.

**The repo's existing posture, which these must not quietly break:** index
metadata, ship no third-party media, keep output non-commercial, and carry
`usage_class` + `source_rights_note` on every source record.

---

## J1 — May we render the CNCF and project marks?

**Labels:** `question` · **Blocks:** C4, G1

Everything in `cncf/artwork` is licensed under the **Linux Foundation Trademark
Usage Guidelines**, not an open-source licence. The guidelines are specific: do
not alter a mark's colors or proportions, do not imply sponsorship or
endorsement, and **do not combine the marks with other marks into a composite**.
A CNCF logo set inside a Destiny-style hex crest, over Bungie footage, is
plausibly all three at once.

**Answer, in writing:**

- [ ] Is a mark drawn unmodified, uncropped, with clear space, on a neutral field
      *beside* the chrome acceptable — or does the surrounding Destiny treatment
      make it a composite regardless?
- [ ] Does a fan video that credits contributors by employer imply sponsorship?
- [ ] If either answer is no: is the text fallback (org name in tier chrome) the
      permanent design, or do we ask `info@cncf.io`?
- [ ] Record the outcome in `design.md` §3 and in a `NOTICE`-style file.

Sources: <https://github.com/cncf/artwork/blob/master/LICENSE.md>,
<https://www.linuxfoundation.org/trademark-usage>,
<https://www.cncf.io/brand-guidelines/>.

---

## J2 — May we show Credly badges, and how?

**Labels:** `question` · **Blocks:** E1

Credly's supported display path is their embed widget. The public
`users/<handle>/badges.json` endpoint is undocumented and unsupported, and badge
*images* are the issuer's marks with no third-party display licence.

**Answer, in writing:**

- [ ] Is reading a person's *public* badge list, storing only
      `{issuer, name, issued_on}`, and rendering our own derived ribbon
      acceptable under Credly's terms?
- [ ] Does naming an issuer on screen need that issuer's permission?
- [ ] Confirm the design decision that we never fetch or draw badge artwork.
- [ ] If the answer is "widget only", the fallback is ribbons with no issuer
      name — decide that now, not in review.

---

## J3 — Music licensing

**Labels:** `question` · **Blocks:** H1

Bungie's fan-content policy covers the footage. It says nothing about the song
over it, and a music claim is the single most likely way this project's output
gets taken down.

**Answer, in writing:**

- [ ] Which `usage_class` values are acceptable for a track (CC-BY, CC0,
      licensed-for-use, permission-in-writing)?
- [ ] Is a `source_rights_note` required on every track record? (The design says
      yes; make it explicit.)
- [ ] State plainly that audio is never committed, so `media/` gitignores it the
      way it gitignores footage.
- [ ] Write the rule into `AGENTS.md`'s Rights section in one sentence.

---

## J4 — CNCF Code of Conduct review of the title vocabulary

**Labels:** `question` · **Blocks:** D1

A generated title names a real person on screen. Thousands of combinations means
nobody will read them all before they ship, so the vocabulary has to be safe by
construction.

**Answer, in writing:**

- [ ] Review every position for: gendered language, implied authority over
      another person, military rank, anything demeaning, and anything that reads
      as a real governance role.
- [ ] Confirm the forbidden list covers CNCF's actual role names (`ambassador`,
      `TOC`, `TAG lead`, `chair`, `maintainer`, `fellow` …).
- [ ] Decide the escalation path: what happens when somebody dislikes their
      title? (Proposal: it is data — open a pull request, change it, done.)
- [ ] Record the review date and reviewer alongside the vocabulary.

---

## J5 — Consent for faces and affiliation

**Labels:** `question`, `documentation` · **Blocks:** B4

Crediting a login is one thing. Putting somebody's face on screen at 20% of frame
height, next to their employer, is another — and the project's own casting rule
already says a claim about a real person has to be right or absent.

**Answer, in writing:**

- [ ] Confirm opt-**out** (`withhold`) rather than opt-in, and say why: the
      ensemble already credits contributors by name, and requiring opt-in would
      silently drop the people who never see the request.
- [ ] Document the one-line opt-out where contributors will find it, in the
      repository they actually contribute to.
- [ ] Confirm that a withheld field is reported, never silently blank.
- [ ] Decide whether a person may withhold *everything* (proposal: yes — no
      record, no line, no plate, reported as withheld).

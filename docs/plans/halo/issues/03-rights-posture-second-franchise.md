# H-03 — Rights posture for a second franchise: Microsoft's GCUR, not Bungie's policy

**What:** every rights statement in this repo names Bungie. Halo is a Microsoft
property governed by the **Game Content Usage Rules**, a different document with
different terms. Indexing Halo footage while telling every record that Bungie's
policy permits it is simply a false statement in the data.

**Where it is hardcoded:**

| Location | Today |
|---|---|
| `tools/ingest.py:31–35` | `RIGHTS_NOTE` is the Bungie paragraph, written into every ingested record |
| `schema/video.schema.json` `source_rights_note` | description tells the writer to state Bungie's policy |
| `schema/video.schema.json` `usage_class` | `const: third_party_copyrighted`, described as "Bungie, Inc. copyrighted material" |
| `AGENTS.md` § Rights | names Bungie's fan-content policy only |

**Differences that matter** (citations in
[`../research.md`](../research.md#1-rights)):
- The GCUR requires a specific attribution/disclaimer and a link to the rules,
  and forbids implying official endorsement.
- Publishing under the GCUR grants Microsoft a royalty-free licence to the fan
  work. Bungie's policy has no equivalent clause.
- The GCUR does not cover soundtrack recordings as standalone audio (H-02).

**Scope:**
- `RIGHTS_NOTE` becomes per-universe, selected by the record's `universe` (H-05).
- Generalize the two schema descriptions; keep `usage_class` as
  `third_party_copyrighted` — it is still accurate for Halo footage under the
  index reading, and H-00 revisits it only if the generation reading wins.
- Add the Halo clause to `AGENTS.md` § Rights, including where the required
  attribution string has to appear.
- Existing Destiny records keep their note verbatim: this is additive.

**Acceptance:**
- [ ] A Halo video record carries a Halo rights note; a Destiny one is unchanged
      byte-for-byte.
- [ ] A test asserts the note matches the record's universe.
- [ ] `AGENTS.md` states both policies and where the GCUR attribution appears.

**Depends on:** H-00 (which framework applies at all), H-05 (`universe` exists)

**Automatable:** partly — the plumbing is mechanical; the exact policy text must
be copied from the live page, and the publishing decision is the owner's.

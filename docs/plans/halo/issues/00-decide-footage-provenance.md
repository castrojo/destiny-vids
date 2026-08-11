# H-00 — Decide the footage provenance: index Halo footage, or generate it

**What:** #11 asks for a "live-action Halo campaign" and writes its subject /
setting / audio block in the shape of a generative video prompt. This repo is an
index of footage that already exists. Those are two different projects, and every
other issue in this plan is written to be provenance-agnostic precisely because
this one has to be answered first.

**The two readings:**

| | Index reading | Generation reading |
|---|---|---|
| Where shots come from | Official Halo footage on the HALO/Xbox channels, indexed by timecode | Clips produced from the prompt in #11 |
| `usage_class` | `third_party_copyrighted` — the schema's current `const` fits | Not third-party; the `const` no longer fits and the rights model needs a new bucket |
| Rights framework | Microsoft's Game Content Usage Rules (H-03) | The generator's terms, plus likeness questions about real people |
| `clean` | Tagged from the frame, as today | Tagged from the frame, as today — a generated HUD disqualifies a shot exactly like a shipped one |
| Repo work | H-05 + H-07 as written | H-05, and H-07 becomes "a new provenance class" instead of "ingest a corpus" |

**Why it blocks:** H-07 cannot start, and H-03 cannot be written correctly,
until this is settled. Nothing else in the plan moves — the campaign format
(H-09), the score (H-10), the HUD (H-11) and the casting (H-08, H-12) sit on top
of either answer unchanged.

**Scope:**
- Owner states which reading #11 means.
- If generation: open a follow-up for the provenance class — `usage_class` gains
  a value, `source_rights_note` describes the generator's terms, and the
  shot-detection pass runs over generated clips rather than published ones.
- If indexing: H-07 proceeds as written.

**Acceptance:**
- [ ] The reading is recorded in `docs/plans/halo/design.md` §3 as decided, not open.
- [ ] H-07's scope is updated to match.

**Depends on:** —

**Automatable:** no — it is a decision about what the project is, and only the
owner can make it.

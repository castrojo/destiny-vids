# H-06 — Move the search lexicon out of `tools/search.py` and into the vocab

**What:** the natural-language lexicon is ~125 lines of Python dictionaries —
`CLASS`, `ELEMENT`, `FACTION`, `ACTIVITY`, `DESTINATION`, `ACTION`, `PHRASES`,
`SINGLE` (`tools/search.py:40–164`). Every Destiny character and every cast
person is a hand-written entry, kept in sync with `vocab/casting.yaml` by a
comment and a test. A second universe doubles the file and puts "vex" and
"covenant" in the same namespace, so a Halo beat can pick up a Destiny filter.

**Why it matters beyond tidiness:** `tools/story.py` parses every beat through
this lexicon, and `docs/skills/editing.md` already warns that domain words in a
beat become hard filters rather than prose. With two universes sharing one
lexicon, that failure mode gets a second source and no error message.

**Scope:**
- Move the phrase→facet mappings into the vocab, per universe for domain terms
  and shared for the neutral ones (`close-up`, `wide shot`, `crowd`, `slow
  motion`, `ensemble`, `gameplay`…).
- Generate the cast phrases from the lead map instead of hand-listing them:
  character key, `aka` entries, `display_name` and `person` already exist in
  `vocab/universes/<universe>/casting.yaml`.
- `search.py` loads the lexicon for the universes present in the segment pool.
- Keep `tests/test_search.py::test_every_cast_person_and_character_is_queryable`
  green — it is the test that guarantees a cast person can be retrieved, and it
  should now hold for both universes without new hand-maintained entries.

**Acceptance:**
- [ ] No character or person name is hardcoded in `tools/search.py`.
- [ ] A Halo query cannot match a Destiny-only facet, and vice versa.
- [ ] Existing search and story tests pass unchanged.

**Depends on:** H-05

**Automatable:** yes.

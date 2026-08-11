# Epic D — Titles: `$Position of $Project`

**Parent:** #9 · **Depends on:** B · **Blocks:** F · **Blocked by:** J4 (for D1)
**Design:** [`docs/plans/wolves/design.md` §4](../design.md)

A new contributor arrives from Kubernetes and gets "Shipwright of Kubernetes".
Someone else arrives from Prometheus and gets "Cartographer of the Watchfire".
Named leads keep the titles they were written with — this is for the new people.

**Done looks like:** `title_for(login, project)` returns a stable, lore-flavored,
Code-of-Conduct-clean title, and the same person gets the same title in every
render until they change projects.

**Invariants for every sub-issue here**

- Deterministic. A title is a credit, not a slot machine.
- No real governance word, ever. "Shipwright of Kubernetes" is evident fiction;
  "Maintainer of Kubernetes" is a false claim about a real role.
- A lead with an authored `plate.title` in `vocab/casting.yaml` is never
  overwritten.

---

## D1 — `vocab/titles.yaml`: positions and the forbidden list

**Labels:** `enhancement` · **Blocked by:** J4

About 64 Destiny-flavored positions, each a job somebody does rather than a rank
somebody holds. Seed set to build on — the trades and the keepers, which is what
open source actually is:

```
Shipwright · Skiffwright · Cartographer · Pathfinder · Wayfinder · Cryptarch
Gunsmith · Forgemaster · Ironsmith · Gatesmith · Archivist · Chronicler
Loremender · Lightkeeper · Lanternbearer · Kindler · Ember-tender
Watchfire-keeper · Signaller · Relay-tender · Frame-tender · Vaultkeeper
Wallwright · Bulwark · Bastion · Warden · Stargazer · Starfarer · Voidfarer
Tidebreaker · Netweaver · Threadwright · Loomkeeper · Beaconwright
```

And the forbidden list, checked at test time against every generated title:

```
maintainer · chair · steering · toc · tag lead · sig lead · approver · reviewer
ambassador · fellow · board · owner · founder · director · officer
commander · captain · marshal · general · admiral · chief · lord
```

**Acceptance**

- [ ] ≥ 60 positions, each ≤ 2 words, each rendering cleanly at nameplate size.
- [ ] No position appears in the forbidden list, and a test enforces it against
      substrings, not just exact matches.
- [ ] No position is gendered, implies authority over another person, or carries
      a military rank.
- [ ] Each position is a *job*: it reads as something done, not something won.
- [ ] The list is reviewed under the CNCF Code of Conduct (J4) before merge.

---

## D2 — `vocab/projects.yaml`: projects, synonyms, repos

**Labels:** `enhancement` · **Depends on:** —

Project id → `display` name, `synonyms[]` (≈8 each), and `repos[]` mapping a
GitHub repo to the project so the roster can answer "which project did this
person come from". Synonyms are nicknames *of that project* — "the Helm" for
Kubernetes, "the Watchfire" for Prometheus — never another project's name, never
a mark, never misleading.

**Acceptance**

- [ ] Positions × synonyms clears 1,000 combinations with the seed projects; a
      test asserts the count, because "thousands of combinations" was the ask.
- [ ] No synonym collides with another project's synonym or display name, and a
      test proves it.
- [ ] Every repo in `tools/ensemble.py`'s `DEFAULT_REPOS` maps to a project.
- [ ] A repo with no mapping resolves to no project, which means no generated
      title — reported, never guessed.

---

## D3 — `title_for()` and where it plugs in

**Labels:** `enhancement` · **Depends on:** D1, D2, B2

```python
def title_for(login: str, project: str) -> str | None
```

Truncated SHA-256 over `(login, project, "pos")` and `(login, project, "syn")`
picks the position and the synonym. `None` when the project is unknown. Write the
result into the person record so a render never recomputes it from a moving
vocabulary — and so a title change shows up as a reviewable diff.

**Acceptance**

- [ ] Same inputs → same title, across processes and Python versions
      (`hash()` is salted per process; use `hashlib`).
- [ ] Adding a position to the middle of the vocabulary reshuffles titles — so
      the test that pins a handful of known logins to their titles is the
      early-warning system, and re-crediting people is a deliberate act.
- [ ] A cast lead's authored `plate.title` wins; a test asserts a lead's title is
      untouched by generation.
- [ ] Every generated title is checked against the forbidden list at generation
      time, not only at vocabulary-review time.

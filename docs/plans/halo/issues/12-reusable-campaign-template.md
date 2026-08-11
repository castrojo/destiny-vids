# H-12 — Re-run the same campaign template with a different cast

**What:** #11 asks for the structure to be re-runnable "for multiple videos with
different casts of GitHub users swapped in", sourcing squad names from the
contributor base of whichever orgs are relevant. That means separating what
varies from what does not.

| Varies per run | Fixed by the template |
|---|---|
| `casts/<name>.yaml` — lead bindings, display copy, org list | Episodes, movement kinds, beat patterns |
| The corpus the beats are matched against | The rules: alternation, one track per combat movement, no reuse |
| Track assignment from the catalogue | The HUD deck and its copy fields |

**Scope:**
- A cast file: lead bindings (character → person → display copy) plus the org
  list H-08 rosters from. It is the only file a new run edits. The universe pack
  (H-05) keeps the *roles* — character ids, aliases, constraints — because Halo
  has one Sgt. Johnson no matter who plays him; the cast file binds a role to a
  person for one run.
- **Decide where casting resolves, and ship one answer.** `casting.person` is
  derived and *stored on every segment* today (`tools/derive.py`), and search and
  plates read the stored value — so swapping a cast file does not recast an
  already-assembled corpus. Either re-run `derive.py` per campaign (legal: it is
  the only writer, so nothing is hand-edited) or resolve casting at assembly time
  from the run's cast file and stop storing `person` on the segment. Both is a
  bug waiting to happen: two sources of truth for who is credited.
- `tools/campaign.py --template … --cast …` as the whole re-run interface.
- **Determinism.** `ensemble.py`'s guarantee extends up: the same (template,
  cast, roster month, corpus) must produce byte-identical cut lists and
  manifests. A re-render that reshuffles assignments re-credits people for shots
  they were not in, which is the same failure rule 3 forbids at tagging time.
- A second cast file, exercised in tests, so "swappable" is proven rather than
  asserted.

**Acceptance:**
- [ ] Two cast files over one template produce two campaigns differing only in
      who is credited.
- [ ] Swapping the cast file changes every credit, with no stale `person` left
      over from a previous run.
- [ ] Running the same inputs twice produces identical output files.
- [ ] Nothing about a cast is hardcoded in `tools/campaign.py`.

**Depends on:** H-08, H-09, H-11

**Automatable:** yes.

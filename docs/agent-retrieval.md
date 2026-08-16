# Agent Retrieval — Mapping Natural-Language Prompts onto the Taxonomy

How the retrieval agent turns a loose editing prompt ("show us Hunters with Arc") into a ranked list of timestamped segments. The reader is assumed to know Destiny and editing; no pipeline internals here.

Retrieval is **hybrid**:

1. **Hard facet filters** — controlled-vocabulary enums (`class`, `element`, `faction`, `shot_scale`, `composition`, `activity`, `action`, `casting.role`, `casting.character`, `casting.person`, `footage_tier`, …). Exact, composable, explainable.
2. **Caption similarity** — a token-overlap stand-in for embedding similarity over each segment's free-text `caption` field (plus `character` names and `mood` tags), catching the long tail of things the enums don't name (specific weapons, "helmet", "ships", vibes). A `norm_token` pass does crude singular-ization in the meantime, so a query for "guardians" still matches a caption's "Guardian".
3. **Editorial ranking** — the project's standing bias, always applied: clean footage first, cinematic over gameplay, Guardian-centric, mythic register.

Wrapping all three: **the candidate pool excludes unclean shots by default.** A shot with an un-removable overlay (HUD, nameplates, burned-text, talking-head) cannot be cut into anything, so it isn't a weak candidate — it's *absent*, before a single facet filter or ranking rule runs. Pass `--include-unclean` to `tools/search.py` to override this for triage; the shots reappear, heavily penalized (§2), never silently promoted into a real result.

The output contract: a ranked list of segments (video id + in/out timestamps) with a one-line reason each, plus notes on anything that was relaxed or matched semantically.

---

## 1. Query Parse

Parse the prompt into two channels:

```jsonc
{
  "filters":       { /* enum facets — hard constraints */ },
  "caption_terms": [ /* leftover words, scored by caption similarity */ ]
}
```

There is no third, per-query "weights" channel — `parse_query` never emits one. The one and only per-query weight that actually exists is the lead bonus, and it isn't part of the parse output at all; it's derived straight from the filters (see below).

Parse rules of thumb:

- **Named Destiny entities** with a matching enum → hard filter (`Hunter` → `class=hunter`, `Cabal` → `faction=cabal`, `raid` → `activity=raid`).
- **Cinematography terms** with a matching enum → hard filter (`close-up` → `shot_scale`, `establishing` → `composition`, `slow-motion` → `pacing`).
- **Composition/tier phrases** → hard filter: `crowd` / `crowd of guardians` → `composition=crowd`; `fireteam` → `composition=group`; `ensemble` / `background guardians` / `anonymous guardians` → `casting.role=ensemble`; `named character` / `lead` → `casting.role=lead`; `gameplay` → `footage_tier=gameplay`; `cinematic` → `footage_tier∈{cinematic,mixed}`.
- **Cast names** — a character name (`Elsie Bray`, `Zavala`, `Cayde-6`, `Saladin`) *or* the person playing them (`Laura`, `Kelsey`, `castrojo`, `jeefy`) → hard filter on `casting.character` / `casting.person` respectively. Either half of a binding resolves to the same lead's footage — "Zavala" and "Kelsey" are the same query in practice. `tools/search.py`'s `PHRASES` table carries an entry for every current cast character and person (see `docs/taxonomy.md`'s casting section for the full roster). Note the field name: `casting.person`, not `casting.performer`.
- **Adjectives of tone, weapon names, and anything else the taxonomy doesn't enumerate** ("epic", "lonely", "Wish-Ender", "hero shot") → **caption terms**, not filters. This includes `mood` and `register` themselves: despite being real schema fields, nothing in the current parser turns a tone word into a `mood` or `register` filter — they fall through to the token-overlap caption signal, and register's actual pull on the result order comes entirely from the standing editorial ranking (§2), which applies to every candidate regardless of what the query asked for.
- **Never invent an enum value.** A term with no matching enum is caption-only, full stop.

### The lead bonus is query-triggered, not standing

`lead_weight_for(filters)` returns `1.0` if the parsed filters contain **any** `casting.*` key, else `0.0`. That single number is the entire per-query weight mechanism in the codebase — there's no generic override channel, and `register`'s multiplier is always its default of `1.0` in practice, because nothing else ever populates `score_segment`'s `weights` dict.

The point of gating it this way: the +0.40 lead boost exists so that *"give me Elsie"* hands you Elsie's footage above everything else — but a query that never names a character shouldn't have a lead shot muscle in just because leads generally score well. "close-up on a Titan's helmet" (below) asks for a class and a scale, not a person, so `lead_weight_for` returns `0.0` and the boost stays off even though a lead's footage (Saladin, who is a Titan) is sitting right there in the candidate pool. Both `tools/search.py` and `tools/story.py` call it the same way.

### Canonical parses

**"show us Hunters with Arc"**
```json
{"filters": {"class": ["hunter"], "element": ["arc"]}, "caption_terms": []}
```
Fully structural, and this is the marquee case for the new model. The only Hunter+Arc footage in the corpus, `hunter-arc-pvp`, is `content_type: gameplay` with `overlays: [hud, nameplates]` — unclean. Default search excludes it from the pool before ranking even runs:

```
0 match(es) from a pool of 7/9 segment(s):
  (nothing matched; try fewer constraints)
```

That empty result **is the correct answer**, not a bug: this footage cannot be cut into a story. `--include-unclean` surfaces it anyway, for triage, buried under the −1.00 penalty:

```
[+0.00] yt_arc30_crucible_viDoc 2:14–3:40  seg_arc_hunter_crucible_0134-0220
        why: -1.00 UNCLEAN (overlays cannot be removed), -0.15 gameplay tier (coverage),
             +0.20 ensemble (1 contributor slot(s)), +0.10 reads as anyone,
             +0.20 guardian/environment salience, +0.15 mythic register
```

**"close-up on a Titan's helmet"**
```json
{"filters": {"shot_scale": ["CU", "ECU", "MCU"], "class": ["titan"]}, "caption_terms": ["helmet"]}
```
Two matches survive, and the order is instructive:

```
[+2.85] seg_titan_helmet_cu_0112-0118   caption 1.00, +1.00 clean, +0.20 cinematic tier,
                                         +0.20 ensemble (1 contributor slot(s)), +0.10 reads as anyone,
                                         +0.20 salience, +0.15 mythic
[+2.55] seg_roi_saladin_cu_0102-0107    caption 1.00, +1.00 clean, +0.20 cinematic tier,
                                         blocked cast (require_far) — no boost,
                                         +0.20 salience, +0.15 mythic
```
`seg_roi_saladin_cu` is Saladin — a lead, and Saladin is a Titan class-wise — but it's also the one shot in the whole corpus that fails the sole constrained binding: `MCU` isn't in `require_far`'s `{ELS,LS,MLS,MS}`, so `casting.usable = false` and `constraints_failed = [require_far]`. Two independent things keep it from any lead score here: the query never asked for a `casting.*` facet, so `lead_weight_for` would be `0.0` even for a *usable* lead — and this lead isn't usable regardless, which `score_segment` reports outright as `blocked cast (require_far) — no boost` rather than staying silent about it. That reason line appears whenever `role == lead` and `usable == false`, whether or not the query named the character — a blocked constrained cast never hides. The anonymous ensemble helmet shot picks up its own +0.20 (plus a +0.10 substitutability tie-break), which is enough to edge out the otherwise near-identical, and here doubly-unboosted, Saladin shot.

**"wide establishing shot of the Traveler"**
```json
{"filters": {"shot_scale": ["ELS", "LS", "MLS"], "composition": ["establishing"], "destination": ["the_traveler"]}, "caption_terms": []}
```
One match:
```
[+1.85] seg_traveler_establishing_0003-0011
        why: +1.00 clean, +0.20 guardian/environment salience, +0.15 mythic register
```
No `register` filter exists in the query-parse vocabulary at all — the "mythic" framing here comes entirely from the standing +0.15 register bonus in §2, which every clean, register ≥ 0 candidate gets whether or not the query asked for it.

**"a crowd of guardians" vs. "fireteam"**
```json
{"filters": {"composition": ["crowd"]}, "caption_terms": []}
{"filters": {"composition": ["group"]}, "caption_terms": []}
```
```
[+2.35] seg_tfs_launch_tower_crowd_0112-0118   +0.20 ensemble (6 contributor slot(s)) …
[+2.25] seg_tfs_launch_bridge_0047-0054        +0.20 ensemble (3 contributor slot(s)) … +0.10 traversal hero
```
Same +0.20 ensemble scoring regardless of slot count — `slots` isn't itself a scoring term, it's a casting fact reported alongside the reason (and consumed downstream by `tools/ensemble.py assign`, which places one contributor per slot). "crowd" seats up to 6 contributor tiles, "group"/"fireteam" up to 3.

**"Elsie Bray hero shot"**
```json
{"filters": {"casting.character": ["elsie_bray"]}, "caption_terms": ["hero"]}
```
```
[+2.95] seg_bl_elsie_hero_0102-0108
        why: caption 1.00, +1.00 clean, +0.20 cinematic tier,
             +0.40 lead: elsie_bray (cast), +0.20 salience, +0.15 mythic register
```
The query supplies a `casting.character` filter, so `lead_weight_for` returns `1.0` and the +0.40 lands. This is the ordinary, unconstrained case the mechanism mostly exists for: name a lead, get that lead's footage boosted to the top, full stop — no resemblance constraint to check, no scale restriction. (The one binding in the corpus that isn't this simple, `saladin` → `jeefy`, is worked through above and just below — asking for it directly doesn't rescue a shot that fails its own constraints.)

**"anonymous guardians" vs. "named character"**
```json
{"filters": {"casting.role": ["ensemble"]}, "caption_terms": []}
{"filters": {"casting.role": ["lead"]}, "caption_terms": []}
```
The first returns all 3 clean ensemble shots in the corpus; the second returns all 3 clean lead shots (two Saladins, one Elsie Bray) — but not all three get the same boost, because `casting.usable` is still checked even when the query asks for `casting.role = lead` directly:
```
[+2.45] seg_roi_saladin_far_0032-0041   … +0.40 lead: saladin (cast) …
[+2.45] seg_bl_elsie_hero_0102-0108     … +0.40 lead: elsie_bray (cast) …
[+2.05] seg_roi_saladin_cu_0102-0107    … blocked cast (require_far) — no boost …
```
This is the direct A/B against the Titan's-helmet example above: same Saladin CU shot, same `blocked cast` outcome. This time `lead_weight_for` does return `1.0` — the query's filters genuinely contain a `casting.*` key — but the weight never gets multiplied against anything, because the blocked branch is checked ahead of it: `casting.usable = false` short-circuits the lead bonus regardless of what the query asked for. Naming the character, or even naming the role directly, cannot rescue a shot that fails its own binding's constraints.

**"guardians parkouring across a bridge"**
```json
{"filters": {}, "caption_terms": ["guardians", "parkouring", "across", "bridge"]}
```
Zero hard filters. `"parkouring"` doesn't match the `traversal` token table (it only recognizes the bare `parkour`; the multi-value facet matcher strips a trailing `s`, not `-ing`), and `"guardians"`/`"bridge"` don't correspond to any enum either. This is pure caption-plus-editorial-ranking:
```
[+2.50] seg_tfs_launch_bridge_0047-0054   caption 0.75, +1.00 clean, +0.20 ensemble,
                                           +0.10 reads as anyone, +0.20 salience,
                                           +0.15 mythic, +0.10 traversal hero
```
`caption 0.75` is `norm_token`'s crude singular-ization at work — "guardians" collapses to "guardian" and matches the caption's "Guardians" — plus "bridge"; 3 of 4 query terms found, none of the plural-mismatch losses a real embedding index wouldn't already avoid.

---

## 2. Editorial Ranking (always applied)

Filtering (and the pool-level clean exclusion above it) produces candidates; **this scoring pass produces the order**. It's the project's standing bias: clean, cinematic-first, Guardian-centric, mythic footage is the house style, applied to every result regardless of what the query asked for.

One weight is genuinely query-conditional — the lead bonus, gated by `lead_weight_for` (§1). Everything else below fires the same way on every query.

### Scoring recipe

Start every candidate at `score = caption_sim(seg, caption_terms) * caption_weight` — a 0–1 token-overlap similarity (embedding cosine similarity in a real deployment), neutral at `0.5` when the query has no caption terms. `caption_weight` is `1.0` for search — a browse wants the editorially strongest shot in the neighborhood — and `3.0` for `tools/story.py` (§5) — a beat is a specific instruction that should out-rank a merely well-rated shot. Then apply additive terms, in this order:

| Signal | Condition | Δ |
|---|---|---|
| **Cleanliness** | `clean = true` | **+1.00** — the dominant term, bigger than everything below combined |
| | `clean = false` | **−1.00**; excluded from the pool outright unless `--include-unclean` |
| Footage tier | `footage_tier = cinematic` | +0.20 |
| | `footage_tier = gameplay` | −0.15 (kept as coverage, just discounted) |
| | `footage_tier = mixed` | (no adjustment) |
| Casting | `casting.role = lead`, `casting.usable = true`, **and** the query asked for a `casting.*` facet | **+0.40** (`lead_weight_for`, §1) |
| | `casting.role = lead` **and** `casting.usable = false` (the corpus's one constrained binding, unmet) | 0 — but the reason still reports `blocked cast (…)` |
| | `casting.role = ensemble` | +0.20 |
| | …and `substitutability >= 3` | +0.10 more — the tie-break between otherwise-equal ensemble shots |
| Salience | `subject_salience` ∈ `{guardian_hero, crowd_group, environment_establishing, object_artifact}` | +0.20 |
| | `subject_salience = enemy_threat` | −0.20 |
| Register | `register >= 0` (mythic side) | +0.15 |
| | `register <= −2` (hard tactical) | −0.15 |
| Camera | `handheld_shaky` ∈ `camera_movement` | −0.25 |
| Traversal | `traversal_hero = true` | +0.10 |

A `register` of exactly `−1` gets neither adjustment — the two conditions are `>= 0` and `<= −2`, so the one tactical-leaning-but-not-hard value is neutral by design, not an oversight.

The casting logic is three mutually exclusive checks, in order: `if role == lead and usable and lead_w: +0.40, reason shown` — `elif role == lead and usable == false: +0, "blocked cast" reason shown` — `elif role == ensemble: +0.20 [+0.10], reason shown`. That middle branch is unconditional on `lead_w`: a blocked constrained lead (currently only `saladin` → `jeefy`, when the shot fails `require_helmet`/`require_far`) reports `blocked cast (…)` whether or not the query asked for that character (see the Titan's-helmet and "named character" examples, §1) — `casting.usable` is checked before the query-conditional weight is even consulted. The *other* way a lead shot gets no casting-related score is silent: an **unconstrained** lead (every current binding except Saladin) outside a casting query falls through all three branches with no reason line at all, because it never reaches the blocked check (`usable` is `true`) and `lead_w` is `0`.

Ties break on score, then `substitutability` (an absent value counts as `0`), then the order segments were loaded from disk — there's no dedicated tiebreak on position within the source video.

The philosophy in one line: **an unclean shot isn't a worse shot, it's not a shot; past that gate, Guardians — named or anonymous — are the subject, enemies are stakes, and the mythic register wins the tie.**

---

## 3. Fuzzy, Over-Specified, and Out-of-Vocab Queries

### Fuzzy — "something epic and lonely"

Nothing maps to a hard facet — not even `mood` or `register`, which aren't wired into parsing at all (§1):

```json
{"filters": {}, "caption_terms": ["something", "epic", "lonely"]}
```

Every clean segment in the corpus survives (there's nothing to filter on), and the standing editorial ranking alone does the ordering — the crowd/helmet/bridge/Saladin/Elsie shots rank purely on tier, salience, and register, with `caption_sim` sitting at `0.00` for all of them (none of "something/epic/lonely" literally appears in any caption). Report this plainly to the user: *"no structural match — ranked entirely on editorial bias and caption text, treat as interpretive."*

### Over-specified — more constraints than any clip satisfies

`relaxed_filter` drops facets **in a fixed order**, one at a time, re-running the filter after each drop, until the pool is non-empty or it runs out of things it's allowed to drop:

```
RELAX_ORDER = [destination, pacing, camera_movement, composition, activity]
```

**"slow-motion supers in a raid"** parses to `{pacing: slow, activity: raid, action: ability_cast}`, and nothing in the corpus satisfies all three. Relaxation walks `RELAX_ORDER` — drops `pacing`, still empty; drops `activity`, still empty — then falls to the **last-resort pass**: drop anything left that isn't in `NEVER_RELAX`, which takes `action` too (it isn't protected). The pool is now unfiltered, and the standing editorial ranking alone orders all 7 clean segments:

```
Relaxed to find matches — dropped: pacing=['slow'], activity=['raid'], action=['ability_cast']
7 match(es) from a pool of 7/9 segment(s):
```

**Relaxation can also legitimately fail.** `NEVER_RELAX = {class, element, faction, casting.person, casting.character, casting.role, footage_tier}` — these never get dropped, full stop. "Vex on Neomuna" parses to `{faction: vex, destination: neptune_neomuna}`; relaxation drops `destination` (it's in `RELAX_ORDER`), but `faction=vex` is protected and there's no Vex-tagged record in this corpus, so it stays at **zero results** even once relaxation has done everything it's allowed to. "Cabal ships over Earth" (`faction: cabal`, `destination` relaxed away) ends the same way. An empty result after full relaxation is not a bug to work around — it means the *user's explicit ask* genuinely isn't in the index, and reporting that honestly beats quietly dropping a protected facet to manufacture a result:

```
Relaxed to find matches — dropped: destination=['neptune_neomuna']
0 match(es) from a pool of 7/9 segment(s).
```

### Out-of-vocab — the taxonomy lacks the term

Example: "a Guardian firing **Wish-Ender**" — there's no `weapon` facet.

```json
{"filters": {}, "caption_terms": ["guardian", "firing", "wish", "ender"]}
```

- Route the term to caption similarity. **Never fabricate an enum value** (`weapon=wish_ender` does not exist; don't emit it).
- Ranking falls back entirely to editorial bias plus whatever partial caption overlap exists (here, "guardian" alone nudges a couple of results up with `caption 0.25`).
- Surface a note: `"Wish-Ender" matched semantically via captions, not structurally — precision depends on caption quality.` If the term recurs across sessions, that's a signal to propose a taxonomy addition, not to patch it in at query time.

---

## 4. End-to-End Example

**Prompt:** *"slow-motion Hunter Arc super moment, something heroic for the chorus"*

### Step 1 — Parse

```json
{
  "filters": {
    "pacing": ["slow"],
    "action": ["ability_cast"],
    "class": ["hunter"],
    "element": ["arc"]
  },
  "caption_terms": ["something", "heroic", "chorus"]
}
```

`slow-motion` → `pacing=slow`, `super` → `action=ability_cast`, `Hunter`/`Arc` → `class`/`element`. "Heroic" and "chorus" have no enum — they fall through to `caption_terms` (§1). No `casting.*` key is present, so `lead_weight_for` will return `0.0` for this query.

### Step 2 — Filter, then relax

The candidate pool is clean-only (7/9 segments — `hunter-arc-pvp` and the burned-in title card are excluded before filtering even runs). No clean segment matches `class=hunter, element=arc` at all: the only Hunter+Arc footage anywhere in the index is that unclean PvP clip. `relaxed_filter` walks `RELAX_ORDER`, dropping `pacing` (present) — still nothing, because the blocker is `class`/`element`, not `pacing`. `destination`, `camera_movement`, `composition`, and `activity` aren't in this query's filters, so the walk falls straight to the last-resort pass, which drops `action` too (not in `NEVER_RELAX`). `class` and `element` are both in `NEVER_RELAX` and never get touched:

```
Parsed filters: {'class': ['hunter'], 'element': ['arc']}
Relaxed to find matches — dropped: pacing=['slow'], action=['ability_cast']
0 match(es) from a pool of 7/9 segment(s):
  (nothing matched; try fewer constraints)
```

(The CLI's "Parsed filters" line reports what's still *active* after relaxation, not the original parse — that's why it only shows `class`/`element` here, with `pacing` and `action` already accounted for on the "dropped" line above it.)

### Step 3 — What actually happened, and why it's correct

`class=hunter` and `element=arc` are both protected, and the only footage that satisfies both is `hunter-arc-pvp` — which is `clean=false`. **There is no clean Hunter-Arc shot to return, and the system says so instead of quietly substituting a Titan, a Warlock, or a different element.** For a chorus-length "something heroic" ask, the honest options are: re-source clean Hunter Arc cinematic footage, or rewrite the beat around a class/element the index actually has clean coverage for — Elsie Bray, Saladin, and the ensemble crowd/bridge/helmet shots are all clean, all mythic-register, and all sitting in this same pool already scoring well. `--include-unclean` will surface `hunter-arc-pvp` itself for triage, deep underwater at a negative score, exactly as in §1 — visible for a re-shoot decision, never promoted into a finished cut.

---

## 5. Story assembly (`tools/story.py`)

Search answers a browse; `tools/story.py` answers **the actual point of the index** — turn an outline into a cut. Write the story as an ordered list of beats in plain language (a text file, one beat per line, `#` comments; or JSON — `{title, fps, beats: [{beat, duration}, …]}`, or a plain list of strings). The tool walks the beats **in order**, casts each to the best distinct clean shot, and never reuses one — a story that cuts the same shot twice reads as padding, so a repeat is reported as a miss instead, and the beat gets rewritten rather than padded.

It reuses the exact same parse/filter/score machinery as search (`parse_query`, `relaxed_filter`, `score_segment`, `lead_weight_for`), with two differences: `caption_weight = BEAT_CAPTION_WEIGHT = 3.0` — a beat is a specific instruction, not a browse, so literal relevance needs to beat the standing editorial bias outright, not just nudge it — and the pool is clean-only by construction, with gameplay tier excluded too unless `--allow-gameplay` widens it back in. There is no `--include-unclean` here; that flag is a `tools/search.py` triage feature. A story never gets an unclean shot, by design, with no override.

Running the worked outline at `stories/example-outline.txt`:

```
$ python3 tools/story.py stories/example-outline.txt
STORY: example-outline.txt
6 shot(s) from a clean pool of 7/9 indexed segment(s)

  1. wide establishing shot of the Traveler
     yt_lightfall_reveal_trailer  0:03–0:11  (8s, mixed, —)
     seg_traveler_establishing_0003-0011  [+2.85] +1.00 clean, +0.20 salience, +0.15 mythic register
     …
  4. Elsie Bray hero shot
     yt_beyond_light_story_trailer  1:02–1:08  (6s, cinematic, elsie_bray)
     seg_bl_elsie_hero_0102-0108  [+4.95] caption 3.00, +1.00 clean, +0.20 cinematic tier,
                                          +0.40 lead: elsie_bray (cast), +0.20 salience, +0.15 mythic
  …
```

All six beats matched — zero misses against the current corpus, so the outline is covered end to end, from the Traveler establishing shot through the closing bridge traversal. `--format edl` emits a CMX3600-style cut list against a contiguous record timeline (`tc()` converts seconds to `HH:MM:SS:FF` at the outline's fps):

```
001  AX       V     C        00:00:03:00 00:00:11:00 00:00:00:00 00:00:08:00
* FROM CLIP NAME: yt_lightfall_reveal_trailer
* BEAT: wide establishing shot of the Traveler
```

`--format csv` gives the same cut list as a spreadsheet-friendly row per shot (`#, beat, video_id, segment_id, start_tc, end_tc, duration, tier, role, character, score`), and `--format json` gives the full structured `{shots, misses, pool_size, index_size}` payload for downstream tooling. When a beat has no clean match, it lands in `misses` (and an "UNMATCHED BEATS" block in `--format text`) instead of silently disappearing or forcing an unclean shot in — the same governing rule as everywhere else in this doc: the fiction bends to the footage, never the other way round.

---

## Cheat sheet

- **Explicit Destiny noun / cinematography term / cast name with a matching enum** → hard filter. **Anything else, including tone words** → caption similarity. **Never invent enums.**
- The pool excludes unclean shots before anything else runs; `--include-unclean` (search only) overrides for triage.
- Editorial ranking is always on: clean, cinematic-tier, Guardian/ensemble-salient, mythic-register, steady-camera, traversal-hero shots rank up; unclean, gameplay-tier, enemy-as-subject, hard-tactical, shaky-cam shots rank down.
- The +0.40 lead bonus is the one query-conditional weight (`lead_weight_for`) — it only fires when the query itself asked for a `casting.*` facet, **and** the lead is `usable`. The corpus's one constrained binding (`saladin` → `jeefy`, `require_helmet` + `require_far`) reports `blocked cast (…)` with no bonus whenever the shot fails its constraints — regardless of whether the query named the character.
- Over-specified? Relax `destination → pacing → camera_movement → composition → activity`, then anything left outside `NEVER_RELAX`. `class`/`element`/`faction`/`footage_tier`/`casting.*` never relax — an empty result after full relaxation is a real answer, not a bug to route around.
- Out-of-vocab? Captions, plus a "matched semantically" note.
- Browsing vs. assembling: `tools/search.py` ranks a neighborhood; `tools/story.py` casts an ordered outline to distinct clean shots and reports what it couldn't cover.

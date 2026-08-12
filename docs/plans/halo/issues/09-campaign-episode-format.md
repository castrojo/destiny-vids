# H-09 — A campaign/episode format: movements that alternate dialogue and combat

**What:** the repo assembles **one cut from one outline**. #11 asks for a
multi-episode campaign where each episode alternates dialogue-only beats with
long combat movements. That structure has nowhere to live today.

**The shape:** a campaign is episodes; an episode is **movements**; a movement is
`dialogue` or `combat`. Sketch and rationale in
[`../design.md`](../design.md#6-the-campaign-format).

```jsonc
{"campaign_id": "halo-ce-ogc", "universe": "halo",
 "cast": "casts/open-gaming-collective.yaml",
 "episodes": [{"episode": 1, "title": "The Pillar of Autumn", "movements": [
   {"kind": "dialogue", "audio": "source", "beats": ["..."]},
   {"kind": "combat", "track": "wolves:<track_id>", "beats": ["..."]}]}]}
```

**Scope:**
- `tools/campaign.py`: campaign file in, one cut list per episode out, plus an
  audio plan for H-10.
- Beat matching stays `tools/story.py`'s scoring, but the **matcher needs a new
  entry point**: `build_story()` owns a fresh local `used` set
  (`tools/story.py:100–136`), so campaign-wide uniqueness is impossible without
  passing shared state in. Add a matcher API taking `used_ids` (and, for H-10, a
  target duration) rather than calling `build_story()` per episode and hoping.
- Validate the rules, because each of them is something that otherwise goes
  wrong silently:
  - exactly one track per combat movement — "scored by its own song" means a
    movement needing two tracks is two movements;
  - **strict alternation**: no two adjacent movements of the same kind, and a
    minimum of two dialogue↔combat switches per episode (i.e. at least three
    movements). Counting switches alone would pass an episode that front-loads
    every dialogue movement, which is not "switching back and forth";
  - **shot uniqueness across the whole campaign**, not per episode — `story.py`
    already refuses reuse within a cut, and across six episodes the same rule has
    to hold or episode 5 replays episode 1;
  - unmatched beats reported per movement, never dropped.
- Tracks are referenced by id and never stored, the same posture as `media/`.

**Acceptance:**
- [ ] A campaign file produces N cut lists and a report naming every unmatched
      beat with its episode and movement.
- [ ] A campaign that reuses a shot across two episodes fails validation.
- [ ] An episode with two adjacent movements of the same kind fails validation.
- [ ] An episode with fewer than two switches fails validation.
- [ ] Tests follow the existing `tests/test_story.py` shape and run offline.

**Depends on:** H-05

**Automatable:** yes.

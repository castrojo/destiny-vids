# The timing pass: mark, don't cut

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep the
skill inside its size budget. The review convention that lets a cut be judged
against its music before a frame is removed, and the traps around filling a span.

### Mark, don't cut: the timing pass

Before an edit is worth making, its timing has to be judged — and you cannot
judge timing against a cut that has already thrown the material away. A
**timing pass** is the intermediate render that answers this:

> Anything destined for removal or replacement **stays in the timeline at its
> exact duration**, blacked out by a marker card saying what will happen there.

Because a card and the footage it replaces are the same number of seconds,
**timing is preserved by construction**: every later anchor lands exactly where
it will land in the finished cut, so the pass can be played against the music
and reviewed before a frame is actually removed.

```bash
python3 tools/marker.py "COMIC PLACEHOLDER" --sub "4:33-4:37  enemy CU"
```

Two kinds, and the sub-line always says *which* material is standing behind the
card:

| Card | Means |
|---|---|
| `COMIC PLACEHOLDER` | **an artwork slot** — artwork will be dropped in here later |
| `REMOVE — <reason>` | this is coming out; it is here so the timing still reads |

`tools/marker.py` renders these deliberately plain — full-frame black, one
tracked line, no chrome. A marker must never be mistakable for a finished
nameplate. They are **production markers, not credits**: a marker carries no
claim about any person, so none of the nameplate vocabulary rules in
[`plates.md`](../../plates/SKILL.md) apply to it, and none of its shapes are reused either.

This is what replaces jump-cutting around unwanted material. A long enemy
close-up, a publisher's mechanic card, a repeated shot: black it out in place
and keep going. The reviewer sees a continuous cut with its holes labelled,
which is a far better artifact than a shorter cut whose rhythm has silently
changed.

**Leaving artwork slots is the point, not a workaround.** The slots are where
the film's own artwork goes; marking them early is what lets the artwork be
made to a known duration instead of being squeezed in afterwards.

Carrying those notes out — what a "replace" costs versus a "cut", where the
seconds come from, verifying a reviewer's proxy clip, and measuring a boundary
the shot detector got wrong — is
[`references/timing-pass-notes.md`](timing-pass-notes.md).

### When the bed does not run end to end

A cut whose song pauses, or starts late, has **two clocks** — `wall` (position
in the film) and `bed` (position in the song) — and a shot marked
`audio: "source"` advances wall and not bed. The mechanic, the tool
(`tools/audiomix.py`), how to choose a pause point by measurement, and why a
diegetic insert has to be allowed to end all live in
[`scoring.md`](../../scoring/references/two-clocks-and-levels.md).

The one rule that belongs here: **anchors in an authored builder are asserted
against bed time, never wall time.** A musical with a pause in it is longer than
its own song.

### Filling a span is how banned material gets into a cut

**The most dangerous edit in this repo is a span that has to be filled.** Both
of the worst defects in the Wolves cut came from the same reflex — a run needed
N seconds, the chosen material held fewer, so the code reached for whatever was
adjacent:

| Symptom | What the fill actually did |
|---|---|
| 25 shots replayed | replayed the pool in reverse once it ran out |
| a Savathûn montage in a no-Savathûn film | started the run 17.8 s early, reaching back past the Neomuna boundary into the Throne World |

Nobody chose either. **A fill does not know what it is picking up**, so every
editorial rule — no repeats, no Savathûn, no Witness body, no enemy subjects —
is silently suspended at exactly the moment the code is under pressure.

So: when a span comes up short, **the shortfall is an editorial question, not an
arithmetic one.** Take the extra material from a *named* source, from the front,
and assert the boundary that must not be crossed:

```python
assert min(s["start_sec"] for s in run) >= BOUNDARY   # not a comment. a test.
```

The Wolves fix pulled 17.8 s from an official trailer rather than reaching
backwards — which also improved the cut's provenance, because a deliberate
choice can be made for more than one reason and a fill cannot.

# Carrying out notes on a timing pass

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to
keep the skill inside its size budget; this is the mechanics of turning a
reviewed timing pass into a real cut — needed when the notes come back, not
when planning one.

The worked example throughout is act VI, *7 Days to the Wolves* — its builder
is `scripts/build_wolves.py` and its plan record is
[`stories/megacut/megacut.json`](../../../../stories/megacut/megacut.json).

## What each note actually costs

When the notes come back, the pass's arithmetic is what makes them cheap — and
it splits every note into exactly two kinds, which cost completely different
things:

| The note | Cost | Why |
|---|---|---|
| **Replace** this span (black, or a placeholder card) | **nothing** | the picture is exactly as long as what it stands in for, so no anchor moves |
| **Cut** this span | its full duration | which has to be found somewhere |

Keep the two in **one ordered list** with a per-entry kind, not in two lists.
They interleave in source order, they can sit flush against each other, and
only one of them feeds the derived in-point:

```python
CAPTURE_IN = CAPTURE_OUT - (ACT_LEN - TITLE_CARD_LEN) - sum(
    o - i for i, o, kind, _ in EDITS if kind == "cut")
```

Two consequences worth knowing before you start:

- **A flush pair produces a zero-length run.** "Cut the dark tail, replace the
  black that follows it" is two entries sharing a boundary. Allow exactly zero
  and raise on negative — a negative gap is overlapping edits, which is a bug
  that otherwise renders as silently duplicated frames.
- **Removing a publisher slide is not always a removal.** If the slide is the
  last thing before an anchor, deleting its seconds drags the anchor early.
  Start the *run* earlier instead and stop it before the slide: bed time is
  unchanged and the slide never appears. Then assert on the **timecode** —
  "no run reaches the slide's in-point" — because asserting "there is no card"
  still passes when a run grows into the slide.

## A removal has to be paid for out of the same act

Where the seconds come from is decided by the act, not by preference:

- **An act bounded only at its end** (an intro running to a hinge) pays off its
  **head** — see "Excisions: derive the in-point". Free, and self-correcting.
- **An act pinned at both ends** has no slack at all, and this is the case
  people get wrong. Check the extract's actual length before assuming the run
  can grow a tail: here `wolves_act2` is 210.015 s and the run already ended at
  210.0. There was no more footage, so 13.9 s of picture had to come from
  another source.

Filling from another source is legitimate **when somebody chose that footage**.
Filling because a number did not add up is how banned material gets in — the
failure written up in the section below. The distinction is not the technique,
it is whether a human picked the shots. Assert the fill's total against the
hole's, so the act cannot silently come up short:

```python
assert sum(s["duration"] for s in fill) == pytest.approx(GHOST_OUT - GHOST_IN)
```

## A proxy clip is not a source

A reviewer's clip — a 640x360 grab with a filename like
`UchfadQhX7w_Kat_77-82.mp4` — tells you the in-point, the out-point and the
intent. It is **not** the footage to cut with, and the id in the name is a
claim to verify rather than trust.

Frame-match it against whatever you think it came from before believing it:

```python
d = abs(frame(candidate, t) - frame(proxy, t0)).mean()   # 160x90, grayscale
```

A real match is **dramatically** better than its neighbours — 3-4 against a
runner-up above 20. A "best" match of 45 whose runner-up is 45.5 is noise, and
that is exactly what a whole-file scan returned when three proxies were assumed
to be from the Final Shape *launch* trailer. They were from the *gameplay*
trailer, a different official upload. Report the runner-up alongside the best
score, always: the ratio is the evidence, not the minimum.

Then re-fetch at full quality, snap the proxy's trims to **detected shot
boundaries** (they are the reviewer's rough marks, not cuts), and trim only
tails if a length has to be forced.

## When the shot detector disagrees with your eyes, measure

`ContentDetector` merges cuts across a white bloom or a heavy dissolve, because
consecutive frames really are similar there. If a boundary matters — an insert's
out-point, say — difference consecutive frames yourself at frame rate:

```text
51.835   delta 170.2   the explosion's cut        <- background is under 30
53.003   delta  36.7   ...decaying into the portrait
53.470   delta  89.1   the cut out of the portrait
```

Two real cuts the detector had reported as one shot. Quote the deltas next to
the constants, so the next person can see the signal rather than re-run the scan.

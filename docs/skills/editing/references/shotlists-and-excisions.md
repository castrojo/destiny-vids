# Excisions, authored shotlists, and picking by eye

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep the
skill inside its size budget. Deriving in-points, the invariant an authored
shotlist must hold, and when eyeballing shots is legitimate.

### Excisions: derive the in-point, never write it down

Cutting a dull span out of the middle of an act does not change what the act
owes the music. Write the excisions as data and **derive** the in-point from
them:

```python
CAPTURE_IN = CAPTURE_OUT - ACT_LEN - sum(o - i for i, o, _ in EXCISIONS)
```

Now dropping another span is a one-line change: the run simply starts earlier,
the act still fills its span, and no anchor moves. Hard-code the in-point
instead and every excision becomes a manual re-solve of the whole act — which is
the arithmetic that produces a short act, and a short act slides every later
anchor.

### An authored shotlist, and the invariant it must hold

A cut list that `story.py` produced is derived, and hand-editing it is a Red Flag
below. A shotlist **authored from the start** is a different object: no matcher
ran, so there is nothing to be out of date with. Name it so the two are never
confused (`stories/<name>-prototype.json`, not `cut.json`) and say so in the
file.

This is the legitimate path when shots are chosen by eye — see the next section.
It comes with one invariant that is easy to miss:

> **A cut is a concatenation. It has no absolute timeline.**

So an act that comes up short does not leave a gap; it slides every later shot
earlier, and any shot that was supposed to land on a musical moment lands
somewhere else. Assert that each act fills its span rather than discovering it in
the render:

```python
assert abs(act_end - ANCHOR) < 0.15, "a short act slides every later anchor"
```

The same arithmetic makes an *unresolvable* shot dangerous. `render.py` skips a
shot whose source is missing and reports it on stderr — but the film is then
shorter than the shotlist says. `media/` is gitignored and varies per host, so
**filter the pool to sources that actually exist** before building.

### Picking shots by eye, without tagging

Tagging exists to feed `story.py`'s matcher. **If a human picks the shots, no
tags are needed** — and for a new source that is the difference between a cut
today and a tagging pass first.

Detection pass 1 alone gives what eyeball selection needs:

```bash
python3 tools/annotate.py index --video media/<window>.mp4 \
    --video-record videos/<id>.json          # no --tags: boundaries + keyframes
```

Then contact-sheet the keyframes (5x4 grids, each tile labelled with the shot
index and its in/out) and read them. Two hundred shots fit on ten sheets.

Two rules make this honest rather than a shortcut around the gate:

- **A midpoint keyframe does not prove the interval is clean.** Keyframes come
  from the middle of a beat by design; a shot whose middle is clean can still
  open or close on a logo card or a HUD frame. Scrub the edges of anything you
  select.
- **It buys a cut, not an index.** Nothing lands in `segments/`, so the shots are
  not searchable and no later cut can find them. That is the trade; make it
  deliberately.


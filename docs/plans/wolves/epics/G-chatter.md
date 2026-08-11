# Epic G — Radio chatter: the comm line

**Parent:** #9 · **Depends on:** A, B, F · **Blocks:** I
**Design:** [`docs/plans/wolves/design.md` §6](../design.md)

In-universe this is a comm line, so it should look like one: a face, a callsign,
a waveform that keys open when someone talks, and no chat box at all. Borderlands'
ECHO is the reference for the feel; the plate's existing chrome is the reference
for the look.

**Done looks like:** `python3 tools/chatter.py plan` turns a parsed comm log plus
a cut list into a timed manifest, `render` turns that into a 12 fps sequence of
transparent tiles, and the burn puts them on the video in the same ffmpeg pass
that burns the plates.

**Invariants for every sub-issue here**

- One voice at a time. Two people talking over each other is unreadable and,
  in-fiction, is not how a comm line works.
- The chatter block and a nameplate never occupy the same rectangle.
- Nothing is drawn from anything but authored text and resolved identity.

---

## G1 — The comm rail

**Labels:** `enhancement` · **Depends on:** F2

Lay out one chatter block: avatar left at Epic F's size, callsign (the login,
uppercase, letter-spaced like the plate's eyebrow), a small org glyph beside it
when the person has one, the sparkline strip, and the line itself on a scrim
sized to the text. Bottom-left, inside title-safe.

**Acceptance**

- [ ] The avatar is the largest element and the chrome budget from F2 holds.
- [ ] A long line wraps to at most two lines and then truncates the *block*, not
      the sentence — an over-long line is a `warn` at parse time (Epic A), not a
      silent ellipsis at render time.
- [ ] The org glyph is the small mark, subject to the same rules as C4: never
      recolored, never composited into the chrome, text fallback when absent.
- [ ] Renders deterministically to RGBA, like every other renderer here.

---

## G2 — The sparkline

**Labels:** `enhancement` · **Depends on:** G1

```
seed     = H(login, section, line_index, text)
pulses   = one per word; amplitude ∝ word length, jittered from the seed
envelope = attack ramp (keys open) · pulses · release ramp (keys shut)
idle     = a low carrier with a slow ping, so the channel reads as open
```

No audio, no TTS, no analysis. The waveform is a function of the sentence, which
is the only "sync" a viewer perceives anyway: a long line visibly chatters more
than a short one.

**Acceptance**

- [ ] Same line in → same waveform out, byte for byte.
- [ ] A one-word line and a fifteen-word line are obviously different.
- [ ] The keying ramps are visible: the line starts and ends closed, not
      mid-chatter.
- [ ] Amplitude is bounded so the strip never overdraws its row.

---

## G3 — The layer: one input, one overlay

**Labels:** `enhancement` · **Depends on:** G2

Render the whole cut's chatter into **one image sequence of the comm rail's
bounding box** — not full frames, not one sequence per line — at 12 fps, and
composite it with `-framerate 12 -i chatter_%05d.png` plus a single
`overlay=x:y:enable='between(t,in,out)'` in the same pass that burns the plates.

**Acceptance**

- [ ] One extra ffmpeg input and one extra overlay, regardless of line count.
- [ ] The tile is the rail's bounding box; a full-frame sequence is a bug.
- [ ] Frames land in a gitignored directory beside the output, never `/tmp`
      (the container only mounts `$HOME` — see `docs/rendering.md`).
- [ ] The burn still stream-copies audio, as `plate.py burn` does today.
- [ ] The command is asserted by a test the way
      `test_burn_builds_one_enable_gated_overlay_per_plate` asserts the plate
      chain — no test may actually invoke ffmpeg.

**If the sequence gets unwieldy**, VP9 in WebM carries alpha with
`-c:v libvpx-vp9 -pix_fmt yuva420p` and works even on Fedora's `ffmpeg-free`
(VP9 is royalty-free; H.264 is what is missing there). Measure before switching —
a PNG sequence needs no codec at all.

---

## G4 — The non-collision invariants

**Labels:** `enhancement` · **Depends on:** G3

`tools/plate.py` already refuses a manifest where two plates are visible at once.
Extend that idea rather than duplicating it: chatter lines may not overlap each
other, and a chatter line may not share a rectangle with a visible plate.

**Acceptance**

- [ ] Two overlapping chatter windows raise, with both line numbers in the
      message.
- [ ] A chatter window overlapping a plate window raises **only** when their
      rectangles intersect — a plate on the right and chatter on the left at the
      same time is legal and looks correct.
- [ ] Both `plan` and `burn` validate, as the plate path does — the invariant
      belongs to the data, not to one code path.
- [ ] The planner resolves a collision by moving the *plate*, never by dropping a
      person's line.

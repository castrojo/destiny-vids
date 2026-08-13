# H-11 — The Halo CE-era HUD layer

**What:** `tools/hud.py`, with `plan | render | burn` mirroring
`tools/plate.py` — visor frame, motion tracker, shield and ammo blocks, corner
readout, waypoint diamonds, target reticles, and a callout that snaps in as each
trooper is introduced, resolving in the final beat of the closing episode into
the Bazzite download call-to-action.

`plate.py` already solved most of this: transparent PNGs at frame size, one
ffmpeg pass building an `overlay` chain (`plate.burn`, `tools/plate.py:527–569`),
`enable='between(t,…)'` windows, and a refusal to put two cards on screen at once
(`plate.load_manifest_entries`, `tools/plate.py:492–513`).

**Scope:**
- `tools/hud.py plan | render | burn`, reusing `plate.py`'s PNG + overlay-chain
  approach rather than inventing a second compositing path.
- **Continuous chrome.** Frame, tracker, shield/ammo and readout ride the whole
  episode: `overlay=0:0` with no `enable` guard, from a PNG sequence for the
  animated parts and a still for the fixed frame.
- **Timed callouts**, one per trooper introduction, on the existing
  `enable='between(t,…)'` window model with its no-overlap rule.
- **Treatment as a filter.** Scan-line flicker and chromatic fringing are ffmpeg
  filters applied once at burn time, not baked into the PNGs.
- **The closing CTA beat** — the HUD resolving into the Bazzite
  download/install callout in the final beat of the last episode.

**Layout, per the CE/Halo 2 reference in
[`../research.md`](../research.md#3-halo-ce--halo-2-era-hud-design-language):**
motion tracker lower left, shield upper centre, ammo and grenades upper right,
centre reticle, waypoints at the screen edge. Health bar present reads as CE;
shield-only reads as Halo 2. Rounded chrome and Forerunner gold read as Halo 4
and are wrong for this brief.

**Two decisions to take before rendering:**
1. **Colour.** #11 asks for translucent *green* military elements; the CE/Halo 2
   HUD is *blue-cyan*, and #11 also says "keep it canon". Both cannot hold.
2. **Typeface.** The era's font is Handel Gothic, which is commercial. Nothing
   proprietary gets bundled: pick from installed candidates and fail loudly when
   none is found, exactly as `plate.py`'s `FONT_CANDIDATES` does.

**What it must not do:**
- **It never makes unclean footage usable.** `overlays: hud` on a *source*
  segment still derives `clean = false`. This HUD is composited at render time
  over shots that passed the gate.
- **A HUD-burned render is not re-ingestable** — it is unclean by this index's
  own definition. Keep the pre-HUD render.
- **It never invents copy.** Callout fields are a closed set in the universe
  pack, like the nameplate deck, and the closing CTA — wording and URL — is
  authored, not composed at render time (`docs/skills/plates/SKILL.md`).
- **It never puts two names on screen at once.** The chrome is continuous, so it
  *does* share the screen with plates — a card over the visor frame is the
  intended look, and forbidding that would forbid every plate. What is mutually
  exclusive is the name-bearing layer: a trooper callout, the CTA and a plate are
  three ways of captioning the same frame. `plate.load_manifest_entries` only
  compares plate windows and knows nothing about HUD manifests, so one scheduler
  has to own the name-bearing timeline across both tools.

**Acceptance:**
- [ ] Chrome rides a whole episode; callouts appear only in their windows.
- [ ] A callout carrying a field outside the closed set fails a test, mirroring
      `tests/test_plate.py::test_no_plate_field_is_invented_beyond_the_reference_deck`.
- [ ] Overlapping *name-bearing* windows are refused across both tools; chrome
      under a plate is allowed.
- [ ] Colour and font decisions are recorded in the universe pack, not in code.

**Depends on:** H-04 (who is named), H-05 (the pack that stores the colour, font
and callout-field decisions), H-09 (episodes exist)

**Automatable:** partly — the compositing is mechanical; the colour, font and CTA
copy decisions are the owner's.

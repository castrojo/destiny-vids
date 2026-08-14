# Act VIII — the credits

**Master:** `renders/08-credits.mp4` → `~/Videos/Wolves/Prod/08-credits.mp4`
**Built by:** `scripts/build_credits.py` from `stories/08-credits.json`
**Design:** [#51](https://github.com/castrojo/destiny-vids/issues/51), rebuilt
on the owner's 2026-08-14 instructions.

Act VIII is the one act with **no film** — it is cards, a music bed and the
comic-cover reveal. It carries no slide and no chapter marker: it is meant to
ambush you.

## The shape

| | |
|---|---|
| **0:00 – 0:22** | The **call to action** — WE MAKE OUR OWN FATE, BECOME LEGEND, the birthday card, FIGHT |
| **0:22 – 0:36** | **The reveal**: the comic cover, held 14 s |
| **0:36 →** | The **credits**: the three fixed cards, the cast, the contributor walls, the wordmark |

The credits used to play *before* the cover. The owner moved them:

> *"Move the existing credits to after the comic reveal, instead let's make
> this part leading up to it a call to action."*

The reveal itself did not move and was not re-timed — `at_sec` is still
22.080, its `hold_sec` still 14.0 (*"do not touch the comic book reveal
length"*).

## The music is two passes now

The bed was Nightwish's *Wish I Had an Angel* **instrumental**, cut into two
spans so it starts on the drum smash, loops back to its own top and never
plays the breakdown. That is still exactly what pass one is, unchanged.

Pass two is the **album version, with vocals**, on the owner's instruction:

> *"switch to the album version with vocals after the entire instrumental
> loops once"*

*after the entire instrumental loops once* is load-bearing: the loop is not
cut short to make room. It runs its full 228.680 s and the vocal version takes
over at the seam, on the same 0.25 s equal-power crossfade the loop join uses.

| | |
|---|---|
| Pass one | `music/bed_wish_i_had_an_angel.json` — 193.420→239.653, then 0.000→181.320 |
| Pass two | `music/bed_wish_i_had_an_angel_album.json` — 0.000→**243.400** |
| Total | **470.453 s (7:50.45)** |

243.400 is measured, not the file's end: the recording holds full level to 242
(−6.7 dB), decays through 242–243 (−19.6 dB) and is at −54.4 dB by 243, so the
film ends on the song's own ending with the digital silence left off the back.
The album record's downbeat phase is **unresolved** and nothing needs it — the
pass is played whole and never snapped to a bar.

## The call to action

Four cards, weighted into the window the cover's own time leaves. FIGHT's
weight is longer than the first two together, which is the instruction
(*"I want this one up longer than the first 2"*) and survives the window
changing.

- **WE MAKE OUR OWN FATE** — the premise, the smallest of the three cries.
- **BECOME LEGEND** — *"noticeably larger font … no italics, I want bold and
  blocky."* Adwaita Sans **Black**, upright, never a synthesised oblique.
- **Happy Tenth Birthday / RAFAEL CASTRO / "We love you" - Mom and Dad** — the
  owner's own words, verbatim. It replaced the *Introducing* card, and the
  second, redacted name went with the card that carried it: it is recorded
  nowhere, which is what a redaction is for.
- **FIGHT** — *"HUGE BOLD FONT. BLUE F."*

### The seared F

The F's are **filled in the film's blue** with an additive bloom around them:
a wide deep-blue haze, a tighter flare, and the solid letter over both. The
bloom adds to the backdrop rather than covering it, which is what separates
heat from an outline.

The first pass drew a white-hot core inside the stroke; the owner corrected it
(*"the F would look better filled in blue!"*), and then asked for the glow to
be **toned down**. Both are in the numbers now, not in a note: the letter is
solid `#93c5fd` and the bloom gains are a third of what they were.

Below the `large` tier the sear is skipped and the F simply takes the blue — a
bloom at 150 px is a smudge.

## The contributor walls

Eight sections. The **upstream tier plays first** and carries a badge lockup
built from each project's own published mark, on its own six-by-three grid.

| Tier | Sections |
|---|---|
| **upstream** | Fedora CoreOS, bootc, **GNOME OS**, **KDE Linux** |
| | Universal Blue, Bazzite, Aurora, Project Bluefin |

- **GNOME OS is `gnome-build-meta` and nothing else** — *"Only have GNOME OS
  since it's such a large org."*
- **GNOME OS and KDE Linux are not on GitHub.** They are fetched from the
  GitLab APIs (`gitlab.gnome.org`, `invent.kde.org`), which answer with a
  commit author's **name and email**. Only the name is taken: an email is
  somebody's contact detail, not copy, and a credit roll is the wrong place
  for a few hundred of them. That also means no cached PFP, so those faces
  degrade to the ring the renderer already draws.
- **`Aleix Pol` and `Harald Sitter` are pinned** to the front of KDE Linux —
  *"put at least aleixpol and harald sitter"* — because GitLab spellings vary
  between a person's own commits and "at least" is a guarantee, not a hope.
- **Universal Blue is still the deduped section**, and that is now bound to
  the section by name. It used to be "the last section"; moving it to the
  front would have silently deduped Project Bluefin instead and taken every
  shared name off its wall.

### The ghost maintainer

The last KDE Linux wall carries an outlined figure captioned **The Next
KyleGospo**, with **Curse of Maintainership** under it. It is drawn, never
fetched: there is no such person, so there is no face, no login, and it is
never counted as a contributor row.

### The two call-outs, and the gag

- The upstream eyebrow is **`#UPSTREAMFIRST`**.
- Every team wall carries **`#linuxforever`** across the bottom.
- A side bubble rides the upstream run: *"So many. Running out of metal."*
  dissolving to *"Deploying CNCF Metal3"*, the **3** set in Metal3's own brand
  green beside its cube. The green is sampled from the mark this repo cached
  from the project's docs, not recalled.

A still cannot fade by itself, so the dissolve is spread across the upstream
walls: the gag sets up on the first third, crosses at a genuine half-and-half
card in the middle, and has landed by the last. It plays **once over the
tier**, not once per wall.

## Reproducing it

```bash
python3 scripts/fetch_brand_marks.py                          # the badges
python3 scripts/build_credits.py --refresh-contributors --write-manifest
python3 scripts/build_credits.py --fetch-avatars --plan
python3 scripts/build_credits.py                              # the master
python3 tools/deliver.py build && python3 tools/deliver.py publish
```

The bed audio is fetched, never committed:
`media/bed_wish_i_had_an_angel.wav` and
`media/bed_wish_i_had_an_angel_album.wav`.

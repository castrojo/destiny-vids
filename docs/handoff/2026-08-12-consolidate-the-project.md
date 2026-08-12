# Handoff: consolidate the project, retire `~/Videos` as policy

**Written 2026-08-12.** For the agent who picks this up next. Delete this file
when its work is filed as issues or done — a handoff that outlives its task is
the stale planning doc `AGENTS.md` exists to prevent.

## What just changed, so you don't undo it

The owner settled two things this session:

1. **The running order is canonical** — eight acts, `mrbobbytables` at III.
   [`docs/running-order.md`](../running-order.md) is now the source of truth for
   it, and it is second in `AGENTS.md`'s read order.
2. **This repo is the source of truth for the project.** `~/Videos` delivers
   files; it does not decide policy. That inversion is new, and most of the work
   below is finishing it.

Also new: `~/Videos/Wolves/{Prod,10mb,megacut}`, `tools/social.py`, and
`tools/megacut.py --chapters`.

**Nothing has been rendered.** The act slides exist as PNGs; the programme does
not. That is deliberate ("fix it in the video don't render it").

## The job

### 1. Retire `~/Videos/UPLOAD/` — carefully

`UPLOAD/` is the **older** staging folder: AAC copies of five cuts, a different
numbering (`01-`, `02-`, `04-`, `07-`, `zz-`), and a `README.md` that still
describes a running order the owner has replaced. `Prod/` supersedes it. The
duplication is exactly the kind that produced "you put mrbobbytables in twice".

It is **not** deleted yet, and you should not delete it without asking, because:

- `CHECKSUMS.md5` and `wolves-review.m3u` reference those exact paths;
- `yt-refresh.py` reads a manifest of them;
- one file in `Prod/` (`06-7daystothewolves.mp4`) is a **hardlink into
  `UPLOAD/`** — it is the one act with no lossless master, so `UPLOAD` currently
  holds the best copy that exists. Deleting the directory entry is safe (the
  inode survives via the link); deleting *contents* you have not re-homed is
  not.

The order of operations that works:

1. Re-home anything `Prod/` still depends on (today: the musical).
2. Rewrite `wolves-review.m3u` against `Prod/`, in the canonical order.
3. Point `yt-refresh.py` at `Prod/` and `10mb/`.
4. Regenerate `CHECKSUMS.md5` for `Prod/`.
5. *Then* ask about removing `UPLOAD/`.

### 2. Move the policy that lives in `~/Videos` into this repo

These files carry **rules**, not files, and rules now live here:

| File | What to do |
|---|---|
| `~/Videos/AUDIO.md` | The audio standard — thresholds, the −1.0 dBTP rule, sourcing by codec. It is genuinely good and genuinely policy. Move it to `docs/skills/references/audio-standard.md`, cite it from `docs/skills/production.md`, and leave a one-line pointer behind. |
| `~/Videos/README.md` | Rewrite as a **thin index**: what each folder is, and "policy lives in `~/src/destiny-vids`". Its "per-project contract" section is policy — move it. |
| `~/Videos/UPLOAD/README.md` | Superseded by `docs/running-order.md`. It already carries a banner saying so. Delete it with the folder. |
| `~/Videos/PREMIERE.md`, `OVERLAYS.md` | Read them first — they may be project notes rather than policy. Decide per file; do not sweep. |

`audio-check.sh` and `audio-source.sh` are **tools**, not policy. Moving them is
a bigger change than it looks (they are referenced by muscle memory and by the
per-cut scripts); leave them, and cite them from here.

**Do not move the reference deck.** `~/Videos/nameplates.json` is *authored
copy* about real people, and this repo reproduces it rather than owning it. Same
for the website's `characters.json`. The rule being inverted is about **policy**,
not about copy.

### 3. Reconcile the documentation

Several files still describe the old world. In rough order of how wrong they are:

- `~/Videos/UPLOAD/README.md` — a playlist order that no longer exists.
- `~/Videos/README.md` — says "`~/src/website` remains the source of truth for
  what is *in* the show". That is now `docs/running-order.md`.
- `docs/cuts/08-directors-cut-megacut.md` — correct, but it is a *build record*
  that also reads as a running-order doc. Trim it to the build; let
  `docs/running-order.md` own the order.
- `docs/release.md` — the T−7-weeks schedule predates the acts. Check whether
  the hero-video release plan and the eight acts still describe the same show.
- `docs/catalog.md` — "two kinds of video" is still true, but the feature is now
  eight acts rather than a musical plus extras. Re-read it against reality.

### 4. Finish `Prod/`

`docs/running-order.md` lists the gaps. The two that need a decision rather than
an encode:

- **Act I** must be rendered and placed as `Prod/01-intro.mp4`.
- **Act IV's master predates the owner's dialogue change** — the Kat/Ian split
  and "Remember kids, cardio!" are staged in `~/Videos/wolves-kat/` and
  unrendered. Rebuild there (`node render/render-plates.mjs && ./render/run-kat.sh`,
  then the `-hq` variant), then re-link into `Prod/`.

## Things that will bite you

- **`Prod/` is hardlinks.** `ln -f`, not `cp`. A hardlink cannot drift from the
  master and costs nothing; a copy does both. But `cp` over an existing link
  *breaks* the link silently — re-link, never overwrite.
- **The megacut is stereo now, and that was a decision.** Every `-hq` master is
  stereo FLAC; the old 5.1 deliverables were those same two channels plus a
  derived LFE, added by each cut's own script. Assembly upmixing to recreate it
  would be inventing a soundfield. If the owner wants 5.1 delivery, it belongs
  in the per-cut scripts. Recorded in `megacut.json`'s `_audio`.
- **Acts II and VIII have no film, and their numerals are load-bearing.** Do not
  renumber to close the gaps. III is `mrbobbytables` permanently.
- **Chapters are derived** (`--chapters`), never typed. Re-run after every
  assembly.
- **Three things still cannot be automated**, and all three are live here: the
  musical's provenance (#55), Cortney Nickerson's and Orlin's identities (#59,
  #73), and any music choice for act II (#74).

## Open issues this touches

#25, #41, #51, #55, #58, #59, #73, #74.

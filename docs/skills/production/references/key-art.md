# Key art stills

Part of the [production skill](../SKILL.md).

The show's two still deliverables — a **YouTube thumbnail** and the website's
**social preview card** — are cut from the same key art. Neither is a frame of
the film, so neither comes out of `Prod/`.

## A cover request means cover art, not a trailer frame

For a standalone channel video, the owner may name a season cover, poster or
hero image instead of the show's painting. Search the publisher's first-party
site and media pages before scrubbing the trailer. **A frame featuring the
right character is not a substitute for the cover the owner asked for.**

Ship a temporary source-backed frame when speed matters, keep the first-party
search running, then replace it rather than polishing the fallback. Record the
direct asset URL and the page that owns it. Prefer a native 16:9 background
without the web page's HTML logo/date overlays; crop only when the supplied
composition requires it.

The Season of Dawn precedent is Bungie's own 1920×1080 hero background,
`hero_desktop_bg.jpg`, linked from the official
[Season of Dawn page](https://www.bungie.net/7/en/Seasons/SeasonofDawn).
Bungie's [IP policy](https://help.bungie.net/hc/en-us/articles/360049201911-Intellectual-Property-and-Trademarks)
still governs the fan use; first-party hosting proves provenance, not a
commercial licence.

Thumbnail copy remains closed: reproduce only a title the owner supplied.
Style and line breaks may fit the composition; new taglines may not. Keep the
named subject's face clear.

## The artwork masters live outside the repo

`~/Pictures/Artwork/` holds two 9075² lossless PNGs of the same painting:
`Bluefin_COVER2_FULL_HD_PNG.png` carries the title, `..._NOTEXT_HD_PNG.png` is
the clean art. They are not committed, for the same reason footage is not.

**Composite onto NOTEXT.** A titled still built on the FULL master has the
painting's own title baked into it and cannot be re-laid out.

## Recover the lettering, never re-typeset it

The title is a drawn lockup, so a lookalike font is an invention. Having both
masters means the matte can be recovered exactly rather than keyed, because the
letters are pure white over known pixels:

```python
alpha = np.clip((FULL - NOTEXT) / np.maximum(255.0 - NOTEXT, 1e-3), 0, 1).mean(axis=2)
alpha[np.abs(FULL - NOTEXT).max(axis=2) < 6] = 0   # kill encoder noise
```

Keying by luminance is the fallback when only one master exists, and it is
strictly worse: the moon and the smoke sit close enough to white to survive a
threshold. Differencing has no threshold to tune.

The lockup includes a tapered rule either side of the words. Crop to the whole
matte, then split into lines on the **letter** columns — measure column ink
height and ignore anything shorter than the cap height, or the rules read as
part of the first and last word.

## One composite, one downscale, one encode

Every generation costs picture. Crop the base from the PNG at full resolution,
composite there, downscale **once** with Lanczos, and encode **once**. A still
assembled on top of an already-delivered JPEG carries two generations of
artefacts into a third.

Encoder settings that matter for white line art on paint:

- **`subsampling=0`** — Pillow's JPEG default is 4:2:0, which halves chroma
  resolution and mushes hard type edges. `0` is 4:4:4.
- **`quality`** — Pillow documents 0–95; above 95 spends bytes for no gain.
- **WebP** for the web card, `method=6`.

```python
im.save(path, quality=95, subsampling=0, optimize=True, progressive=True)
```

Source-verified against `/websites/pillow_readthedocs_io_en_stable`.

## Where each still goes

| Still | Home | Shape |
|---|---|---|
| YouTube thumbnail | `~/Videos/Wolves/` | 1920×1080, under YouTube's 2 MB cap |
| Social preview card | `projectbluefin/website`, `public/wolves/og.webp` | 2400×1260 — the 1.91:1 Open Graph aspect |

Judge a thumbnail at **336×189** and a preview card at **600×315**. Those are
the sizes they are actually seen at, and a layout that reads at full size can
lose a whole line at listing size.

**Keep faces clear.** The composition rule is the casting rule wearing a hat:
the art names real people, so a title parked over a face is worth re-laying out.

## The website is a different repository

`~/src/website` is never written to — see `AGENTS.md`, "Three workspaces, one of
them writable". Clone `projectbluefin/website` fresh instead, and expect three
things that a plain clone and commit get wrong:

```bash
GIT_LFS_SKIP_SMUDGE=1 gh repo clone projectbluefin/website <dir> -- --depth 20
```

- Without `GIT_LFS_SKIP_SMUDGE=1` the checkout dies on an LFS video under
  `recordings/`, leaving every file staged as deleted.
- Commit messages must be **Conventional Commits**; a plain subject is rejected
  by a hook.
- A pre-commit hook **recompresses images**, so a committed still is smaller
  than the one written. That is the hook working, not corruption — verify the
  committed bytes render, rather than matching file sizes.

`og:image` must be an **absolute** URL. `wolves.projectbluefin.io` is a
Cloudflare edge redirect to the canonical page, so a relative reference resolves
against a host that serves no assets.

## Verification

- [ ] Base cropped from NOTEXT, not from a delivered JPEG
- [ ] Title recovered by differencing, not keyed and not re-typeset
- [ ] Downscaled once; saved `subsampling=0`, `quality` ≤ 95
- [ ] Read at 336×189 (thumbnail) or 600×315 (card)
- [ ] No face, and no crest, under type
- [ ] If the owner asked for a cover/hero: first-party asset URL and owning
      page recorded; no trailer frame substituted
- [ ] Every word on the still is owner-supplied or already part of the source
- [ ] For the web card: fetched back from the live URL and decoded, since the
      bytes served are the hook's, not yours

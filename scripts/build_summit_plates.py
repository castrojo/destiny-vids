#!/usr/bin/env python3
"""Build the Contributor Summit group-shot plates for *Seven Days to the Wolves*.

These replace every black span and every ``COMIC PLACEHOLDER`` marker in the
Wolves cut with a photograph of the people the film is about. They are
**picture**, not slates, which is why this lives here and not in
``tools/marker.py`` -- a marker must never be mistakable for finished picture,
and the reverse holds too.

RIGHTS -- READ THIS BEFORE CHANGING ANYTHING
--------------------------------------------
The photographs are CNCF's, from the Maintainer Summit North America 2025
album, and they are licensed **CC BY-NC-ND 4.0**. The ND term forbids
distributing a *cropped* version, and every plate here is a crop: the sources
are 3:2 and the film is 16:9.

    Owner decision, recorded verbatim: "crop it I have authority I work for
    the cncf"

That is a licensing decision, which ``AGENTS.md`` reserves for the owner. It
has been made, by the owner, and it is written down here and in
``docs/cuts/07-seven-days-to-the-wolves.md`` so nobody re-litigates it and
nobody mistakes it for an agent's judgement. Attribution is **not** burned onto
the slides; it belongs to the credits sequence (issue #51).

WHY THE CROP IS COMPUTED RATHER THAN CENTRED
--------------------------------------------
The website's own sequence file already records the problem, next to its
``backgroundMotion: 'kenburns'`` flag: these are wide group shots with empty
plant and floor padding, and a centred crop frames the padding instead of the
people. So the crop window is chosen by measuring where the *detail* is --
faces, lanyards and badges carry high local variance; foliage, carpet and
ceiling do not -- and keeping the densest band.

TRUNCATION
----------
Every arithmetic step stays in float and rounds once, at the end. ``np.uint8``
casting truncates, and so do ffmpeg's ``geq`` and ``blend``; that pair of bugs
cost a full rebuild of the Europa cut's Jupiter slot (see
``~/Videos/wolves-directors-cut/STORYBOARD.md``). Nothing here is allowed to
repeat it.

    python3 scripts/build_summit_plates.py --fetch   # first run: download too
    python3 scripts/build_summit_plates.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SRC_DIR = REPO / "media" / "summit"
OUT_DIR = REPO / "renders" / "summit-plates"
# The photo list is an AUTHORED INPUT -- ids, resolved URLs, the licence and
# the owner's crop authorisation -- so it is committed, the same way the megacut
# keeps its manifests in stories/ rather than in the gitignored renders/.
MANIFEST = REPO / "stories" / "summit-photos.json"

W, H = 1920, 1080

# Which photograph fills which slot, and the duplicate limit, are AUTHORED
# INPUTS -- they are editorial choices, not code -- so they live in the
# committed manifest beside the licence and the URLs. Reading them from there
# also lets the offline test suite check the slots against build_wolves.py
# WITHOUT importing this module, which needs numpy and Pillow that CI does not
# install: the frame-touching extras are optional here by design (AGENTS.md).
_META = json.loads(MANIFEST.read_text())
ASSIGNMENT = _META["assignment"]

# Above this, two plates are the same picture as far as an audience is
# concerned. Measured on 32x32 normalised luma.
DUPLICATE_CORRELATION = _META["duplicate_correlation_limit"]

# Grade applied to all six, so they sit in one film rather than six.
# Deliberately gentle: these are photographs of colleagues, not a look.
GAMMA = 1.06          # a touch of lift, so faces do not crush against the cut
SATURATION = 0.94     # pulled back toward the cinematic footage either side
VIGNETTE = 0.18       # matches the darkening the surrounding shots carry


def detail_map(img):
    """Local variance, as a stand-in for 'where are the people'.

    Faces, lanyards and badges are high-frequency; foliage at this scale,
    carpet and ceiling are not. Cheap, deterministic, and good enough to keep
    a crop off the empty half of a wide group shot.
    """
    import numpy as np

    g = np.asarray(img.convert("L"), dtype=float)
    # 2-D box variance via separable running sums.
    k = 17
    pad = k // 2
    p = np.pad(g, pad, mode="edge")
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    c2 = np.cumsum(np.cumsum(p ** 2, axis=0), axis=1)

    def win(cs):
        return (cs[k:, k:] - cs[:-k, k:] - cs[k:, :-k] + cs[:-k, :-k])

    n = k * k
    mean = win(c) / n
    return np.maximum(win(c2) / n - mean ** 2, 0.0)


def best_crop(img):
    """The 16:9 window holding the most detail, at the largest possible size."""
    import numpy as np

    w, h = img.size
    if w / h >= W / H:                      # source is wider: crop left/right
        cw, ch = int(round(h * W / H)), h
    else:                                   # source is taller: crop top/bottom
        cw, ch = w, int(round(w * H / W))
    d = detail_map(img)
    if cw < w:
        col = d.sum(axis=0)
        run = np.convolve(col, np.ones(cw), mode="valid")
        return int(np.argmax(run)), 0, cw, ch
    if ch < h:
        row = d.sum(axis=1)
        run = np.convolve(row, np.ones(ch), mode="valid")
        return 0, int(np.argmax(run)), cw, ch
    return 0, 0, cw, ch


def grade(arr):
    """One common treatment, in float, rounded exactly once by the caller."""
    import numpy as np

    x = arr / 255.0
    x = np.power(x, 1.0 / GAMMA)
    lum = (x * [0.2126, 0.7152, 0.0722]).sum(axis=2, keepdims=True)
    x = lum + (x - lum) * SATURATION

    h, w = x.shape[:2]
    yy = (np.linspace(-1.0, 1.0, h) ** 2)[:, None]
    xx = (np.linspace(-1.0, 1.0, w) ** 2)[None, :]
    r = np.sqrt((yy + xx) / 2.0)
    x *= (1.0 - VIGNETTE * np.clip(r, 0.0, 1.0) ** 2)[:, :, None]
    return np.clip(x, 0.0, 1.0) * 255.0


def build(stem, dest):
    import numpy as np
    from PIL import Image

    src = SRC_DIR / f"{stem}.jpg"
    if not src.exists():
        return None
    img = Image.open(src).convert("RGB")
    x, y, cw, ch = best_crop(img)
    img = img.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS)
    out = grade(np.asarray(img, dtype=float))
    # Round once, at the very end. np.uint8() truncates; np.rint does not.
    Image.fromarray(np.rint(out).astype(np.uint8)).save(dest, quality=96)
    return {"source": src.name, "crop": [x, y, cw, ch], "size": [W, H]}


def signature(path):
    """A 32x32 normalised-luma fingerprint, for telling near-duplicates apart."""
    import numpy as np
    from PIL import Image

    a = np.asarray(Image.open(path).convert("L").resize((32, 32)), dtype=float)
    return ((a - a.mean()) / (a.std() + 1e-9)).ravel()


def assert_distinct(stems):
    """No two plates may be the same picture.

    Three frames of one group photo, seconds apart, are three different files
    and one image. Catching that needs a measurement, not a filename check.
    """
    import numpy as np

    sigs = {s: signature(SRC_DIR / f"{s}.jpg") for s in stems
            if (SRC_DIR / f"{s}.jpg").exists()}
    worst = []
    keys = sorted(sigs)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            r = float(np.dot(sigs[a], sigs[b]) / len(sigs[a]))
            if r > DUPLICATE_CORRELATION:
                worst.append((r, a, b))
    if worst:
        worst.sort(reverse=True)
        raise SystemExit(
            "two slots would show the same picture:\n" + "\n".join(
                f"  {a} vs {b}: correlation {r:.2f} "
                f"(limit {DUPLICATE_CORRELATION})" for r, a, b in worst))
    return max((float(np.dot(sigs[a], sigs[b]) / len(sigs[a]))
                for i, a in enumerate(keys) for b in keys[i + 1:]), default=0.0)


def fetch():
    """Download the photographs named in the committed manifest.

    Stills are never committed, so a fresh clone has to fetch. The URLs live in
    the manifest rather than being derived here on purpose: Flickr gives every
    size at ``_h`` and above its own secret, so the largest rendition cannot be
    computed from a photo id -- it has to be read off the photo's own sizes
    page, which is what put these URLs in the manifest.
    """
    import urllib.request

    meta = json.loads(MANIFEST.read_text())
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    for photo in meta["photos"]:
        dest = REPO / photo["file"]
        if dest.exists() or not photo.get("url"):
            continue
        urllib.request.urlretrieve(photo["url"], dest)
        print(f"fetched {dest.relative_to(REPO)}")
    print(f"{meta['creator']} -- {meta['license']}. {meta['attribution']}")


def main():
    if "--fetch" in sys.argv:
        fetch()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    peak = assert_distinct(ASSIGNMENT.values())
    manifest, missing = {}, []
    for slot, stem in ASSIGNMENT.items():
        dest = OUT_DIR / f"{slot}.jpg"
        rec = build(stem, dest)
        if rec is None:
            # Degrade, never block: a slot with no photograph is reported, and
            # build_wolves.py falls back to its marker card for that slot.
            missing.append((slot, stem))
            continue
        manifest[slot] = dict(rec, plate=str(dest.relative_to(REPO)))
        print(f"{slot:14s} <- {stem}  crop={rec['crop']}")

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1))
    if missing:
        print("\nMISSING -- these slots keep their marker card:", file=sys.stderr)
        for slot, stem in missing:
            print(f"  {slot}: {stem}.jpg not in media/summit/", file=sys.stderr)
    print(f"-> {OUT_DIR / 'manifest.json'}  ({len(manifest)}/{len(ASSIGNMENT)} slots)"
          f"  peak pairwise correlation {peak:.2f}")


if __name__ == "__main__":
    main()

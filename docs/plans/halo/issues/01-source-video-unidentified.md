# H-01 — The source video in #11 is not identified

**What:** #11 says "Take the video provided and turn it into Halo 1" and
"Reuse the same underlying implementation and structure built for the
Destiny-universe version of this trailer". Neither the video nor the
Destiny-universe version is linked. Every other issue in the repo that names a
source names it with a URL (#1, #2, #3, #4); this one does not.

**Why it blocks:** the corpus (H-07) is built from specific video ids, and a
video record carries a canonical URL and a rights note. Guessing which video is
meant produces an index of the wrong footage that looks correct.

**Scope:** owner supplies, in the issue:
- the URL of "the video provided";
- the URL or PR of the Destiny-universe version of this trailer, so the
  structure being re-skinned can actually be read rather than inferred;
- whether the campaign is cut from that one video or from a wider Halo corpus —
  #11 asks for "the full arc of the game" across multiple episodes, which one
  trailer cannot cover, so this is a real question and not a formality.

**Acceptance:**
- [ ] URLs are in the issue.
- [ ] H-07 lists the video ids it will ingest.

**Depends on:** —

**Automatable:** no — nobody but the owner knows which video was meant.

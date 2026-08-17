# Attributions

Credits that a licence **requires**, reproduced verbatim.

Everything here is **copy, not policy**: the licensor specifies the wording, so
these strings are reproduced exactly — never paraphrased, reformatted,
shortened, or merged. `tests/test_index_integrity.py` asserts that every bed
record claiming `usage_class: cc_by_4_0` has each line of its credit present in
this file, so deleting a line here fails the suite rather than the licence.

This file is where an attribution obligation lands **today**. Act VIII, the
credits sequence, is not designed yet ([#51]) — when it is, these credits get an
on-screen home too, and this file stays as the machine-checkable record. A
missing credits sequence is not a reason to refuse a track: attribution has to
land *somewhere*, not somewhere specific.

## Music

### Local Forecast – Slower — act VI, the Ambassadors interruption

Kevin MacLeod / Incompetech, licensed **CC BY 4.0**. Commercial use, sync and
redistribution are all permitted; attribution is the only condition. **Not
CC0.** Required credit, exactly as the licensor gives it:

```text
Local Forecast - Slower Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0
https://creativecommons.org/licenses/by/4.0/
```

Record: [`music/bed_local_forecast_slower.json`](music/bed_local_forecast_slower.json).
Source: <https://incompetech.com/music/royalty-free/mp3-royaltyfree/Local%20Forecast%20-%20Slower.mp3>

`TODO(owner)`: this credit also belongs in the video description at publication,
and on screen once the credits act exists — [#51].

## Still photography

### Maintainer Summit North America 2025 — act I title cover, act VI plates, Perfume movement 4

The KubeCon contributor summit group photographs are CNCF's, licensed
**CC BY-NC-ND 4.0**. This film is non-commercial, which the NC clause permits;
the ND clause forbids distributing a derivative, and every plate is a crop —
the crop authorisation is the owner's own decision, recorded verbatim in the
record. The same album's overhead wide (group-002) is also the "CNCF
Contributor picture" overlaid in Perfume movement 4's derivative
(`contributor-summit` in
[`stories/00-perfume-thread.json`](stories/00-perfume-thread.json)) — the same
licence, the same authorisation, the same credit. Required credit, built from
the record's own fields:

```text
Maintainer Summit North America 2025 — Cloud Native Computing Foundation
https://www.flickr.com/photos/143247548@N03/albums/72177720330210424/
Licensed under Creative Commons: By Attribution-NonCommercial-NoDerivatives 4.0
https://creativecommons.org/licenses/by-nc-nd/4.0/
```

Record: [`stories/summit-photos.json`](stories/summit-photos.json), including
which photograph fills which slot.

`TODO(owner)`: this credit also belongs in the video description at publication,
and on screen once the credits act exists — [#51].

## Bungie footage

Not an attribution licence and **not listed here**. Destiny footage is
third-party copyrighted and used under Bungie's fan-content policy, which
permits non-commercial fan creations. Every video record carries `usage_class`
and `source_rights_note`; the film's own title card states the position on
screen. See [`AGENTS.md`](AGENTS.md), "Rights".

[#51]: https://github.com/castrojo/destiny-vids/issues/51

## Kubernetes

The Kubernetes logo (the white helm) appears as the **O of WOLVES** in the
feature's main title. It is a trademark of The Linux Foundation, distributed by
the CNCF under **CC BY 4.0**:

> The Kubernetes logo is a trademark of The Linux Foundation. Artwork from
> [cncf/artwork](https://github.com/cncf/artwork), licensed under
> [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Cached by `scripts/fetch_brand_marks.py` from
`projects/kubernetes/icon/white/kubernetes-icon-white.svg`. The mark is
**reproduced unmodified** -- the published white icon is already `fill:#fff`,
so nothing here recolours it; it is scaled and seated on the title's baseline
and nothing else.

## Project Bluefin artwork

The extra wallpapers in the Perfume interludes -- `bluefin`, `prey`, `dusk`,
`huntress`, `leaf-collector`, `eyes`, `lazy-days`, `duality` -- and the angry
raptor used for the jump scare are **Project Bluefin's own artwork**, from
[ublue-os/artwork](https://github.com/ublue-os/artwork) and the project's
website. This film is Project Bluefin's; the art is not a third party's.
Cached by `scripts/fetch_artwork.py`.

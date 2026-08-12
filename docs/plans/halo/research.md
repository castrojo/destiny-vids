# Halo campaign — research

The external facts [`design.md`](design.md) rests on, with citations, and an
explicit list of what could not be verified. Researched 2026-08-11.

Repo-internal facts (file paths, line numbers, enum values) are not cited here —
`vocab/`, `schema/` and the tool docstrings are authoritative and were read
directly.

## 1. Rights

### Halo — Microsoft's Game Content Usage Rules

Halo is a Microsoft property, and Microsoft's **Game Content Usage Rules**
(<https://www.xbox.com/en-US/developers/rules>) are the operative fan-content
policy; Halo Studios (formerly 343 Industries) publishes no separate policy
document. Background and clarification:
[Xbox Wire, 2015](https://news.xbox.com/en-us/2015/01/15/game-content-usage-rules-clarification/),
[Halo Waypoint creator guide](https://www.halowaypoint.com/news/content-creator-guide).

What matters for this project:

| Term | Effect here |
|---|---|
| Non-commercial fan videos using game footage are permitted | The episodes are fine in principle. |
| A prescribed **attribution/disclaimer** must appear, plus a link to the rules | It is on-screen or in-description copy, so it is authored text like every other string this repo puts on a frame. |
| No implication of official endorsement | The campaign's title and framing must not read as an official Halo release. |
| Assets obtained by datamining or reverse engineering are excluded | Index published footage only, which is what this repo does anyway. |
| Publishing fan content grants Microsoft a royalty-free licence to it | An asymmetry Bungie's policy does not have. Worth the owner knowing before publishing. |
| **Soundtrack recordings as standalone audio are not covered** | The Halo OST cannot be the score bed on this repo's own posture. See §5. |

### Destiny — Bungie's policy, for contrast

<https://www.bungie.net/7/en/legal/intellectualpropertytrademarks>. Stricter on
donations and on re-uploading cutscene-only compilations; no equivalent reverse
licence grant. The repo's current `source_rights_note` (`tools/ingest.py:31`)
states the Bungie position, which is correct for Destiny records and wrong for
Halo ones — hence H-03.

## 2. Official footage sources

| Channel | URL |
|---|---|
| HALO (official) | <https://www.youtube.com/@Halo> |
| Xbox | <https://www.youtube.com/@Xbox> |

The official channel publishes cinematic compilations, and `tools/ingest.py`
already reads titles from YouTube's oEmbed endpoint without an API key, so
ingesting Halo videos needs no new plumbing beyond per-universe inference rules.

**No specific Halo video id is committed to in this plan.** Candidate URLs
surfaced during research could not be opened from this environment, and a video
record carries a rights note and a canonical URL — both wrong-able. H-07 starts
by verifying the uploads on the official channel by hand.

One live ambiguity: search results reference a **"Halo: Campaign Evolved"**
Halo Studios project distinct from the 2011 *Combat Evolved Anniversary*
remaster. Which release the corpus comes from decides the `era` value, the HUD
era, and possibly whether the material is pre-release. Verify before ingesting.

## 3. Halo CE / Halo 2-era HUD design language

Sources: [Halopedia — Heads-up display](https://www.halopedia.org/Heads-up_display),
[Halo Alpha — Heads-up display](https://halo.fandom.com/wiki/Heads-up_display),
[Game UI Database — Halo CE Anniversary](https://www.gameuidatabase.com/gameData.php?id=1347).

### Halo: Combat Evolved (2001)

| Element | Position | Notes |
|---|---|---|
| Motion tracker | **lower left** | 15 m radius; moving contacts only; red hostiles, yellow allies |
| Shield bar | **upper centre** | recharges after a delay |
| Health bar | upper centre, with the shield | does **not** recharge; removed in Halo 2 |
| Ammo counter | **upper right** | magazine + reserve |
| Grenade counter | upper right, under the ammo | frag and plasma icons |
| Reticle | centre | weapon-dependent shape |
| Waypoints / objective markers | screen edge | |
| Damage direction | screen-edge flash | |

Palette is **translucent blue-cyan**, read as projected on the inside of the
visor, with hard angular geometry. The era's typeface is **Handel Gothic**
([Wikipedia](https://en.wikipedia.org/wiki/Handel_Gothic)) — a commercial font,
so nothing gets bundled and a licensed or installed substitute is chosen at
render time.

### Halo 2 (2004), and the eras to avoid

Halo 2 keeps the layout, widens the tracker to 20 m, and **removes the health
bar** — shield-only is the single clearest "this is Halo 2" tell. Halo 3 onward
moves to Conduit ITC and softer chrome; Halo 4 adds Forerunner gold and angular
redesign; Infinite is minimalist. Any of those in the overlay is an anachronism
against the brief, which asks for CE/Halo 2 specifically.

**Conflict to resolve (H-11):** #11 asks for "translucent green UNSC interface
elements" and "military green", and also says "keep it canon". The CE/2 HUD is
blue-cyan. Both instructions cannot hold; the owner picks.

## 4. Halo: Combat Evolved campaign arc

Ten missions, in order — the spine the episode map in
[`design.md`](design.md#12-proposed-episode-map-draft) groups into six episodes.
Source: [Halopedia — Halo: Combat Evolved](https://www.halopedia.org/Halo:_Combat_Evolved).

| # | Mission | Beat |
|---|---|---|
| 1 | The Pillar of Autumn | Waking aboard the cruiser as it flees; crash-landing at the ring. |
| 2 | Halo | Escaping the wreck and establishing a beachhead on the surface. |
| 3 | Truth and Reconciliation | A night raid on a Covenant cruiser to recover Captain Keyes. |
| 4 | The Silent Cartographer | An island assault to reach the Forerunner map room. |
| 5 | Assault on the Control Room | A long push through canyons and Forerunner interiors. |
| 6 | 343 Guilty Spark | A distress signal in the swamp; first contact with the Flood. |
| 7 | The Library | Fighting through the stacks for the Activation Index. |
| 8 | Two Betrayals | The Monitor's real agenda; destroying the ring's power. |
| 9 | Keyes | Boarding a Covenant ship to find Keyes consumed. |
| 10 | The Maw | Detonating the Autumn's reactor and escaping the ring. |

## 5. Halo canon audio

Composed by **Martin O'Donnell and Michael Salvatori**; the *Halo Original
Soundtrack* was released in 2002 through Sumthing Else Music Works, with the
copyright held by **Microsoft**
([Wikipedia](https://en.wikipedia.org/wiki/Halo_Original_Soundtrack)). The
signature cues are the Opening Suite (the chant), "Under Cover of Night",
"Rock Anthem for Saving the World", "Perilous Journey" and the "Halo" title
track.

Two facts that decide H-02:

1. The Game Content Usage Rules cover **game content in videos**, not soundtrack
   recordings used as standalone audio. A Halo-OST-scored fan episode is outside
   what the policy grants.
2. Halo OST audio is Content ID-claimed on YouTube. Claims on these tracks have
   also been filed by third parties with no rights to them — famously against
   O'Donnell himself
   ([Freezenet](https://www.freezenet.ca/destiny-halo-composer-martin-odonnell-hit-with-copyright-fraud-on-youtube/)) —
   so even a correct use invites a dispute.

The Wolves catalogue, which the body of #11 names as the audio source, has none
of these problems. **The repo has no catalogue file today**; H-02 asks the owner
to supply one (metadata only: track id, title, duration, rights — never the
audio).

## 6. The orgs and handles to be cast

Verified against the GitHub API on 2026-08-11 from this session:

| In #11 | Reality |
|---|---|
| `bazzite-gg` | **Does not exist as an org.** Bazzite lives at `ublue-os/bazzite`; the site repo is `ublue-os/bazzite.gg`. |
| `aurora` | **Not a standalone org.** Aurora is `ublue-os/aurora` (KDE image, ~763 stars). |
| `ublue-os` | Exists — Universal Blue. Flagship `ublue-os/bazzite`. |
| `nobara` | The org is **`Nobara-Project`** (8 public repos; flagship `rpm-sources`). |
| `opengamingcollective` | Resolves to **`OpenGamingCollective`** (13 public repos; `asusctl`, `ScopeBuddy`, `cardwire`). |
| `fyralabs` | Resolves to **`FyraLabs`**. |
| `kylegospo` | Canonical login is **`KyleGospo`**. |
| `bketelsen` | Exists. |
| `GloriousEggroll` | Exists. |

Two of the six named orgs are not orgs, so an unattended run would silently
credit a smaller squad than the brief describes — H-04.

### Enumerating a contributor base

`tools/ensemble.py` today asks `gh api repos/{repo}/commits?since=&until=` per
repo over a hardcoded Bluefin list (`tools/ensemble.py:41–47`). For orgs:

- `GET /orgs/{org}/repos` then per-repo contributors or commits.
  ([REST docs](https://docs.github.com/en/rest/repos/repos#list-repository-contributors))
- `GET /orgs/{org}/members` returns **public members only** unless authenticated
  as an admin, and org membership is not the same population as contributors.
  ([REST docs](https://docs.github.com/en/rest/orgs/members))
- Pagination is `per_page` (max 100) + `page`; authenticated rate limit is 5,000
  requests/hour. `ublue-os` alone is ~93 repos, so a naive org walk is ~100
  requests before any commit queries.
  ([Rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api))

## 7. Could not verify

| Item | Why | Who resolves it |
|---|---|---|
| Exact current text of the Game Content Usage Rules and the required disclaimer string | `xbox.com` not reachable from this environment | H-03, by reading the page |
| Exact current text of Bungie's IP policy | same | H-03 |
| Specific official Halo CE/Anniversary cinematic video ids | YouTube not reachable from this environment | H-07 |
| Whether "Halo: Campaign Evolved" is the intended source and what its status is | reported by search, unconfirmed | H-00/H-07 |
| Authoritative hex values for the CE HUD palette | no published spec found; screenshots are the only reference | H-11 |
| The contents of the Wolves catalogue | owner-supplied, not in this repo | H-02 |
| Which video #11 means by "the video provided" | no link in the issue body | H-01 |
| Brand-guideline / permission terms for each org's logo | each project publishes its own, and none were reachable to confirm | H-14 |

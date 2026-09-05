# Where plate copy is authored

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep the
skill inside its size budget. **This is the file that decides whether a
credit is reproduced or invented** — read it before writing any plate copy.


"The deck" is shorthand for **four** files outside this repo, and knowing which
one to read is the difference between reproducing a credit and inventing one.
None of them is editable from here — this repo *reproduces* them:

| Source | What it is authoritative for |
|---|---|
| `~/Videos/nameplates.json` | The **field set**, the chrome flags, and the KubeCon interview's own plate timings. The worked example of every shape. |
| `~/src/website/public/wolves/characters/characters.json` | The **authored Guardian identities** — `label`, `class`, `name`, `title` per person. The broadest roster: seven people. |
| `~/src/website` `src/data/wolves-intro-sequence.ts` | The same identities as they appear in the Wolves intro, and the second corroboration when one disagrees. |
| `~/Videos/wolves-{kat,natali}/render/reveal.html` | The **baked** treatment the finished cuts actually shipped. Where it disagrees with the live site CSS, it wins — see "Styling provenance". |

**Never touch `~/src/website`.** Several agents run worktrees against it; read
it, quote it, and cite the file you read.

The seven authored identities, verbatim:

| Person | Label | Class | Title |
|---|---|---|---|
| Bob Killen | `TRUSTEE // GUARDIAN` | Voidwalker Warlock | Reconciler of the Plane |
| Kat Cosgrove | `MAINTAINER // GUARDIAN` | Sentinel Titan | Defender Queen of the Lost |
| Kaslin Fields | `MAINTAINER // GUARDIAN` | Stormcaller Warlock | Rage of the Paradox |
| Laura Santamaria | `MAINTAINER // GUARDIAN` | Gunslinger Hunter | The Order of Seven |
| Christoph Blecker | `TRUSTEE // GUARDIAN` | Broodweaver Warlock | First Among Equals — The North Star |
| Natali Vlatko | `MAINTAINER // GUARDIAN` | Behemoth Titan | Shipwright of Kubernetes |
| Doc Anderson | `MAINTAINER // GUARDIAN` | Shadebinder Warlock | Foundry of the Forbidden |

Plus, from `nameplates.json` only: **Jeffrey Sica** (Stormbreaker Titan,
*Forgemaster of the Seven*) and **Amber Graner** (Striker Titan, *The Iron
Standard*). The deck's Jorge Castro entry says Harbinger Titan with trustee
chrome; the owner has superseded both fields for this repo. The canonical
casting record is **Harbinger Hunter** on basic blue, with the full title
*Upender of Antipatterns | The First Disciple*.

Two things follow, and they are the reason this section exists:

- **An identity that is authored must be reproduced, never paraphrased and
  never replaced by the generic fallback.** A person with an entry above is not
  a Bluefin Blueberry, wherever their credit lands.
- **An identity that is not authored is not yours to write.** `np_amber`'s own
  note records the correct shape of that gap: the deck carried
  `Subclass [ REDACTED ]` until the *owner* supplied Amber's class. That is
  exactly the state issue #5 is in for Karena Angell's subclass — the row ships
  short until the owner has the word.

### Known divergences and owner overrides

This is the lookup point for both unresolved disagreements and owner decisions
that supersede an external source. Unresolved items remain somebody's call, not
an agent's:

- **Jorge Castro's class and chrome are resolved owner overrides.** The external
  deck still says Harbinger Titan with silver trustee chrome. This repo's
  canonical binding says Harbinger Hunter on basic blue: the owner superseded
  both deck fields, while keeping `TRUSTEE // GUARDIAN` as label copy.
- **Jeffrey Sica's title.** The deck says *Forgemaster of the Seven*; issue #1's
  owner-authored brief copy says *Forgemaster of Kubernetes*. A brief is the
  owner speaking, so `plan` will use it — but the two records disagree and one
  of them wants editing. See #27 (and #17 for whether he is cast at all).
- **A portrait row.** `reveal.html`'s `pfp` is implemented as the `avatar`
  chrome flag — see [`references/plate-chrome.md`](plate-chrome.md).
- **Kelsey Hightower has no deck entry** — but his plate is authored anyway.
  The owner wrote all four rows (`ARCHITECT // GUARDIAN`, Dawnblade Warlock,
  Kelsey Hightower, *Evangelist of the Open Sky*) into issue #8, so the issue —
  not the deck — is the authorisation, and the rows are reproduced verbatim on
  Zavala's binding. #33 added gold chrome (`variant: leader`) **on top of** that
  copy, not instead of it. Anything beyond those four rows is still not ours to
  write: a lead's `class: titan` tags describe *Zavala*, and printing one on
  the card would make it a claim about Kelsey, which only the owner may make.
- **Four of the seven have no binding here** — Kaslin, Christoph, Natali and
  Andy (see #26); Bob, Laura and Kat are bound and their copy is reproduced
  above. Adding a binding is a casting decision ([`casting.md`](../../casting/SKILL.md));
  copying authored copy onto an existing binding is reproduction and is allowed.

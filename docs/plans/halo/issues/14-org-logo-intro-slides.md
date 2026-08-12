# H-14 — Replace the intro slides with org logos

**What:** #11's last line asks to "replace the logo intro slides with logos from
nobara, bazzite, etc." — a title-card deck at the head of each episode carrying
the marks of the orgs whose contributors are in the squad. `tools/plate.py`
already renders and burns cards; what it has never handled is a **third-party
image asset**, and that is the whole of this issue.

**Why it is not just another plate:**

| | A nameplate today | An org logo |
|---|---|---|
| Content | Text the owner authored | A trademark owned by someone else |
| Rights basis | The repo's own copy | That project's mark, used with its permission and to its brand guidelines |
| Storage | Rendered from a font at build time | A binary asset that has to come from somewhere |

Bungie's fan-content policy and Microsoft's GCUR (H-03) are about *game*
content. Neither says anything about an open-source project's logo. That is a
separate permission, per org.

**Scope:**
- A logo manifest: one entry per org with the mark's source URL, a checksum, the
  permission basis (brand-guidelines link, licence, or explicit grant), and the
  owner-authored on-screen name. Same posture as footage — **referenced, not
  vendored**: `media/` is gitignored, and committing third-party marks into the
  repo is a rights decision, not a convenience one.
- The org list is the corrected one from
  [H-04](04-cast-and-org-list-corrections.md), not the list as written in #11.
  A slide is a claim about who made this; two of the orgs named in the brief do
  not exist.
- Intro composition: the deck at the head of each episode, on the existing
  plate scheduling rules (one card at a time, held long enough to read).
- Marks are used **as given**: no recolouring into HUD green, no compositing into
  the visor frame, no invented tagline. On-screen copy stays the closed authored
  set `docs/skills/plates.md` requires.
- A missing or unverifiable logo is **missing, not a failure**: the episode
  ships with that org's slide omitted and the gap recorded in the run's miss
  report, per "Degrade, never block" in `AGENTS.md`. What stays forbidden is
  *inventing* — no substitute mark, no recoloured placeholder, no stand-in. The
  roster itself still comes from the corrected list (H-04); what degrades is
  the slide, never the credit.

**Acceptance:**
- [ ] Every logo in the manifest has a source, a checksum and a permission basis.
- [ ] No image asset is committed to the repo.
- [ ] The intro deck renders from the manifest, and a missing asset is omitted
      and recorded, never substituted.
- [ ] No mark is recoloured or restyled by the renderer.

**Depends on:** H-04 (which orgs), H-09 (episodes to put a head on)

**Automatable:** partly — composition is mechanical; sourcing each mark and
recording its permission basis is the owner's, per org.

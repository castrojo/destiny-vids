# H-04 — Cast list and org list need correcting before anyone is credited

**What:** #11 names three people and six GitHub orgs. Checked against the GitHub
API on 2026-08-11, **two of the six orgs do not exist** and two handles are
spelled differently from their canonical logins. An unattended run would credit a
smaller squad than the brief describes and print handles nobody uses.

| In #11 | Reality |
|---|---|
| `bazzite-gg` | not an org — Bazzite is `ublue-os/bazzite`, the site is `ublue-os/bazzite.gg` |
| `aurora` | not an org — Aurora is `ublue-os/aurora` |
| `nobara` | the org is `Nobara-Project` |
| `opengamingcollective` | resolves to `OpenGamingCollective` |
| `fyralabs` | resolves to `FyraLabs` |
| `ublue-os` | correct |
| `kylegospo` | canonical login `KyleGospo` |
| `bketelsen`, `GloriousEggroll` | correct |

**Why it blocks:** rule 3 — casting names real people. A roster built from a list
with two dead entries silently drops whole communities from the credits, and a
callout that prints a handle the person does not use is unauthored copy on a card
whose only job is naming them.

**Scope:**
- Owner confirms the corrected org list, and whether "the Bazzite org" means
  `ublue-os` or a filtered subset of it (Aurora and Bazzite are repos inside one
  org, so an org walk credits both communities as one).
- Owner authors the three lead bindings, which are claims about real people:
  - `john_17` → `KyleGospo`, with **no** blanket `require_helmet`: #11's own
    opening shot has the helmet under his arm, and he pulls it on later. The
    `saladin` precedent constrains a character who is never helmeted; this one is
    helmeted for most of the campaign but not all of it, so the helmet state
    belongs on the beat (`helmet_simplicity` / `identity_visibility` filters in
    the outline), not on the binding;
  - `sgt_johnson` → `bketelsen`;
  - the second veteran on the heavy weapon → `GloriousEggroll`; #11 gives no
    canon name, so the binding is keyed on the description, like
    `iron_lord_red_haired`.
- Owner supplies each person's on-screen display form. Handles are identifiers,
  not copy, and `docs/skills/plates.md` forbids inventing what a card says.
- Confirm "John 17" is the intended spelling (canon is John-117). It is carried
  verbatim either way; this asks once rather than correcting silently.

**Acceptance:**
- [ ] The org list in the campaign cast file resolves — every entry returns repos
      from the API.
- [ ] Three lead bindings exist in the Halo universe pack with owner-authored
      display names.
- [ ] No display string is derived from a handle at render time.

**Depends on:** —

**Automatable:** no — every line of it is a claim about a real person.

# H-13 — Skills and docs for the campaign and HUD stages

**What:** two new pipeline stages (campaign assembly, HUD burn) and a
multi-universe index need routing, or the next agent reads `editing.md`, finds
nothing about movements, and improvises.

**Scope:**
- `docs/skills/campaign.md` — writing a campaign file, movement rules, what a
  reported unmatched beat means, how the score constrains a combat movement's
  length. Category `editing`; depends on `editing`.
- `docs/skills/hud.md` — planning and burning the HUD layer, the closed callout
  set, the era decisions, and the "our overlay never launders unclean source
  footage" rule. Category `editing`; depends on `editing`, `casting`.
- Update `docs/skills/casting.md` and `docs/skills/indexing.md` for universes:
  which vocab pack applies, that a lead binding lives under
  `vocab/universes/<universe>/`, and where a *run's* cast file binds people to
  those roles (H-12).
- Update `docs/skills/plates/SKILL.md` for the org logo deck (H-14): a third-party mark
  is not authored copy, and it is referenced rather than vendored.
- Route both from `docs/SKILL.md`, then regenerate the catalog:
  `python3 scripts/generate_skill_index.py --write`.
- Update the `README.md` layout table for the new tools and directories.

**Acceptance:**
- [ ] `python3 scripts/generate_skill_index.py --check` passes.
- [ ] `tests/test_skill_catalog.py` passes — every skill is routed, every routed
      skill exists, and each file is inside the size budget.
- [ ] Each new skill follows the front-matter contract and the 200-line soft
      budget in `docs/SKILL.md`.

**Depends on:** H-09, H-10, H-11, H-14

**Automatable:** yes.

# Halo campaign — plan

Planning artifact for [#11](https://github.com/castrojo/destiny-vids/issues/11):
a multi-episode Halo: Combat Evolved campaign starring the Open Gaming
Collective, built on the machinery this repo already has, and re-runnable as a
template with a different cast of GitHub users swapped in.

**This directory changes no pipeline behaviour.** It is the planning phase: the
design, the research it rests on, and one issue-ready file per unit of work.

| Read | For |
|---|---|
| [`design.md`](design.md) | The system: universe packs, the campaign/episode format, scored assembly, the HUD layer, the re-runnable template. |
| [`research.md`](research.md) | External facts with citations — rights, footage sources, CE-era HUD language, the CE mission arc, the orgs to be cast — and what could not be verified. |
| [`issues/`](issues) | One file per issue, ready to file verbatim. |

## How to file these

Each file in [`issues/`](issues) is a complete issue body. File them in the
order below, title them with the file's `#` heading, and replace the plan ids
(`H-00`…`H-13`) in the **Depends on** lines with the real issue numbers as they
are created. #11 becomes the epic that tracks them.

## The map

Cross-references use plan ids, not GitHub numbers, until the issues exist.

### Decide first — nothing downstream is safe to build until these land

| Id | Issue | Automatable |
|---|---|---|
| H-00 | [Decide the footage provenance: index Halo footage, or generate it](issues/00-decide-footage-provenance.md) | no — owner |
| H-01 | [The source video in #11 is not identified](issues/01-source-video-unidentified.md) | no — owner |
| H-02 | [Score: the Wolves catalogue and "use the Halo music" are mutually exclusive](issues/02-audio-source-contradiction.md) | no — owner |
| H-03 | [Rights posture for a second franchise: Microsoft's GCUR, not Bungie's policy](issues/03-rights-posture-second-franchise.md) | partly |
| H-04 | [Cast list and org list need correcting before anyone is credited](issues/04-cast-and-org-list-corrections.md) | no — owner |

### Foundations — make the index multi-franchise

| Id | Issue | Depends on | Automatable |
|---|---|---|---|
| H-05 | [Universe packs: scope the Destiny-specific vocab so a second universe can exist](issues/05-universe-packs.md) | H-00 | yes |
| H-06 | [Move the search lexicon out of `tools/search.py` and into the vocab](issues/06-data-driven-lexicon.md) | H-05 | yes |
| H-07 | [Ingest the Halo corpus: video records, rights notes, era/destination rules](issues/07-halo-corpus-ingestion.md) | H-00, H-01, H-03, H-05 | partly |
| H-08 | [Roster the squad from arbitrary GitHub orgs, not the Bluefin repo list](issues/08-org-sourced-rosters.md) | H-04 | yes |

### The campaign — episodes, score, HUD

| Id | Issue | Depends on | Automatable |
|---|---|---|---|
| H-09 | [A campaign/episode format: movements that alternate dialogue and combat](issues/09-campaign-episode-format.md) | H-05 | yes |
| H-10 | [Scored assembly: fill a combat movement to one track, and lay per-movement audio](issues/10-scored-assembly-and-audio-plan.md) | H-02, H-09 | yes |
| H-11 | [The Halo CE-era HUD layer](issues/11-hud-layer.md) | H-04, H-09 | partly |
| H-12 | [Re-run the same campaign template with a different cast](issues/12-reusable-campaign-template.md) | H-08, H-09, H-11 | yes |

### Meta

| Id | Issue | Depends on | Automatable |
|---|---|---|---|
| H-13 | [Skills and docs for the campaign and HUD stages](issues/13-skills-and-docs.md) | H-09, H-10, H-11 | yes |

## Dependency order, as a line

```
H-00 ─┬─> H-05 ─┬─> H-06
      │         ├─> H-07  (also H-01, H-03)
      │         └─> H-09 ─┬─> H-10  (also H-02)
      │                   ├─> H-11  (also H-04)
      │                   └─> H-13
H-04 ─┴─> H-08 ─────────────> H-12
```

## The three rules still outrank this plan

Everything here is subordinate to [`AGENTS.md`](../../../AGENTS.md):

1. **`clean` is the primary gate, positively established.** The HUD this plan
   burns is a render-time layer over clean sources. An untagged `overlays` on a
   *source* segment still derives `clean = false`, and no episode deadline
   changes that.
2. **The fiction bends to the footage.** A campaign beat with no clean match is
   rewritten, not filled from unclean coverage. The Halo arc in
   [`design.md`](design.md#11-proposed-episode-map-draft) is a draft that the
   footage gets to veto.
3. **Casting names real people.** Every handle in #11 is a person. A wrong
   `character` tag, or an invented plate line, credits them for something they
   did not do — see H-04.

# Wolves: the radio-chatter comm line — plan

Planning artifacts for [#9](https://github.com/castrojo/destiny-vids/issues/9),
"Change chat to radio chatter". **Nothing here is implemented.** Every file in
`epics/` is an issue body, ready to file as written.

**Read [`design.md`](design.md) first.** It is the system; the epics are only how
it gets built. If an epic and the design disagree, the design is wrong and should
be fixed — not worked around in an issue.

## The one-paragraph version

A maintainer edits **one plain-markdown file at the repo root**, `WOLVES.md`, and
re-runs **one command** to get a new video. That file holds the cut's beats and
its radio chatter, and nothing else: every fact about a person — display name,
face, employer, title, badges — is resolved from GitHub, because GitHub is the
source of truth. Chatter renders as a comm line with a big profile picture and a
text-generated sparkline instead of a chat box. Nameplates carry the person's
title (`$Position of $Project`), their employer's emblem in that employer's
membership tier, and their Credly badges as a military-style ribbon rack.
Everything lands on the music, because shot durations quantize to a beat grid and
sections end on bar lines.

## The epics

Ten of them, 38 sub-issues. Each file below is one epic issue plus its
sub-issues, each of which is one pull request's worth of work.

| # | File | Epic issue title | Subs | Depends on | Blocked by |
|---|---|---|---|---|---|
| A | [`epics/A-comm-log.md`](epics/A-comm-log.md) | The comm log: `WOLVES.md` is the whole show | 4 | — | — |
| B | [`epics/B-identity.md`](epics/B-identity.md) | Identity: GitHub is the source of truth | 4 | A | — |
| C | [`epics/C-affiliation.md`](epics/C-affiliation.md) | Affiliation and emblems: the bling matches the org | 4 | B | J1 |
| D | [`epics/D-titles.md`](epics/D-titles.md) | Titles: `$Position of $Project` | 3 | B | J4 |
| E | [`epics/E-heraldry.md`](epics/E-heraldry.md) | Heraldry: the Credly ribbon rack | 3 | B | J2 |
| F | [`epics/F-nameplate.md`](epics/F-nameplate.md) | Nameplate v2: the face is the interface | 4 | B, C, D, E | — |
| G | [`epics/G-chatter.md`](epics/G-chatter.md) | Radio chatter: the comm line | 4 | A, B, F | — |
| H | [`epics/H-tempo.md`](epics/H-tempo.md) | Tempo: make the cut land on the music | 4 | A | J3 |
| I | [`epics/I-autopilot.md`](epics/I-autopilot.md) | The autopilot: one command, living project | 3 | all | — |
| J | [`epics/J-rights.md`](epics/J-rights.md) | Rights, Code of Conduct, and consent | 5 | — | — |

```
        ┌──────────────── J (rights & CoC — start immediately, blocks C4/D1/E1/H1)
        │
A ──┬── B ──┬── C ─┐
    │       ├── D ─┼── F ── G ─┐
    │       └── E ─┘           ├── I
    └── H ──────────────────────┘
```

**Start with A and J in parallel.** A unblocks everything downstream; J is four
written answers that cost nothing now and can invalidate finished work later —
which is exactly what happened in
[#6](https://github.com/castrojo/destiny-vids/issues/6), where a licence checked
after the design cost the whole treatment.

**F4 can be picked up by anyone, today.** It is a real bug (`tools/plate.py` only
looks for Fedora font paths, so the plate tests fail on Debian/Ubuntu and in a
bare CI container) and it is on the critical path for the chatter renderer.

## Filing these

Each file starts with the epic body; each `## X<n> — Title` section is one
sub-issue. Suggested labels are on every one; the repo's existing set
(`enhancement`, `bug`, `documentation`, `question`, `help wanted`) covers all of
them, so nothing new needs creating.

```bash
gh issue create --repo castrojo/destiny-vids \
  --title "Epic A — The comm log: WOLVES.md is the whole show" \
  --label enhancement \
  --body-file docs/plans/wolves/epics/A-comm-log.md
```

Then split each `##` section into its own issue and link it to its epic. Keep the
`**Depends on:**` lines — the order is load-bearing, and an implementer who takes
B2 before B1 will invent a schema that B1 then has to undo.

## For whoever implements these

Read [`AGENTS.md`](../../../AGENTS.md) first. Its three rules outrank anything
convenient an issue here seems to permit, and the design adds two more of the
same kind (§"The rules that outrank convenience, extended"). The short version,
for this plan specifically:

- **Nothing about a person is guessed.** Not their employer, not their title, not
  their face. Resolve it or render nothing, and report what did not resolve.
- **Nothing is silently dropped.** Not an unmatched beat, not a chatter line that
  did not fit, not a contributor with no room in the cut. The report exists so
  that "it worked" and "it quietly lost somebody" cannot look the same.
- **No third-party media enters the repository.** Footage, audio, avatars, org
  marks, badge art — all referenced, none committed. That rule already exists for
  footage; this plan does not get an exception for anything else.

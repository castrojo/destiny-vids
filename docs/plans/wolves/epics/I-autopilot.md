# Epic I — The autopilot: one command, living project

**Parent:** #9 · **Depends on:** A, B, C, D, E, F, G, H
**Design:** [`docs/plans/wolves/design.md` §8](../design.md)

Everything above is a stage. This is the one command that runs them in order and
the one report that says what did not resolve — plus the CI that re-checks the
whole plan every time somebody edits the file, which is what makes it a living
project instead of a one-off render.

**Done looks like:**

```bash
python3 tools/wolves.py render --month 2026-08 --out renders/wolves.mp4
```

**Invariants for every sub-issue here**

- The orchestrator holds no logic of its own. Every decision lives in the stage
  that owns it; this just sequences them.
- CI never renders. It has no footage, and it must never acquire any.
- The report is the product. A silent success that dropped somebody is a failure.

---

## I1 — `tools/wolves.py render`

**Labels:** `enhancement` · **Depends on:** A4, G3, H3

Parse → resolve → match → quantize → cut → plate → chatter → burn. Each stage is
skippable (`--no-chatter`, `--no-plates`) and each writes its intermediate next
to the output so a failed run is debuggable.

**Acceptance**

- [ ] `--dry-run` does everything except touch a frame, and prints the report —
      so it works on a machine with no `media/`.
- [ ] Plate planning is handed the same hold cap the render used (the trap
      `docs/skills/editing.md` and `plates.md` both already warn about).
- [ ] Missing source media is reported and skipped, as `render.py` does today.
- [ ] Every stage's ffmpeg invocation prints which ffmpeg it resolved, as
      `render.py` does today.
- [ ] No new logic: a test asserts the orchestrator's output equals running the
      stages by hand.

---

## I2 — `docs/skills/comms.md` and the router

**Labels:** `documentation` · **Depends on:** I1

One new skill covering the comm log, chatter, and the one-command render;
category `editing`; following `projectbluefin/common`'s write-a-skill contract
like every other skill here. Link it from `docs/SKILL.md`'s table, then
regenerate the catalog.

**Acceptance**

- [ ] `python3 scripts/generate_skill_index.py --write` run, and
      `tests/test_skill_catalog.py` passes.
- [ ] Routed from `docs/SKILL.md` — a skill nobody can find does not exist.
- [ ] Under the 200-line soft budget; links to `design.md` rather than restating
      it.
- [ ] `plates.md`, `casting.md`, and `editing.md` gain a "when NOT to use" line
      pointing here, so the four do not overlap.

---

## I3 — CI: validate the plan on every push

**Labels:** `enhancement` · **Depends on:** I1

A workflow that runs `tools/wolves.py render --dry-run --json` plus the test
suite on every push and pull request touching `WOLVES.md`, `people/`, `tracks/`,
`vocab/`, or `tools/`. Publish the report as a job summary, and fail on any
`fatal`.

**Acceptance**

- [ ] No footage, no audio, no avatars fetched in CI. The dry run works from
      committed metadata alone — which is exactly why the person records are
      committed.
- [ ] A pull request that adds an unknown `@login` fails with a message naming
      the login and its line number.
- [ ] `python3 scripts/generate_skill_index.py --check` runs too; a stale catalog
      is a router that misdirects agents.
- [ ] The job summary shows the report, so a reviewer sees what changed about
      the cut without rendering it.

**Do not** add a step that downloads footage, uploads a render, or posts to
anything outside this repository.

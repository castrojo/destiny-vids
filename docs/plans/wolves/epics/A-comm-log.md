# Epic A — The comm log: `WOLVES.md` is the whole show

**Parent:** #9 · **Depends on:** — · **Blocks:** B, G, H, I
**Design:** [`docs/plans/wolves/design.md` §1](../design.md)

A maintainer should edit **one file** and get a video. This epic builds that
file's grammar, its parser, and the report that tells you what did not resolve.
It replaces nothing yet: `stories/*.txt` keeps working, and `WOLVES.md` is a
superset that adds sections, directives, and chatter.

**Done looks like:** `python3 tools/comms.py parse WOLVES.md` prints the sections,
beats, and chatter lines it found, names every problem it found, and exits
non-zero if any of them are fatal.

**Invariants for every sub-issue here**

- Order in the file *is* the timeline. Never accept a timestamp in `WOLVES.md`.
- An unknown `@login` is a warning, recorded and named in the report. Never
  drop a line to keep a parse alive — and never let one stop it.
- Prose is ignored, not rejected — the file is also the maintainer's notebook.

---

## A1 — Write `WOLVES.md` and the parser fixtures

**Labels:** `enhancement`, `documentation` · **Depends on:** —

Create the real `WOLVES.md` at the repo root, using the five constructs in the
design (`# title`, `## section`, `> key: value`, `- beat`, `@login: line`), built
from beats that already match today's index so the first parse produces a real
cut. Start from `stories/hero-cut.txt` and `stories/osiris-sagira.txt`.

Add `tests/fixtures/wolves/` with three small files: a valid log, one with an
unknown login, one with a directive naming a track that does not exist.

**Acceptance**

- [ ] `WOLVES.md` exists at the repo root, renders correctly on GitHub, and
      contains at least two sections with directives, beats, and chatter.
- [ ] Every `@login` in it is a real GitHub login of someone already cast in
      `vocab/casting.yaml` or in a recent ensemble roster.
- [ ] Fixtures added; no fixture invents a person who does not exist.

**Do not** put timestamps, display names, companies, or titles in the file.

---

## A2 — `tools/comms.py parse`: markdown → comm log

**Labels:** `enhancement` · **Depends on:** A1

Write the parser. Pure stdlib, no markdown library — the grammar is five line
shapes and a regex each.

```python
parse(text) -> {
  "title": str,
  "sections": [
    {"name": str, "directives": {"track": str, "register": int, ...},
     "beats": [{"text": str, "chatter": [{"login": str, "text": str}]}]}
  ],
  "problems": [{"level": "fatal"|"warn", "line": int, "message": str}],
}
```

Rules: a chatter line attaches to the most recent beat in its section; a chatter
line before any beat attaches to the section's first beat; unknown directive keys
are a `warn`; a chatter line whose login is not resolvable is a `warn`, counted in the
report's unresolved logins (A4 does the resolving — here, just record the login).

**Acceptance**

- [ ] Round-trips the three fixtures with the expected structure.
- [ ] Prose, `###` headings, HTML comments, and tables are ignored silently.
- [ ] A `> key: value` outside a section is a `fatal` with its line number.
- [ ] Line numbers on every problem — a report you cannot navigate is a diary.

**Tests:** `tests/test_comms.py`, following `tests/test_story.py`'s shape.

---

## A3 — Sections drive the matcher

**Labels:** `enhancement` · **Depends on:** A2

Teach `tools/story.py` to accept a parsed comm log instead of a flat outline:
match each section's beats independently, carry the section name onto every shot
in the cut list, and apply two new biases from the design:

- `register` directive → bias the score toward shots at that register
  (`vocab/register.yaml`, −2..+2). A missing directive means no bias.
- source diversity → refuse a candidate that would make a third consecutive shot
  from the same `video_id`; take the next-best instead, and if none exists, use
  it anyway and record a `warn`.

**Acceptance**

- [ ] `build_story()` accepts sections and returns `shots` tagged with `section`.
- [ ] A flat outline still works, unchanged, through the existing entry point.
- [ ] Register bias is a *bias*: it never promotes an unclean shot, never
      overrides the clean gate, and never widens the pool.
- [ ] Unmatched beats are still reported per section, never dropped.

**Tests:** a section with `register: +2` prefers the mythic shot of two otherwise
equal candidates; three shots from one video in a row is impossible when an
alternative exists.

---

## A4 — The report

**Labels:** `enhancement` · **Depends on:** A2

One printed report, the same shape everywhere, listing everything that did not
resolve: unmatched beats, unresolved logins, unrecognized companies, withheld
fields, uncredited contributors, off-grid shots. Exit non-zero when any `fatal`
is present.

**Acceptance**

- [ ] Every counter prints even when zero — a silent absence is indistinguishable
      from a bug.
- [ ] Each non-zero counter names the offending item, not just a count.
- [ ] `--json` emits the same data for CI to consume (Epic I).

**Do not** let the report become a log. It is a fixed set of counters; if
something new can go wrong, it gets its own counter.

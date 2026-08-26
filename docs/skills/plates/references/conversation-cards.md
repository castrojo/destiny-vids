# Cards that are not lower thirds, and showing a conversation

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep the
skill inside its size budget. The card kinds that own a row of their own,
and the chat card that puts recovered dialogue on screen.

## Cards that are not lower thirds

Five `kind`s sit outside the reveal plate's row: the site's `status` HUD,
Destiny's `miniboss` bar, the Xbox `achievement` toast, the `companion`
GUARDIAN BOND card and the `banner` letterbox callout —
[`references/other-cards.md`](other-cards.md),
[`references/status-nameplate.md`](status-nameplate.md). The
`miniboss` bar is the only card here that may carry copy nobody's identity was
authored for, because **it names a villain, not a person**.

The `banner` is the persistent strip, not a credit: one tracked line on the
bottom bar of a letterboxed frame (`position: "letterbox"`), below the
picture entirely, so it can hold for a whole film without sharing the lower
third's row. Its `text` is owner-authored copy, reproduced verbatim and never
uppercased — the same rule the chat pill's message follows.

## Cinematic text and authorised censors

Owner-authored narration uses `kind: caption` in the top-safe rail while
Guardian and companion cards keep the lower third. Scene-setting metadata uses
`kind: context` above that lower-third lane; a full-screen deployment beat uses
`kind: warning`. Each is an independent chrome row, not an extra nameplate
field, and carries `copy_source: owner_supplied`.

Keep chat `text` verbatim. When an owner requests a swear censor, use the
Kubernetes helm only as an `o` replacement: add a `censor` entry whose `find`
value occurs exactly once and whose `replace` value uses `{k8s}`.
`tools/plate.py` replaces that token with the cached official white helm and
does not alter the authored source string. Use an asterisk for other letters;
do not add censorship the owner did not request.

Caption glyphs are data, not template guesses. A replacement keeps the authored
`text` unchanged and records the mark under `glyphs`, identifying the target
letter (and its word/index where needed). The renderer reserves the mark's
**real width before wrapping or centering**, so a Kubernetes helm replacing an
`o` cannot cover the next letter. If the mark is missing, it degrades to the
plain authored letter. This `glyphs` contract is distinct from a full-frame
card's `glyph` / `glyph_src` query pair; see
[`full-frame-cards.md`](full-frame-cards.md).

## Showing a conversation

The chat card (`kind: chat`) puts a line of dialogue on screen under the name
of the person cast in that role. It exists because the alternative — typing the
conversation into a manifest — is exactly the invented copy the rest of this
skill forbids. Both of its fields are recovered, never authored here:

- `speaker` comes from `vocab/casting.yaml`, preferring the character's `plate:`
  name, so a line and that character's reveal credit the person identically.
- `text` comes from `dialogue/<video_id>/dialogue.json`, which carries the
  source timecodes, the recovery method, and per-line `evidence` for who is
  speaking. Fix a wrong line **there**, not in a render.

Owner-authored act conversations are moving to one Markdown file per
chapter, `chapters/<act>.md` — see [`../../chapters.md`](../../chapters.md),
whose table says which acts are migrated and where the rest of the copy
still lives. What follows is the per-video record that convention seats
against:

Each video's conversation lives in its own folder, beside the Markdown the
owner actually edits:

```text
dialogue/<video_id>/DIALOGUE.md         the conversation, as prose
dialogue/<video_id>/dialogue.json      immutable source windows and evidence
dialogue/<video_id>/presentation.json  sequence, film start, explicit delivered holds and owner pins
```

`tools/dialogue_md.py` keeps the two in step, and is the only supported way to
rewrite a line:

```bash
python3 tools/dialogue_md.py export <video_id>            # record -> DIALOGUE.md
python3 tools/dialogue_md.py apply  <video_id> --dry-run  # preview the edits
python3 tools/dialogue_md.py apply  <video_id>            # DIALOGUE.md -> record
python3 tools/dialogue_md.py restore-source-times <video_id> --from-ref <ref>
```

Editing the Markdown never loses provenance. Timecodes and evidence ride in the
heading as immutable source evidence, and `apply` refuses any changed source
window; restore source-window drift from a named git ref instead. Sequence,
film start, any explicit delivered-hold preservation, and `| pin ...`
annotations live in `presentation.json`, so reordering sections or moving a
pin is planning rather than a source edit. A line the owner rewrites is marked
`text_source: owner_supplied`, while
`text_source: placeholder` marks a cue whose words do not exist yet -- a
blank line in `DIALOGUE.md` is kept as a slot rather than failing the file, and
renders as lorem credited to `TBD`. An owner rewrite instead records
`recovered_text`; a deleted section moves to `dropped` with a reason. The
owner supplying copy is allowed — an *agent* inventing it is not, and keeping
both versions is what tells the two apart. A test asserts the checked-in
`DIALOGUE.md` still matches the record, so the pair cannot drift.

A record can also hold a line **never recovered at all** (act II's owner-
written closer): the top-level methods and the cue's `text_source`/`evidence`
are `owner_supplied` with no `recovered_text`, and it still enters via `apply`.

It deliberately carries no `class` row and no character line: who plays whom is
established once by the Guardian reveal.

```bash
# 1. reveals first -- naming the cast right is the job the index exists for
python3 tools/plate.py plan cut.json --only leads --hold 4 --out leads.json
# 2. dialogue fits around them (anchored: each line where its footage landed)
python3 tools/dialogue.py cut.json --video-id <id> --around leads.json \
    --out chat.json
# 3. the ensemble takes what is left, then merge and burn
python3 tools/plate.py plan cut.json --roster roster.json --only ensemble \
    --around fixed.json --out ens.json
python3 tools/plate.py merge leads.json chat.json ens.json --out plates.json
```

`--mode script` is the alternative: it replays the exchange in spoken order
instead of anchoring each line to its own footage. Anchored is right for an
uncut source, where the picture and the conversation share a clock. Script mode
is for a **re-ordered cut**, where anchoring scatters the lines out of sequence
and the exchange stops reading as a conversation.

Dropped lines are always reported with a reason — a line whose footage is not
in the cut, or that a reveal already covers, is never lost silently.

---

## Unwritten prose: lorem ipsum, credited to nobody

A chat pill with no `text` does **not** block, and does not render an empty
pill. `tools/placeholder.py` fills it with deterministic lorem ipsum so the cut
is watchable before its words exist — timing, letterbox seat, read length and
the gaps between plates are all reviewable while the copy is still being
written.

```bash
python3 tools/placeholder.py list        # every punch-list item in the show
python3 tools/placeholder.py list --check   # non-zero if any remain (final cuts)
```

**A placeholder credits nobody.** It carries the vocab's uncast speaker (`TBD`)
and the drawn crest — never a real login, never somebody's avatar. Whoever the
line is destined for is kept in `speaker_pending`: recorded, not rendered.

This is written in scar tissue. Act IV's first pass put lorem on `krook`,
`jeefy` and `mrbobbytables`, and all three were dropped from the film once real
copy arrived, because they had only ever "spoken" words nobody wrote. **Lorem
under a real name is still putting words in a colleague's mouth.**

Do not confuse it with act II's **named placeholder badge**
(`placeholder_dylan_taylor`): a real person, credited by name, with every
unauthored row omitted. Its copy is not missing but deliberately partial, so
`list` reports it and `fill` never touches it. `needs_prose` is the narrow
question, `is_placeholder` the union.

# Intake: from a dictated note to a filed issue

## Why this skill exists

On the night of 2026-08-12→13 the owner dictated four notes. The two an agent
happened to read landed in the repo; the two it did not — a full Kat/Nat
dialogue round and act III's plate round — were silently lost for a day and
found only by a forensic audit. The pipeline was never broken; the handoff
was. **A note in Whisp has no queue, no state, and no acknowledgement.**

## The one rule

**A dictated note is not submitted until it is a GitHub issue.** Whisp is a
microphone, not a backlog — the backlog is issues
([`issues/SKILL.md`](issues/SKILL.md)). The issue number *is* the
acknowledgement; a note without one has not been received, however many agents
have read it.

## Where the notes live

`~/.var/app/io.github.tanaybhomia.Whisp/data/whisp/notes/*.md` — one file per
dictation, mtime is the last edit. Many notes are out of this repo's scope
(other projects); an in-scope note names acts, characters, timecodes, plates,
or dialogue.

## Core Process

At the **start** of a session that touches owner requests, and at the **end**
of every session:

1. `python3 tools/inbox.py --check` — every note it lists has no receipt.
   `--write` adds newly-dictated notes to the ledger; `--set <id> <status>`
   records one (`filed #N`, `landed`, `superseded`, `ignored`,
   `out-of-scope`). To see what is new without the ledger,
   `ls -t .../notes/*.md | head`.
2. For each in-scope note, find its issue: search distinctive strings with
   `gh search issues --repo castrojo/destiny-vids "<phrase>"`.
3. A note with no issue gets one, now — prose quoted verbatim (the owner's
   words are the owner's), plus a proposed `brief` block per
   [`issues/SKILL.md`](issues/SKILL.md). File it even when you also intend to
   do the work; the issue is the receipt, not the task.
4. A note that is clearly superseded or out of scope is noted as such **in the
   issue or session log**, not just in your head.

## Every timecode names its clock

The owner reviews from whichever file he watched, so his marks come off that
file's clock — megacut time, act film time, or source time. Two are already
paid for (#109: act II film vs megacut; the act III round's ambiguous 5:43).
When filing:

- Ask the note which clock it is on; **settle it by frame, not by argument** —
  `python3 tools/megacut.py stories/megacut/megacut.json --locate <mm:ss>` and
  look at the extracted frame.
- Record the clock in the brief beside every mark.

## Worktrees are per-issue and die on merge

A note that says "do this in a new worktree" creates one; nothing says to
remove it, so stale trees accumulate (`destiny-vids-archon` sat 64 commits
behind main). The lifecycle:

- Create against the issue, name it for the issue.
- `git worktree remove` it when the PR merges — same breath as the merge.
- `git worktree list` showing anything >7 days stale is a punch-list item.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I read the note, so it's received." | Reading leaves no record. The next agent cannot tell a read note from an ignored one. The issue number is the receipt. |
| "I'll do the work directly, filing is overhead." | Tonight's loss was exactly this: the newest note got done, the two before it got nothing. File first; the issue costs a minute. |
| "The note is old, it must have landed already." | Grep the repo for its distinctive strings. A 4,000-word dialogue bank sat unfiled for a month. |
| "The timecode is obviously megacut time." | #109 cost a session's investigation. Prove the clock with a frame. |
| "I'll clean the worktree up later." | Later is never; that is why the stale tree existed. Remove on merge. |

## Red Flags

- A Whisp note with dialogue, plate copy, or timecodes and no matching issue.
- Several notes dictated in one sitting — check **all** of them, not the newest.
- A timecode filed without its clock named.
- A worktree whose branch is fully merged.
- Ending a session without step 1–4 of the core process.

## Verification

```bash
python3 tools/inbox.py --check   # every dictated note has a status
# any in-scope note strings missing from repo and issues?
grep -o '<distinctive phrase>' -r . --include='*.md' --include='*.json'
gh search issues --repo castrojo/destiny-vids "<distinctive phrase>"
git worktree list   # nothing stale
```

`--check` is a session ritual, not a CI gate: it fails whenever the owner
dictates something new, which is exactly what it is for, and exactly why it
must not gate unrelated PRs.

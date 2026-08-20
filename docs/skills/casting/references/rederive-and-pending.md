# Rederiving, plate-only people, and the pending queue

Part of the [casting skill](../SKILL.md).

### Re-casting the index after a vocab edit

`casting` is a pure function of the tagger's `character` list plus this vocab,
so a vocab edit re-casts the whole index **without re-tagging** — but the
checked-in segments still carry the previous value until something recomputes
them. `tools/annotate.py index` writes them too, but it needs the source video
and `media/` is gitignored, so it cannot be the remedy for a vocab rename.

`tools/rederive.py` is that remedy. It recomputes every derived field from the
fields the record already carries — no video, no keyframes, no model:

```bash
python3 tools/rederive.py --check    # report drift, change nothing, exit 1
python3 tools/rederive.py            # rewrite the drifted segments
```

It reports each change, so a vocab edit's blast radius is visible before it is
committed:

```text
seg_yt_..._0027-0029.json
    casting.person: 'karena_angel' -> 'karena_angell'
```

This is not a licence to edit a derived field by hand. It is the opposite: the
one supported way to make the files agree with the vocab again, which is why it
refuses to touch a tagger field and preserves each file's existing JSON layout
so the diff shows the change and nothing else.

### Plate-only people

A person can carry owner-written nameplate copy and still have no binding here,
and that is a **terminal state, not a gap**. A `leads` binding is for someone who
*recurs*: it fixes their credit across every cut for the life of the project. A
one-video credit belongs in the copy the owner wrote for that video, and adding a
binding for it would claim a permanence nobody asked for.

Nothing in this repo can tell the two apart, so nothing in this repo tries —
`automatable: no`, blocked on an owner decision. The open ones (see
castrojo/destiny-vids#1 for the copy itself; do not transcribe it, it has one
home):

| Person | State | Blocked on |
|---|---|---|
| Paris Pittman | Cast, as `iron_lord_red_haired` — but the binding has no `plate:`, and the copy the owner wrote is a Guardian plate for Paris, not copy for an Iron Lord. | Authoring plate copy for the character, or deciding she stays plate-only. |
| Jeffrey Sica | Not cast, not in the index. Plate-only. | Whether he is recurring cast (add a binding) or a one-video credit (nothing to do). |

Neither blocks anything. A cast-but-unplated lead like Paris still makes the cut:
`tools/plate.py plan` writes the manifest and lists her under `unresolved` with
the reason, so the credit is never dropped in silence — see
[`plates.md`](../../plates/SKILL.md). Someone with no binding at all is not in the index's
casting, and the brief that carries their copy is their punch-list.

### When the character is not known yet

A request often arrives the other way round: here is a person, and here is a
figure on screen — "the woman", "the main character". Turning that into a
Destiny character is a **visual judgment** on the footage, and it is not
available at all when the source video is not indexed. Park it in
`leads.pending` rather than guessing:

```yaml
  pending:
    <github-handle>:
      github: <github-handle>
      described_as: Woman        # the requester's words, never a character name
      automatable: no
      blocked_on: >
        The source video is not ingested, so no indexed shot shows this figure.
```

Derivation never reads `pending` (`load_leads` reads only `leads.values`), so a
pending entry casts nobody, plates nothing and needs no search phrase — it is a
queue, not a binding. It surfaces in exactly two places, per the contract's
"record the gap where the next person will trip over it": the vocab file itself,
beside the bindings, and the requester's GitHub issue, which stays open as the
punch-list (the live example is castrojo/destiny-vids#14, three logins and an
un-ingested video). `tests/test_casting_pending.py` pins the queue so it cannot
be silently dropped. Promoting an entry is an ordinary binding: move it under
its character key in `values`, add the search phrases, and run the checklist
above.

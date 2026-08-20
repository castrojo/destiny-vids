# Labels, races, and finding the unfinished

Part of the [issues skill](../SKILL.md).

## Labels

Four say what **state** the work is in, and they are deliberately few:

| Label | Meaning |
|---|---|
| `triage` | Filed. Nobody has looked at it. |
| `agent-ready` | Enough detail that an agent can start. |
| `blocked` | Waiting on an owner decision. |
| `automatable/no` | Needs human judgement, permanently. |

Three more axes say how the backlog is **read**, and exist so ordering lives on
the issue rather than in a planning file that goes stale:

| Axis | Values | What it answers |
|---|---|---|
| `area/*` | `indexing`, `cut`, `casting`, `plates`, `rights`, `tooling` | Which stage of the pipeline — so an agent picks up work it is equipped for. Mirrors the skills in this directory. |
| `size/*` | `S` (<2h), `M` (2–8h), `L` (8–24h), `XL` (>24h) | Agent-hours, so nobody re-estimates a backlog they are only scanning. An `XL` wants splitting before it is started. |
| `priority/*` | `now`, `next`, `later` | The running order. |

An area or a size is a routing hint, so getting one wrong costs a re-read.
That is the bar a new axis has to clear before it is added — a label that
made a claim about a person or a frame would not clear it.

`python3 scripts/sync_labels.py --check` reports drift; `--write` fixes it.

`agent-ready` is how the owner says a brief is confirmed — the block itself
cannot say so, because an issue body is editable. Don't put it on your own
proposal.

**Characters are not labels.** They live in the brief block, keyed by the lead
ids in `vocab/casting.yaml`, because that is the same vocabulary the segment
index tags — one spelling of a name across the whole repo. Find them with
`gh issue list --search 'saint_14'`. Adding a `character/*` label set would
mean a second vocabulary that drifts from the first.

## Two agents, one issue

Branch-per-issue keeps two agents off the same files, but nothing stops two
agents picking up the same issue. **Assign yourself before you start**, and
check before you do:

```bash
gh issue view <n> --json assignees
gh issue edit <n> --add-assignee @me
```

`tools/gaps.py --file` races the same way when two runs overlap; it is
self-healing, because the second run finds the first run's fingerprint and
updates rather than duplicating.


## Finding the unfinished

```bash
python3 tools/gaps.py                    # unindexed, unreviewed, uncast
python3 tools/gaps.py --file --dry-run   # what filing would do
python3 tools/gaps.py --file             # open/update the issues
```

Each filed issue carries a fingerprint, so a rerun edits its own issue instead
of filing a second one, and a gap a person already described in their own words
is skipped rather than buried under a robot copy.

`gaps.py` never closes an issue. Opening one and closing one are very different
amounts of trust.

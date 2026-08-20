# Delivering a programme

Reference for [`../SKILL.md`](../SKILL.md). This is the delivery step after the
programme has been assembled and verified.

A programme is delivered like any other cut — see
[`production`](../../production/SKILL.md) — with one extra question that only
compilations raise.

```bash
cd ~/Videos && ./audio-check.sh <master>     # the workspace's own gate, first
ln -f <master> ~/Videos/Wolves/Prod/<NN>-<act>.mp4
cd ~/Videos/Wolves/Prod
ffmpeg -v error -xerror -i <NN>-<act>.mp4 -f null -   # verify the delivered file
md5sum *.mp4 > CHECKSUMS.md5 && md5sum -c CHECKSUMS.md5
```

`ln -f`, **never `cp`** — `Prod/` is hardlinks to each project's master, so it
costs no disk and cannot drift. A `cp` over an existing entry breaks the link
silently and leaves a copy that goes stale. `NN` is the **act number** from
[`docs/running-order.md`](../../../running-order.md), not a sort key.

Then update `Wolves/Prod/README.md`: the act, and the master it links to. A
delivered file with no row is a file nobody can trace.

**Ask what the programme duplicates.** Its segments are usually already
delivered as standalone acts, so publishing both shows the same footage twice.
That is an ordering decision and it belongs to the owner, so **deliver the file
but leave it out of `yt-refresh.py`'s `VIDEOS` list** until they choose.

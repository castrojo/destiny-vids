# Testing and CI

The suite is the gate. Everything about keeping it honest, and about the one
failure shape that costs the most here: a check that is **green on the
workstation and red on the runner**.

## When to use

- A test you changed passes locally and fails in CI, or you cannot tell why CI
  is red
- You are adding a check, or tempted to add a CI step beside the suite
- You touched anything that resolves a binary, a font, a path outside the repo,
  or a delivered file

## What CI actually is

One workflow, one blocking job, one step that matters: `python3 -m pytest -q`.
A clean run is about **50 seconds**.

The four `--check` commands in [`AGENTS.md`](../../AGENTS.md) are **local
pre-commit commands, not CI steps**. Each is already asserted inside the suite
— `tests/test_corpus.py`, `tests/test_rederive.py`, `tests/test_schema_enums.py`
— and pytest runs first in the same job, so a duplicate step beside it could
only ever execute in the case where it would pass.

> **A check that is unreachable when it fails is not a check.** Before adding a
> step, name the failure it catches that the suite does not, and the evidence
> it happens.

## What the runner does not have

| Absent | Consequence |
|---|---|
| ffmpeg and ffprobe | Anything that encodes or probes must **skip or be faked**, never fail |
| Any footage; `media/`, `renders/`, `keyframes/` | A test may not assert a rendered file's content or existence |
| `~/Videos` | Nothing may assert the delivered programme's state |
| The owner's home directory | No absolute path resolves |

Delivery freshness therefore **reports**, and does not gate: it compares the
owner's rendered masters against committed inputs, which is a question a runner
holding no footage cannot usefully ask. That is the contract's "a gate may
inform, it may never withhold the film" applied to CI itself. It reports from
[`tools/deliver.py`](../../tools/deliver.py) `status`, and assembly prints
`NOTE: act ... is stale and seated` and carries on.

## Reproduce the runner before you push

The whole class of "green here, red there" is catchable in fifty seconds. Build
a `PATH` that has everything except the media binaries, and run the suite in it:

```bash
mkdir -p /tmp/ci-sim/bin && cd /usr/bin
for b in *; do
  case "$b" in ffmpeg|ffprobe|ffplay) continue;; esac
  ln -sf "/usr/bin/$b" "/tmp/ci-sim/bin/$b"
done
cd -
env -u DESTINY_FFMPEG -u DESTINY_FFPROBE PATH=/tmp/ci-sim/bin python3 -m pytest -q
```

Unsetting the two environment variables matters as much as the `PATH`: a
resolver that reads `DESTINY_FFPROBE` will happily return a path the runner
does not have.

## The four ways a check goes green here and red there

**1. It resolves a real binary.** Faking the thing that *uses* a binary is not
enough if something resolves the binary first. `tests/test_farm.py` fakes
`farm.probe` but the verify step calls `farm.find_ffprobe` before it, so the
fake never gets reached on a machine without one. Fake both.

**2. It names an absolute path.** A repo file written as
`/var/home/jorge/src/destiny-vids/renders/...` resolves on one machine.
[`tools/plate.py`](../../tools/plate.py) `_load_avatar` documents and
implements the rule: a path inside the repo is **relative**, and resolves
against the repo root; a path outside it is **`~`-rooted**. Both travel.

**3. A portability test anchored on the current checkout root.** This one
inverts, so it is worth stating on its own:

```python
# WRONG: REPO is wherever this checkout happens to be.
assert not avatar.startswith(f"{REPO}/")
```

A committed `/var/home/jorge/...` string does not start with the *runner's*
checkout path, so the assertion passes in CI and fails only on the machine
where the path happens to work. Assert the property, not the location:

```python
assert not PurePosixPath(avatar).is_absolute()
```

**4. It asserts the state of the owner's delivery workspace.** See the table
above. Report it instead.

## A passing test that prints tells nobody

pytest hides output from passing tests by design — "output from passing tests
is hidden", so a report moved out of an assertion into a `print` is captured
and discarded, and the "may inform" half of the rule is lost with the gate.
Use `warnings.warn`, which pytest collects and shows in the warnings summary
with no setup, and which survives `-q`:

```python
if stale:
    warnings.warn(f"DELIVERY REPORT: act(s) {', '.join(stale)} ...")
```

`pytest -rpP` will show captured output from passing tests when you actually
want it. (Verified against Context7 `/pytest-dev/pytest`.)

## Nothing in CI may hang

A step with no ceiling can hold the concurrency group indefinitely, and
everything pushed behind it queues. One run sat for **5h44m**, and a docs
change for six hours, both inside `apt-get update` waiting on a mirror.

- The job carries `timeout-minutes`.
- **Look before you install.** The runner already ships DejaVu Sans Mono, so
  the font step tests for the file and only calls `apt` if it is genuinely
  missing. A package step that always runs is a network dependency on every
  build.

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "It passes locally, CI must be flaky." | Three of this repo's four failure shapes pass locally by construction. Run the sandbox above before saying flaky. |
| "I'll add a CI step so this can't regress." | If the suite can assert it, the suite should. A step beside pytest runs after it and only when it would pass. |
| "The check is important, so it should block." | Importance is not the test. A runner with no footage cannot judge a delivered film; it can only judge the records. |
| "`--force` lets people through when it's wrong." | A flag to get past your own gate means the gate was wrong. `--allow-stale` sat in the CLI promising a backstop that was never implemented. |

## Red flags

- A test comparing a path against the current checkout root
- A committed record naming an absolute path inside the repo
- A CI step that duplicates something the suite already asserts
- A `print` used to report from a test that passes
- A step that installs a package unconditionally, or a job with no timeout
- A new `--force`/`--allow-*` flag added to get past a check
- A worktree under `/tmp` or `/var/tmp`, or one on a detached HEAD
- A render started from a branch that has never been pushed

## Verification

```bash
python3 -m pytest -q                              # the gate
python3 tools/corpus.py --check                   # the four local checks
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
python3 tools/deliver.py status --check           # reports; never gates

# and the runner, before pushing:
env -u DESTINY_FFMPEG -u DESTINY_FFPROBE PATH=/tmp/ci-sim/bin python3 -m pytest -q

# nothing authored is stranded in a worktree that is on no branch:
for w in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
  h=$(git -C "$w" rev-parse HEAD)
  [ "$(git branch -r --contains "$h" 2>/dev/null | wc -l)" -eq 0 ] &&
    echo "UNPUSHED: $w ($h)"
done
```

- [ ] The suite passes in the ffmpeg-free sandbox, not only on this machine
- [ ] No new absolute path, in a record or a test
- [ ] Any new report reaches the log — `warnings.warn`, not `print`
- [ ] No new blocking step that the suite could have asserted
- [ ] No worktree is holding commits that exist on no branch

## See also

- [`rendering`](../rendering.md) — how a test that touches ffmpeg skips
- [`farm`](farm.md) — the cluster, and what a farmed encode fakes in tests
- [`AGENTS.md`](../../AGENTS.md) — the merge queue and the gate's shape

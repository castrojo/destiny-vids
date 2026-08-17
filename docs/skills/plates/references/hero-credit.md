# The hero credit

Act VIII's cast placard, rendered by `render_cast_placard` in
`tools/credits.py` from the `cast` array in
[`stories/08-credits.json`](../../../../stories/08-credits.json). It is not a
Guardian nameplate — it credits the **person**, not the character — so the
closed field set in [`SKILL.md`](../SKILL.md) does not apply to it. Its own
field set is below, and is just as closed.

## Three rows, and every one of them is quoted

```
NAME
as <Guardian title>
<what this person does, in their own words>
```

| Row | Where the words come from |
|---|---|
| name | `person` — the real name, as the acts credit it |
| `as` | `guardian_title`, the **authored** seal, verbatim from `guardian_title_source`; the placard resolves it from `card` when the website authored one. **Omitted entirely when nobody authored one** — the generic blueberry fallback is as wrong here as an invention. |
| body | `title`, verbatim from `title_source` — the person's own GitHub bio, or copy the owner supplied. `<br>` is a hard break; `<br><br>` is a paragraph. |

**The Destiny character name is never drawn.** Owner: *"drop the Destiny
names, do it like 'Kat Cosgrove as Defender Queen... blah'."* `character_id`
stays on the record because redactions key off it.

**A missing `title` is `title_pending`, not a gap.** It renders as deterministic
lorem (`cast_title` in `scripts/build_credits.py`) so the row exists to be
watched, and the record says who is owed one. That is the one place lorem sits
under a real name in this repo, and it is only survivable because the row is
*about* them rather than *spoken by* them — see the scar in
[`../SKILL.md`](../SKILL.md).

**A face is never guessed.** `login` requires `login_source` recording how the
account was checked — the account's own name, company or bio matching the
credit, or a binding in `vocab/casting.yaml` keyed by the login itself. A
principal with no recorded login renders the empty ring and their initial.
Avatars come from the cache: [`../../production/references/avatars.md`](../../production/references/avatars.md).

## Who gets one

Principals only, and only people who are **on screen in a delivered act**.
Each entry carries `seen_in` naming that act and the record that puts them
there; `tests/test_credits.py` pins it. Everyone else is in the contributor
wall.

The array is ordered by the act that introduces them, so the credits replay
the show.

## Why it is a lower third

The deck's backdrop is the **day** wallpapers, and centred type over them
measured 1.02:1 at its worst. Everything else was tried and rejected by the
owner: brightening the art, an opaque surface card, a feathered veil. A chyron
does not fight the picture, it owns a corner of it — ink solid to `LOWER_RAMP`
and ramped to nothing across the frame, an accent hairline on its top edge, the
face left, the type beside it. A test measures band luminance under the type on
every month and requires it below 0.18.

Do not restyle the deck to suit the art. Owner: *"I just want light coloured
wallpapers"* — the palette stays white-on-blue, and `_graded()` has no exposure
step.

## Verification

```bash
python3 -m pytest -q tests/test_credits.py
python3 scripts/build_credits.py --cards --master
python3 tools/deliver.py publish --act VIII
```

Then look at a card. `renders/cards-08-credits/` is where they land.

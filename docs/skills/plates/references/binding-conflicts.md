# When a card must diverge from its binding

Reference for [`../SKILL.md`](../SKILL.md). This is the escape hatch for a card
that must knowingly disagree with the committed binding.

Only with an explicit, greppable record. `render` and `burn` call
`check_copy_against_bindings`, which refuses any card whose `name` matches an
authored identity but whose `label`/`class`/`title` do not — unless it carries:

```json
"copy_override": {
  "reason": "owner brief 2026-08-13 contradicts the committed binding",
  "binding": "cayde_6",
  "decided_by": "https://github.com/castrojo/destiny-vids/issues/111"
}
```

`decided_by` is required, so the escape hatch cannot be taken by accident and
always names who is settling it. An override is a **recorded violation with an
owner on the hook**, not a second way to be right — act VI's tail is the worked
example, and its two cards exist to be resolved, not copied.

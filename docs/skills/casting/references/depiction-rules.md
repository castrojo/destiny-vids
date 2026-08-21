# Depiction rules

Part of the [casting skill](../SKILL.md).

## A binding can carry a depiction rule

Casting says *who* a figure is. A **depiction rule** says how a character may be
shown at all, and it applies whether or not anybody is cast as them.

The Witness is the standing example:

```yaml
the_witness:
  person: null
  aka: [witness]
  depiction:
    rule: eyes_or_smoke_only
    approved: []
```

> Eyes or smoke, never the body.

Three properties make it work, and all three are deliberate:

- **The default is exclusion.** An empty `approved` means *no* shots of that
  character are usable, exactly like an untagged `overlays` deriving
  `clean = false`. Permission is positively established or it does not exist.
- **It is not derived.** `clean`, `footage_tier`, `traversal_hero` and `casting`
  are the four derived fields and this is not a fifth. "Is that a body or a
  wisp?" is a visual judgement about a frame, which
  [`AGENTS.md`](../../../../AGENTS.md) lists among the things that can never be
  automated. A human adds a `segment_id` to `approved` after looking at it.
- **A rule is not an editorial choice.** "Cut Savathûn from this video" belongs
  in the outline for that video. "The Witness is never shown bodily" belongs
  here, because it holds for every cut the project ever makes. Putting the
  first one here would quietly ban a character from the whole index; putting the
  second in an outline loses it the moment somebody writes a new one.

The mechanism is generic — any binding may carry `depiction` — while the rules
themselves are specific and few. Add one only when the owner states it as a rule
about the character, not as a note about one cut.

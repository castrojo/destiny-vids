# Season of the Blueberries — Expansion Pack authoring

These files are the durable owner-authored copy for the next pass.
`tools/hive_authoring.py` parses them into the episode plan: `chat-*` cues
render as plate.py chat pills, `top-third`/`bottom-right` cues render as
verbatim lore cards, and every other placement is recorded in the episode's
`unresolved` sidecar rather than rendered with an invented treatment.
Lines sharing one timecode are ordered by the Direction markers
(`sequence line N`, `follows the X cue`, `sequence after X`, `Final ...
line`); lines without a marker keep their written order. Remaining
placement support is tracked in the GitHub backlog.

- [Open decisions](00-open-decisions.md)

## Episodes

- [The Enclave](01-the-enclave.md)
- [On Mars](02-on-mars.md)
- [Savathun](03-savathun.md)
- [The Relic](04-the-relic.md)
- [To Be Chosen](05-to-be-chosen.md)
- [Council](07-council.md)
- [Worm](08-worm.md)
- [Defeated](09-defeated.md)
- [The Witness](10-the-witness.md)
- [With Mara](11-with-mara.md)

- [Final CTA](final-cta.md)

---
act: II
manifest: stories/02-endless-forms-plates.json
# WHERE THIS ACT STARTS IN THE PROGRAMME, in seconds. A measurement of the
# running order, not something to recompute from memory: prologue 101.200
# (megacut.json item 0 `dur`) + act I 116.200 (trim 2.000 -> 118.200) +
# Perfume movement 2, 66.400 (source 93.000 -> 159.400) = 283.800 --
# verified against the seven-days-to-the-wolves-v4.2 dry run on 2026-08-20.
# Restate the derivation when the running order's timings move.
programme_start: 283.800
# The act's own length comes from the manifest's `_film_sec`; it is not
# restated here, because a second copy is a future contradiction.
---

# Act II — Endless Forms Most Beautiful: conversations

This file is where you write and rewrite this chapter's chat dialogue. The
build (`scripts/build_efmb_plates.py`) reads it; you never touch a timecode
per line unless you want to.

Drop a whole conversation at one programme time (the clock the full show
plays on — the same clock you scrub in the delivered film):

    ## 6:45
    Karena: Hit 'em with your lessons learned
    Rochaporto: One reference architecture coming up!
    jrsapi: Shit are you taking notes?

(That example is indented, so it is documentation, not dialogue. Yours start
at the left margin.)

The rules:

- **One `## <time>` heading per conversation.** Every line under it plays in
  order. You do not time the lines: each stays up for as long as it takes to
  read (15 characters a second, never less than 2.2 s, never more than 7 s,
  a 0.25 s beat between pills).
- **One speaker, many lines.** Put the same name on consecutive lines and
  each becomes its own pill — no more one huge line or nothing.
- **Pin a line** when it must land exactly: `jrsapi @ 6:52: Shit…` puts that
  pill at 6:52 and the lines after it flow from there. Slack between the
  previous line and the pin is just silence; a pin that lands before the
  previous line finishes is still honoured, and the overlap is reported,
  never silent.
- **Times are programme time** — 6:45 means 6:45 into the whole show. The
  tool converts to this act's own clock (act II starts at 4:43.8).
- **A red splash** — the boss bar — is a `!` line: `! POOR TECHNICAL
  DECISIONS`. Add a second row with `| the title`; a bare trailing `|` keeps
  the title as a placeholder slot (lorem, credited to nobody) until somebody
  writes it. `[an_id]` after the `!` keeps an existing card's id when this
  file takes over a seat the build script used to hold — both red splashes
  in this act are authored below, that way.
- **A lowercase login** (`rochaporto:`) also earns its GitHub avatar, like
  the other pills in this act. A display name (`Karena:`) prints verbatim.
- **Lines that match the footage seat themselves.** If your words match what
  the characters on screen are visibly saying (the act's recovered dialogue
  is the evidence), the line is placed at that moment instead of its cascade
  spot. A `@` pin still wins; either way the seat is reported — in `show`,
  on stderr at build time, and in the manifest's `unresolved`.
- **A line with no words** renders as a placeholder credited to nobody —
  write `TBD: ` and the slot exists in the cut, waiting for copy.
- Anything the scheduler cannot honour exactly is recorded in the manifest's
  `unresolved` and printed by the check below. The build never stops.

Preview what this file resolves to:

    python3 tools/chapter_md.py show II

Then rebuild the manifest (never hand-edit the JSON):

    python3 scripts/build_efmb_plates.py --write

## 6:45
! [late_poor_technical_decisions] POOR TECHNICAL DECISIONS |

    The red flash. Owner, 2026-08-20: it goes to 6:45 on the programme
    clock. The trailing `|` keeps the second-row slot: it renders as lorem
    credited to nobody until somebody writes the words.

## 10:00
! [mapped_haters] HATERS |

    Owner, 2026-08-19: "Haters goes at 10:00 on the red face with the bright
    red dot", and the red overlays "should match the style of the original
    kernel one" — this is that boss bar. Evidence: the red-lit face shot,
    measured 315.267 → 316.967 film by scene detection. (An earlier record
    pointed at the hallway frame, source 323.933; per code review that is
    not the shot the bar sits on, so this card carries no `seen_at_src`
    rather than a wrong one.) The bar is a chrome row at the top of frame,
    so it shares the screen with Kyle's lower-third pill by design.


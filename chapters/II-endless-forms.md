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
# THE COLUMN ORDER THIS ACT'S MANIFEST READS IN.
#
# Act II's plates were built by about ten different code paths, so they came
# out in thirteen different key orders -- an accident of which branch made
# which pill, never a decision. One order for the whole act is the point of
# moving them here. It starts with the boss bar's shape, which is what the
# two red splashes already carried, so no card changes but the pills that
# had no order to keep.
field_order: id, at, dur, name, title, title_source, kind, position,
  copy_source, speaker, text, text_source, scale, seen_at_src,
  avatar, avatar_url, bond_of
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

## 5:54.233

[chat_joseph_slop] Joseph @ 5:54.233 +2.6: Here comes the slop
  - cast: joseph_sandoval
  - position: null

    Owner brief, this round: "03:12 chat bubble for Joseph: Here comes the
    slop / 03:19 karena: I love this job". Megacut marks; these are the
    programme seats they land on. He also asked for Joseph's "Master your
    skills" and "You got this" one second apart at 3:39 and 3:40 — a pill
    needs 2.2 s to be read, so they could never both play. The later
    5:59 → 6:14 pass replaced them on the same face shots and neither ever
    reached a frame; the strings are in git.

## 6:01.233

[chat_karena_job] Karena @ 6:01.233 +2.6: I love this job
  - position: null

## 6:12.683

[late_mfahlandt_clean] mfahlandt @ 6:12.683 +2.2: K1 Logistics is clean

[late_kfaseela_gamers] kfaseela @ 6:15.383 +2.2: The gamers were here alright

[late_markmandel_online] markmandel @ 6:18.083 +2.2: Agones Cluster - ONLINE

[late_riaankleinhans_close] riaankleinhans @ 6:20.783 +2.2: You're getting close

[late_jrsapi_learn] jrsapi @ 6:23.300 +2.2: They learn quickly
  - seen_at_src: 117.266

[late_rochaporto_move] rochaporto @ 6:25.750 +2.2: We need to move!
  - seen_at_src: 119.716

[late_metrics_cluster] jrsapi @ 6:28.300 +2.75: Projects Teams Metrics are strong They just need mentoring in the right skills
  - seen_at_src: 122.266

[late_karena_cardio] karena @ 6:31.300 +2.2: Like cardio!
  - seen_at_src: 125.266
  - avatar: null
  - avatar_url: null

## 6:45
! [late_poor_technical_decisions] POOR TECHNICAL DECISIONS |

    The red flash. Owner, 2026-08-20: it goes to 6:45 on the programme
    clock. The trailing `|` keeps the second-row slot: it renders as lorem
    credited to nobody until somebody writes the words.

## 6:47.300

[late_karena_lessons] karena @ 6:47.300 +2.2: Hit 'em with your lessons learned
  - seen_at_src: 141.266
  - avatar: null
  - avatar_url: null

[late_rochaporto_cern] rochaporto @ 6:49.750 +2.6: One reference architecture coming up!
  - seen_at_src: 143.716

## 6:58.300

[late_jrsapi_notes] jrsapi @ 6:58.300 +2.6: Shit are you taking notes?
  - seen_at_src: 152.266

[toc_karena] Karena @ 7:01.333 +3.2: One hundred thousand bootc volunteers, ready to power up

[toc_joseph_worth] Joseph @ 7:04.783 +2.2: Is it worth it?
  - cast: joseph_sandoval

[toc_ricardo] Ricardo @ 7:07.233 +2.4: You really think they can save open source?
  - cast: rochaporto

    THE EXCHANGE BELONGS TO THE WALK, and its seats were chained backward
    from the walk's first frame so Ricardo's question clears exactly as the
    walking shot opens. They are pinned here at the moments that produced,
    because the scene they belong to is the walk.

    It used to start at MONTAGE_OUT and give the last line whatever was
    left. That worked only while the walk was mis-anchored a shot late;
    correcting it to the walking shot's real first frame left 7.033 s for
    three cards needing 7.100, and Ricardo's question would have been
    squeezed under the readable minimum. Chaining backward keeps every
    authored hold and moves the whole exchange 1.07 s earlier instead, into
    clear air — Dylan Taylor's badge is out at film 134.767, and the run
    starts after it.

    The speakers are the brief's own tags ([KARENA] / [JOSEPH] /
    [RICARDO]), not a casting lookup. `cast:` rides along only to find the
    portrait; Karena has no recorded avatar, so she gets the drawn crest by
    omission rather than by accident. The 2:19 lead-in banner that was to
    open the scene has no copy yet (#98), so the first line takes its slot.

    Their three answers — "Dunno, how much faith DO we have in the CNCF?",
    "Cloud native desktop? ...", "LOL" — went out with AN4-CH3CK-12's pass
    and are not authored here; the mapped pass renders that beat.

## 7:23.300

[mapped_kernel_bump] [redacted] @ 7:23.300 +2.2: Time to bump the kernel
  - seen_at_src: 183.366

## 7:29.300

[mapped_pastaq_tests] pastaq @ 7:29.300 +2.2: All your tests passed right?
  - seen_at_src: 189.366

[mapped_lionheartp_what_tests] LionHeartP @ 7:33.300 +2.2: What tests?
  - seen_at_src: 193.366
  - avatar_login: LionHeartP

## 7:39.300

[mapped_a1rmax_intro] A1RM4X @ 7:39.300 +2.5: Thank you I never thought I could help! I'm not like you I'm just a lowly user
  - seen_at_src: 199.366
  - avatar_login: A1RM4X

[walk_ge_stream] GloriousEggroll @ 7:42.300 +2.2: It's your patch, turn the stream on
  - seen_at_src: 202.366
  - cast: GloriousEggroll

[walk_a1rm4x] LionHeartP @ 7:45.000 +2.2: Let's get these numbers up
  - seen_at_src: 205.066
  - avatar_login: LionHeartP

[mapped_lionheartp_hardware] LionHeartP @ 7:47.450 +2.7: Why spend the extra dollar to support Linux hardware
  - seen_at_src: 207.516
  - avatar_login: LionHeartP

[walk_ge_glorious] GloriousEggroll @ 7:51.300 +2.8: There's nothing glorious about this job
  - seen_at_src: 211.366
  - cast: GloriousEggroll

## 7:59.300

[mapped_lionheartp_together] LionHeartP @ 7:59.300 +3.8: When we work together This gets easier
  - seen_at_src: 219.366
  - avatar_login: LionHeartP

## 8:09.300

[mapped_eggroll_title] GloriousEggroll @ 8:09.300 +4.5: Nice work testing that patch Usually Blueberries just Send me a bunch of crap
  - seen_at_src: 229.366
  - cast: GloriousEggroll

[mapped_eggroll_didyou] GloriousEggroll @ 8:16.300 +2.2: You didn't test any of this did you.
  - seen_at_src: 236.366
  - cast: GloriousEggroll

[mapped_pastaq_what_tests] pastaq @ 8:20.300 +2.2: Hey man WHAT tests?
  - seen_at_src: 240.366

## 8:22.566

[walk_ge_lesson] LionHeartP @ 8:22.566 +2.2: Let's go!
  - position: right
  - seen_at_src: 242.632
  - avatar_login: LionHeartP

[mapped_redacted_unlearning] [redacted] @ 8:25.300 +2.75: Unlearning bad habits takes time
  - seen_at_src: 290.0

[mapped_redacted_options] [redacted] @ 8:28.300 +6.75: Your options are success Or a lifetime of servitude in the Toilmaster's Packaging Mines
  - seen_at_src: 293.0

[owner_convo_karena] karena @ 8:35.300 +2.867: The Kube always seeks open source potential
  - seen_at_src: 300.0

[owner_convo_joseph] joseph @ 8:38.417 +3.6: We can't let The Toilmaster enslave another generation
  - seen_at_src: 303.117
  - avatar: null
  - avatar_url: null

[mapped_kyle_titanfall] KyleGospo @ 8:43.750 +2.2: FOR TITANFALL!
  - seen_at_src: 308.45
  - avatar_login: KyleGospo

[mapped_redacted_blow] [redacted] @ 8:46.200 +2.6: Or go blow some shit up
  - seen_at_src: 310.9

## 8:59.733

[mapped_akgraner_kyle] akgraner @ 8:59.733 +2.2: Hi sugar, I'm looking for Kyle

[mapped_hikari_ouch] HikariKnight @ 9:02.183 +2.2: Ouch man wtf!
  - avatar_login: HikariKnight

[mapped_owen_sorry] Owen @ 9:04.633 +2.2: Oh sorry my bad

[mapped_kolunmi_pvp] kolunmi @ 9:07.083 +2.2: Who turned PvP on?

[mapped_karena_pve] karena @ 9:09.533 +3.0: Don't look at me I only put PvE on Legendary

[mapped_cam_noone] cam @ 9:12.783 +2.2: Mom no one plays this game
  - avatar: null
  - avatar_url: null

[mapped_hikari_wait] HikariKnight @ 9:15.233 +2.2: Hey wait?!
  - avatar_login: HikariKnight

[mapped_kolunmi_users] kolunmi @ 9:17.683 +2.6: Are those ... other linux users?

## 9:32.203

[mapped_owen_slay] Owen @ 9:32.203 +2.2: Slay out, Queen!
  - scale: 1.0

[mapped_akgraner_kindness_1] akgraner @ 9:34.653 +2.2: Kindness is doing what's right
  - scale: 1.18

[mapped_akgraner_kindness_2] akgraner @ 9:37.103 +2.2: For the ecosystem.
  - scale: 1.18

[mapped_akgraner_kindness_3] akgraner @ 9:39.553 +2.2: For our users.
  - scale: 1.18

[mapped_akgraner_kindness_4] akgraner @ 9:42.003 +2.2: And for our maintainers.
  - scale: 1.18

[mapped_akgraner_kindness_5] akgraner @ 9:44.453 +2.2: Don't be nice.
  - scale: 1.18

[mapped_akgraner_kindness_6] akgraner @ 9:46.903 +2.2: Be kind.
  - scale: 1.18

[mapped_which_kyle] akgraner @ 9:49.353 +2.6: Which one of you is Kyle?
  - scale: 1.0

## 9:57.000

[mapped_kolunmi_disco] kolunmi @ 9:57.000 +2.2: Disco!
  - seen_at_src: 329.73

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

## 10:00.767

[mapped_kyle_sup] kylegospo @ 10:00.767 +2.2: Sup
  - position: right
  - seen_at_src: 333.497
  - bond_of: mapped_kyle_reveal
  - avatar_login: KyleGospo

    OWNER-PLACED, DO NOT MOVE. Owner, verbatim: "sup is a purple titan",
    "put it when it's zoomed into his face". This is the first frame of that
    close-up, measured by scene detection (the shot runs 316.967 → 317.733
    film). The pill OPENS on his face, which is what he asked for.

    An earlier agent slid it to 316.287 to make a builder assertion pass,
    which put it AFTER kolunmi's "Disco!" and reordered the authored
    exchange. That is the fourth class in AGENTS.md: a gate refusing a seat
    is not permission to move an authored beat. It was reverted, and the
    assertion that provoked it is gone — an overrun is reported now, never
    raised.

    `bond_of` puts it in the deck's bonded-pair shape: his nameplate holds
    the left lane, the pill takes the RIGHT. The owner locked both TIMES
    ("lock the plate"; the pill on the close-up's first frame) — the lane
    was never his instruction, and stacking both on the left drew them on
    top of each other for the pill's last 0.43 s, since the nameplate
    arrives at 318.737. Right lane, same seats: the pair reads as the site's
    GUARDIAN BOND composition.

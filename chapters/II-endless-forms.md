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

>> THE GLIDER LINK IS AN UPLOAD ANNOTATION, NOT A PLATE. Owner, 2026-08-23:
"Add youtube click link thing to this video, it's the backstory to the
glider: https://www.youtube.com/watch?v=P-rIeI6ynuM ... Have it show up
during this combo and stay in the top right until later." A YouTube card is
set on the upload, so nothing here burns it into a frame -- filed as an
issue against the publish step. The window it wants is this block. <<

## 5:14.433

>> THESE FOUR SEATS ARE MINE, NOT THE OWNER'S. He wrote the banter with no
times, above the 5:54 block, and 5:54 onwards is packed with authored beats
that may not move. This is the largest clear stretch in the act -- film
30.433 -> 45.200, measured from the manifest, not from this file, because
the builder adds plates this file never sees. It is the combo the note
above describes. Worth a look when he watches it: the words are his, the
moment is a guess. <<

[chat_joseph_ricardos] Joseph @ 5:14.433 +3.4: No one can tell which Ricardo is which so roll with it
  - cast: joseph_sandoval
  - position: null

[chat_ricardo_nukeguy] Ricardo @ 5:18.233 +3.4: It's me the nuke guy how do you think I got here?

    THE OTHER RICARDO, deliberately uncast. This act has two: Ricardo Rocha
    (`rochaporto`, who carries `toc_ricardo` below) and the one jrsapi
    cannot tell apart. Naming the second would credit a real person on the
    strength of a joke about not knowing which one he is, so he takes the
    display name and the drawn crest, and no portrait.

[chat_pilot_lunar] pilot @ 5:22.033 +2.8: Lunar record baby! Hello KubeCon + CloudNativeCon
  - avatar: null
  - avatar_url: null

[chat_ricardo_ai] Ricardo @ 5:25.233 +3.4: They wanted us to put AI in the glider so we did.

## 5:54.233

[chat_joseph_slop] Joseph @ 5:54.233 +2.6: That explains the slop
  - cast: joseph_sandoval
  - position: null

    Owner brief, this round: "03:12 chat bubble for Joseph: That explains
    the slop". Megacut marks; this is the programme seat it lands on. The
    line was "Here comes the slop" until
    2026-08-23, when he revised the brief above it -- it answers the new
    glider banter now, so the pill follows the brief. He also asked for Joseph's "Master your
    skills" and "You got this" one second apart at 3:39 and 3:40 — a pill
    needs 2.2 s to be read, so they could never both play. The later
    5:59 → 6:14 pass replaced them on the same face shots and neither ever
    reached a frame; the strings are in git.

## 6:12.683

[late_mfahlandt_clean] mfahlandt @ 6:12.683 +2.2: K1 Logistics is clean

[late_kfaseela_gamers] kfaseela @ 6:15.383 +2.2: The gamers were here alright

[late_markmandel_online] markmandel @ 6:18.083 +2.2: Agones Cluster - ONLINE

[late_riaankleinhans_close] riaankleinhans @ 6:20.783 +2.2: You're getting close

[late_jrsapi_learn] jrsapi @ 6:23.300 +2.2: They learn quickly
  - seen_at_src: 117.266

[late_rochaporto_move] rochaporto @ 6:25.750 +2.2: We need to move!
  - seen_at_src: 119.716

[late_metrics_cluster] jrsapi @ 6:28.300 +2.2: Projects Teams Metrics are strong
  - seen_at_src: 122.266

[late_metrics_mentoring] jrsapi @ 6:34.000 +2.8: They just need mentoring in the right skills

## 6:45
! [late_poor_technical_decisions] YOUR POOR TECHNICAL DECISIONS |

    The red flash. Owner, 2026-08-20: it goes to 6:45 on the programme
    clock. The trailing `|` keeps the second-row slot: it renders as lorem
    credited to nobody until somebody writes the words.

[late_rochaporto_cern] rochaporto @ 6:49.750 +2.6: One reference architecture coming up!
  - seen_at_src: 143.716

## 6:58.300

[late_jrsapi_notes] jrsapi @ 6:58.300 +2.6: I still don't know which Ricardo this is
  - seen_at_src: 152.266

>> "Timed to when the hunter shows off with the hoodie pulloff." -- owner,
2026-08-23, about the line above. It is already pinned at 6:58.300; whether
that is the pulloff frame is a judgement about a picture, so it is left
where he put it and flagged for his eye. <<

[toc_joseph_worth] Joseph @ 7:04.783 +2.2: The gamers would have to impress BOTH Ricardos
  - cast: joseph_sandoval

    ONE PILL, NOT TWO. The owner wrote "BOTH Ricardos" on its own line, but
    this exchange is chained backward from the walk's first frame and has
    7.033 s for three cards needing 7.100 -- there is no room for a fourth,
    and no authored beat here may be slid to make one. It is one sentence
    with no punctuation between the halves, so every word he wrote reaches
    the screen; only the line break does not. `tools/readtime.py` will call
    the hold short, which is a report, not a re-time.

[toc_ricardo] Ricardo @ 7:07.233 +2.4: Look man I am so tired just jump
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

>> "It could be either one" HAS NOWHERE TO GO, and it is in the overflow
below. Its own question clears at 7:00.900 and Karena is pinned at 7:01.333;
the next second and a half is a no-plate zone on her jump; and everything
after that until film 220.966 is The Long Walk, which credits only its own
speakers. <<

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

    ONE PILL, as it was. The owner broke the line in two and tagged the
    second half `[a1irmax]`, a typo for this pill's own speaker, so it is
    the same person still talking. 7:39.300 clears at 7:41.800 and
    GloriousEggroll is pinned at 7:42.300; there is no room for a second
    pill and nothing here may be moved to make one.

[walk_ge_stream] GloriousEggroll @ 7:42.300 +2.2: It's your patch, turn the stream on
  - seen_at_src: 202.366
  - cast: GloriousEggroll

[walk_a1rm4x] LionHeartP @ 7:45.000 +2.2: Let's get these numbers up
  - seen_at_src: 205.066
  - avatar_login: LionHeartP

[mapped_wrkode_dibs] wrkode @ 7:47.450 +2.7: Oh dibs on this one
  - seen_at_src: 207.516
  - avatar_login: wrkode

    THIS SEAT WAS LIONHEARTP'S "Why spend the extra dollar to support Linux
    hardware". The owner replaced the line and the speaker on 2026-08-23;
    the deleted string is in git. `avatar_login` came across from the old
    line and is corrected here -- left as it was, wrkode would have worn
    LionHeartP's face.

[walk_ge_glorious] GloriousEggroll @ 7:51.300 +2.8: There's nothing glorious about this job
  - seen_at_src: 211.366
  - cast: GloriousEggroll

## 7:59.300

[mapped_lionheartp_together] LionHeartP @ 7:59.300 +3.8: When we work together
  - seen_at_src: 219.366
  - avatar_login: LionHeartP

[mapped_wrkode_kairos] wrkode @ 8:03.500 +3.0: Have I shown you Kairos my friend?
  - avatar_login: wrkode

## 8:09.300

[mapped_eggroll_title] lionheartp @ 8:09.300 +2.2: Nice work testing that patch
  - seen_at_src: 229.366
  - cast: lionheartp
  - avatar_login: LionHeartP

[mapped_eggroll_blueberries] lionheartp @ 8:12.000 +3.4: Usually Blueberries just send me a bunch of crap
  - cast: lionheartp
  - avatar_login: LionHeartP

    THE OWNER SPLIT ONE 4.5 s PILL INTO TWO and recast it from
    GloriousEggroll to lionheartp. There was room: 8:09.300 + 4.5 cleared at
    8:13.800 and the next beat is 8:16.300, so the two halves fit inside the
    old line's own span plus a beat. The id of the first is kept -- it lost
    its `[id]` in the rewrite, and an auto-derived id is unstable across
    edits, which is how a delivered plate loses its seat.

[mapped_eggroll_didyou] lionheartp @ 8:16.300 +2.2: You didn't test any of this did you.
  - seen_at_src: 236.366
  - cast: lionheartp
  - avatar_login: LionHeartP

[mapped_pastaq_what_tests] pastaq @ 8:20.300 +2.2: Hey man WHAT tests?
  - seen_at_src: 240.366

## 8:22.566

[walk_ge_lesson] LionHeartP @ 8:22.566 +2.2: Let's go!
  - position: right
  - seen_at_src: 242.632
  - avatar_login: LionHeartP

[mapped_redacted_unlearning] [redacted] @ 8:25.300 +2.75: Unlearning bad habits takes time
  - seen_at_src: 290.0

[mapped_redacted_options] [redacted] @ 8:28.300 +2.75: Your options are success
  - seen_at_src: 293.0

[mapped_redacted_mines] [redacted] @ 8:31.500 +3.55: Or a lifetime of servitude in the Toilmaster's Packaging Mines

    THE SPLIT FITS INSIDE THE OLD PILL'S OWN 6.75 s span (8:28.300 ->
    8:35.050).

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

[mapped_cam_noone] cam @ 9:12.783 +2.2: Mom no one plays this game
  - avatar: null
  - avatar_url: null

[mapped_hikari_wait] HikariKnight @ 9:15.233 +2.2: Hey wait?!
  - avatar_login: HikariKnight

[mapped_kolunmi_users] kolunmi @ 9:17.683 +2.6: Are those ... other linux users?

>> ACT II IS FULL, AND THIS IS WHERE IT RAN OUT. The owner wrote eighteen
new lines into the 9:12 -> 9:40 stretch on 2026-08-23. Between kolunmi's
"other linux users?" and Owen's "Slay out, Queen!" there is 6.97 seconds
of clear air once her own nameplate has been up -- two readable pills.
Every other second in this act is an authored beat that may not be slid.
Two are seated below, and three in the stretch after Kyle's reveal -- his
own two there ("Bobonomics", "We had to make this movie") were removed at
his word on 2026-08-24: "Remove kyle's lines after 'Sup', the others
aren't needed". The other eight, and two more from earlier in the act,
are recorded verbatim under "OVERFLOW" further down -- reported,
never dropped -- and filed as one issue so he can say what gives. <<

[chat_amber_dungeon] akgraner @ 9:25.433 +2.2: Oh wow I forgot what the starter dungeon was like! Hi!
  - avatar_login: akgraner

    "AMBER" IS AKGRANER. The owner tagged these lines `[amber]` and others
    in the same scene `[akgraner]`; the act's own `mapped_amber_reveal`
    nameplate names her Amber Graner, so they are one person and she keeps
    her face rather than losing it to a first name.

    THE SEATS ARE BEHIND HER NAMEPLATE. That reveal and the plate beside it
    hold the left lane, which is where a pill sits, until film 281.433, so
    her first words open the moment her name clears -- which is the right
    beat anyway.

[chat_amber_kyleford] akgraner @ 9:27.883 +2.2: Which one of you is Kyleford?
  - avatar_login: akgraner

    "Kyleford" is the owner's spelling and is reproduced. This line takes
    over the question the act used to ask at 9:49.353 -- akgraner's "Which
    one of you is Kyle?", which he rewrote to "Extinction is the Rule".

## 9:32.203

[mapped_owen_slay] Owen @ 9:32.203 +2.2: Slay out, Queen!
  - scale: 1.0

[mapped_akgraner_kindness_1] akgraner @ 9:34.653 +2.2: Kindness is doing what's right
  - scale: 1.18

[mapped_akgraner_kindness_2] akgraner @ 9:37.103 +2.2: For the ecosystem
  - scale: 1.18

[mapped_akgraner_kindness_3] akgraner @ 9:39.553 +2.2: For our users
  - scale: 1.18

[mapped_akgraner_kindness_4] akgraner @ 9:42.003 +2.2: And for our maintainers
  - scale: 1.18

[mapped_akgraner_kindness_5] akgraner @ 9:44.453 +2.2: Don't be nice
  - scale: 1.18

[mapped_akgraner_kindness_6] akgraner @ 9:46.903 +2.2: Be kind
  - scale: 1.18

[mapped_which_kyle] akgraner @ 9:49.353 +2.6: Extinction is the Rule
  - scale: 1.0

## 9:52.203 paused

>> THE PAUSE HOLDS UNTIL THIS WHOLE CONVERSATION HAS PLAYED. Owner,
2026-08-24: "Don't unpause, at 'Oh I see your problem', keep that in the
paused section, put cortney's conversation here." The hallway used to
resume at 9:53.203 with akgraner's pill still up and cortney's line playing
over moving picture; the hold now runs until the last line below clears,
however long that grows to be -- `chapter_md.block_end("II", "paused")`
derives it, so a line added or removed here never has to be re-typed as a
duration anywhere else. kolunmi's "Disco!", deleted from this stretch on
2026-08-23, was restored the next day on the hunter corridor
(## 10:04.187). The ten-plus lines the owner wrote on 2026-08-23 for a
stretch this act had no room for, and later updated on 2026-08-25, used to
sit here verbatim as OVERFLOW prose reaching no frame; the pause section is
their room, so they are seated below, right after cortney's line, in the
order and words he wrote them. <<

[chat_amber_problem] akgraner @ 9:52.203 +2.2: Oh I see your problem
  - avatar_login: akgraner

[chat_cortney_solid] cortney @ 9:54.653 +2.2: And we're gonna do you a solid
  - avatar_login: CortNick

    The owner wrote the speaker as `https://github.com/CortNick [cortney]`.
    The login resolves the portrait; the name row prints what he typed.

[chat_amber_sent] akgraner: [Redacted] sent me

[chat_amber_bazaar] akgraner: "How bazaar?"

[chat_amber_crap] akgraner: Who writes this crap?

[chat_kolunmi_sweaty] kolunmi: I'm sorry I signed up for teamwork, why are people so sweaty?

[chat_kyle_halo] KyleGospo: castrojo killed me in Halo today
  - avatar_login: KyleGospo

[chat_noelmiller_seen] noelmiller: I feel seen

[chat_amber_harder] akgraner: Ok well, it gets harder from here on out

[chat_cortney_trash] cortney: Take out this trash all their contributions are
  - avatar_login: CortNick

[chat_cortney_goose] cortney: Goose eggs? Nothing?
  - avatar_login: CortNick

[chat_amber_notthere] akgraner: Those people will not be there when it matters the most

[chat_amber_trustme] akgraner: Trust me

[chat_amber_scars] akgraner: I have the scars to prove it

[chat_kolunmi_cook] kolunmi: I like how you cook sister, I'll try

[chat_amber_phpforums] akgraner: Why do you take technical advice from people who post in PHP forums?

[chat_amber_dothereisnotry] akgraner: "Do. There is no try"

[chat_amber_shittywriting] akgraner: I can't save you from this shitty writing though

    The owner tagged two of these `[amber]` and two `[akgraner]`; they are
    the same person, so they are listed under the login her nameplate
    already carries. SETTLED 2026-08-23, owner, verbatim: "kyle is
    kylegospo" -- so the lowercase `kyle` is KyleGospo, who also speaks at
    8:43.750 and 10:04.867, and every one of his lines now carries his own
    portrait rather than the drawn crest. There is no second Kyle.

    SETTLED 2026-08-25, owner-approved: the login is exactly `kolunmi`
    (verified at github.com/kolunmi) -- the same person who already speaks
    at 9:07.083, 9:17.683 and 10:04.187 in this act, so the "Eve"/"Eva"
    handle above was never a second voice.

## 10:01.2
! [mapped_haters] HATERS |

    Owner, 2026-08-24: "9:57, all the enemies are the haters, it just needs
    to be obvious" — on the alpha2 clock he was watching, the red-lit enemy
    face with the bright red dot opens at 9:57. The bar used to fire at
    10:00, over the guardian sunset silhouettes, and read as the GUARDIANS
    being the haters; it now opens on the enemy face's first frame (the
    shot ran film 313.3 → 315.2 before the pause grew 4.1 s; it is
    317.4 → 319.3 now). The red overlays still "match the style of the
    original kernel one" (owner, 2026-08-19) — this is that boss bar, a
    chrome row at the top of frame that shares the screen with whatever
    pill is up by design.

## 10:04.187

[mapped_kolunmi_disco] kolunmi @ 10:04.187 +2.2: Disco!
  - avatar_login: kolunmi
  - bond_of: mapped_kyle_sup

    Owner, 2026-08-24: "around 10:02 when the hunter is onscreen have
    kolunmi do 'Disco!'". The hunter is the cloaked figure in the red
    corridor fight — the shot right after the enemies HATERS now opens on.
    "Around 10:02" was the alpha2 clock; the pause growth makes that
    corridor film 321.067 → 323.0. The pill opens 0.68 s earlier so its
    2.2 s hold clears Kyle's nameplate (arrives 322.837, same lane) with
    the house 0.25 s gap, and it answers his "Sup" — which is why it bonds
    to that pill by name: the overlap exemption in `tools/plate.py` is NAMED
    precisely so it cannot spread, and this pair is the owner's call-and-
    response across the deck's two lanes (Disco! left, Sup right). Deleted
    2026-08-23, restored verbatim a day later.

## 10:04.867

[mapped_kyle_sup] kylegospo: Sup
  - position: right
  - source_anchor: 335.267
  - bond_of: mapped_kyle_reveal
  - avatar_login: KyleGospo

    OWNER-PLACED, DO NOT MOVE. Owner, verbatim: "sup is a purple titan",
    "put it when it's zoomed into his face". This is the first frame of that
    close-up; the pause growth of 2026-08-24 moved the content 4.1 s, so the
    shot now runs 321.067 → 321.833 film. The pill OPENS on his face, which
    is what he asked for; owner, 2026-08-24, asked again and confirmed the
    seat stays.

    An earlier agent slid it to 316.287 to make a builder assertion pass,
    which put it AFTER kolunmi's "Disco!" and reordered the authored
    exchange. That is the fourth class in AGENTS.md: a gate refusing a seat
    is not permission to move an authored beat. It was reverted, and the
    assertion that provoked it is gone — an overrun is reported now, never
    raised. ("Disco!" was deleted on 2026-08-23 and restored on 2026-08-24,
    above; the warning stands, because the seat it protects has not moved.)

    `bond_of` puts it in the deck's bonded-pair shape: his nameplate holds
    the left lane, the pill takes the RIGHT. The owner locked both TIMES
    ("lock the plate"; the pill on the close-up's first frame) — the lane
    was never his instruction, and stacking both on the left drew them on
    top of each other for the pill's last 0.43 s, since the nameplate
    arrives at 322.837. Right lane, same seats: the pair reads as the site's
    GUARDIAN BOND composition.

## 10:14.937

>> THE BLOCK THE OWNER WROTE UNDER "Slay out, Queen!". There is no air
there -- akgraner's six kindness pills run 9:34.653 to 9:51.953 without a
gap -- so these play a beat later, after Kyle's reveal. Owner, 2026-08-24:
"Remove kyle's lines after 'Sup', the others aren't needed" -- his
"I'm not calling this Bobonomics" and "We had to make this movie" pills are
gone. His line "castrojo killed me in Halo today" used to be parked below
as unreachable overflow; it is now seated in the paused conversation above
(## 9:52.203, id `chat_kyle_halo`). nwoods3, kolunmi and Hikari stay here. <<

[chat_nwoods3_seen] nwoods3 @ 10:14.937 +2.2: I feel seen
  - avatar_login: nwoods3

    The owner wrote the speaker as `https://github.com/nwoods3`; the URL
    resolves the login and the portrait, and never reaches a frame.

[chat_kolunmi_level] kolunmi @ 10:17.387 +2.2: Hey did you see how we just loaded up in a new level?

[chat_hikari_warframe] Hikari @ 10:19.837 +2.366: Finally, I can play WARFRAME!
  - avatar: null
  - avatar_url: null

## 10:28.100

[retirement-1] [redacted] @ 10:28.100 +2.125: Finally, retirement
  - avatar: null
  - avatar_url: null

[retirement-2] [redacted] @ 10:30.475 +2.125: The long walk beckons
  - avatar: null
  - avatar_url: null

    MOVED VERBATIM FROM ACT III. Owner, 2026-08-24: "10:24 is where
    redacted's 'retirement conversation' should go, not in the next
    chapter." 10:24 on the alpha2 clock is the Cayde-6 neon-street shot
    that closes this act's picture; with the pause holding 4.1 s longer,
    that shot opens at 10:28.100. The speaker is `[redacted]` on purpose —
    he is revealed later in the programme, in act VI — so the pills carry
    no avatar and no crest, exactly as they did in act III. The second pill
    clears 0.8 s into the black tail; the picture has ended on the heroes
    and the words ride the outro.

>> The ten-plus lines the owner wrote on 2026-08-23, and updated 2026-08-25,
that this stretch of the act had no room for now have a home: they are
seated in the paused conversation above (## 9:52.203), right after
cortney's line, in the order and words he wrote them -- see that block for
the identity notes on `[amber]`/`[akgraner]`, `kyle`/KyleGospo and the
settled "Eve"/"Eva"/`kolunmi` handle.

Still unresolved: `Hikari` at 10:19.837 may be the act's existing
`HikariKnight`, who already speaks at 9:02.183 and 9:15.233 with his own
portrait. Naming him would credit a real person on a hunch, so he renders
uncast until the owner says. <<

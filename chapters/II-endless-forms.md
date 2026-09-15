---
act: II
manifest: stories/02-endless-forms-plates.json
# Measured from the final running order: prologue 101.200 + Act I 111.600 +
# Act II's embedded front 76.600 = 289.400 seconds.
programme_start: 289.400
field_order: id, at, dur, name, title, title_source, kind, position,
  copy_source, speaker, text, text_source, speaker_pending, scale,
  seen_at_src, avatar, avatar_url, bond_of
reseat: scripts/build_efmb_plates.py:reseat_chapter_entries
---

# Act II — Endless Forms Most Beautiful: conversations

Every chat speaker is either a verified GitHub login or the intentionally
uncast `TBD`. `speaker_pending` records copy whose author named
a voice without evidence for a GitHub identity.

The hallway interruption has three authored blocks: `paused` holds the
hallway before the Amber insert, `amber-action` is the inserted source clip,
and `post-amber` holds the returned hallway before Destiny picture resumes.
The builder derives those intervals from the records below.

## 5:20.033

[chat_joseph_ricardos] jrsapi @ 5:20.033 +3.4: No one can tell which Ricardo is which so roll with it
  - position: null

[chat_ricardo_nukeguy] rochaporto @ 5:23.833 +3.4: It's me the nuke guy how do you think I got here?

[chat_pilot_lunar] TBD @ 5:27.633 +2.883: Lunar record baby! Hello KubeCon + CloudNativeCon
  - speaker_pending: pilot

[chat_ricardo_ai] ricardosalveti @ 5:30.833 +3.4: They wanted us to put AI in the glider so we did.

## 5:59.833

[chat_joseph_slop] jrsapi @ 5:59.833 +2.6: That explains the slop
  - position: null

>> KARENA'S FOUR LINES ARE OUT, AND THIS IS THE ONLY RECORD OF THEM.
Two authored passes disagree and neither is an agent's to overrule, so the
copy is written down here rather than seated or lost. #396 removed them as
"old conflicting windows" and guards the removal with a test; the 2026-08-28
pass restored them at their pre-removal seats. Verbatim, with the seats that
pass gave them, on the verified `angellk` identity:

    [chat_karena_job]      6:01.233 +2.6  I love this job
    [late_karena_cardio]   6:31.300 +2.2  Like cardio!
    [late_karena_lessons]  6:47.300 +2.2  Hit 'em with your lessons learned
    [toc_karena]           7:01.333 +3.2  One hundred thousand bootc
                                          volunteers, ready to power up

Seating them again is not mechanical: `toc_karena` +3.2 from 7:01.333 runs
to 7:04.533, and `toc_joseph_worth` is pinned at 7:04.477, so one of two
authored beats has to move for both to play. That is the owner's call.
OMITTED, NEVER STALE: the act ships without them and this note is the
punch-list entry. <<

## 6:18.283

[late_mfahlandt_clean] mfahlandt @ 6:18.283 +2.2: K1 Logistics is clean

[late_kfaseela_gamers] kfaseela @ 6:20.983 +2.2: The gamers were here alright

[late_markmandel_online] markmandel @ 6:23.683 +2.2: Agones Cluster - ONLINE

[late_riaankleinhans_close] riaankleinhans @ 6:26.383 +2.2: You're getting close

[late_jrsapi_learn] jrsapi @ 6:28.900 +2.2: They learn quickly
  - seen_at_src: 117.266

[late_rochaporto_move] rochaporto @ 6:31.350 +2.2: We need to move!
  - seen_at_src: 119.716

[late_metrics_cluster] jrsapi @ 6:33.900 +2.2: Projects Teams Metrics are strong
  - seen_at_src: 122.266

[late_metrics_mentoring] jrsapi @ 6:39.600 +2.8: They just need mentoring in the right skills

## 6:50.600

! [late_poor_technical_decisions] YOUR POOR TECHNICAL DECISIONS |


## 6:52

[rev_glider] rochaporto: The glider can take us around the solar system
[rev_not_mars] angellk: Yeah but this isn't Mars
[rev_know_what] raravena80: Make it look like we know what we are doing

## 7:03.900


[toc_joseph_worth] jrsapi @ 7:10.077 +2.706: The gamers would have to impress BOTH Ricardos

[toc_ricardo] rochaporto @ 7:13.033 +2.4: Look man I am so tired just jump

## 7:17

[rev_love_job] angellk: I love this job
  - position: letterbox

## 7:28.900

[mapped_kernel_bump] castrojo @ 7:28.900 +2.2: Time to get this driver upstream
  - seen_at_src: 183.366

## 7:34.900

[mapped_pastaq_tests] pastaq @ 7:34.900 +2.2: All your tests passed right?
  - seen_at_src: 189.366

[mapped_lionheartp_what_tests] LionHeartP @ 7:38.900 +2.2: What tests?
  - seen_at_src: 193.366

## 7:41.350

[mapped_a1rmax_intro] A1RM4X @ 7:41.350 +2.295: Thank you I never thought I could help!
  - bond_of: walk_A1RM4X

[mapped_a1rmax_intro_2] A1RM4X @ 7:43.895 +2.236: I'm not like you I'm just a lowly user
  - bond_of: walk_A1RM4X

[walk_ge_stream] GloriousEggroll @ 7:46.381 +2.2: It's your patch, turn the stream on


## 7:49

[rev_like_cardio] angellk: Like cardio!


## 7:53

[rev_getting_sloppy] jrsapi: This is getting sloppy!
[rev_dress] angellk: It's getting all over my dress!


## 7:58

[rev_just_here] rochaporto: Weren't we just here?
[rev_new_people] jrsapi: I'm tired man we need new people

## 8:04

[rev_cncf_rolls] angellk: Show them how the CNCF rolls

## 8:14.900

[mapped_eggroll_title] LionHeartP @ 8:14.900 +2.2: Nice work testing that patch
  - seen_at_src: 229.366

[mapped_eggroll_blueberries] LionHeartP @ 8:17.600 +3.4: Usually Blueberries just send me a bunch of crap

[mapped_eggroll_didyou] LionHeartP @ 8:21.900 +2.2: You didn't test any of this did you.
  - seen_at_src: 236.366

[mapped_pastaq_what_tests] pastaq @ 8:25.900 +2.2: Hey man WHAT tests?
  - seen_at_src: 240.366

## 8:28.166

[walk_ge_lesson] LionHeartP @ 8:28.166 +2.2: Let's go!
  - position: right
  - seen_at_src: 242.632

[mapped_redacted_unlearning] castrojo @ 8:30.900 +2.75: Unlearning bad habits takes time
  - seen_at_src: 290.000

[mapped_redacted_options] castrojo @ 8:33.900 +2.75: Your options are success
  - seen_at_src: 293.000

[mapped_redacted_mines] castrojo @ 8:37.100 +3.648: Or a lifetime of servitude in the Toilmaster's Packaging Mines


[mapped_kyle_titanfall] KyleGospo @ 8:49.350 +2.2: FOR TITANFALL!
  - seen_at_src: 308.450

[mapped_redacted_blow] castrojo @ 8:51.800 +2.6: Or go blow some shit up
  - seen_at_src: 310.900

## 9:52 paused

[rev_cayde_spirit] castrojo @ 8:54.650: There's the spirit
[rev_cayde_story] castrojo: Never let stop energy tell YOUR story
[rev_cayde_children] castrojo: Go forth and conquer my gamer children!
[owner_convo_joseph] jrsapi: We can't let The Toilmaster enslave another generation
[rev_legendary] angellk @ 9:11.517: Don't look at me I only turned on Legendary Mode
[chat_amber_bazaar] akgraner @ 9:14.967: Let me clean out this trash

## 9:17.417 amber-action

## 9:27.887 post-amber

[chat_kolunmi_level] kolunmi: Hey did you see how we just loaded up in a new level?



## 11:39.013

! [mapped_haters] HATERS @ 10:23.601 +5.0 |
  - source_anchor: 326.163

    Source 326.163 is the enemy attack; the shield formation at source
    331.163 is the heroes and never carries HATERS, so the bar clears there.
    OPEN, owner 2026-08-28: "I want it until the 'sup' and the closeup on
    Kyle". Sup is source-anchored to 331.763, which is 0.6 s INSIDE the hero
    shot, so honouring that phrase literally would put HATERS on the heroes.
    Which reading is right is a judgement about the frame and is the owner's;
    the evidenced seat is kept until then.

## 11:44.613

[mapped_kyle_sup] KyleGospo @ 10:29.201 +2.2: Sup
  - position: right
  - source_anchor: 331.763

## 11:46.667

[mapped_kolunmi_disco] kolunmi @ 10:31.255 +2.2: Cardio!
  - source_anchor: 333.817
  - bond_of: mapped_kyle_sup

## 12:09.583

[retirement-1] castrojo @ 10:54.168 +2.2: Finally, retirement
  - source_anchor: 358.497

[retirement-2] castrojo @ 10:56.618 +2.2: The long walk beckons
  - source_anchor: 360.947

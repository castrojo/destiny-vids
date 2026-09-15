---
act: VI
manifest: stories/06-wolves-cayde-plates.json
# Programme start measured from `python3 tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-25. The programme item-duration rule is authoritative.
programme_start: 1115.367
# This act's manifest holds BOTH kinds of plate: the pills below, and four
# `copy_source: brief` nameplates that resolve from the roster. This file
# authors only its own -- `sync` carries the nameplates through in place.
owns_plates: true
field_order: id, kind, position, speaker, avatar, detail, label, title, subtitle, body, text, copy_source, at, dur, fade_in, fade_out_at, fade_out, seen_at_film, _note
defaults:
  kind: chat
  position: letterbox
  copy_source: owner_supplied
  avatar: auto
  fade_in: 0.6
  fade_out: 0.25
  # This act's pills start fading 0.6 s before their window closes, not
  # 0.25 s: the fade is a fade-IN's length long on the way out. That is what
  # is on the delivered master, so it is stated rather than re-derived.
  fade_out_at: derived 0.6
  text_source: null
  avatar_url: null
---

# Act VI — the wolves, and what is asked of you

Jorge Castro's six lines over his own close-up, and the Ghost's welcome an
act earlier. Act II plates him as `[ REDACTED ]`; this act is the reveal, so
these are the first words on screen carrying his name.

Every line here is **owner-supplied verbatim**, including two the owner
corrected himself: "For fives years" → "For five years", and "Lead the way,
open source will follow" → "Lead the way, we will follow". Reproduce them as
written; never tidy them.

Four gold nameplates sit between the welcome and the pills — the Cayde-6
reveal and three credits. They are **not here on purpose**: they carry
`copy_source: brief` and resolve from the roster, which is the one place
those names live. Edit them there.

## 18:51

* [popup_18_infrastructure] title @ 18:51 +2.2
  - position: top-right
  - title: Humanity had conquered infrastructure

* [popup_18_open_source] title +2.2
  - position: top-right
  - title: Uniting the entirety of Open Source

* [popup_18_white_ball] title +2.2
  - position: top-right
  - title: Under in one big white ball of hope in the sky

* [popup_18_cloud_native] title +2.2
  - position: top-right
  - title: The warm white ball of Cloud Native brought many gifts

* [popup_18_deployments] title +2.2
  - position: top-right
  - title: Deployment times halved

* [popup_18_headcount] title +2.2
  - position: top-right
  - title: You even got some headcount

## 19:12

* [popup_19_reached_stars] title @ 19:12 +2.2
  - position: top-right
  - title: We reached out to the stars

* [popup_19_built_wonder] title +2.2
  - position: top-right
  - title: We basked in wonder at what we had built

* [popup_19_ok] title +2.2
  - position: top-right
  - title: ... Ok

## 19:23

* [popup_19_solar_system] title @ 19:23 +2.2
  - position: top-right
  - title: The light of open source spread through our solar system

* [popup_19_together] title +2.2
  - position: top-right
  - title: Humanity used them together, in peace

* [popup_19_europa] title +2.2
  - position: top-right
  - title: Except Europa, we were told to never make an attempt

## 19:36

* [ghost_welcome] status @ 19:36 +6.0
  - position: top-right
  - fade_in: null
  - fade_out: null
  - fade_out_at: null
  - detail: AN4-CH4K-12
  - label: Welcome to KubeCon + Cloud Native Con
  - seen_at_film: 60.633
## 19:45

* [popup_19_civilization] title @ 19:45 +2.2
  - position: top-right
  - title: Humanity united around our great cloud native civilization

* [popup_19_sharing] title +2.2
  - position: top-right
  - title: Our primary purpose had turned to knowledge sharing

* [popup_19_beacon] title +2.2
  - position: top-right
  - title: A beacon in what remained of our once great empire

## 20:00

* [popup_20_toilmaster] title @ 20:00 +2.2
  - position: top-right
  - title: Each passing cycle the Toilmaster enboldens his attack

* [popup_20_burnout] title +2.2
  - position: top-right
  - title: Our noblest Maintainer-Guardians falling to burnout, or worse


## 20:12

* [jonathan_bryce] - @ 20:12 +2.0
  - position: left
  - label: DIRECTOR // GUARDIAN
  - name: Jonathan Bryce
  - title: The First Automator | Master Sommelier
  - tagline: "Solves Hard Problems"
  - avatar_login: jbryce
  - _note: https://www.cncf.io/people/staff/?p=jonathan-bryce&_sf_s=jonathan%20bryce
## 20:14

[jbryce_empower] jbryce @ 20:14 +2.8: We will empower those who come after

## 20:19

[angellk_deploy] angellk @ 20:19 +2.8: Deploy all Guardians! We're under attack!
[rochaporto_infrastructure] rochaporto +2.8: Our infrastructure will suffer the Toilmaster
[https://github.com/alolita] Deploying our units to the southern perimeter
[https://github.com/chira001] Western Wall secured
[https://github.com/chadbeaudin] All fighter wings deployed, good hunting

## 20:42

[akgraner_interdictor] akgraner @ 20:42 +2.8: Let's roll, interdictor squad on me!

## 20:46

[marcoceppi_speed] marcoceppi @ 20:46 +2.2: Speeeeed!

## 20:51

! [terrible_ai_mandate] TERRIBLE AI MANDATE @ 20:51 +4.0

## 20:56

* [talia_marketing] - @ 20:56 +4.0
  - position: left
  - label: BLUEBERRY // MARKETING
  - name: Talia S.
  - title: University of Michigan | VULTR
  - tagline: "Intern with more Wins than You"
  - avatar: null

## 21:00

* [abbey_bangser] - @ 21:00 +4.0
  - position: left
  - label: TRUSTEE // GUARDIAN
  - name: Abbey Bangser
  - class: Platform Specialist
  - tagline: "Delivers. Every Time."
  - avatar_login: abangser

## 21:06

* [mario_fahlandt] - @ 21:06 +4.0
  - position: left
  - label: MAINTAINER // GUARDIAN
  - name: Mario Fahlandt
  - tagline: "Supposed to be Farming"
  - avatar_login: mfahlandt

## 21:12

[anita_count] Anita-ihuman @ 21:12 +2.8: How many of these things are there!

## 21:15

[akgraner_together] akgraner @ 21:15 +2.8: To me! Stay together!

## 21:22

! [cncf_expertise] LACK OF INHOUSE CNCF EXPERTISE @ 21:22 +4.0

## 21:29

* [tank_techdebt] title @ 21:29 +4.0
  - position: top-right
  - title: Same techdebt over and over

## 21:35

[pthomas_launch] pthomas @ 21:35 +2.2: LAUNCH LAUNCH LAUNCH

## 21:39

[mrbobbytables_breach] mrbobbytables @ 21:39 +2.2: All sandboxes breached

## 21:43

! [platform_tormentor] PLATFORM TORMENTOR @ 21:43 +3.0 | Destroyer of Budgets | Sapper of Talent | Tech Debt Conjurer
  - tagline: "Thrives on Cloud Native Hubris"

[ingress_talk] ingress-nginx @ 21:43 +2.2: I've had enough of your smug talk

## 21:46

[akgraner_kyle_destroy] akgraner @ 21:46 +2.2: Kyle will destroy you

## 21:50

* [cloud_native_nyc] context @ 21:50 +4.0
  - position: top-right
  - title: Cloud Native New York City

[https://github.com/abebars] @ 21:50 +1.8: You picked the wrong town
[https://github.com/justaugustus] +1.8: And the wrong day

## 21:54

[https://github.com/juliafmorgado] Disco!

## 21:57

[https://github.com/kevin-wangzefeng] CNCF Projects team, plan "Bazzite" approved ... do it
[https://github.com/jeremyrickard] Full autonomous mode authorized
[https://github.com/thschue] : Mechaphippy Deployment: [ APPROVED ]

## 22:07

[alatiera_toys] alatiera @ 22:07 +2.8: I've brought some new toys Mister Clanker man ...

## 22:11

* [james_reilly] - @ 22:11 +4.0
  - position: left
  - label: MAINTAINER // GUARDIAN
  - name: James Reilly
  - title: Master Buildstream Architect
  - tagline: "The Kid from Ohio"
  - avatar_login: hanthor

## 22:14

! [ai_tormentor] AI TORMENTOR @ 22:14 +4.0 | RISE FROM THE SLOP - OR DROWN IN IT

## 22:21

* [ahmed_adan] - @ 22:21 +4.0
  - position: left
  - label: MAINTAINER // GUARDIAN
  - name: Ahmed Adan
  - title: Master Buildstream Architect
  - tagline: "The New Kid"
  - avatar_login: ahmedadan

## 22:26

* [jordan_petridis] - @ 22:26 +4.0
  - position: left
  - label: MAINTAINER // GUARDIAN
  - name: Jordan Petridis
  - title: Master Buildstream Architect
  - tagline: "The Greek Kid"
  - avatar_login: alatiera

## 22:32

[clubanderson_elite] clubanderson @ 22:32 +2.8: Introducing our Elite Cloud Native Guardians

## 22:35

! [deliver_more] DELIVER MORE @ 22:35 +4.0 | WITH LESS

[shuah_khan_guardian] shuahkh: They're sending everything, you got this!

## 22:49

[alatiera_slop] alatiera @ 22:49 +2.8: James you and your fucking SLOP!
[hanthor_not_me] hanthor +2.8: That wasn't me!

## 22:51

! [ai_founder_ops] AI FOUNDER OPS @ 22:51 +4.0 | IS STILL FOUNDER OPS

* [castrojo_force_push] status @ 22:51 +4.0
  - position: status
  - label: has force pushed to `main`
  - detail: castrojo

## 22:59

[hanthor_buildstream] hanthor @ 22:59 +2.8: Just connect Buildstream to Kubernetes!

## 23:05

[ahmedadan_ai] ahmedadan @ 23:05 +2.8: Jordan does this mean you like AI?

## 23:08

[alatiera_ciao] alatiera @ 23:08 +2.8: No, Greeks can do this naturally. Ciao

## 23:16

* [maintainer_firepower] - @ 23:16 +6.0
  - position: left
  - label: CNCF and Apache Foundation
  - title: Synergy Optimized
  - tagline: MAXIMUM MAINTAINER FIREPOWER
  - variant: leader

## 23:26

* [popup_23_abyss] title @ 23:26 +2.2
  - position: top-right
  - title: Maintainer-Guardians clawed their way from the abyss

* [popup_23_retake] title +2.2
  - position: top-right
  - title: And started to retake what was theirs

* [popup_23_humanity] title +2.2
  - position: top-right
  - title: To share and protect for for all humanity

## 23:58

[bsherman_late] bsherman @ 23:58 +2.0: Are we late?
[krook_snow] krook +2.0: What's with the snow gear?
[pthomas_story] pthomas +2.0: Long story
[bsherman_new] bsherman +2.0: We're new
[p5_strong] p5 +2.0: But strong
[fatherlinux_hummingbird] fatherlinux +2.4: Team Hummingbird reporting for duty!

## 24:12

* [cblecker_ai] - @ 24:12 +2.8
  - position: left
  - name: Christoph Blecker
  - tagline: Shot by his own AI Conformance Program
  - avatar_login: cblecker

## 24:15

[akgraner_rez] akgraner @ 24:15 +2.2: Thanks for the rez Kyle!

## 24:19

[robertsirc_go] robertsirc @ 24:19 +2.2: Let's goooooo!




# UNRESOLVED / TODO(owner):
# robertsirc_trash @ 24:23 +2.2 ("Taking out the trash!") collides with
# owner-authored castrojo_line_1 seated verbatim at 24:23.557 (+2.8).
# It is omitted from the plate schedule for this degraded render pending
# owner decision on placement.

## 24:23.557

[castrojo_line_1] castrojo @ 24:23.557 +2.8: Now you are ready
[castrojo_line_2] castrojo +2.8: In the world of technology there are the sheep
[castrojo_line_3] castrojo +2.8: And then there are the wolves

## 24:45

* [gold_robertsirc] - @ 24:45 +2.8
  - position: left
  - label: "#HIREAWOLF // MAINTAINER"
  - class: Harbinger Titan
  - name: Robert Sirchia
  - title: Protector of the Helm
  - variant: leader
  - avatar_login: robertsirc

## 24:48.821

[castrojo_line_6] castrojo @ 24:48.821 +2.8: I follow my mentors
  - bond_of: cayde_reveal_castrojo
## 24:57

[castrojo_line_7] castrojo @ 24:57 +2.8: Of the past
  - bond_of: gold_kelsey_hightower

## 25:02
[castrojo_line_8] castrojo @ 25:02 +1.7: The Present
  - bond_of: gold_brian_ketelsen

## 25:04

[castrojo_line_9] castrojo @ 25:04 +2.8: And Future
  - bond_of: gold_angie_jones

## 25:11

[castrojo_line_10] castrojo @ 25:11 +2.2: You will fail
[castrojo_line_11] castrojo +2.2: Don't let it take you
[castrojo_line_12] castrojo +2.2: The only winning move is not to play
[castrojo_line_13] castrojo +2.2: Think like a dinosaur
[castrojo_line_14] castrojo +2.2: Lift each other
[castrojo_line_15] castrojo +2.2: and rise ...

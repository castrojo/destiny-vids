#!/usr/bin/env python3
"""Build act VIII -- the credits -- from its committed manifest.

The owner's design is issue #51, revised in session on 2026-08-13. Act VIII was
the one act with **no film** (docs/running-order.md), and the last thing between
the programme and the feature.

## The music, and why it is cut this way

The bed is Nightwish's *Wish I Had an Angel* (instrumental), already measured
into ``music/bed_wish_i_had_an_angel.json``. The owner's instruction: *"design
the song to loop back to the beginning where it makes sense since people miss
that part of the song. Also cut out the weird drum section with the moaning we
want the song on loop basically but starting at the drum smash."*

So the bed is TWO spans, in this order, and everything is measured rather than
eyeballed:

* **A -- the drum smash to the end**: 193.420 -> 240.780 (47.360 s).
  193.420 is the measured re-entry after the breakdown, a **+12.98 dB** step --
  the largest onset in the song. 240.780 is the last audible window: the file
  carries ~4.4 s of digital silence after it, and joining on the file end
  instead would land the loop in exactly the silence issue #105 is about.
* **B -- the top of the song to the breakdown**: 0.000 -> 181.320 (181.320 s).
  181.320 is where the "moaning" breakdown starts (level falls to about
  -13 dB and stays). Cutting there removes it, which is what was asked. The
  12.10 s this drops is the same section the bed record's committed excision
  already found (``removed_sec: 12.097596``) -- two independent measurements
  agreeing.

One pass is **228.680 s** (3:48.68), which is what the credits run.

## The reveal

*"when the crescendo for the next riff is, the crescendo of this song, drop the
comic book cover, we are removing it from the end of europa, this is the real
reveal."*

There is no crescendo inside span A -- it is one sustained final chorus, its
onsets uniform at about +7 dB. The song's crescendo is its **opening riff**,
and the loop is what makes it reachable: a **+10.53 dB** onset at 9.080 s,
lifting the smoothed level from -12 dB to -6 dB. That is the biggest build in
the song and it is precisely the part the loop exists to let people hear.

On the credits clock that is **47.360 + 9.080 = 56.440 s**, and the cover lands
there.

The cover is ``wolves.jpg``, the same asset act I uses as its title cover and
the one the Europa director's cut currently ends on. **Removing it from the end
of Europa is act VII's job, and act VII has no committed inputs at all (#152)**
-- it is cut in ``~/Videos/wolves-directors-cut``, so this builder cannot do it
and does not pretend to. It is recorded in the manifest and reported here.

## What is on screen

Nothing is invented. The four fixed cards are the owner's words. The cast comes
from ``vocab/casting.yaml``. The contributors are the GitHub API's all-time
lists for the four projects, **frozen into the manifest** so a rebuild is
reproducible and so the render needs no network.

    python3 scripts/build_credits.py --refresh-contributors  # re-snapshot (network)
    python3 scripts/build_credits.py --plan                   # the schedule, no render
    python3 scripts/build_credits.py --cards-only             # just the PNGs
    python3 scripts/build_credits.py                          # the master
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import conform  # noqa: E402
from tools import credits as C  # noqa: E402
from tools.bed import fmt_tc  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "08-credits.json"
CARDS_DIR = REPO_ROOT / "renders" / "cards-08-credits"
OUT = REPO_ROOT / "renders" / "08-credits.mp4"

# How much longer than the film the last card is held, so `-t` -- not the
# concat demuxer's arithmetic -- decides where the picture ends.
CONCAT_TAIL_SEC = 20.0

# THE UPSTREAM TIER COMES FIRST, AND IT IS FOUR PROJECTS NOW.
#
# Owner: *"Add Fedora CoreOS and bootc upstream groups to the credits and have
# them top tier in the credits before bluefin - make theirs larger and more
# distinguished."*, then on 2026-08-14: *"Add GNOME OS Upstream as the same
# level as coreOS"*, *"Only have GNOME OS since it's such a large org"*, and
# *"Put KDE Linux Upstream"*.
#
# Bluefin is an image built on other people's work, and these four are the
# work: Fedora CoreOS is where the ostree-native model this whole thing rides
# on is maintained, bootc is the boot-from-container project the LTS line is
# built with, and GNOME OS and KDE Linux are the two desktops doing the same
# thing from the other end. They are credited BEFORE the projects that depend
# on them, on their own larger grid (``tier: upstream``).
#
# GNOME OS is `gnome-build-meta` and NOTHING ELSE, on the owner's instruction:
# GNOME the organisation is enormous and crediting all of it would drown the
# tier. The project builds GNOME OS and that is what is being credited.
#
# `bootc-dev/bootc` is the project's OWN current home -- `containers/bootc`
# redirects to it, and the API confirms the redirect rather than the name
# being assumed.
#
# THE UBLUE ORDER IS THE OWNER'S: *"Put universal blue and aurora ahead of
# bluefin"*, with Bazzite placed between them in session. Universal Blue is
# still the deduped section (see `fetch_contributors`) -- that is bound to the
# SECTION and not to its position, which is the bug moving it first would
# otherwise have caused.
GITHUB, GITLAB_GNOME, GITLAB_KDE = "github", "gitlab.gnome.org", "invent.kde.org"

CONTRIB_REPOS = [
    ("Fedora CoreOS", GITHUB, "coreos/fedora-coreos-config", "upstream"),
    ("bootc", GITHUB, "bootc-dev/bootc", "upstream"),
    ("GNOME OS", GITLAB_GNOME, "GNOME/gnome-build-meta", "upstream"),
    ("KDE Linux", GITLAB_KDE, "kde-linux/kde-linux", "upstream"),
    ("Universal Blue", GITHUB, "ublue-os/main", None),
    ("Bazzite", GITHUB, "ublue-os/bazzite", None),
    ("Aurora", GITHUB, "ublue-os/aurora", None),
    ("Project Bluefin", GITHUB, "ublue-os/bluefin", None),
]

# The section whose list is "deduped from above". It is named, not inferred
# from position: it used to be the LAST entry and the dedup was written as
# "the last section", so moving Universal Blue to the front would have quietly
# deduped Project Bluefin instead and taken every shared name off its wall.
DEDUPED_SECTION = "Universal Blue"

# KDE LINUX'S TWO NAMED MAINTAINERS, pinned. Owner: *"put at least aleixpol
# and harald sitter"*. GitLab's contributor list is by commit author name and
# spelling varies between a person's commits, so "at least" is enforced here
# rather than hoped for. Both are reproduced as the project's own commits
# spell them.
KDE_PINNED = ["Aleix Pol", "Harald Sitter"]

# THE GHOST MAINTAINER -- an easter egg, and the owner's own words:
# *"then put a outline of a ghost maintainer 'The Next KyleGospo' and then put
# a title under it 'Curse of Maintainership'"*. It is NOT a contributor row: it
# carries no login, fetches no avatar, and is drawn as an empty outline. It
# rides on the KDE Linux wall, the last upstream section, so the joke lands at
# the end of the tier rather than in the middle of it.
GHOST_MAINTAINER = {
    "name": "The Next KyleGospo",
    "title": "Curse of Maintainership",
}


# MACHINE ACCOUNTS, NAMED RATHER THAN PATTERN-MATCHED.
#
# The API's `type == "User"` filter does not catch these: both are ordinary
# user accounts that a project drives with a token. A credit roll names
# people, so they come out -- but by an explicit list, because a login ending
# in "bot" is not evidence about a human ("bobslept" is a person, and so is
# anyone else a suffix rule would sweep up).
BOT_LOGINS = {"coreosbot", "platform-engineering-bot"}


def fetch_github_contributors(repo):
    """All-time human contributors for a GitHub repo, as logins."""
    raw = subprocess.run(
        ["gh", "api", f"repos/{repo}/contributors?per_page=100&anon=0",
         "--paginate", "--jq", '.[] | select(.type=="User") | .login'],
        capture_output=True, text=True, check=True).stdout.split()
    return sorted({n for n in raw if n.lower() not in BOT_LOGINS}, key=str.lower)


def fetch_gitlab_contributors(host, project):
    """All-time contributors for a GitLab project, as NAMES.

    GNOME OS and KDE Linux are not on GitHub, so ``gh`` cannot reach them and
    there are no logins to reach for -- GitLab's contributor endpoint answers
    with a commit author's **name and email**.

    Only the NAME is taken. An email address is not copy, it is somebody's
    contact detail, and a credit roll harvested into a committed manifest is
    exactly the wrong place for a few hundred of them. A GitLab contributor
    therefore has no cached PFP either, and their face degrades to the ring
    the renderer already draws for an unverified login.

    Degrades rather than blocks: a network failure returns nothing and the
    section renders empty with a note, because act VIII must still build with
    no network at all.
    """
    import urllib.error
    import urllib.parse
    import urllib.request

    url = (f"https://{host}/api/v4/projects/{urllib.parse.quote(project, safe='')}"
           f"/repository/contributors?per_page=100&order_by=commits&sort=desc")
    names = []
    try:
        for page in range(1, 12):
            req = urllib.request.Request(f"{url}&page={page}",
                                         headers={"User-Agent": "destiny-vids"})
            with urllib.request.urlopen(req, timeout=30) as fh:
                rows = json.loads(fh.read())
            if not rows:
                break
            for row in rows:
                name = (row.get("name") or "").strip()
                if name and name.lower() not in BOT_LOGINS:
                    names.append(name)
            if len(rows) < 100:
                break
    except Exception as exc:  # noqa: BLE001 -- degrade, never block
        print(f"note: no contributors for {project} on {host}: {exc}",
              file=sys.stderr)
        return []
    return sorted(dict.fromkeys(names), key=str.lower)


def fetch_contributors():
    """All-time contributors per project, in the owner's order.

    One section is *"deduped from above"* -- Universal Blue -- and it is named
    rather than positional: it now plays FIRST, and a rule that said "the last
    section" would have deduped Project Bluefin instead.

    Bots are dropped by ``type == "User"`` on GitHub and by name on GitLab; a
    credit roll names people.
    """
    raw = {}
    for label, host, repo, _tier in CONTRIB_REPOS:
        if host == GITHUB:
            raw[label] = fetch_github_contributors(repo)
        else:
            raw[label] = fetch_gitlab_contributors(host, repo)

    # The owner's two named KDE maintainers are guaranteed to be on screen --
    # "put AT LEAST aleixpol and harald sitter" -- and are not duplicated if
    # the API already returned them under the same spelling.
    kde = raw.get("KDE Linux", [])
    have = {n.lower() for n in kde}
    raw["KDE Linux"] = [n for n in KDE_PINNED if n.lower() not in have] + kde

    # ONLY the deduped section is deduped, and only against the other sections
    # that are not upstream. The owner asked for "all the contributors to ever
    # contribute to aurora" under Aurora and so on -- somebody who worked on
    # both Bluefin and Aurora is credited under both, because they did both.
    # The upstream sections are NEVER deduped against, in either direction:
    # somebody who maintains bootc and also files Bluefin issues did both, and
    # the upstream credit is the point of the tier.
    seen = {n.lower() for label, _h, _r, tier in CONTRIB_REPOS
            if tier is None and label != DEDUPED_SECTION
            for n in raw[label]}
    raw[DEDUPED_SECTION] = [n for n in raw[DEDUPED_SECTION]
                            if n.lower() not in seen]

    out = []
    for label, host, repo, tier in CONTRIB_REPOS:
        section = {"section": label, "repo": repo, "names": raw[label]}
        if host != GITHUB:
            # Recorded on the section so the renderer knows these are names
            # and not logins -- it is why they carry no faces.
            section["host"] = host
            section["names_are"] = "display names, not logins (GitLab)"
        if tier:
            section["tier"] = tier
        if label == "KDE Linux":
            section["ghost"] = dict(GHOST_MAINTAINER)
        out.append(section)
    return out


def character_name(character_id):
    """A character id as the credits print it: ``cayde_6`` -> ``Cayde-6``.

    A trailing number is joined with a hyphen because that is how Destiny
    writes these names (Cayde-6, Saint-14); everything else is title case.
    """
    parts = character_id.split("_")
    out = []
    for part in parts:
        if part.isdigit() and out:
            out[-1] = f"{out[-1]}-{part}"
        else:
            out.append(part.title())
    return " ".join(out)


def cast_in_order(verified_logins=None):
    """The cast, as the film credits them: person, and who they played.

    Read from vocab/casting.yaml, never composed. A lead with no bound person
    is skipped rather than guessed -- rule 3.
    """
    from tools.derive import load_leads
    leads = load_leads()

    # plate.name is the person's REAL name -- what their own Guardian nameplate
    # says. display_name is sometimes a login ("castrojo") and sometimes the
    # CHARACTER ("Nimbatus"), so neither is safe alone. Build the map once from
    # every entry that has a plate, then a second role played by the same
    # person is credited under the same human name.
    real = {}
    for entry in leads.values():
        name = (entry.get("plate") or {}).get("name")
        if name and entry.get("person"):
            real.setdefault(entry["person"], name)

    cards = authored_cards()
    verified = dict(verified_logins or {})
    out = []
    for character_id, entry in leads.items():
        person = entry.get("person")
        if not person:
            continue
        credited = real.get(person) or entry.get("display_name") or person
        member = {
            "person": credited,
            "character": character_name(character_id),
            "character_id": character_id,
        }
        # A face, in strict order of what can be proved. An authored Guardian
        # card is the owner's own identity for that person; a `github:` login
        # in the vocab is verified. Neither is guessed, and there is no third
        # fallback -- a placard with no face is correct, a placard with the
        # wrong face is not recoverable.
        if credited in cards:
            member["card"] = cards[credited]
        if entry.get("github"):
            member["login"] = entry["github"]
        elif credited in verified:
            member["login"] = verified[credited]
        out.append(member)
    return out


AUTHORED_CARDS = Path.home() / "src/website/public/wolves/characters/characters.json"


def authored_cards():
    """``{person name: card slug}`` from the website's authored identities.

    READ ONLY, and deliberately tolerant of the file being absent: several
    agents run worktrees against that checkout, and a credits build must not
    depend on another repo being present. Missing simply means no cast art.
    """
    try:
        data = json.loads(AUTHORED_CARDS.read_text())
    except (OSError, ValueError):
        return {}
    rows = data.get("characters", []) if isinstance(data, dict) else data
    return {r["name"]: r["slug"] for r in rows
            if isinstance(r, dict) and r.get("name") and r.get("slug")}


def fetch_avatars(manifest, verbose=True):
    """Cache a face for every login the manifest names.

    The renderer never touches the network (``tools/credits.avatar``), so a
    contributor with no cached PFP silently degrades to a ring. Adding two
    upstream sections added ~200 logins nobody had ever fetched, which would
    have been two walls of empty rings and no error. Missing is still not
    fatal -- this only fills the cache in.
    """
    import urllib.request

    C.AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    logins = []
    for section in manifest.get("contributors", []):
        # A GitLab section carries display NAMES, not logins. Asking
        # github.com for "Harald Sitter.png" is not a missing avatar, it is a
        # category error -- and it would fetch whatever account happened to
        # answer, which is a face beside somebody else's name.
        if section.get("host") and section["host"] != GITHUB:
            continue
        logins.extend(section["names"])
    for value in (manifest.get("cast_logins") or {}).values():
        if isinstance(value, str) and not value.startswith("_"):
            logins.append(value)
    for person in manifest.get("cast", []):
        if person.get("login"):
            logins.append(person["login"])

    got = missed = 0
    for login in dict.fromkeys(logins):
        path = C.AVATAR_DIR / f"{login}.png"
        if path.exists() and path.stat().st_size >= 512:
            continue
        url = f"https://github.com/{login}.png?size=256"
        try:
            with urllib.request.urlopen(url, timeout=20) as fh:
                path.write_bytes(fh.read())
            got += 1
        except Exception as exc:  # noqa: BLE001 -- degrade, never block
            missed += 1
            if verbose:
                print(f"note: no avatar for {login}: {exc}", file=sys.stderr)
    if verbose:
        print(f"avatars: {got} fetched, {missed} missing")
    return got, missed


def build_manifest(refresh, refresh_cast=False):
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    if refresh or "contributors" not in manifest:
        manifest["contributors"] = fetch_contributors()
    # THE CAST IS NOT REFRESHED WITH THE CONTRIBUTORS, and that is deliberate.
    #
    # A credit names a real person, so the owner gets the last word on how
    # they are named -- the committed list is 8 curated entries with "Karena
    # Angel" spelled the way she and the README spell it and Cayde held out of
    # the starring roles. Deriving it from the vocab returns 15 entries,
    # "Karena Angell", and Cayde. Wiring that to --refresh-contributors meant
    # a routine contributor snapshot silently threw the owner's casting away;
    # it did exactly that on 2026-08-14 and the suite caught it.
    #
    # It regenerates only when it is MISSING, or when somebody asks for it by
    # name with --refresh-cast.
    if refresh_cast or "cast" not in manifest:
        manifest["cast"] = cast_in_order(manifest.get("cast_logins"))
    return manifest


def bed_passes(bed):
    """The bed's passes in play order: the instrumental loop, then the album.

    The manifest keeps pass one at the top level (it was the whole bed before
    the vocal version was added, and every measured number in it is unchanged)
    and hangs the pass that follows off ``then``. One pass or five, everything
    downstream walks this list rather than reaching for ``bed["segments"]``.
    """
    out = [bed]
    nxt = bed.get("then")
    while nxt:
        out.append(nxt)
        nxt = nxt.get("then")
    return out


def bed_spans(bed):
    """Every span the bed plays, in order, flattened across its passes."""
    return [span for p in bed_passes(bed) for span in p["segments"]]


def bed_total(bed):
    """The bed's length on the CREDITS clock.

    ``acrossfade`` OVERLAPS its two inputs, so a crossfaded join is shorter
    than the sum of its spans by the fade duration. Everything after the seam
    moves earlier by the same amount, which is exactly the bug this function
    exists to stop: the reveal was hand-set to 56.440 and landed at 56.180,
    0.26 s late against a transient it is supposed to hit.

    Every seam counts, including the hand-over from the instrumental loop into
    the album version -- it is the same kind of join and it costs the same
    overlap.
    """
    spans = bed_spans(bed)
    total = sum(s["end_sec"] - s["start_sec"] for s in spans)
    return total - max(0, len(spans) - 1) * bed.get("crossfade_sec", 0.0)


def reveal_at(bed, reveal):
    """Where the cover drops, on the CREDITS clock.

    Two ways to say it, and the difference matters:

    * ``at_sec`` -- the owner naming a time in the finished cut ("**:22** is
      when I want the comic book shot"). Taken literally, because it is a
      statement about the film, not about the song.
    * ``segment`` + ``source_sec`` -- pinned to a moment in the music, which
      survives the bed being re-cut. The crossfade's overlap is subtracted
      here; forgetting it once already put the cover eight frames late.
    """
    if reveal.get("at_sec") is not None:
        return float(reveal["at_sec"])
    xf = bed.get("crossfade_sec", 0.0)
    n = reveal["segment"]
    spans = bed_spans(bed)
    before = sum(s["end_sec"] - s["start_sec"] for s in spans[:n])
    return before - n * xf + (reveal["source_sec"] - spans[n]["start_sec"])


def schedule(manifest):
    """Lay the sequence on the credits clock.

    Two anchors are fixed by the music and everything else flexes around them:
    ``t=0`` is the drum smash, and the cover lands on the measured crescendo.
    The walls take whatever is left, split evenly, so adding a contributor
    slows the roll instead of overrunning the song.
    """
    bed = manifest["bed"]
    total = bed_total(bed)
    reveal = reveal_at(bed, manifest["reveal"])
    items = []
    t = 0.0

    # THE CALL TO ACTION FILLS EVERYTHING BEFORE THE REVEAL.
    #
    # Owner, 2026-08-14: *"Move the existing credits to after the comic reveal,
    # instead let's make this part leading up to it a call to action."* The
    # dur_sec are RELATIVE WEIGHTS scaled to the anchor -- the owner named a
    # time for the cover, so the cards give way to it rather than the other way
    # round, exactly as the fixed cards used to. FIGHT's weight is longer than
    # the first two together, which is what "up longer than the first 2" buys
    # it whatever the window is.
    cta = manifest.get("cta_cards", [])
    weight = sum(c["dur_sec"] for c in cta) or 1.0
    for card in cta:
        dur = card["dur_sec"] / weight * reveal
        item = {"kind": card.get("kind", "cta"), "t": t, "dur": dur}
        item.update({k: v for k, v in card.items()
                     if k not in ("dur_sec", "kind") and not k.startswith("_")})
        items.append(item)
        t += dur
    t = reveal

    hold = manifest["reveal"]["hold_sec"]
    items.append({"kind": "cover", "t": reveal, "dur": hold,
                  "image": manifest["reveal"]["image"]})
    t = reveal + hold

    # THE CREDITS FOLLOW THE COVER. Their dur_sec are seconds, not weights:
    # nothing is anchored between the reveal and the cast, so a card the owner
    # gave six seconds gets six seconds.
    for card in manifest["fixed_cards"]:
        items.append({"kind": "role", "t": t, "dur": card["dur_sec"],
                      "role": card["role"], "names": card["names"]})
        t += card["dur_sec"]

    # The whole cast follows them, in order. The reveal introduces the people
    # rather than interrupting them.
    # The verified-login overlay is applied HERE, not baked into `cast` when it
    # is generated: the cast list is only rewritten by --refresh-contributors,
    # so a login added to the manifest afterwards would otherwise never reach a
    # placard. Applying it every schedule keeps the two independent.
    verified = {k: v for k, v in (manifest.get("cast_logins") or {}).items()
                if not k.startswith("_")}
    photos = {k: v for k, v in (manifest.get("cast_photos") or {}).items()
              if not k.startswith("_")}
    target = manifest.get("cast_hold_sec", 4.0)
    redacted = set(manifest.get("cast_redactions") or [])
    for person in manifest["cast"]:
        name = person["person"]
        if person["character_id"] in redacted:
            # The name goes, and with it the face and the authored card --
            # otherwise the placard redacts a word and reveals the person.
            items.append({"kind": "cast", "t": t, "dur": target,
                          "person": C.REDACTED, "character": person["character"],
                          "card": None, "login": None, "photo": None})
        else:
            items.append({"kind": "cast", "t": t, "dur": target,
                          "person": name, "character": person["character"],
                          "card": person.get("card"),
                          "login": person.get("login") or verified.get(name),
                          "photo": photos.get(name)})
        t += target

    wordmark = manifest["wordmark"]
    # The upstream sections lead, whatever order they are stored in: the
    # owner's instruction is about the SEQUENCE, so it is enforced here rather
    # than left to how somebody happened to edit the manifest.
    sections = sorted(manifest["contributors"],
                      key=lambda s: 0 if s.get("tier") == "upstream" else 1)
    walls = []
    for section in sections:
        tier = section.get("tier")
        per_page = C.UPSTREAM_PER_WALL if tier == "upstream" else C.NAMES_PER_WALL
        pages = C.paginate(section["names"], per_page)
        for n, page in enumerate(pages):
            # The ghost maintainer rides the LAST page of its section, so it
            # closes the section rather than interrupting it.
            ghost = section.get("ghost") if n == len(pages) - 1 else None
            walls.append((section["section"], page, tier, ghost))
    wall_window = total - t - wordmark["dur_sec"]
    # An upstream wall holds a third as many faces, so at one flat rate it
    # would flick past three times as fast as the tier it is meant to
    # outrank. It is weighted instead: the upstream roll is slower per wall,
    # which is the other half of "more distinguished".
    weights = [C.UPSTREAM_WALL_WEIGHT if tier else 1.0
               for _, _, tier, _ in walls]
    unit = wall_window / max(1e-9, sum(weights) or 1.0)
    pages_by_section = {}
    for name, _, _, _ in walls:
        pages_by_section[name] = pages_by_section.get(name, 0) + 1

    # THE BUBBLE DISSOLVES ACROSS THE UPSTREAM RUN, ONCE.
    #
    # Owner: the side bubble reads "So many. Running out of metal." and *"have
    # that fade to 'Deploying CNCF Metal3'"*. A still cannot fade by itself, so
    # the dissolve is spread over the walls it rides: the gag sets up on the
    # first upstream walls, crosses at the middle one, and has landed by the
    # last. It plays once over the whole tier rather than once per wall, which
    # would be the same joke eight times.
    upstream_walls = [i for i, (_, _, tier, _) in enumerate(walls) if tier]
    mix_by_wall = {}
    if upstream_walls:
        last = max(1, len(upstream_walls) - 1)
        for n, i in enumerate(upstream_walls):
            # 0 for the first third, 1 for the last third, and a genuine
            # half-and-half card in between.
            span = n / last
            mix_by_wall[i] = 0.0 if span < 0.34 else (1.0 if span > 0.66 else 0.5)

    idx = {}
    for i, ((name, page, tier, ghost), weight) in enumerate(zip(walls, weights)):
        idx[name] = idx.get(name, 0) + 1
        dur = unit * weight
        item = {"kind": "wall", "t": t, "dur": dur, "section": name,
                "names": page, "page": idx[name], "tier": tier,
                "pages": pages_by_section[name]}
        if ghost:
            item["ghost"] = ghost
        if i in mix_by_wall:
            item["bubble_mix"] = mix_by_wall[i]
        items.append(item)
        t += dur

    items.append({"kind": "wordmark", "t": t, "dur": total - t,
                  "text": wordmark["text"], "sub": wordmark.get("sub")})
    return items, total


def render_cards(items, out_dir):
    # Cleared, not overwritten: the card set changes shape between builds (a
    # dropped placard, a new wall), and a stale `012-cover.png` sitting beside
    # this build's `012-cast.png` is a frame nobody can account for.
    if out_dir.exists():
        for stale in out_dir.glob("*.png"):
            stale.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, item in enumerate(items):
        path = out_dir / f"{i:03d}-{item['kind']}.png"
        if item["kind"] == "role":
            img = C.render_role_card(item["role"], item["names"], index=i)
        elif item["kind"] == "cta":
            img = C.render_cta_card(item["text"], item.get("scale", "large"),
                                    index=i)
        elif item["kind"] == "birthday":
            img = C.render_birthday_card(item["eyebrow"], item["name"],
                                         item["body"], index=i)
        elif item["kind"] == "cast":
            img = C.render_cast_placard(item["person"], item["character"],
                                        card=item.get("card"), login=item.get("login"),
                                        photo=item.get("photo"), index=i)
        elif item["kind"] == "wall":
            img = C.render_name_wall(item["section"], item["names"],
                                     item["page"], item["pages"],
                                     tier=item.get("tier"), index=i,
                                     ghost=item.get("ghost"),
                                     bubble_mix=item.get("bubble_mix"))
        elif item["kind"] == "wordmark":
            img = C.render_wordmark(item["text"], item.get("sub"), index=i)
        elif item["kind"] == "cover":
            img = None
        else:
            raise ValueError(f"unknown card kind: {item['kind']}")
        if img is not None:
            img.convert("RGB").save(path)
        paths.append(path)
    return paths


def cover_frame(image_path, out_path, index=0):
    """The comic cover, letterboxed into the frame on the deck's ink.

    The art is square (9075x9075) and the frame is 16:9, so it fills the height
    and leaves a margin either side -- the same geometry the title cover uses in
    act I, and the reason its identities were never plates.
    """
    from PIL import Image
    art = Image.open(image_path).convert("RGB")
    side = min(art.size)
    art = art.crop(((art.width - side) // 2, (art.height - side) // 2,
                    (art.width + side) // 2, (art.height + side) // 2))
    art = art.resize((C.H, C.H), Image.LANCZOS)
    # The pillars are the month's wallpaper, not black -- the owner's *"use the
    # dinosaur artwork here instead of black"*. The reveal is the one card
    # where the margin is wide enough to see one.
    frame = C.backdrop(index).convert("RGB")
    frame.paste(art, ((C.W - C.H) // 2, 0))
    frame.save(out_path)
    return out_path


def audio_filter(bed, stream=1):
    """One ffmpeg filtergraph: every span of every pass, in order, joined.

    ``stream`` is the INPUT index of the FIRST music file. The cards are input
    0 (the concat demuxer), so the instrumental is input 1 and the album
    version is input 2 -- getting this wrong is a filtergraph that binds to
    nothing rather than a wrong sound.

    A short equal-power crossfade at every seam, so neither the loop's join
    into its own intro nor the hand-over from the instrumental into the vocal
    version clicks. ``acrossfade`` takes two inputs at a time, so the spans are
    folded left to right. Nothing else is applied -- no gain, no normaliser
    (the audio tenet).
    """
    parts, labels = [], []
    n = 0
    for offset, cut in enumerate(bed_passes(bed)):
        for span in cut["segments"]:
            parts.append(f"[{stream + offset}:a]atrim=start={span['start_sec']:.6f}:"
                         f"end={span['end_sec']:.6f},asetpts=PTS-STARTPTS[a{n}]")
            labels.append(f"[a{n}]")
            n += 1
    xf = bed.get("crossfade_sec", 0)
    if xf and len(labels) > 1:
        acc = labels[0]
        for i, nxt in enumerate(labels[1:], start=1):
            out = "[aout]" if i == len(labels) - 1 else f"[x{i}]"
            parts.append(f"{acc}{nxt}acrossfade=d={xf}:c1=tri:c2=tri{out}")
            acc = out
    else:
        parts.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[aout]")
    return ";".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh-contributors", action="store_true",
                    help="re-snapshot the contributor lists and the cast, "
                         "overwriting any hand-edited copy in the manifest (network)")
    ap.add_argument("--refresh-cast", action="store_true",
                    help="re-derive the CAST from vocab/casting.yaml, "
                         "overwriting the owner's curated names (rarely what "
                         "you want -- see build_manifest)")
    ap.add_argument("--fetch-avatars", action="store_true",
                    help="cache a PFP for every login the manifest names (network)")
    ap.add_argument("--plan", action="store_true", help="print the schedule, render nothing")
    ap.add_argument("--cards-only", action="store_true", help="render the PNGs and stop")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--write-manifest", action="store_true",
                    help="save the manifest back (use with --refresh-contributors)")
    args = ap.parse_args(argv)

    manifest = build_manifest(args.refresh_contributors, args.refresh_cast)
    if args.write_manifest:
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {MANIFEST}")

    if args.fetch_avatars:
        fetch_avatars(manifest)

    items, total = schedule(manifest)

    if args.plan:
        for item in items:
            extra = ""
            if item["kind"] == "wall":
                extra = f"  {item['section']} {item['page']}/{item['pages']} ({len(item['names'])} names)"
            elif item["kind"] == "cast":
                extra = f"  {item['person']} as {item['character']}"
            elif item["kind"] == "role":
                extra = f"  {item['role']}: {', '.join(item['names'])}"
            elif item["kind"] == "cover":
                extra = "  *** THE REVEAL ***"
            elif item["kind"] == "cta":
                extra = f"  {item['text']}"
            elif item["kind"] == "birthday":
                extra = f"  {item['eyebrow']} -- {item['name']}"
            print(f"{fmt_tc(item['t']):>9}  {item['dur']:6.2f}s  {item['kind']:<9}{extra}")
        print(f"\ntotal {fmt_tc(total)} ({total:.3f}s), {len(items)} cards")
        names = sum(len(i['names']) for i in items if i['kind'] == 'wall')
        print(f"{names} contributor name(s) on screen")
        return 0

    paths = render_cards(items, CARDS_DIR)
    cover_idx = next(i for i, it in enumerate(items) if it["kind"] == "cover")
    cover_frame(Path(manifest["reveal"]["image"]).expanduser(), paths[cover_idx],
                index=cover_idx)
    print(f"rendered {len(paths)} card(s) -> {CARDS_DIR}")
    if args.cards_only:
        return 0

    ffmpeg = find_ffmpeg()
    medias = []
    for cut in bed_passes(manifest["bed"]):
        media = REPO_ROOT / "media" / cut["media_filename"]
        if not media.exists():
            raise SystemExit(f"bed audio is missing: {media}\n"
                             f"fetch it from {cut['source_url']}")
        medias.append(media)

    # THE TAIL IS DELIBERATELY LONGER THAN THE FILM.
    #
    # The concat demuxer does not deliver a still for exactly the `duration`
    # it is given -- it lands short, and across 38 cards the shortfall came to
    # **4.347 s**: act VIII muxed with 227.303 s of audio over 222.956 s of
    # picture, and the megacut's own join check caught it (`programme is
    # 1447.132s but the plan sums to 1442.681s`) rather than anybody seeing
    # it. Four and a half seconds of the wordmark simply were not there.
    #
    # So the last card is held for a generous extra span and `-t` below cuts
    # both streams to the same frame. Overshooting is free; undershooting is a
    # film that ends before its music does.
    concat = CARDS_DIR / "concat.txt"
    lines = []
    for path, item in zip(paths, items):
        lines.append(f"file '{path}'\nduration {item['dur']:.4f}\n")
    lines.append(f"file '{paths[-1]}'\nduration {CONCAT_TAIL_SEC:.4f}\n")
    lines.append(f"file '{paths[-1]}'\n")
    concat.write_text("".join(lines))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [*ffmpeg, "-nostdin", "-hide_banner", "-v", "error", "-y",
           "-f", "concat", "-safe", "0", "-i", str(concat),
           *[arg for media in medias for arg in ("-i", str(media))],
           "-filter_complex", audio_filter(manifest["bed"], stream=1),
           "-map", "0:v:0", "-map", "[aout]",
           # THE DELIVERY BITSTREAM, from the spec rather than typed: every
           # card is a still, so the rate costs nothing visually, and matching
           # the spec means the megacut joins act VIII by stream copy instead
           # of conforming it at assembly time. `video_encode_args` is what
           # writes the bt709 VUI -- hand-rolled x264 flags left all three
           # colour fields unset and the file came back NONCONFORM.
           *conform.video_encode_args(preset="medium"),
           # `tpad` CLONES the last frame, and that is the only thing that
           # actually made the picture reach the end of the music. The concat
           # demuxer lands short of the durations it is given -- 4.347 s short
           # over 38 cards -- and holding the last card longer in `concat.txt`
           # does NOT fix it, because the shortfall is in the demuxer's output
           # timeline rather than in the list. Padding after the demuxer does.
           # `-t` below then cuts both streams on the same frame.
           "-vf", (f"tpad=stop_mode=clone:stop_duration={CONCAT_TAIL_SEC:.0f},"
                   f"fps={conform.DELIVERY.fps},setsar=1"),
           "-c:a", "flac",
           "-t", f"{total:.3f}",
           str(out_path)]
    subprocess.run(cmd, check=True)
    print(f"wrote {out_path}  ({fmt_tc(total)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

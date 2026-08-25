#!/usr/bin/env python3
"""Build act VIII -- the credits -- from its committed manifest.

The owner's design is issue #51, revised in session on 2026-08-13. Act VIII was
the one act with **no film** (docs/running-order.md), and the last thing between
the programme and the feature.

## The music, and why it is cut this way

The bed starts with Nightwish's *Wish I Had an Angel* instrumental, already
measured into ``music/bed_wish_i_had_an_angel.json``, then hands over to
Nightwish's vocal *Storytime* recording. The owner's instruction: *"design
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

The cover is ``wolves-final.jpg`` -- the finished colour art, swapped in at the
owner's word on 2026-08-23 (see the manifest's ``reveal._art``). Act I's title
cover still renders the greyscale ink ``wolves.jpg``; the two are the same
9075x9075 composition, so only the credits reveal changed. **Removing the cover
from the end of Europa is act VII's job, and act VII has no committed inputs at
all (#152)** -- it is cut in ``~/Videos/wolves-directors-cut``, so this builder
cannot do it and does not pretend to. It is recorded in the manifest and
reported here.

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

from tools import chapter_md  # noqa: E402
from tools import conform  # noqa: E402
from tools import credits as C  # noqa: E402
from tools import peaks  # noqa: E402
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


def merge_contributors(previous, fetched):
    """Union a fresh snapshot with the roster already on record.

    A refresh may only ADD people. Upstream history is not append-only --
    a rebase, a squash, or a default-branch change quietly rewrites who
    GitLab's contributor endpoint reports, and on 2026-08-23 a routine
    refresh of GNOME/gnome-build-meta returned 56 names where the committed
    roster had 58. The two it no longer named, Dan Yeaw and Jamie Murphy,
    had not stopped contributing; the API had stopped counting them.

    Dropping them would be this repo's third rule inverted: a credit roll
    that removes a real person is as much a claim about them as one that
    invents them, and it is the claim nobody made. So a name once earned
    stays, and a disappearance is REPORTED for the owner rather than acted
    on -- un-crediting somebody is `automatable: no`.

    Ordering stays the fetch's own, with survivors appended in their
    previous order, so the walls only ever grow at their tail.
    """
    if not previous:
        return fetched
    was = {s.get("section"): list(s.get("names") or []) for s in previous}
    for section in fetched:
        old = was.get(section["section"])
        if not old:
            continue
        have = {n.lower() for n in section["names"]}
        kept = [n for n in old if n.lower() not in have]
        if kept:
            print(f"note: {section['section']} no longer reports "
                  f"{len(kept)} previously credited name(s); keeping them "
                  f"({', '.join(kept)}). Removing a credit is the owner's "
                  f"call, never a refresh's.", file=sys.stderr)
            section["names"] = section["names"] + kept
    return fetched


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


# The four authored strings a placard reproduces. The `card` PNG is NOT among
# them: it is a splash composite, and act VIII does not set type over one
# ("get rid of those hero splashes they suck"). Copying more of that file than
# the credits print would be a second, staler home for somebody's identity.
IDENTITY_FIELDS = ("label", "class", "name", "title")


def cache_identities(verbose=True):
    """Copy the authored Guardian identities into the render cache, verbatim.

    ``tools/credits`` must not read another checkout -- several agents run
    worktrees against the website -- so the strings are cached beside the cast
    art in gitignored ``renders/cast-cards/identities.json``. Absent website,
    absent cache, and the placard degrades to the person's name: never a
    guessed label, never an invented title.
    """
    try:
        data = json.loads(AUTHORED_CARDS.read_text())
    except (OSError, ValueError) as exc:
        if verbose:
            print(f"note: no authored identities ({exc}); the cast placards "
                  f"run on names alone.", file=sys.stderr)
        return {}
    rows = data.get("characters", []) if isinstance(data, dict) else data
    out = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("slug"):
            continue
        out[row["slug"]] = {k: row[k] for k in IDENTITY_FIELDS
                            if isinstance(row.get(k), str) and row[k].strip()}
    C.CAST_CARD_DIR.mkdir(parents=True, exist_ok=True)
    (C.CAST_CARD_DIR / "identities.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    if verbose:
        print(f"identities: {len(out)} cached from {AUTHORED_CARDS}")
    return out


def vocab_logins():
    """``{credited name: github login}`` for every lead the vocab verifies.

    A login is recorded per BINDING, and one person can hold several -- so the
    map is keyed by the name the credits print, which is the same key the
    manifest's own ``cast_logins`` overlay uses. Only what the vocab states is
    used; a lead with ``github: null`` stays faceless, because a login that
    merely matches a character name is the nimbatus/nimbinatus trap.
    """
    from tools.derive import load_leads

    real, logins = {}, {}
    for entry in load_leads().values():
        person = entry.get("person")
        if not person:
            continue
        name = (entry.get("plate") or {}).get("name")
        if name:
            real.setdefault(person, name)
        if entry.get("github"):
            logins.setdefault(person, entry["github"])
    return {real.get(person) or person: login
            for person, login in logins.items()}


def cast_title(person):
    """The second line of a hero credit: what this person does, in their words.

    Owner: *"for the 'hero' credits use the github titles"*. So the copy is
    either supplied by the owner or lifted verbatim off the person's own GitHub
    profile, and it is recorded in the manifest with `title_source` naming
    which. Nothing here composes a sentence about anybody.

    A title nobody has supplied renders as LOREM IPSUM rather than as a gap --
    the deck's own rule -- and `title_pending` records who it is owed to. The
    Latin is the safeguard: nobody mistakes it for approved English, and it is
    visibly missing copy rather than an invented description of a colleague.
    """
    from tools import placeholder

    title = person.get("title")
    if title:
        return title
    if not person.get("title_pending"):
        return None
    return placeholder.lorem(chars=110, seed=f"cast:{person['person']}")


def avatar_logins(manifest):
    """Every GitHub login act VIII will ask for a face for, in order.

    One definition, because two callers need exactly the same list: the build,
    and ``tools/avatars.py`` when it runs on a CI runner with no idea what a
    placard is.
    """
    logins = []
    for section in manifest.get("contributors", []):
        # A GitLab section carries display NAMES, not logins. Asking
        # github.com for "Harald Sitter.png" is not a missing avatar, it is a
        # category error -- and it would fetch whatever account happened to
        # answer, which is a face beside somebody else's name.
        if section.get("host") and section["host"] != GITHUB:
            continue
        logins.extend(section["names"])
    for key, value in (manifest.get("cast_logins") or {}).items():
        # ``_comment`` is prose about the overlay, not a person. Asking
        # github.com for a paragraph is one wasted request per build, and
        # whatever it returned would be somebody else's face.
        if key.startswith("_") or not isinstance(value, str):
            continue
        logins.append(value)
    for person in manifest.get("cast", []):
        if person.get("login"):
            logins.append(person["login"])
    # The same overlay the schedule applies, so a face the vocab verifies is
    # actually in the cache by the time a placard asks for it.
    logins.extend(vocab_logins().values())
    return list(dict.fromkeys(logins))


def fetch_avatars(manifest, verbose=True, from_actions=False):
    """Cache a face for every login the manifest names.

    The renderer never touches the network (``tools/credits.avatar``), so a
    contributor with no cached PFP silently degrades to a ring. Adding two
    upstream sections added ~200 logins nobody had ever fetched, which would
    have been two walls of empty rings and no error. Missing is still not
    fatal -- this only fills the cache in.

    The fetching itself lives in ``tools/avatars.py``: conditional requests,
    negative caching and backoff, and the same code the Actions workflow runs.
    """
    from tools import avatars

    if from_actions:
        avatars.pull_from_actions(verbose=verbose)
    tally, missing = avatars.fetch(avatar_logins(manifest), verbose=verbose)
    return tally["fetched"], len(missing)


def build_manifest(refresh, refresh_cast=False):
    # THE CARDS' WORDS LIVE IN `chapters/VIII-cta.md` AND `VIII-fixed.md`.
    # Both write into this manifest, so both are put back before it is read:
    # the cries and the birthday card are the act's most-edited copy, and
    # rendering last week's version of them is the one thing a build here
    # must never do.
    for act in ("VIII-cta", "VIII-fixed"):
        for note in chapter_md.sync(act, write=True)[1]:
            print(f"chapter: {note}", file=sys.stderr)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    if refresh or "contributors" not in manifest:
        manifest["contributors"] = merge_contributors(
            manifest.get("contributors"), fetch_contributors())
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
    """The bed's passes in play order: the instrumental loop, then Storytime.

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


def pass_start(bed, index):
    """Where a bed pass begins on the CREDITS clock.

    Same arithmetic as :func:`reveal_at`: every seam before it is an
    ``acrossfade`` overlap, so the clock runs ahead of the summed span lengths
    by one crossfade per join.
    """
    xf = bed.get("crossfade_sec", 0.0)
    spans_before = sum(len(p["segments"]) for p in bed_passes(bed)[:index])
    spans = bed_spans(bed)
    before = sum(s["end_sec"] - s["start_sec"] for s in spans[:spans_before])
    return before - spans_before * xf


def concert(manifest):
    """The performance that becomes the picture, or ``None``.

    A pass carrying ``picture`` is not just a bed: from the moment it starts,
    act VIII stops being a slideshow and the performance IS the frame. The
    block is read here rather than in the renderer so that an act with no
    concert -- every build before 2026-08-24 -- schedules exactly as it did.
    """
    for i, cut in enumerate(bed_passes(manifest["bed"])):
        pic = cut.get("picture")
        if pic:
            start = pass_start(manifest["bed"], i)
            return {**pic, "pass_index": i, "at_sec": start,
                    "trim_from": cut["segments"][0]["start_sec"],
                    # Where the MUSIC stops and the applause takes over, on the
                    # credits clock. The wordmark waits for it: the mark is the
                    # last thing in the film and it is not going to share the
                    # frame with a band still playing.
                    "music_ends_at": start + (pic["music_end_sec"]
                                              - cut["segments"][0]["start_sec"])}
    return None


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
    # The vocab's own `github:` fields join that overlay, keyed by the person
    # rather than by the binding they happen to sit on. Laura's verified login
    # lives on the NIMBATUS binding while her authored identity lives on the
    # Elsie Bray one; before the splash cards came out, the identity carried
    # her face and nobody noticed the login never reached the placard.
    verified = {**vocab_logins(), **verified}
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
                          "card": None, "login": None, "photo": None,
                          "guardian_title": None,
                          "title": None})
        else:
            items.append({"kind": "cast", "t": t, "dur": target,
                          "person": name, "character": person.get("character"),
                          "card": person.get("card"),
                          "login": person.get("login") or verified.get(name),
                          "photo": photos.get(name),
                          # The seal is authored in two places -- the website's
                          # identity card (reached through `card`) and, for the
                          # people the website never carded, the manifest's own
                          # `guardian_title`. Both have to reach the placard or
                          # the `as` row silently disappears for half the cast.
                          "guardian_title": person.get("guardian_title"),
                          "title": cast_title(person)})
        t += target

    wordmark = manifest["wordmark"]
    show = concert(manifest)
    # The upstream sections lead, whatever order they are stored in: the
    # owner's instruction is about the SEQUENCE, so it is enforced here rather
    # than left to how somebody happened to edit the manifest.
    sections = sorted(manifest["contributors"],
                      key=lambda s: 0 if s.get("tier") == "upstream" else 1)

    # WHERE THE FILM STOPS BEING A SLIDESHOW.
    #
    # Everything before the concert keeps the full-frame wall it always had;
    # everything after it moves into the band, because the frame now belongs to
    # the performance. The sections are split between the two by NAME COUNT in
    # proportion to the time each side has, so a login is up for about as long
    # on either side of the seam -- the layout changes, the reading rate does
    # not. A section is never split across the seam: its badge, its ghost and
    # its page numbering stay in one design.
    if show:
        # The mark is the last thing in the film, and it waits for the band to
        # stop playing rather than being given a hand-typed hold. The 77.78 s
        # in the manifest was measured against Storytime's double-bass climax,
        # and that climax left with Storytime.
        wordmark_start = show["music_ends_at"]
        pre_window = max(0.0, show["at_sec"] - t)
        post_window = max(0.0, wordmark_start - max(t, show["at_sec"]))
    else:
        wordmark_start = total - wordmark["dur_sec"]
        pre_window, post_window = max(0.0, wordmark_start - t), 0.0

    # Names are counted at their READING weight, not their raw count, so the
    # seam falls where the two sides read at the same speed. An upstream name
    # is worth 1.25 of a Bluefin one here for the same reason its wall holds
    # 1.25x as long: the owner asked for the upstream tier to be the more
    # distinguished of the two. Counted raw, the seam landed exactly on the
    # tier boundary and inverted that -- every upstream page pre-concert, every
    # Bluefin page in the band, and each side then paced itself, which made the
    # distinguished tier the faster one.
    counted = [(s, len(s["names"]) * (C.UPSTREAM_WALL_WEIGHT
                                      if s.get("tier") == "upstream" else 1.0))
               for s in sections]
    all_names = sum(n for _, n in counted) or 1
    target_pre = all_names * pre_window / max(1e-9, pre_window + post_window)
    banded, seen = set(), 0
    for section, n in counted:
        # A section joins the band once the pre-concert side has had its share.
        # Comparing against the section's MIDPOINT puts the seam wherever it
        # falls closest, instead of always overfilling one side.
        if show and seen + n / 2 > target_pre:
            banded.add(section["section"])
        seen += n

    walls = []
    for section in sections:
        tier = section.get("tier")
        band = section["section"] in banded
        if band:
            per_page = (C.UPSTREAM_PER_BAND if tier == "upstream"
                        else C.NAMES_PER_BAND)
        else:
            per_page = (C.UPSTREAM_PER_WALL if tier == "upstream"
                        else C.NAMES_PER_WALL)
        names = list(section["names"])
        ghost = section.get("ghost")
        if band and ghost:
            # THE GHOST NEEDS A CELL, NOT A CORNER. The full-frame wall can
            # overrun its grid by one and still look deliberate; the band is
            # three rows and there is nothing below them, so the last page is
            # paginated with the ghost already counted. Otherwise the outlined
            # maintainer is silently the name that does not fit.
            marker = object()
            pages = [[n for n in page if n is not marker]
                     for page in C.paginate(names + [marker], per_page)]
        else:
            pages = C.paginate(names, per_page)
        for n, page in enumerate(pages):
            # The ghost maintainer rides the LAST page of its section, so it
            # closes the section rather than interrupting it.
            last = ghost if n == len(pages) - 1 else None
            walls.append((section["section"], page, tier, last, band))

    # An upstream wall holds a third as many faces, so at one flat rate it
    # would flick past three times as fast as the tier it is meant to
    # outrank. It is weighted instead: the upstream roll is slower per wall,
    # which is the other half of "more distinguished".
    weights = [C.UPSTREAM_WALL_WEIGHT if tier else 1.0
               for _, _, tier, _, _ in walls]
    # Each side of the seam fills its OWN window. One shared rate would let a
    # rounding error walk the band layout over the join, which is the one place
    # in this act where a frame is either concert or slideshow and cannot be
    # half of each.
    pre_weight = sum(w for w, (_, _, _, _, b) in zip(weights, walls) if not b)
    post_weight = sum(w for w, (_, _, _, _, b) in zip(weights, walls) if b)
    pre_unit = pre_window / max(1e-9, pre_weight or 1.0)
    post_unit = post_window / max(1e-9, post_weight or 1.0)
    pages_by_section = {}
    for name, _, _, _, _ in walls:
        pages_by_section[name] = pages_by_section.get(name, 0) + 1

    # THE BUBBLE DISSOLVES ACROSS THE UPSTREAM RUN, ONCE.
    #
    # Owner: the side bubble reads "So many. Running out of metal." and *"have
    # that fade to 'Deploying CNCF Metal3'"*. A still cannot fade by itself, so
    # the dissolve is spread over the walls it rides: the gag sets up on the
    # first upstream walls, crosses at the middle one, and has landed by the
    # last. It plays once over the whole tier rather than once per wall, which
    # would be the same joke eight times.
    upstream_walls = [i for i, (_, _, tier, _, _) in enumerate(walls) if tier]
    mix_by_wall = {}
    if upstream_walls:
        last = max(1, len(upstream_walls) - 1)
        for n, i in enumerate(upstream_walls):
            # 0 for the first third, 1 for the last third, and a genuine
            # half-and-half card in between.
            span = n / last
            mix_by_wall[i] = 0.0 if span < 0.34 else (1.0 if span > 0.66 else 0.5)

    idx = {}
    for i, ((name, page, tier, ghost, band), weight) in enumerate(zip(walls, weights)):
        idx[name] = idx.get(name, 0) + 1
        dur = (post_unit if band else pre_unit) * weight
        item = {"kind": "wall", "t": t, "dur": dur, "section": name,
                "names": page, "page": idx[name], "tier": tier,
                "pages": pages_by_section[name],
                "layout": "band" if band else "full"}
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
    # The authored identities are refreshed from the website on every build,
    # so a placard cannot print an identity the author has since rewritten.
    cache_identities(verbose=False)
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
                                        photo=item.get("photo"),
                                        guardian_title=item.get("guardian_title"),
                                        title=item.get("title"), index=i)
        elif item["kind"] == "wall":
            draw = (C.render_name_band if item.get("layout") == "band"
                    else C.render_name_wall)
            img = draw(item["section"], item["names"],
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
    0 (the concat demuxer), so the instrumental is input 1 and Storytime
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
    ap.add_argument("--avatars-from-actions", action="store_true",
                    help="pull CI's avatar artifact first, then fill any gaps "
                         "-- one request instead of five hundred")
    ap.add_argument("--plan", action="store_true", help="print the schedule, render nothing")
    ap.add_argument("--cards-only", action="store_true", help="render the PNGs and stop")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--local", action="store_true",
                    help="encode on THIS host even when the farm cluster is "
                         "reachable (the escape hatch; the encode runs under "
                         "tools.farm.run_capped_local's memory cap)")
    ap.add_argument("--write-manifest", action="store_true",
                    help="save the manifest back (use with --refresh-contributors)")
    args = ap.parse_args(argv)

    manifest = build_manifest(args.refresh_contributors, args.refresh_cast)
    if args.write_manifest:
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {MANIFEST}")

    if args.fetch_avatars or args.avatars_from_actions:
        fetch_avatars(manifest, from_actions=args.avatars_from_actions)

    items, total = schedule(manifest)

    if args.plan:
        for item in items:
            extra = ""
            if item["kind"] == "wall":
                extra = f"  {item['section']} {item['page']}/{item['pages']} ({len(item['names'])} names)"
            elif item["kind"] == "cast":
                extra = f"  {item['person']}"
                if item.get("character"):
                    extra += f" as {item['character']}"
                if item.get("title"):
                    extra += "  [title]"
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

    # `~` must be expanded here, not left to a shell: deliver.py's recorded
    # rebuild route quotes the path, so the tilde reaches ffmpeg literally and
    # the encode dies after nine minutes of card rendering -- having created a
    # directory named `~` in the repo on its way past.
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # THE PERFORMANCE IS COMPOSITED OVER THE CARDS, NOT CUT BESIDE THEM.
    #
    # From the swap the picture is the concert, and the band beneath it is
    # still a card in the same concat list -- so the whole act keeps ONE
    # picture timeline, the scheduler keeps deciding when every screen
    # changes, and the only new thing in the graph is an overlay that switches
    # on at the seam. Cutting the act into two encodes and joining them would
    # have re-encoded the untouched first half for nothing.
    #
    # The clip is 1920x794 and the frame is 1920x1080, so it seats at (0, 0) at
    # NATIVE resolution: no scale filter, no resample, no generation loss. The
    # band cards draw nothing above y=794 because nothing drawn there would
    # survive this overlay.
    #
    # `tpad` CLONES the last frame, and it is the only thing that makes the
    # picture reach the end of the music. The concat demuxer lands short of the
    # durations it is given -- 4.347 s short over 38 cards -- and holding the
    # last card longer in `concat.txt` does NOT fix it, because the shortfall
    # is in the demuxer's output timeline rather than in the list. Padding
    # after the demuxer does. `-t` below then cuts both streams on one frame.
    show = concert(manifest)
    vgraph = (f"[0:v]tpad=stop_mode=clone:stop_duration={CONCAT_TAIL_SEC:.0f},"
              f"fps={conform.DELIVERY.fps},setsar=1[base]")
    inputs, vout = [], "[base]"
    if show:
        source = REPO_ROOT / "media" / show["media_filename"]
        if not source.exists():
            raise SystemExit(f"concert picture is missing: {source}\n"
                             f"fetch it from {show['source_url']}")
        inputs = ["-i", str(source)]
        stream = 1 + len(medias)
        # SEATING THE PERFORMANCE COSTS NOTHING, AND IT MUST NOT.
        #
        # Two obvious ways to start an overlay at 3:47 both blow up. `setpts`
        # with an offset makes overlay's framesync hold the main picture until
        # the overlay stream produces its first frame -- 3:47 of buffered
        # cards, killed by the OOM reaper at 12.9 GB. `tpad` is worse: it
        # pushes its 13,608 pad frames downstream in one burst.
        #
        # A generated source concatenated in front streams instead, because
        # concat pulls from `color` one frame at a time as overlay asks for
        # them. Those frames are never seen -- `enable` keeps the overlay off
        # until the swap -- so their colour is arbitrary and their only job is
        # to exist. `enable` is what does the actual switching, on the card
        # clock, so the seam is exact rather than rounded to the pad length.
        #
        # The trim stays on the OUTPUT side. This source is a DASH webm, and
        # `-ss` on one lands in the wrong place (docs/rendering.md) -- the
        # decode from zero is the price of knowing which frame we started on.
        vgraph += (f";[{stream}:v]trim=start={show['trim_from']:.6f}:"
                   f"end={show['music_end_sec']:.6f},setpts=PTS-STARTPTS,"
                   f"fps={conform.DELIVERY.fps},setsar=1,format=yuv420p[live]"
                   f";color=c=black:s={C.W}x{show['height']}:"
                   f"r={conform.DELIVERY.fps}:d={show['at_sec']:.6f},"
                   f"setsar=1,format=yuv420p[wait]"
                   f";[wait][live]concat=n=2:v=1:a=0[showv]"
                   f";[base][showv]overlay=0:0:eof_action=pass:"
                   f"enable='between(t,{show['at_sec']:.6f},"
                   f"{show['music_ends_at']:.6f})'[vout]")
        vout = "[vout]"

    cmd = [*ffmpeg, "-nostdin", "-hide_banner", "-v", "error", "-y",
           "-f", "concat", "-safe", "0", "-i", str(concat),
           *[arg for media in medias for arg in ("-i", str(media))],
           *inputs,
           "-filter_complex",
           audio_filter(manifest["bed"], stream=1) + ";" + vgraph,
           "-map", vout, "-map", "[aout]",
           # THE DELIVERY BITSTREAM, from the spec rather than typed: every
           # card is a still, so the rate costs nothing visually, and matching
           # the spec means the megacut joins act VIII by stream copy instead
           # of conforming it at assembly time. `video_encode_args` is what
           # writes the bt709 VUI -- hand-rolled x264 flags left all three
           # colour fields unset and the file came back NONCONFORM.
           *conform.video_encode_args(preset="medium"),
           "-c:a", "flac",
           "-t", f"{total:.3f}",
           str(out_path)]
    # THE ENCODE IS REMOTE BY DEFAULT (AGENTS.md: "always prefer remote
    # encoding when available"). A bare local run of this exact argv is what
    # OOM-killed the owner's workstation at 03:08Z on 2026-08-24 -- minutes
    # of x264 over the card inputs with no memory ceiling. The cards are
    # read by the concat LIST's contents, not by argv tokens, so they travel
    # as staged inputs with the list's content rewritten to the pod's paths;
    # the beds and the concert picture are argv `-i` inputs and stage
    # directly (the list itself must NOT be an `inputs` entry -- its pod
    # copy is the rewritten one). A local fallback runs the identical argv
    # under farm.run_capped_local's memory cap, with the reason printed.
    from tools import farm
    farm.run_encode(cmd,
                    inputs=[Path(cmd[i + 1]) for i, tok in enumerate(cmd)
                            if tok == "-i" and cmd[i + 1] != str(concat)],
                    out=out_path, local=args.local,
                    text_files={concat: concat.read_text()},
                    expected_duration=total)
    peaks.trim_master_peak(out_path.resolve())
    print(f"wrote {out_path}  ({fmt_tc(total)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

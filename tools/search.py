#!/usr/bin/env python3
"""Natural-language search over Destiny 2 segment records.

Hybrid retrieval + editorial ranking over the JSON segment records in a
directory (default: examples/).

Retrieval is hybrid:
  * controlled-vocab ENUM FILTERS for hard facets (class, element, faction,
    shot_scale, activity, action, destination, casting) parsed from the query;
  * a CAPTION similarity signal for the long tail. Real deployments should swap
    `caption_sim` for embedding cosine similarity; this prototype uses a
    dependency-free token-overlap stand-in so it runs offline.

Then a standing EDITORIAL RANKING pass orders the survivors: CLEAN footage
first (a shot with a HUD or burned-in text cannot be cut into the story at all),
cinematic tier over gameplay tier, then Guardian-centric and mythic.

Usage:
    python3 tools/search.py "show us Hunters with Arc"
    python3 tools/search.py "wide establishing shot of the Traveler" --top 3
    python3 tools/search.py "Elsie Bray hero shot" --dir examples
    python3 tools/search.py "guardians on a bridge" --include-unclean
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- lexicon: query token -> (facet, value) ---------------------------------
# Multi-word phrases are matched before single tokens.

CLASS = {"hunter": "hunter", "titan": "titan", "warlock": "warlock"}
ELEMENT = {
    "arc": "arc", "solar": "solar", "void": "void", "stasis": "stasis",
    "strand": "strand", "prismatic": "prismatic",
}
FACTION = {
    "cabal": "cabal", "fallen": "fallen_eliksni", "eliksni": "fallen_eliksni",
    "hive": "hive", "vex": "vex", "taken": "taken", "scorn": "scorn",
    "witness": "witness_forces",
}
ACTIVITY = {
    "raid": "raid", "crucible": "crucible_pvp", "pvp": "crucible_pvp",
    "gambit": "gambit", "strike": "strike", "dungeon": "dungeon",
    "patrol": "patrol", "cinematic": "cinematic", "cutscene": "cinematic",
    "trailer": "cinematic", "story": "story_mission", "campaign": "story_mission",
}
DESTINATION = {
    "edz": "edz", "cosmodrome": "cosmodrome", "moon": "moon",
    "dreaming": "dreaming_city", "europa": "europa", "nessus": "nessus",
    "traveler": "the_traveler", "io": "io", "mars": "mars",
    "neomuna": "neptune_neomuna", "neptune": "neptune_neomuna",
    "pale": "the_pale_heart", "tangled": "tangled_shore",
}
ACTION = {
    "combat": "combat", "fighting": "combat", "traversal": "traversal",
    "parkour": "traversal", "running": "traversal", "sprint": "traversal",
    "sprinting": "traversal", "jumping": "traversal", "emote": "emote",
    "dialogue": "dialogue", "talking": "dialogue", "ritual": "ritual",
    "vehicle": "vehicle", "sparrow": "vehicle", "idle": "idle",
}

# Multi-word phrase -> list of (facet, {values}) filter contributions.
# Casting names/handles map onto casting.person / casting.character so a search
# for a cast character (or the person playing them) pulls first-party footage.
PHRASES = {
    "close-up": [("shot_scale", {"CU", "ECU", "MCU"})],
    "close up": [("shot_scale", {"CU", "ECU", "MCU"})],
    "closeup": [("shot_scale", {"CU", "ECU", "MCU"})],
    "wide shot": [("shot_scale", {"ELS", "LS", "MLS"})],
    "wide establishing": [("shot_scale", {"ELS", "LS"}), ("composition", {"establishing"})],
    "establishing shot": [("shot_scale", {"ELS", "LS"}), ("composition", {"establishing"})],
    "establishing": [("composition", {"establishing"})],
    # `crowd` and `group` are controlled-vocab composition values, so they parse
    # as hard facets rather than leaking into the caption signal as loose text.
    "crowd of guardians": [("composition", {"crowd"})],
    "crowd": [("composition", {"crowd"})],
    "fireteam": [("composition", {"group"})],
    "slow-motion": [("pacing", {"slow"})],
    "slow motion": [("pacing", {"slow"})],
    "slowmo": [("pacing", {"slow"})],
    "super": [("action", {"ability_cast"})],
    "supers": [("action", {"ability_cast"})],
    # Tier + casting-tier facets, so a query can ask for the crowd directly.
    "ensemble": [("casting.role", {"ensemble"})],
    "background guardians": [("casting.role", {"ensemble"})],
    "anonymous guardians": [("casting.role", {"ensemble"})],
    "named character": [("casting.role", {"lead"})],
    "lead": [("casting.role", {"lead"})],
    "gameplay": [("footage_tier", {"gameplay"})],
    "cinematic": [("footage_tier", {"cinematic", "mixed"})],
}

# Nicknames the vocabulary cannot supply: a first name, a surname, or a
# shortening people actually type. Everything else about the cast -- every
# character key, every `aka`, every person id and display name -- is derived
# from vocab/casting.yaml below, so a recast reaches search with no edit here.
CAST_SHORTHAND = {
    "elsie": ("casting.character", "elsie_bray"),
    "laura": ("casting.person", "laura_santamaria"),
    "santamaria": ("casting.person", "laura_santamaria"),
    "joanna": ("casting.person", "joanna_lee"),
    "kelsey": ("casting.person", "kelsey_hightower"),
    "hightower": ("casting.person", "kelsey_hightower"),
    "andy": ("casting.person", "clubanderson"),
    "anderson": ("casting.person", "clubanderson"),
    "saint": ("casting.character", "saint_14"),
    "mara": ("casting.character", "mara_sov"),
    "karena": ("casting.person", "karena_angell"),
    "lori": ("casting.person", "lori_lorusso"),
    "lorusso": ("casting.person", "lori_lorusso"),
    "waddington": ("casting.person", "nate_waddington"),
    "ashley": ("casting.person", "ashley_willis"),
    "ikora": ("casting.character", "ikora_rey"),
    "iron lord": ("casting.character", "iron_lord_red_haired"),
    "uldren": ("casting.character", "crow"),
}


def _cast_phrases(leads):
    """Query phrases for every lead binding, straight from the vocabulary.

    ``vocab/casting.yaml`` is the single source of truth for the cast
    (AGENTS.md), and this table used to be a hand-kept second copy of it --
    two tests existed only to assert the two agreed. A character key, each of
    its ``aka`` spellings, and the bound person's id and display name are all
    spellings somebody will type, so all four become phrases; the residue that
    a vocabulary genuinely cannot carry is ``CAST_SHORTHAND`` above.
    """
    out = {}

    def add(phrase, facet, value):
        phrase = str(phrase).replace("_", " ").lower().strip()
        if not phrase:
            return
        out.setdefault(phrase, []).append((facet, {value}))
        # `cayde_6` is typed "cayde-6" at least as often as "cayde 6", and the
        # matcher is literal, so both spellings are registered rather than
        # relying on whichever one the vocab key happens to look like.
        hyphenated = phrase.replace(" ", "-")
        if hyphenated != phrase:
            out.setdefault(hyphenated, []).append((facet, {value}))

    for character, entry in leads.items():
        add(character, "casting.character", character)
        for alias in entry.get("aka") or []:
            add(alias, "casting.character", character)
        person = entry.get("person")
        if person:
            add(person, "casting.person", person)
            if entry.get("display_name"):
                add(entry["display_name"], "casting.person", person)
    for phrase, (facet, value) in CAST_SHORTHAND.items():
        add(phrase, facet, value)
    return out


def _load_cast_phrases():
    """Fold the cast phrases into PHRASES, degrading if the vocab is unreadable.

    An unreadable vocabulary costs the CAST facets and nothing else: the
    vocabulary-driven enum filters and the caption signal still answer, which
    is the repo's standing degrade-never-block posture.
    """
    try:
        from tools.derive import load_leads
    except ImportError:  # running as a script with tools/ on sys.path
        from derive import load_leads
    for phrase, contributions in _cast_phrases(load_leads()).items():
        PHRASES.setdefault(phrase, []).extend(contributions)


_load_cast_phrases()

# single tokens
SINGLE = {
    "wide": [("shot_scale", {"ELS", "LS", "MLS"})],
    "earth": [("destination", {"edz", "cosmodrome"})],  # Earth = its Destiny destinations
}

STOPWORDS = {
    "show", "us", "me", "a", "an", "the", "of", "with", "and", "in", "on",
    "over", "shot", "shots", "clip", "clips", "footage", "give", "get", "find",
    "some", "any", "for", "to", "at", "is", "are", "moment", "moments",
}

MULTI = {"class": CLASS, "element": ELEMENT, "faction": FACTION,
         "activity": ACTIVITY, "destination": DESTINATION, "action": ACTION}

# Saliences the editorial line favours. `crowd_group` is here because the
# anonymous crowd is now the ensemble cast, not background noise.
PREFERRED_SALIENCE = {"guardian_hero", "crowd_group", "environment_establishing",
                      "object_artifact"}
# Facets safe to relax (least-editorial) when a query over-specifies, in order.
RELAX_ORDER = ["destination", "pacing", "camera_movement", "composition", "activity"]
NEVER_RELAX = {"class", "element", "faction", "casting.person", "casting.character",
               "casting.role", "footage_tier"}


def load_segments(directory):
    segs = []
    for path in sorted(Path(directory).glob("*.json")):
        rec = json.loads(path.read_text())
        if "segment_id" in rec:  # skip video-level records
            rec["_path"] = path.name
            segs.append(rec)
    return segs


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())]


def parse_query(query):
    """Return {filters, caption_terms}. filters: facet -> set(values)."""
    q = query.lower()
    filters = {}
    consumed_spans = []

    def add(facet, values):
        filters.setdefault(facet, set()).update(values)

    # phrases first (longest-first so 'elsie bray' wins over 'elsie', etc.)
    # Word-boundary matched, not substring matched: "crowd of guardians" must not
    # trigger the "crow" phrase, and "kat" must not fire inside "katana".
    for phrase in sorted(PHRASES, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", q):
            for facet, values in PHRASES[phrase]:
                add(facet, values)
            consumed_spans.append(phrase)
    for token in sorted(SINGLE, key=len, reverse=True):
        if re.search(rf"\b{re.escape(token)}\b", q):
            for facet, values in SINGLE[token]:
                add(facet, values)
            consumed_spans.append(token)

    tokens = tokenize(q)
    consumed = set()
    for facet, table in MULTI.items():
        for tok in tokens:
            key = tok if tok in table else (tok[:-1] if tok.endswith("s") and tok[:-1] in table else None)
            if key:
                add(facet, {table[key]})
                consumed.add(tok)

    # leftover tokens (minus stopwords / consumed / single chars) -> caption query
    phrase_tokens = set()
    for span in consumed_spans:
        phrase_tokens.update(tokenize(span))
    caption_terms = [
        t for t in tokens
        if t not in STOPWORDS and t not in consumed and t not in phrase_tokens
        and len(t) > 1
    ]
    return {"filters": filters, "caption_terms": caption_terms}


def get_field(seg, facet):
    if facet.startswith("casting."):
        sub = facet.split(".", 1)[1]
        return (seg.get("casting") or {}).get(sub)
    return seg.get(facet)


def matches_filter(seg, facet, wanted):
    val = get_field(seg, facet)
    if val is None:
        return False
    # A constrained lead only matches when the shot satisfies its constraints:
    # a too-tight or face-clear Saladin (usable=false) is NOT returned for a
    # "Saladin"/"jeefy" query, because it does not read as the character.
    if facet in ("casting.person", "casting.character"):
        if (seg.get("casting") or {}).get("usable") is False:
            return False
    if isinstance(val, list):
        return any(v in wanted for v in val)
    return val in wanted


def filter_segments(segments, filters):
    return [s for s in segments if all(matches_filter(s, f, v) for f, v in filters.items())]


def relaxed_filter(segments, filters):
    """Filter; if empty, relax least-editorial facets one at a time. Returns
    (survivors, active_filters, dropped)."""
    active = dict(filters)
    dropped = []
    survivors = filter_segments(segments, active)
    if survivors:
        return survivors, active, dropped
    for facet in RELAX_ORDER:
        if facet in active:
            dropped.append((facet, active.pop(facet)))
            survivors = filter_segments(segments, active)
            if survivors:
                return survivors, active, dropped
    # last resort: drop anything not in NEVER_RELAX
    for facet in list(active):
        if facet not in NEVER_RELAX:
            dropped.append((facet, active.pop(facet)))
            survivors = filter_segments(segments, active)
            if survivors:
                return survivors, active, dropped
    return survivors, active, dropped


def norm_token(token):
    """Crude singular-ization so 'guardians' matches a caption's 'Guardian'.

    A real embedding index makes this unnecessary; while the caption signal is a
    token-overlap stand-in, plural mismatches otherwise lose obviously-correct
    matches.
    """
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def caption_sim(seg, caption_terms):
    """Token-overlap stand-in for embedding similarity (0..1).

    Neutral 0.5 when the query has no caption component. Otherwise a recall-style
    overlap of query terms found in the segment's caption + a few text-ish tags.
    Swap this for real embedding cosine similarity in production.
    """
    if not caption_terms:
        return 0.5
    hay = " ".join([
        seg.get("caption", ""),
        " ".join(n.get("name", "") for n in seg.get("character", []) or []),
        " ".join(seg.get("mood", []) or []),
    ]).lower()
    hay_tokens = {norm_token(t) for t in tokenize(hay)}
    wanted = {norm_token(t) for t in caption_terms}
    hits = sum(1 for t in wanted if t in hay_tokens)
    return hits / len(wanted)


def score_segment(seg, caption_terms, weights=None, caption_weight=1.0):
    """Score one segment. ``caption_weight`` scales how much literal relevance to
    the query beats the standing editorial boosts.

    Search leaves it at 1.0 — a browsing query wants the editorially strongest
    shots in the neighbourhood. Story assembly raises it (tools/story.py), where
    a beat is a specific instruction and the shot that actually depicts it must
    win over a merely well-rated one.
    """
    weights = weights or {}
    reasons = []
    score = caption_sim(seg, caption_terms) * caption_weight
    if caption_terms:
        reasons.append(f"caption {score:.2f}")

    casting = seg.get("casting") or {}
    role = casting.get("role")
    sub = seg.get("substitutability")
    salience = seg.get("subject_salience")
    register = seg.get("register")
    cam = seg.get("camera_movement", []) or []

    # THE dominant signal. An unclean shot carries a HUD, nameplates, burned-in
    # text or a talking head, none of which any edit can remove, so it cannot be
    # cut into the story at all. The penalty is bigger than every other weight
    # combined: unclean results only ever surface when nothing clean matched.
    if seg.get("clean"):
        score += 1.00
        reasons.append("+1.00 clean")
    else:
        score -= 1.00
        reasons.append("-1.00 UNCLEAN (overlays cannot be removed)")

    # Gameplay stays retrievable, just under the cinematics.
    if seg.get("footage_tier") == "cinematic":
        score += 0.20
        reasons.append("+0.20 cinematic tier")
    elif seg.get("footage_tier") == "gameplay":
        score -= 0.15
        reasons.append("-0.15 gameplay tier (coverage)")

    lead_w = weights.get("lead", 1.0)
    lead_usable = role == "lead" and casting.get("usable") is not False
    if lead_usable and lead_w:
        score += 0.40 * lead_w
        who = casting.get("character") or "lead"
        cast_note = "cast" if casting.get("person") else "UNCAST"
        reasons.append(f"+{0.40 * lead_w:.2f} lead: {who} ({cast_note})")
    elif role == "lead" and casting.get("usable") is False:
        failed = ", ".join(casting.get("constraints_failed") or []) or "unusable"
        reasons.append(f"blocked cast ({failed}) — no boost")
    elif role == "ensemble":
        score += 0.20
        reasons.append(f"+0.20 ensemble ({casting.get('slots')} contributor slot(s))")
        # Anonymity is now only a tie-break between ensemble shots — it decides
        # how comfortably a contributor's name sits on that Guardian, and never
        # whether the shot is usable.
        if isinstance(sub, int) and sub >= 3:
            score += 0.10
            reasons.append("+0.10 reads as anyone")

    if salience in PREFERRED_SALIENCE:
        score += 0.20
        reasons.append("+0.20 guardian/environment salience")
    elif salience == "enemy_threat":
        # doc intent: enemies as *subject* are penalized (vocab uses enemy_threat)
        score -= 0.20
        reasons.append("-0.20 enemy-as-subject")

    reg_w = weights.get("register", 1.0)
    if isinstance(register, int):
        if register >= 0:
            score += 0.15 * reg_w
            reasons.append(f"+{0.15 * reg_w:.2f} mythic register")
        elif register <= -2:
            score -= 0.15 * reg_w
            reasons.append(f"-{0.15 * reg_w:.2f} hard-tactical register")

    if "handheld_shaky" in cam:
        score -= 0.25
        reasons.append("-0.25 shaky")

    if seg.get("traversal_hero"):
        score += 0.10
        reasons.append("+0.10 traversal hero")

    return score, reasons


def lead_weight_for(filters):
    """The lead bonus applies only when the query ASKED for a named character.

    Its whole purpose is "when you ask for Elsie, hand me Elsie's footage". A
    query that never mentions a character should not have a lead shot muscle in
    on it just for being a lead, so the bonus switches off.
    """
    return 1.0 if any(f.startswith("casting.") for f in filters) else 0.0


def search(query, segments, top=10, include_unclean=False):
    parsed = parse_query(query)
    filters = parsed["filters"]
    # Unclean shots are excluded outright by default: they are not candidates
    # for an edit, so showing them just pads the result list. --include-unclean
    # keeps them (heavily penalized) for triage — e.g. finding the shots worth
    # re-sourcing at a higher tier.
    pool = segments if include_unclean else [s for s in segments if s.get("clean")]
    survivors, active, dropped = relaxed_filter(pool, filters)

    weights = {"lead": lead_weight_for(filters)}
    scored = []
    for seg in survivors:
        s, reasons = score_segment(seg, parsed["caption_terms"], weights=weights)
        scored.append((s, seg, reasons))
    # tie-break: score, then substitutability, then video order (stable sort)
    scored.sort(key=lambda r: (r[0], r[1].get("substitutability") or 0), reverse=True)

    return {
        "parsed": parsed,
        "active_filters": active,
        "dropped": dropped,
        "results": scored[:top],
        "total": len(scored),
        "pool": len(pool),
        "index": len(segments),
    }


def fmt(query, out):
    lines = []
    parsed = out["parsed"]
    filt = {k: sorted(v) for k, v in out["active_filters"].items()}
    lines.append(f'Query: "{query}"')
    lines.append(f"Parsed filters: {filt or '(none — caption-only)'}")
    if parsed["caption_terms"]:
        lines.append(f"Caption terms: {parsed['caption_terms']}  "
                     f"(matched semantically, not structurally)")
    if out["dropped"]:
        drops = ", ".join(f"{f}={sorted(v)}" for f, v in out["dropped"])
        lines.append(f"Relaxed to find matches — dropped: {drops}")
    lines.append(f"{out['total']} match(es) from a pool of "
                 f"{out['pool']}/{out['index']} segment(s):")
    if not out["results"]:
        lines.append("  (nothing matched; try fewer constraints)")
    for score, seg, reasons in out["results"]:
        vid = seg.get("video_id", "?")
        span = f"{seg.get('start_tc', '?')}–{seg.get('end_tc', '?')}"
        lines.append(f"  [{score:+.2f}] {vid} {span}  {seg['segment_id']}")
        lines.append(f"          why: {', '.join(reasons)}")
        cap = (seg.get("caption") or "").strip()
        if cap:
            lines.append(f"          “{cap[:120]}{'…' if len(cap) > 120 else ''}”")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Search Destiny 2 segment records.")
    ap.add_argument("query", help="natural-language query")
    ap.add_argument("--dir", default=os.path.join(REPO_ROOT, "examples"),
                    help="directory of segment JSON records (default: examples/)")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--include-unclean", action="store_true",
                    help="also search shots with un-removable overlays (HUD, burned-in text)")
    args = ap.parse_args(argv)

    segments = load_segments(args.dir)
    if not segments:
        print(f"No segment records found in {args.dir}", file=sys.stderr)
        return 1
    out = search(args.query, segments, top=args.top, include_unclean=args.include_unclean)
    print(fmt(args.query, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

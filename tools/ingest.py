#!/usr/bin/env python3
"""Ingest Bungie YouTube videos into video-level records.

This is the frame-free, metadata-first half of the pipeline (docs/pipeline.md
§2): from a video's title (+ optional description / playlist) it derives the
video-scoped INHERITED defaults — era, activity, content_type, destination —
that every segment of the video starts from. No frames, no vision model: one
cheap deterministic pass, stamped source='observed', label_source='heuristic'.

Titles are fetched via YouTube's public oEmbed endpoint (no API key). Offline
mode (`--title "..."`) skips the network so ingestion is testable anywhere.

Usage:
    python3 tools/ingest.py https://www.youtube.com/watch?v=VIDEOID
    python3 tools/ingest.py VIDEOID --playlist "Destiny 2 Cinematics"
    python3 tools/ingest.py --id yt_demo --title "Destiny 2: The Final Shape | Launch Trailer"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEOS_DIR = os.path.join(REPO_ROOT, "videos")

RIGHTS_NOTE = (
    "Bungie, Inc. copyrighted footage. Bungie's fan-content policy permits "
    "non-commercial fan creations, including fan music videos, using Bungie "
    "assets. This index stores only metadata and timestamps, not the footage."
)

# --- keyword inference rules (checked against title + description, lowercased) ---
# Order matters where phrases overlap (longer/more specific first).
ERA_RULES = [
    ("the final shape", "the_final_shape"), ("final shape", "the_final_shape"),
    ("lightfall", "lightfall"), ("witch queen", "witch_queen"),
    ("beyond light", "beyond_light"), ("shadowkeep", "shadowkeep"),
    ("forsaken", "forsaken"), ("warmind", "warmind"),
    ("curse of osiris", "curse_of_osiris"), ("rise of iron", "rise_of_iron"),
    ("the taken king", "the_taken_king"), ("taken king", "the_taken_king"),
    ("house of wolves", "house_of_wolves"), ("the dark below", "the_dark_below"),
    ("into the light", "the_final_shape"),  # D2 Y7 free update preceding TFS
]
DESTINATION_RULES = [
    ("the pale heart", "the_pale_heart"), ("pale heart", "the_pale_heart"),
    ("neomuna", "neptune_neomuna"), ("neptune", "neptune_neomuna"),
    ("dreaming city", "dreaming_city"), ("throne world", "savathun_throne_world"),
    ("tangled shore", "tangled_shore"), ("cosmodrome", "cosmodrome"),
    ("europa", "europa"), ("nessus", "nessus"), ("the traveler", "the_traveler"),
    ("traveler", "the_traveler"), ("the moon", "moon"), ("edz", "edz"),
    ("mars", "mars"), ("infinite forest", "mercury"), ("mercury", "mercury"),
    ("io", "io"),
]


def match_kw(keyword, hay):
    """Whole-word keyword match.

    A bare ``in`` test is wrong for the short entries in these tables: ``io``
    matched the middle of "Act**io**n Trailers" and tagged a compilation of
    Earth and Moon footage as ``destination: io``. Word boundaries make a
    two-letter destination as safe as a ten-letter one.
    """
    return re.search(r"\b%s\b" % re.escape(keyword), hay) is not None


def infer_video_defaults(title, description="", playlist=""):
    """Rule-based inference of video-scoped defaults from text metadata.

    Returns {field: {"value": ..., "confidence": float}} for era, activity,
    content_type, and (optionally) destination.
    """
    hay = " ".join([title or "", description or "", playlist or ""]).lower()
    out = {}

    era = next((v for kw, v in ERA_RULES if match_kw(kw, hay)), "unknown")
    out["era"] = {"value": era, "confidence": 0.9 if era != "unknown" else 0.2}

    # content_type + activity
    if "gameplay" in hay:
        out["content_type"] = {"value": "gameplay", "confidence": 0.85}
        out["activity"] = {"value": "unknown", "confidence": 0.4}
    elif any(k in hay for k in ("launch trailer", "reveal trailer", "trailer",
                                "teaser", "announce")):
        out["content_type"] = {"value": "trailer", "confidence": 0.9}
        out["activity"] = {"value": "cinematic", "confidence": 0.8}
    elif any(k in hay for k in ("cinematic", "cutscene", "story", "the movie",
                                "lore", "vidoc", "vidoc:")):
        out["content_type"] = {"value": "cinematic", "confidence": 0.8}
        out["activity"] = {"value": "cinematic", "confidence": 0.75}
    else:
        # Bungie's channel is overwhelmingly promotional/cinematic material.
        out["content_type"] = {"value": "trailer", "confidence": 0.5}
        out["activity"] = {"value": "cinematic", "confidence": 0.5}

    if "raid" in hay:
        out["activity"] = {"value": "raid", "confidence": 0.7}
    elif "dungeon" in hay:
        out["activity"] = {"value": "dungeon", "confidence": 0.7}
    elif "crucible" in hay or "pvp" in hay:
        out["activity"] = {"value": "crucible_pvp", "confidence": 0.7}

    dest = next((v for kw, v in DESTINATION_RULES if match_kw(kw, hay)), None)
    if dest:
        out["destination"] = {"value": dest, "confidence": 0.7}
    return out


def slug(text):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


def parse_video_id(url_or_id):
    """Return (canonical_watch_url, youtube_id) from a URL or bare id."""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        yid = url_or_id
    else:
        q = urllib.parse.urlparse(url_or_id)
        if q.hostname and "youtu.be" in q.hostname:
            yid = q.path.lstrip("/")
        else:
            yid = urllib.parse.parse_qs(q.query).get("v", [""])[0]
    if not yid:
        raise ValueError(f"could not extract a YouTube id from {url_or_id!r}")
    return f"https://www.youtube.com/watch?v={yid}", yid


def fetch_title(watch_url, timeout=10):
    """Fetch a video's title via YouTube oEmbed (no API key). None on failure."""
    api = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": watch_url, "format": "json"})
    try:
        with urllib.request.urlopen(api, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("title")
    except Exception:
        return None


def build_video_record(video_id, watch_url, title, description="", playlist="",
                       youtube_tags=None, rights_note=None):
    defaults = infer_video_defaults(title, description, playlist)
    rec = {
        "video_id": video_id,
        "youtube_url": watch_url,
        "title": title,
        "usage_class": "third_party_copyrighted",
        "source_rights_note": rights_note or RIGHTS_NOTE,
    }
    if description:
        rec["description"] = description
    if playlist:
        rec["playlist"] = playlist
    if youtube_tags:
        rec["youtube_tags"] = list(youtube_tags)

    provenance = {}
    for field, info in defaults.items():
        rec[field] = info["value"]
        provenance[field] = {
            "source": "observed",  # determined from THIS video's own metadata
            "label_source": "heuristic",
            "confidence": info["confidence"],
        }
    rec["provenance"] = provenance
    return rec


def validate_video(rec):
    """Validate against schema/video.schema.json; return list of error messages."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return []  # validation optional if jsonschema missing
    schema = json.load(open(os.path.join(REPO_ROOT, "schema", "video.schema.json")))
    return [e.message for e in Draft202012Validator(schema).iter_errors(rec)]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ingest a Bungie YouTube video.")
    ap.add_argument("url", nargs="?", help="YouTube watch URL or 11-char video id")
    ap.add_argument("--id", help="explicit index video_id (default: derived from title)")
    ap.add_argument("--title", help="offline: provide the title instead of fetching")
    ap.add_argument("--description", default="")
    ap.add_argument("--playlist", default="")
    ap.add_argument("--out", default=VIDEOS_DIR, help="output directory")
    ap.add_argument("--rights-note", default=None,
                    help="override source_rights_note; use when the upload is "
                         "NOT the publisher's own (a fan compilation), so the "
                         "weaker provenance is recorded rather than assumed")
    args = ap.parse_args(argv)

    watch_url, yid = ("", "")
    if args.url:
        watch_url, yid = parse_video_id(args.url)

    title = args.title or (fetch_title(watch_url) if watch_url else None)
    if not title:
        print("Could not obtain a title (offline? use --title). ", file=sys.stderr)
        return 1

    video_id = args.id or f"yt_{slug(title)[:60]}"
    rec = build_video_record(video_id, watch_url or f"https://youtu.be/{yid or 'unknown'}",
                             title, args.description, args.playlist,
                             rights_note=args.rights_note)
    errs = validate_video(rec)
    if errs:
        print("VALIDATION ERRORS:", errs, file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{video_id}.json")
    with open(path, "w") as fh:
        json.dump(rec, fh, indent=2)
        fh.write("\n")
    print(f"Wrote {path}")
    print(f"  title: {title}")
    print(f"  era={rec['era']}  activity={rec['activity']}  "
          f"content_type={rec['content_type']}  destination={rec.get('destination','-')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

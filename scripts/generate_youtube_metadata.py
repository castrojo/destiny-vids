#!/usr/bin/env python3
"""Generate consistent YouTube upload metadata for recent Bluefin videos.

Enforces:
- Required hashtags: #7wolves #k8s #linux on all entries
- Full band and music credits with albums, labels, and official URLs
- Standardized Project Bluefin links (training.projectbluefin.io, projectbluefin.io)
- Standardized tag sets for discoverability
Outputs:
- JSON master: ~/Videos/bluefin-youtube-metadata.json
- Individual copy-paste text cards: ~/Videos/youtube-metadata/<num>-<slug>.txt
"""

import json
from pathlib import Path

VIDEOS_DIR = Path.home() / "Videos"
OUT_DIR = VIDEOS_DIR / "youtube-metadata"
JSON_OUT = VIDEOS_DIR / "bluefin-youtube-metadata.json"

METADATA = [
    {
        "id": "iE51WeDjnRc",
        "slug": "bluefin-and-leonardo",
        "title": "Bluefin and Leonardo (feat. Unleash The Archers)",
        "summary": "Leonardo's tactical armory meets Unleash The Archers' 'Ten Thousand Against One'. One hundred thousand bootc users to one. WE are the overwhelming odds.",
        "music": {
            "song": "Ten Thousand Against One",
            "artist": "Unleash The Archers",
            "album": "Abyss (2020)",
            "label": "Napalm Records",
            "url": "https://www.unleashthearchers.com/",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "bluefin", "unleashthearchers",
            "leonardo", "tenthousandagainstone", "kubernetes", "cloudnative", "opensource"
        ],
    },
    {
        "id": "Nl7wnWeNjb0",
        "slug": "bluefin-and-la-villa-strangiato-1",
        "title": "Bluefin and La Villa Strangiato — Part I",
        "summary": "The Linux Nerd's Dream Band meets cloud native resilience. Part I of the La Villa Strangiato trilogy.",
        "music": {
            "song": "La Villa Strangiato (An Exercise in Self-Indulgence)",
            "artist": "Rush",
            "album": "Hemispheres (1978)",
            "label": "Anthem / Mercury Records",
            "url": "https://www.rush.com/",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "rush", "lavillastrangiato",
            "bluefin", "progrock", "kubernetes", "opensource"
        ],
    },
    {
        "id": "lGlhvo8g480",
        "slug": "bluefin-and-la-villa-strangiato-2",
        "title": "Bluefin and La Villa Strangiato — Part II",
        "summary": "Part II of the La Villa Strangiato trilogy. Continuing the journey of open source infrastructure and cloud native reliability.",
        "music": {
            "song": "La Villa Strangiato",
            "artist": "Rush",
            "album": "Hemispheres (1978)",
            "label": "Anthem / Mercury Records",
            "url": "https://www.rush.com/",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "rush", "lavillastrangiato",
            "bluefin", "progrock", "kubernetes", "opensource"
        ],
    },
    {
        "id": "cagz9UxzMhA",
        "slug": "bluefin-and-la-villa-strangiato-3",
        "title": "Bluefin and La Villa Strangiato — Part III",
        "summary": "Part III: The grand finale of La Villa Strangiato. Technical mastery meets open source craftsmanship.",
        "music": {
            "song": "La Villa Strangiato",
            "artist": "Rush",
            "album": "Hemispheres (1978)",
            "label": "Anthem / Mercury Records",
            "url": "https://www.rush.com/",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "rush", "lavillastrangiato",
            "bluefin", "progrock", "kubernetes", "opensource"
        ],
    },
    {
        "id": "pmpokKEteRQ",
        "slug": "bluefin-and-lakshmi",
        "title": "Bluefin and Lakshmi (feat. Nightwish)",
        "summary": "Lakshmi, Apprentice Maintainer, featured against the symphonic backdrop of Nightwish's epic 'Ghost Love Score'.",
        "music": {
            "song": "Ghost Love Score",
            "artist": "Nightwish",
            "composer": "Tuomas Holopainen",
            "album": "Once (2004)",
            "label": "Nuclear Blast",
            "url": "https://www.nightwish.com/",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "nightwish", "ghostlovescore",
            "lakshmi", "bluefin", "symphonicmetal", "opensource"
        ],
    },
    {
        "id": "M1orbal-pzA",
        "slug": "seven-days-to-the-wolves-credits",
        "title": "Seven Days to the Wolves — Credits",
        "summary": "Don't worry, there is more wolves to come. When it comes to open source, lead with the credits!\n\nAct VIII — the official credits for Seven Days to the Wolves.",
        "music": {
            "song": "Wish I Had an Angel (Instrumental) / Last Ride of the Day (Live at Masters of Rock)",
            "artist": "Nightwish",
            "composer": "Tuomas Holopainen",
            "label": "Nuclear Blast",
            "url": "https://www.nightwish.com/",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "nightwish", "sevendaystothewolves",
            "bluefin", "credits", "kubernetes", "opensource"
        ],
    },
    {
        "id": "948JJTPurn0",
        "slug": "bluefin-and-the-blueberries",
        "title": "Bluefin and the Blueberries",
        "summary": "Keep training. Don't overdo it, one step at a time. The journey from new contributor (Blueberry) to seasoned Guardian.",
        "music": {
            "song": "Destiny 2 Original Soundtrack",
            "artist": "Bungie Music Publishing",
            "composers": "Michael Salvatori, Skye Lewin, C Paul Johnson, Rotem Moav, Pieter Schlosser",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "bluefin", "blueberries",
            "destiny2", "kubernetes", "cloudnative", "opensource"
        ],
    },
    {
        "id": "KDflkF1YPBI",
        "slug": "bluefin-and-the-linux-users",
        "title": "Bluefin and the Linux Users",
        "summary": "Dedicated to everyone who believes desktop Linux should just work. Bluefin brings containerized, image-based reliability to the desktop.",
        "music": {
            "song": "Destiny 2 Original Soundtrack",
            "artist": "Bungie Music Publishing",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "bluefin", "desktoplinux",
            "bootc", "cloudnative", "opensource"
        ],
    },
    {
        "id": "FAknlweDwuE",
        "slug": "bluefin-and-the-patron-of-lost-causes",
        "title": "Bluefin and the Patron of Lost Causes",
        "summary": "Saint-14, the legendary Titan and patron of lost causes, stands for resilience against impossible odds.",
        "music": {
            "song": "Destiny 2: Season of Dawn Original Soundtrack",
            "artist": "Bungie Music Publishing",
            "composers": "Michael Salvatori, Skye Lewin",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "saint14", "bluefin",
            "destiny2", "cloudnative", "opensource"
        ],
    },
    {
        "id": "qmKoBWukQIQ",
        "slug": "bluefin-care-for-a-drink",
        "title": "Bluefin: Care for a Drink?",
        "summary": "Cayde-6 takes a moment at the bar before heading out into the fray. Humble work and the joy of building.",
        "music": {
            "song": "Destiny 2 Original Soundtrack",
            "artist": "Bungie Music Publishing",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "cayde6", "bluefin",
            "destiny2", "cloudnative", "opensource"
        ],
    },
    {
        "id": "c6icX2YnMhQ",
        "slug": "bluefin-and-the-lost-reinforcements",
        "title": "Bluefin and the Lost Reinforcements",
        "summary": "Reinforcements are on their way to help the kids. Unfortunately no one reads emails.",
        "music": {
            "song": "Destiny 2 Original Soundtrack",
            "artist": "Bungie Music Publishing",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "bluefin", "destiny2",
            "cloudnative", "opensource", "kubernetes"
        ],
    },
    {
        "id": "AsHhUT6TTww",
        "slug": "bluefin-and-the-hive",
        "title": "Bluefin and the Hive",
        "summary": "Connecting human contributors and autonomous agents into the hosted KubeStellar Hive.",
        "music": {
            "song": "Destiny 2 Original Soundtrack",
            "artist": "Bungie Music Publishing",
        },
        "extra_links": [
            ("KubeStellar Hive", "https://hive.kubestellar.io")
        ],
        "tags": [
            "7wolves", "k8s", "linux", "kubestellar", "hive",
            "bluefin", "aiagents", "opensource"
        ],
    },
    {
        "id": "TwLhuUzxDWo",
        "slug": "bluefin-and-the-witness",
        "title": "Bluefin and the Witness",
        "summary": "Facing the monolithic architecture. The Final Shape meets the distributed power of cloud native open source.",
        "music": {
            "song": "Destiny 2: The Final Shape Original Soundtrack",
            "artist": "Bungie Music Publishing",
            "composers": "Michael Salvatori, Skye Lewin",
        },
        "extra_links": [],
        "tags": [
            "7wolves", "k8s", "linux", "witness", "destiny2",
            "thefinalshape", "bluefin", "opensource"
        ],
    },
    {
        "id": "WlNSRqFTdWA",
        "slug": "bluefin-the-law-of-the-jungle",
        "title": "Bluefin: The Law of the Jungle",
        "summary": "Homework: Learn what this organizational body does: https://github.com/cncf/toc/\n\nThree of them will star in the movie. Add up how many years of Open Source Experience is in that group.\n\nThey are the people I work for. This is important for you to know because the first episodes show what true mastery of Open Source is.\n\nWe need YOU, to be the next [REDACTED].\n\nThe song's lyrics symbolize fighting against overwhelming odds. One hundred thousand bootc users to one. WE, are the overwhelming odds.",
        "music": {
            "song": "Ten Thousand Against One",
            "artist": "Unleash The Archers",
            "album": "Abyss (2020)",
            "label": "Napalm Records",
            "url": "https://www.unleashthearchers.com/",
        },
        "extra_links": [
            ("Director's Cut Soundtrack", "https://www.youtube.com/watch?v=sMMboHJJFPI"),
            ("CNCF TOC", "https://github.com/cncf/toc/")
        ],
        "tags": [
            "7wolves", "k8s", "linux", "cncf", "toc",
            "bluefin", "unleashthearchers", "opensource"
        ],
    },
    {
        "id": "nXO3RdRjovc",
        "slug": "bluefin-welcome-to-the-jungle",
        "title": "Bluefin: Welcome to the Jungle",
        "summary": "ALL GUARDIANS: https://training.projectbluefin.io\n\nFIND LOCAL EVENTS: https://www.cncf.io/kcds/\n\nGet involved in your local KCD. We are looking for Wolves.",
        "music": {
            "song": "Welcome to the Jungle (Orchestral / In-Engine Arrangement)",
            "artist": "Project Bluefin Ensemble / Bungie Destiny",
        },
        "extra_links": [
            ("Find Local KCDs", "https://www.cncf.io/kcds/")
        ],
        "tags": [
            "7wolves", "k8s", "linux", "cncf", "kcd",
            "bluefin", "cloudnative", "opensource"
        ],
    },
]


def format_description(item: dict) -> str:
    lines = []
    # Summary
    lines.append(item["summary"].strip())
    lines.append("")

    # Band / Music Credits
    music = item.get("music", {})
    lines.append("--- Music & Band Credits ---")
    if "song" in music:
        lines.append(f"Track: {music['song']}")
    if "artist" in music:
        lines.append(f"Artist: {music['artist']}")
    if "composer" in music or "composers" in music:
        c = music.get("composer") or music.get("composers")
        lines.append(f"Composer: {c}")
    if "album" in music:
        lines.append(f"Album: {music['album']}")
    if "label" in music:
        lines.append(f"Record Label: {music['label']}")
    if "url" in music:
        lines.append(f"Official Band Link: {music['url']}")
    lines.append("")

    # Extra links
    if item.get("extra_links"):
        for label, url in item["extra_links"]:
            lines.append(f"{label}: {url}")
        lines.append("")

    # Project Bluefin
    lines.append("--- Project Bluefin ---")
    lines.append("Free Linux Foundation Training: https://training.projectbluefin.io")
    lines.append("Operating System: https://projectbluefin.io")
    lines.append("Discourse Community: https://universal-blue.discourse.group/")
    lines.append("")

    # Attribution Note
    lines.append("Destiny 2 footage courtesy of Bungie, used under Bungie Fan Content Policy.")
    lines.append("")

    # Hashtags (Always include #7wolves #k8s #linux)
    lines.append("#7wolves #k8s #linux #bluefin #opensource")

    return "\n".join(lines)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    master = {}

    for idx, item in enumerate(METADATA, 1):
        desc = format_description(item)
        entry = {
            "id": item["id"],
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "slug": item["slug"],
            "title": item["title"],
            "description": desc,
            "tags": item["tags"],
        }
        master[item["id"]] = entry

        # Save individual copy-paste file
        txt_path = OUT_DIR / f"{idx:02d}-{item['slug']}.txt"
        card_content = (
            f"=== YouTube Video ID: {item['id']} ===\n"
            f"URL: https://www.youtube.com/watch?v={item['id']}\n\n"
            f"--- TITLE ---\n{item['title']}\n\n"
            f"--- DESCRIPTION ---\n{desc}\n\n"
            f"--- TAGS ---\n{', '.join(item['tags'])}\n"
        )
        txt_path.write_text(card_content, encoding="utf-8")
        print(f"Generated {txt_path.name}")

    JSON_OUT.write_text(json.dumps(master, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote full master metadata to {JSON_OUT}")


if __name__ == "__main__":
    main()

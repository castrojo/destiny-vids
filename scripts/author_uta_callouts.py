#!/usr/bin/env python3
"""Author the RAFI weapon/component callouts into the edit record.

Run once to seed composition/callouts. The wording is transcribed from
`Cha Design_RAFI.jpg`; every record carries the sheet crop it was read from,
so the transcription can be re-checked against the picture rather than
trusted. Corrections the owner authorized ("correct the spelling and copyedit
too", 2026-09-05) are recorded as explicit from/to edits, never applied
silently -- `build_uta_art_video.validate_callout_copy` rebuilds each rendered
string from its verbatim one and fails if they disagree.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EDIT = REPO / "stories" / "uta-general-dark-army.json"
SHEET = "Cha Design_RAFI.jpg"


def crop(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


# Crops are the rectangles actually cut from the 6447x9410 sheet and read
# during review; the evidence images are in the Hero work directory.
CALLOUTS = {
    "spear": {
        "copy": {
            "label": "DIY MAGICAL/ HI TECH SPEAR",
            "label_render": "DIY MAGICAL / HI-TECH SPEAR",
            "subtitle": "TUNGSTEN ALLOY",
            "subtitle_render": "TUNGSTEN ALLOY",
            "description": (
                "A SPEAR THAT CAN BE SHORTENED OR LENGTHENED FOR TACTICAL "
                "PURPOSES, WHETHER FOR CLOSE-QUARTERS INDIVIDUAL COMBAT OR "
                "CAVALRY COMBAT."
            ),
            "description_render": (
                "A SPEAR THAT CAN BE SHORTENED OR LENGTHENED FOR TACTICAL "
                "PURPOSES, WHETHER FOR CLOSE-QUARTERS INDIVIDUAL COMBAT OR "
                "CAVALRY COMBAT."
            ),
            "copyedits": [
                {
                    "from": "MAGICAL/ HI TECH",
                    "to": "MAGICAL / HI-TECH",
                    "reason": (
                        "punctuation and spelling: space the solidus and "
                        "hyphenate the compound modifier 'hi-tech'"
                    ),
                }
            ],
        },
        "source": {
            "sheet": SHEET,
            "crop": crop(5093, 5646, 1031, 1129),
            "evidence": "review/xcrop-spear.png",
        },
        "label_box": {"x": 2100, "y": 375, "width": 1612, "height": 806},
        "leader_anchor": {"x": 3480, "y": 780},
        "font_size": 96,
        "description_font_size": 54,
        "usage": "dedicated-hold",
        "min_hold_seconds": 4.5,
        "art_asset": "RAFI_WEAPONS_04",
    },
    "hippershell_exox": {
        "copy": {
            "label": "DIY HIPPERSHELL EXO-X",
            "label_render": "DIY HIPPERSHELL EXO-X",
            "subtitle": "TUNGSTEN ALLOY",
            "subtitle_render": "TUNGSTEN ALLOY",
            "description": "EXTRA LOAD CAPACITY: 47 KG",
            "description_render": "EXTRA LOAD CAPACITY: 47 KG",
            "copyedits": [],
        },
        "source": {
            "sheet": SHEET,
            "crop": crop(4383, 8045, 1741, 706),
            "evidence": "review/xcrop-exox_br.png",
        },
        "label_box": {"x": 300, "y": 300, "width": 1400, "height": 520},
        "leader_anchor": {"x": 1760, "y": 560},
        "font_size": 88,
        "description_font_size": 52,
        "usage": "accompany-art",
    },
    "double_kopis": {
        "copy": {
            "label": "DAMASCUS STEEL DOUBLE KOPIS",
            "label_render": "DAMASCUS STEEL DOUBLE KOPIS",
            "subtitle": "WITH BONE & SKIN ORNAMENT",
            "subtitle_render": "WITH BONE & SKIN ORNAMENT",
            "description": (
                "THIS IS AN ANCIENT GREEK SWORD WITH A SINGLE-EDGED, CURVED "
                "BLADE THAT IS HIGHLY EFFECTIVE FOR SLASHING AND THRUSTING."
            ),
            "description_render": (
                "THIS IS AN ANCIENT GREEK SWORD WITH A SINGLE-EDGED, CURVED "
                "BLADE THAT IS HIGHLY EFFECTIVE FOR SLASHING AND THRUSTING."
            ),
            "copyedits": [],
        },
        "source": {
            "sheet": SHEET,
            "crop": crop(644, 8045, 2257, 1176),
            "evidence": "review/xcrop-kopis.png",
        },
        "label_box": {"x": 260, "y": 340, "width": 1560, "height": 760},
        "leader_anchor": {"x": 1880, "y": 720},
        "font_size": 88,
        "description_font_size": 52,
        "usage": "dedicated-hold",
        "min_hold_seconds": 4.0,
    },
    "composite_bow": {
        "copy": {
            "label": "COMPOSITE BOW",
            "label_render": "COMPOSITE BOW",
            "subtitle": "TITANIUM ALLOY",
            "subtitle_render": "TITANIUM ALLOY",
            "copyedits": [],
        },
        "source": {
            "sheet": SHEET,
            "crop": crop(902, 3058, 2708, 1270),
            "evidence": "review/xcrop-bow_top.png",
        },
        "label_box": {"x": 320, "y": 320, "width": 1200, "height": 320},
        "leader_anchor": {"x": 1580, "y": 480},
        "font_size": 88,
        "usage": "accompany-art",
    },
    "ai_control_module": {
        "copy": {
            "label": "AI CONTROL MODULE",
            "label_render": "AI CONTROL MODULE",
            "subtitle": "WITH GPS",
            "subtitle_render": "WITH GPS",
            "copyedits": [],
        },
        "source": {
            "sheet": SHEET,
            "crop": crop(902, 3058, 2708, 1270),
            "evidence": "review/xcrop-bow_top.png",
        },
        "label_box": {"x": 320, "y": 320, "width": 1200, "height": 320},
        "leader_anchor": {"x": 1580, "y": 480},
        "font_size": 88,
        "usage": "accompany-art",
    },
    "bead_catcher": {
        "copy": {
            "label": "MAGNET BEADS CATCHER",
            "label_render": "MAGNETIC BEAD CATCHER",
            "copyedits": [
                {
                    "from": "MAGNET BEADS",
                    "to": "MAGNETIC BEAD",
                    "reason": (
                        "grammar: the adjectival form is 'magnetic', and an "
                        "attributive noun takes the singular ('bead catcher')"
                    ),
                }
            ],
        },
        "source": {
            "sheet": SHEET,
            "crop": crop(3739, 5457, 1612, 1130),
            "evidence": "review/xcrop-beads.png",
        },
        "label_box": {"x": 300, "y": 300, "width": 1200, "height": 260},
        "leader_anchor": {"x": 1560, "y": 430},
        "font_size": 84,
        "usage": "accompany-art",
    },
    "bomb_10mm": {
        "copy": {
            "label": "10MM BOM",
            "label_render": "10MM BOMB",
            "copyedits": [
                {
                    "from": "BOM",
                    "to": "BOMB",
                    "reason": "spelling: 'bomb' is misspelled on the sheet",
                }
            ],
        },
        "source": {
            "sheet": SHEET,
            "crop": crop(3739, 5457, 1612, 1130),
            "evidence": "review/xcrop-beads.png",
        },
        "label_box": {"x": 300, "y": 300, "width": 900, "height": 220},
        "leader_anchor": {"x": 1260, "y": 410},
        "font_size": 84,
        "usage": "accompany-art",
    },
    "magazine_20": {
        "copy": {
            "label": "20 ROUND MAGAZINE",
            "label_render": "20-ROUND MAGAZINE",
            "copyedits": [
                {
                    "from": "20 ROUND",
                    "to": "20-ROUND",
                    "reason": (
                        "punctuation: hyphenate the compound modifier before "
                        "the noun"
                    ),
                }
            ],
        },
        "source": {
            "sheet": SHEET,
            "crop": crop(3739, 5457, 1612, 1130),
            "evidence": "review/xcrop-beads.png",
        },
        "label_box": {"x": 300, "y": 300, "width": 1000, "height": 220},
        "leader_anchor": {"x": 1360, "y": 410},
        "font_size": 84,
        "usage": "accompany-art",
    },
}


def main():
    edit = json.loads(EDIT.read_text())
    edit["composition"]["callouts"] = CALLOUTS
    EDIT.write_text(json.dumps(edit, indent=2) + "\n")
    print(f"wrote {len(CALLOUTS)} callouts to {EDIT}")


if __name__ == "__main__":
    main()

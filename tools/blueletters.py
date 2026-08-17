#!/usr/bin/env python3
"""The blue letters, in one place.

The owner's rule, and its history:

* 2026-08-13, on act VIII: *"fill in every b with bluefin blue"*.
* Then, because a wall of GitHub logins is a wall of names and somebody with a
  B was getting blue twice while somebody with only an F got none, F was
  allowed to stand in **instead of** B for a string that had no B.
* **2026-08-15, and this is the rule now:** *"Ensure every b is blue, and every
  f is blue in all the dialogue except the chat bubbles and nameplates."*

So it is **both letters, always**, and the either/or is gone. The owner also
drew the boundary, which is the part that cannot be inferred from the letters:

===========================  ==========================================
Gets blue b's and f's        Does not
===========================  ==========================================
The main title               **Chat bubbles** -- dialogue pills
Act cards and interstitials  **Nameplates** -- and their whole family:
The call-to-action cards       companion cards, miniboss cards, anything
The choice screen              that exists to print a real person's name
Credit walls and role cards
===========================  ==========================================

A nameplate is excluded for a reason worth keeping written down: it prints a
real person's name, and recolouring letters inside somebody's name is a change
to how that person is credited. The owner excluded them, and the exclusion is
enforced here by *what calls this module* rather than by a flag, so a new
renderer has to opt in deliberately.

This lives in its own module because the rule used to exist only inside
``tools/credits.py`` while three other surfaces drew type of their own. One
rule, one definition -- the same reason ``vocab/`` owns every enum.
"""

from __future__ import annotations

# Both cases. Burned copy in this film is a mix of display capitals and
# authored lower-case logins, and matching only capitals would leave the effect
# invisible in exactly the places that are mostly lower-case.
BLUE = "BbFf"


def blue_letters(text=None):
    """The characters of ``text`` that are set in the film's blue.

    ``text`` is accepted and ignored: the rule used to depend on the whole
    string (F only when there was no B) and no longer does. The parameter stays
    so callers read the same, and so the signature still says "this is a
    property of the copy" rather than a global.
    """
    return BLUE


def draw(drawer, xy, text, font, fill, accent, tracking_em=0.0):
    """Draw ``text`` glyph by glyph with its blue letters picked out.

    Glyph by glyph because Pillow has no letter-spacing -- the same reason
    ``plate.py`` hand-places all of its tracked type.

    Returns the x it finished at, so a caller can continue a run.
    """
    x, y = xy
    extra = tracking_em * font.size
    for ch in text:
        drawer.text((x, y), ch, font=font, fill=accent if ch in BLUE else fill)
        x += drawer.textlength(ch, font=font) + extra
    return x

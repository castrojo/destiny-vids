"""Jungle-family YouTube thumbnails: a source frame in, a credited card out.

The layout follows the approved "Law of the Jungle" reference: the source
hero frame fills the canvas, a BLUEFIN eyebrow and a blue rule sit centered
at the top, and the outlined white title rides directly beneath them, above
the vertical midpoint so the central subject stays visible.
"""

import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFile, ImageOps

from tools import credits

SIZE = (1920, 1080)
BYTE_CAP = 2_000_000

# Progressive+optimized JPEG encoding of a noisy frame can fill libjpeg's
# output buffer; a large MAXBLOCK keeps Pillow from dying with "broken data
# stream when writing image file" on exactly the frames the quality retry
# exists for.
ImageFile.MAXBLOCK = max(ImageFile.MAXBLOCK, 4 * SIZE[0] * SIZE[1])

BLUE = credits.ACCENT                     # the film's blue, #93c5fd
WHITE = (255, 255, 255, 255)
NEAR_BLACK = (12, 12, 16, 255)
_SHADOW = (0, 0, 0, 160)

_EYEBROW_SIZE = 76
_TITLE_MAX = 116
_TITLE_FLOOR = 72
_RULE_WIDTH = 360
_RULE_HEIGHT = 6
_STROKE = 8

_MAX_LINE_WIDTH = 1680
# A detected crop shorter than a quarter of the frame is a dark scene or a
# bright sliver, not a letterbox; the original frame is kept.
_MIN_CONTENT_DIVISOR = 4
# The whole title block must clear the frame's vertical midpoint.
_MIDPOINT = SIZE[1] // 2

_PREFIX = re.compile(r"\s*bluefin\b", re.IGNORECASE)


def extract_source_frame(ffmpeg, source, source_at, out, runner=subprocess.run):
    """Pull exactly one frame at ``source_at`` seconds from ``source``."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    runner([
        *ffmpeg,
        "-v", "error",
        "-y",
        "-ss", f"{source_at:.3f}",
        "-i", str(Path(source).resolve()),
        "-frames:v", "1",
        str(out.resolve()),
    ], check=True)
    return out


def split_bluefin_title(title):
    """Split a display title into the BLUEFIN eyebrow and the uppercased rest.

    Only the leading "Bluefin", an optional immediately following colon, and
    surrounding space are stripped; later colons are title text and stay.
    """
    match = _PREFIX.match(title)
    if not match:
        raise ValueError(f"title must start with 'Bluefin': {title!r}")
    rest = title[match.end():].lstrip()
    if rest.startswith(":"):
        rest = rest[1:].lstrip()
    return "BLUEFIN", rest.upper()


def _crop_letterbox(image, threshold=16):
    """Crop uniform near-black bars from the top and bottom, if present."""
    gray = image.convert("L")
    w, h = gray.size

    def black_row(y):
        return gray.crop((0, y, w, y + 1)).getextrema()[1] <= threshold

    top = 0
    while top < h // 2 and black_row(top):
        top += 1
    bottom = h
    while bottom > h // 2 and black_row(bottom - 1):
        bottom -= 1
    if top >= 8 and bottom <= h - 8 and bottom - top >= h // _MIN_CONTENT_DIVISOR:
        return image.crop((0, top, w, bottom))
    return image


def _split_candidates(words):
    """Every one- or two-line layout of ``words``, in order, keeping all words."""
    yield [" ".join(words)]
    for cut in range(1, len(words)):
        yield [" ".join(words[:cut]), " ".join(words[cut:])]


def _ink_width(draw, line, font):
    """The width of the pixels actually drawn, not the advance width.

    ``textlength`` ignores side bearings, so a line that "fits" by advance
    can still paint outside the title margins; the ink bbox cannot.
    """
    box = draw.textbbox((0, 0), line, font=font)
    return box[2] - box[0]


def _best_layout(draw, words, font):
    """The preferred layout at ``font``: one line only when it actually fits
    the width, otherwise the most balanced two-line split (least maximum line
    width). Every word is kept; nothing ever reverts to an overflowing line."""
    def width(lines):
        return max(_ink_width(draw, line, font) for line in lines)

    candidates = list(_split_candidates(words))
    one_line = candidates[0]
    if width(one_line) <= _MAX_LINE_WIDTH:
        return one_line
    two_line = candidates[1:]
    if not two_line:  # a single word has no split
        return one_line
    return min(two_line, key=width)


def _fit_title(draw, text):
    """The largest size from 116 down to the 72 floor whose best one/two-line
    split fits the width; the floor's best split otherwise. Never more than
    two lines, and every word is kept."""
    words = text.split()
    for size in range(_TITLE_MAX, _TITLE_FLOOR - 1, -4):
        font = credits._font("black", size)
        lines = _best_layout(draw, words, font)
        if all(
            _ink_width(draw, line, font) <= _MAX_LINE_WIDTH for line in lines
        ):
            return font, lines
    font = credits._font("black", _TITLE_FLOOR)
    return font, _best_layout(draw, words, font)


def _stroked(draw, xy, text, font, fill):
    x, y = xy
    draw.text((x + 3, y + 5), text, font=font, fill=_SHADOW, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm",
              stroke_width=_STROKE, stroke_fill=NEAR_BLACK)


def render_jungle_thumbnail(source, title):
    """Compose the approved Jungle card over the fitted source frame."""
    frame = ImageOps.fit(
        _crop_letterbox(source.convert("RGB")), SIZE, Image.Resampling.LANCZOS
    )
    eyebrow, rest = split_bluefin_title(title)

    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cx = SIZE[0] // 2

    eyebrow_font = credits._font("black", _EYEBROW_SIZE)
    eyebrow_top = 24
    _stroked(draw, (cx, eyebrow_top + _EYEBROW_SIZE // 2), eyebrow,
             eyebrow_font, BLUE)
    eyebrow_box = draw.textbbox(
        (cx, eyebrow_top + _EYEBROW_SIZE // 2), eyebrow,
        font=eyebrow_font, anchor="mm", stroke_width=_STROKE,
    )

    rule_top = eyebrow_box[3] + 10
    draw.rectangle(
        (cx - _RULE_WIDTH // 2, rule_top,
         cx + _RULE_WIDTH // 2, rule_top + _RULE_HEIGHT),
        fill=BLUE,
    )

    title_font, lines = _fit_title(draw, rest)
    line_height = round(title_font.size * 1.12)
    block_top = rule_top + _RULE_HEIGHT + 22
    block_height = line_height * len(lines)
    if block_top + block_height > _MIDPOINT:
        block_top = _MIDPOINT - block_height
    for index, line in enumerate(lines):
        # Center the ink itself, not the anchor: advance-width centering lets
        # side bearings push glyph pixels past the title margins.
        box = draw.textbbox((0, 0), line, font=title_font,
                            stroke_width=_STROKE)
        x = cx - (box[0] + box[2]) // 2
        y = (block_top + line_height * index + line_height // 2
             - (box[1] + box[3]) // 2)
        draw.text((x + 3, y + 5), line, font=title_font, fill=_SHADOW)
        draw.text((x, y), line, font=title_font, fill=WHITE,
                  stroke_width=_STROKE, stroke_fill=NEAR_BLACK)

    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def save_jungle_thumbnail(source, title, out):
    """Render and save under the 2 MB YouTube cap, stepping quality down."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    image = render_jungle_thumbnail(Image.open(source), title)
    for quality in (95, 92, 89, 86):
        image.save(
            out,
            "JPEG",
            quality=quality,
            subsampling=0,
            optimize=True,
            progressive=True,
        )
        if out.stat().st_size <= BYTE_CAP:
            return out
    raise ValueError(
        f"thumbnail exceeds the {BYTE_CAP}-byte cap even at quality 86: {out}"
    )

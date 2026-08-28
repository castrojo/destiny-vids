"""Jungle-family YouTube thumbnails: a source frame in, a credited card out.

The layout follows the approved "Law of the Jungle" reference: the source
hero frame fills the canvas, a BLUEFIN eyebrow and a blue rule sit centered
at the top, and the outlined white title rides directly beneath them, above
the vertical midpoint so the central subject stays visible.
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from tools import credits

SIZE = (1920, 1080)
BYTE_CAP = 2_000_000

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
_MAX_TITLE_LINES = 2
# The whole title block must clear the frame's vertical midpoint.
_MIDPOINT = SIZE[1] // 2


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
    """Split a display title into the BLUEFIN eyebrow and the uppercased rest."""
    head, colon, tail = title.partition(":")
    words = head.split()
    if not words or words[0].lower() != "bluefin":
        raise ValueError(f"title must start with 'Bluefin': {title!r}")
    rest = tail.strip() if colon else " ".join(words[1:])
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
    if top >= 8 and bottom <= h - 8:
        return image.crop((0, top, w, bottom))
    return image


def _wrap(draw, text, font, max_width):
    """Greedy word wrap; an over-long word stands on its own line."""
    lines = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and draw.textlength(trial, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _fit_title(draw, text):
    """The largest size from 116 down to the 72 floor that wraps in 2 lines."""
    for size in range(_TITLE_MAX, _TITLE_FLOOR - 1, -4):
        font = credits._font("black", size)
        lines = _wrap(draw, text, font, _MAX_LINE_WIDTH)
        if len(lines) <= _MAX_TITLE_LINES:
            return font, lines
    font = credits._font("black", _TITLE_FLOOR)
    return font, _wrap(draw, text, font, _MAX_LINE_WIDTH)


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
        _stroked(draw, (cx, block_top + line_height * index + line_height // 2),
                 line, title_font, WHITE)

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

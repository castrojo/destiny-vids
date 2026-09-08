#!/usr/bin/env python3
"""Build YouTube thumbnail candidates for Bluefin: Not Your Monster.

Follows the approved Children of the Dark Army specification:
- 1920x1080 JPEG (< 2 MB)
- Full-bleed band scene with letterbox cropped
- Centered Bluefin wordmark top
- Inter-Bold title block with blue accent rule
- Keyed character art seated with glow & shadow on the right
"""

import sys
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WORK = Path("/var/home/jorge/Videos/Wolves/Hero/.work-not-your-monster")
HERO_ROOT = Path("/var/home/jorge/Videos/Wolves/Hero")
THUMBS_DIR = HERO_ROOT / "thumbnails"
THUMBS_DIR.mkdir(parents=True, exist_ok=True)
ART_DIR = Path("/var/home/jorge/Videos/Wolves/Hero/.work-uta-general/assets")

W, H = 1920, 1080
MAX = 2_000_000
BLUE = (66, 133, 244)

INTER_B = "/tmp/Inter-Bold.ttf"
INTER_R = "/tmp/Inter-Regular.ttf"
INTER_L = "/tmp/Inter-Light.ttf"
f = lambda p, s: ImageFont.truetype(p, s)


def crop_zoom(img: Image.Image, cx: int, cy: int, w: int) -> Image.Image:
    h = round(w * H / W)
    x = max(0, min(img.width - w, round(cx - w / 2)))
    y = max(0, min(img.height - h, round(cy - h / 2)))
    return img.crop((x, y, x + w, y + h)).resize((W, H), Image.LANCZOS)


def art(name: str, height: int) -> Image.Image:
    im = Image.open(ART_DIR / name).convert("RGBA")
    im = im.crop(im.getchannel("A").getbbox())
    return im.resize((round(im.width * height / im.height), height), Image.LANCZOS)


def glow(fig: Image.Image, colour=BLUE, radius=40, strength=170) -> Image.Image:
    a = fig.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda v: min(255, int(v * strength / 100)))
    g = Image.new("RGBA", fig.size, colour + (0,))
    g.putalpha(a)
    return g


def shadow(fig: Image.Image, radius=26, opacity=150, offset=(14, 18)):
    a = fig.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda v: int(v * opacity / 255))
    s = Image.new("RGBA", fig.size, (0, 0, 0, 0))
    s.putalpha(a)
    return s, offset


def seat(base: Image.Image, fig: Image.Image, x: int, y: int, bloom=True):
    if bloom:
        base.alpha_composite(glow(fig), (x, y))
    s, (dx, dy) = shadow(fig)
    base.alpha_composite(s, (x + dx, y + dy))
    base.alpha_composite(fig, (x, y))


def scrim(base: Image.Image, box: tuple[int, int, int, int], direction="up", strength=225):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    g = Image.new("L", (1, h))
    for i in range(h):
        t = i / max(1, h - 1)
        v = t if direction == "down" else 1 - t
        g.putpixel((0, i), int(strength * (v ** 1.35)))
    g = g.resize((w, h))
    layer = Image.new("RGBA", (w, h), (6, 8, 14, 0))
    layer.putalpha(g)
    base.alpha_composite(layer, (x0, y0))


def tracked(d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill, track=0, shadow_px=3):
    x, y = xy
    for ch in text:
        if shadow_px:
            d.text((x + shadow_px, y + shadow_px), ch, font=font, fill=(0, 0, 0, 170))
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + track
    return x - xy[0]


def tracked_w(d: ImageDraw.ImageDraw, text: str, font, track=0):
    return sum(d.textlength(c, font=font) + track for c in text) - track


def title_block(base: Image.Image, x: int, y: int, eyebrow: str, title: str, size=84, eb=28, track_eb=6):
    d = ImageDraw.Draw(base)
    fe, ft = f(INTER_L, eb), f(INTER_B, size)
    we = tracked_w(d, eyebrow, fe, track_eb)
    wt = d.textlength(title, font=ft)
    rule = x - 24
    d.rectangle([rule - 4, y - 6, rule, y + size + eb + 26], fill=BLUE)
    tracked(d, (x, y), eyebrow, fe, BLUE + (255,), track_eb, 2)
    tracked(d, (x, y + eb + 18), title, ft, (255, 255, 255, 255), 0, 4)


def wordmark(px: int) -> Image.Image:
    w = Image.open(WORK / "assets/bluefin-wordmark.png").convert("RGBA")
    w = w.crop(w.getchannel("A").getbbox())
    return w.resize((px, round(w.height * px / w.width)), Image.LANCZOS)


def save(img: Image.Image, dest: Path):
    rgb = img.convert("RGB")
    for q in range(95, 59, -1):
        b = BytesIO()
        rgb.save(b, "JPEG", quality=q, subsampling=0, optimize=True, progressive=True)
        if len(b.getvalue()) < MAX:
            dest.write_bytes(b.getvalue())
            print(f"Saved {dest.name}: {len(b.getvalue()) // 1024} KiB (quality {q})")
            return
    raise RuntimeError(f"Could not save {dest} under {MAX} bytes")


EYE = "THE DARK ELEMENT"
TITLE = "BLUEFIN: NOT YOUR MONSTER"


def build_variant(scout_name: str, char_name: str, out_name: str, ch_h=880, char_pad_right=50):
    src = Image.open(WORK / scout_name).convert("RGBA")
    # Letterbox crop: crop black borders if any
    g = src.convert("L")
    bbox = g.point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        src = src.crop(bbox)
    base = crop_zoom(src, src.width // 2, src.height // 2, src.width)
    
    # Scrim for top wordmark and bottom title
    scrim(base, (0, 0, W, 260), "up", 200)
    scrim(base, (0, H - 420, W, H), "down", 240)
    
    # Seat character
    fig = art(char_name, ch_h)
    seat(base, fig, W - fig.width - char_pad_right, H - ch_h)
    
    # Top wordmark
    w = wordmark(320)
    base.alpha_composite(w, ((W - w.width) // 2, 44))
    
    # Bottom title block
    title_block(base, 78, H - 330, EYE, TITLE, size=82)
    
    out_file = THUMBS_DIR / out_name
    save(base, out_file)
    return out_file


def main():
    print("Building thumbnail variants...")
    # Option A: Lead singer (scout-300s.jpg) + Spear General (RAFI_03.png)
    tA = build_variant("scout-300s.jpg", "RAFI_03.png", "not-your-monster-A.jpg", ch_h=900)
    
    # Option B: Awesome Guitar Riff (scout-240s.jpg) + Sword Hunter (RAFI_01.png)
    tB = build_variant("scout-240s.jpg", "RAFI_01.png", "not-your-monster-B.jpg", ch_h=860)
    
    # Option C: Lead Singer wide/climax (scout-200s.jpg) + Lakshmi with glowing shard (CHA_LAKSHMI_01.png)
    tC = build_variant("scout-200s.jpg", "CHA_LAKSHMI_01.png", "not-your-monster-C.jpg", ch_h=880)
    
    # Promote primary (Option A: Lead singer) to Hero root
    primary = HERO_ROOT / "BLUEFIN_NOT_YOUR_MONSTER-thumbnail.jpg"
    primary.write_bytes(tA.read_bytes())
    print(f"Promoted primary thumbnail to {primary}")


if __name__ == "__main__":
    main()

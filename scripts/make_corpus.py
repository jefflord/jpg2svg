"""Generate a small synthetic test corpus for preset tuning (PRD 25.4).

Run from the repository root:

    python scripts/make_corpus.py [--out corpus]

Creates one image per preset family so ``raster2svg preset compare`` can be
run on inputs that actually exercise each recipe. Everything is drawn with
Pillow (no other dependencies) and is deterministic (fixed seed).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512


def _base(fill: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (SIZE, SIZE), fill)


def draw_line_art() -> Image.Image:
    """Black ink strokes on white paper (sketch-like, uneven weight)."""
    img = _base((250, 249, 244))
    d = ImageDraw.Draw(img)
    d.ellipse((80, 120, 430, 420), outline=(20, 20, 25), width=7)
    d.line((80, 270, 430, 270), fill=(20, 20, 25), width=5)
    d.arc((150, 160, 360, 330), start=20, end=160, fill=(30, 30, 35), width=9)
    d.line((120, 380, 400, 380), fill=(40, 40, 45), width=3)
    for i, x in enumerate(range(140, 390, 25)):
        d.line((x, 388, x, 398 + (i % 3) * 6), fill=(35, 35, 40), width=3)
    return img


def draw_photo_like() -> Image.Image:
    """Soft sky gradient with a sun disc and rolling hills (photo stand-in)."""
    img = Image.new("RGB", (SIZE, SIZE))
    d = ImageDraw.Draw(img)
    top = (92, 140, 190)
    bottom = (226, 236, 244)
    for y in range(SIZE):
        t = y / SIZE
        color = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom, strict=True))
        d.line((0, y, SIZE, y), fill=color)
    d.ellipse((330, 60, 450, 180), fill=(250, 220, 120))
    d.ellipse((0, 300, SIZE, 560), fill=(96, 148, 92))
    d.ellipse((120, 340, 560, 640), fill=(74, 122, 78))
    # A little "lens noise" so denoise/blur has something to do.
    for i in range(600):
        x = (i * 97 + 13) % SIZE
        y = (i * 61 + 29) % SIZE
        shade = 200 + (i % 50)
        d.point((x, y), fill=(shade, shade + 4, shade + 8))
    return img


def draw_poster_like() -> Image.Image:
    """Bold flat bands and shapes: screen-print style, few colors."""
    img = _base((244, 238, 224))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, SIZE, 200), fill=(198, 58, 44))
    d.rectangle((0, 200, SIZE, 330), fill=(232, 168, 48))
    d.rectangle((0, 330, SIZE, SIZE), fill=(34, 78, 110))
    d.ellipse((160, 90, 350, 280), fill=(244, 238, 224))
    d.polygon([(200, 420), (310, 360), (360, 470), (250, 470)], fill=(232, 168, 48))
    return img


def draw_clip_art() -> Image.Image:
    """A simple cartoon bird: flat fills, thick outline, minimal detail."""
    img = _base((232, 244, 248))
    d = ImageDraw.Draw(img)
    d.ellipse((120, 140, 380, 400), fill=(240, 150, 50), outline=(30, 30, 30), width=8)
    d.polygon(
        [(300, 240), (440, 200), (380, 320)], fill=(250, 200, 70), outline=(30, 30, 30), width=6
    )
    d.ellipse((160, 120, 260, 220), fill=(240, 150, 50), outline=(30, 30, 30), width=8)
    d.ellipse((185, 150, 235, 195), fill=(250, 248, 240), outline=(30, 30, 30), width=4)
    d.ellipse((200, 162, 222, 184), fill=(25, 25, 25))
    d.line((250, 250, 330, 260), fill=(30, 30, 30), width=6)
    d.line((200, 400, 190, 460), fill=(30, 30, 30), width=7)
    d.line((300, 400, 310, 460), fill=(30, 30, 30), width=7)
    d.line((185, 460, 210, 460), fill=(30, 30, 30), width=7)
    d.line((305, 460, 330, 460), fill=(30, 30, 30), width=7)
    return img


def draw_logo() -> Image.Image:
    """A clean geometric badge: two rings, a diamond, precise curves."""
    img = _base((250, 250, 252))
    d = ImageDraw.Draw(img)
    d.ellipse((106, 106, 406, 406), outline=(24, 52, 92), width=18)
    d.ellipse((156, 156, 356, 356), outline=(198, 58, 44), width=10)
    d.polygon([(256, 196), (316, 256), (256, 316), (196, 256)], fill=(34, 78, 110))
    d.rectangle((96, 248, 150, 264), fill=(24, 52, 92))
    d.rectangle((362, 248, 416, 264), fill=(24, 52, 92))
    return img


def draw_pixel_art() -> Image.Image:
    """A blocky 16x16 sprite scaled up (hard edges, no anti-aliasing)."""
    grid: list[list[int]] = [
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
        [0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0],
        [0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0],
        [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    palette = {0: (250, 250, 252), 1: (80, 160, 60)}
    cell = SIZE // 18
    img = Image.new("RGB", (cell * 18, cell * 16))
    d = ImageDraw.Draw(img)
    for y, row in enumerate(grid):
        for x, bit in enumerate(row):
            d.rectangle(
                (x * cell, y * cell, (x + 1) * cell - 1, (y + 1) * cell - 1),
                fill=palette[bit],
            )
    return img


def draw_silhouette() -> Image.Image:
    """A solid dark bird shape on a light sky (single-color subject)."""
    img = _base((226, 236, 242))
    d = ImageDraw.Draw(img)
    body = (35, 40, 48)
    d.ellipse((140, 180, 380, 380), fill=body)
    d.ellipse((250, 120, 380, 240), fill=body)
    d.polygon([(330, 170), (450, 130), (390, 250)], fill=body)
    d.polygon([(150, 300), (60, 420), (260, 380)], fill=body)
    d.polygon([(230, 250), (270, 200), (310, 260), (250, 290)], fill=(240, 200, 60))
    d.ellipse((290, 150, 320, 180), fill=(20, 22, 26))
    return img


def draw_comic() -> Image.Image:
    """Flat cel color, bold black outlines, high contrast (comic panel)."""
    img = _base((252, 250, 244))
    d = ImageDraw.Draw(img)
    d.ellipse((150, 110, 360, 320), fill=(250, 220, 190), outline=(15, 15, 15), width=9)
    d.ellipse((205, 175, 245, 225), fill=(252, 252, 252), outline=(15, 15, 15), width=4)
    d.ellipse((280, 175, 320, 225), fill=(252, 252, 252), outline=(15, 15, 15), width=4)
    d.ellipse((216, 190, 236, 210), fill=(15, 15, 15))
    d.ellipse((292, 190, 312, 210), fill=(15, 15, 15))
    d.arc((230, 240, 300, 290), start=20, end=160, fill=(15, 15, 15), width=6)
    d.rectangle((90, 330, 420, 470), fill=(52, 100, 160), outline=(15, 15, 15), width=8)
    d.line((120, 360, 390, 360), fill=(15, 15, 15), width=5)
    d.ellipse((420, 60, 500, 140), fill=(244, 240, 120), outline=(15, 15, 15), width=6)
    return img


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("corpus"), help="Output directory.")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    builders = {
        "line-art": draw_line_art,
        "photo": draw_photo_like,
        "poster": draw_poster_like,
        "clip-art": draw_clip_art,
        "logo": draw_logo,
        "pixel-art": draw_pixel_art,
        "silhouette": draw_silhouette,
        "comic": draw_comic,
    }
    for name, builder in builders.items():
        path = args.out / f"{name}.png"
        builder().save(path)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()

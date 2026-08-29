"""Generate the small test fixture images (run once; commit the results)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "fixtures"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Color photo-like fixture: gradient background with a few shapes.
    width, height = 96, 96
    img = Image.new("RGB", (width, height))
    for y in range(height):
        for x in range(width):
            img.putpixel((x, y), (int(255 * x / width), int(255 * y / height), 128))
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 20, 70, 70], fill=(240, 240, 240))
    draw.rectangle([10, 60, 40, 80], fill=(30, 90, 200))
    img.save(OUT / "fixture_photo.jpg", quality=90)

    # Flat logo with transparency.
    logo = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    logo_draw = ImageDraw.Draw(logo)
    logo_draw.rectangle([8, 8, 56, 56], fill=(27, 27, 27, 255))
    logo_draw.rectangle([16, 16, 48, 48], fill=(224, 192, 136, 255))
    logo.save(OUT / "fixture_logo.png")

    # Black and white line art.
    bw = Image.new("L", (48, 48), 255)
    bw_draw = ImageDraw.Draw(bw)
    bw_draw.line([0, 24, 48, 24], fill=0, width=2)
    bw_draw.ellipse([8, 8, 40, 40], outline=0, width=2)
    bw.save(OUT / "fixture_bw.png")

    # Corrupt file with a valid extension.
    (OUT / "fixture_corrupt.jpg").write_bytes(b"\xff\xd8\xdb\x00not a real jpeg")

    # JPEG with an EXIF orientation tag (rotate 90 CW = tag 6), 96x48 stored,
    # 48x96 after auto-orientation.
    oriented = Image.new("RGB", (96, 48))
    o_draw = ImageDraw.Draw(oriented)
    o_draw.rectangle([8, 8, 88, 40], fill=(200, 40, 40))
    exif = oriented.getexif()
    exif[0x0112] = 6
    oriented.save(OUT / "fixture_oriented.jpg", quality=90, exif=exif)

    print(f"fixtures written to {OUT}")


if __name__ == "__main__":
    main()

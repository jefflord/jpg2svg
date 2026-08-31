"""Quick structural sanity check of the preset-test SVGs (dev helper)."""

import pathlib
import re

ROOT = pathlib.Path("preset-test")


def stats(path: pathlib.Path) -> tuple[int, int, int, int]:
    text = path.read_text(encoding="utf-8")
    paths = re.findall(r"<path\b", text)
    curves = lines = 0
    for d in re.findall(r'd="([^"]+)"', text):
        letters = re.sub(r"[\d\s,.\-+eE]+", "", d)
        curves += sum(1 for ch in letters if ch in "CQcquSTst")
        lines += sum(1 for ch in letters if ch in "LHVlhvZz")
    fills = set(re.findall(r'fill="([^"]+)"', text))
    return len(paths), curves, lines, len(fills)


def main() -> None:
    for image_dir in sorted(ROOT.iterdir()):
        if not image_dir.is_dir():
            continue
        print(f"== {image_dir.name}")
        for svg in sorted(image_dir.glob("*.svg")):
            print(f"  {svg.stem:28s} paths/curves/lines/fills = {stats(svg)}")


if __name__ == "__main__":
    main()

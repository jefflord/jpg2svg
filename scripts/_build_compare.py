"""Build a side-by-side HTML comparison of two SVG files (dev helper)."""

import sys
from pathlib import Path

normal = Path("preset-test/normal-lineart.svg").read_text(encoding="utf-8")
inv = Path("preset-test/inv-lineart.svg").read_text(encoding="utf-8")

page = (
    "<html><body style='margin:0;display:flex'>"
    "<div style='width:50%;background:#fff;padding:20px'>"
    "<h3>normal input (black on white)</h3>" + normal + "</div>"
    "<div style='width:50%;background:#fff;padding:20px'>"
    "<h3>inverted input (white on black)</h3>" + inv + "</div>"
    "</body></html>"
)
Path("preset-test/compare.html").write_text(page, encoding="utf-8")
print("written", len(sys.argv))

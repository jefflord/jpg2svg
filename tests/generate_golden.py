"""Regenerate the committed golden SVG files (PRD section 25.3).

Run from the repository root:

    python tests/generate_golden.py

This re-traces each pinned golden case and overwrites the expected SVG under
``tests/golden/``. Commit the results after reviewing the diff.
"""

from __future__ import annotations

from golden_cases import GOLDEN_CASES, GOLDEN_DIR

from raster2svg import Converter
from raster2svg.config.models import OutputConfig
from raster2svg.engines.vtracer_engine import VTracerEngine


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    # Goldens are pinned to the Python 0.6 engine (see test_golden.py); the
    # 1.0 CLI build is still in alpha. Once 1.0 is final, use Converter()
    # and commit the regenerated output.
    converter = Converter(engine=VTracerEngine())
    for case in GOLDEN_CASES:
        converter.convert(
            case.fixture,
            case.golden_path,
            config=case.config,
            output=OutputConfig(overwrite=True),
        )
        size = case.golden_path.stat().st_size
        print(f"wrote {case.golden_path} ({size} bytes)  [{case.name}]")


if __name__ == "__main__":
    main()

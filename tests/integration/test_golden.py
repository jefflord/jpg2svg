"""Golden, structural, and semantic SVG output tests (PRD section 25.3).

Three tiers of coverage, from strictest to most engine-tolerant:

* **exact**    - normalized output is byte-identical to the committed golden
                 file. Catches any geometry change. Tied to the engine version.
* **structural** - element tree shape, canvas size, and per-path attributes are
                 well-formed. Tolerates coordinate re-serialization.
* **semantic**   - the image's meaning survives (expected colors present, sane
                 path counts). Tolerates engine and config-serialization drift.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest
from golden_cases import GOLDEN_CASES

from raster2svg import Converter
from raster2svg.config.models import OutputConfig

_XML_DECL = re.compile(r"<\?xml\b[^>]*\?>", re.DOTALL)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_WS_BETWEEN_TAGS = re.compile(r">\s+<")

CASE_IDS = [case.name for case in GOLDEN_CASES]
BY_NAME = {case.name: case for case in GOLDEN_CASES}


def normalize_svg(text: str) -> str:
    """Strip harmless serialization metadata (PRD 25.3).

    Removes the XML declaration, generator comments, and whitespace between
    elements. Geometry (path data, fills, transforms) is preserved.
    """
    text = _XML_DECL.sub("", text)
    text = _COMMENT.sub("", text)
    text = _WS_BETWEEN_TAGS.sub("><", text)
    return text.strip()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _paths(root: ET.Element) -> list[ET.Element]:
    return [el for el in root.iter() if _local(el.tag) == "path"]


def parse_hex(value: str | None) -> tuple[int, int, int] | None:
    """Parse a ``#RRGGBB`` fill into an (r, g, b) tuple, else None."""
    if value is None:
        return None
    value = value.strip()
    if value.startswith("#") and len(value) == 7:
        try:
            return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
        except ValueError:
            return None
    return None


def _near(rgb: tuple[int, int, int], target: tuple[int, int, int], tol: int) -> bool:
    """True if each channel of ``rgb`` is within ``tol`` of ``target``."""
    return all(abs(actual - expected) <= tol for actual, expected in zip(rgb, target, strict=True))


@pytest.fixture(scope="module")
def generated_svgs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Convert every golden case once and cache the raw SVG text by name."""
    out_dir = tmp_path_factory.mktemp("golden")
    cache: dict[str, str] = {}
    converter = Converter()
    for case in GOLDEN_CASES:
        target = out_dir / f"{case.name}.svg"
        converter.convert(
            case.fixture,
            target,
            config=case.config,
            output=OutputConfig(overwrite=True),
        )
        cache[case.name] = target.read_text(encoding="utf-8")
    return cache


@pytest.mark.parametrize("name", CASE_IDS)
def test_golden_exact(name: str, generated_svgs: dict[str, str]) -> None:
    case = BY_NAME[name]
    if not case.golden_path.is_file():
        pytest.fail(
            f"Golden file missing: {case.golden_path}. "
            "Regenerate with: python tests/generate_golden.py"
        )
    expected = normalize_svg(case.golden_path.read_text(encoding="utf-8"))
    actual = normalize_svg(generated_svgs[name])
    assert actual == expected, (
        f"SVG for '{name}' diverged from the golden file. "
        "Regenerate with: python tests/generate_golden.py (and review the diff)."
    )


@pytest.mark.parametrize("name", CASE_IDS)
def test_golden_structural(name: str, generated_svgs: dict[str, str]) -> None:
    case = BY_NAME[name]
    root = ET.fromstring(generated_svgs[name])
    assert _local(root.tag) == "svg"

    width = root.get("width")
    height = root.get("height")
    assert width is not None and height is not None, "svg must declare width and height"
    assert int(width) == case.width, "canvas width mismatch"
    assert int(height) == case.height, "canvas height mismatch"

    paths = _paths(root)
    assert paths, "expected at least one <path> element"
    fills = [path.get("fill") for path in paths]
    assert all(fill is not None for fill in fills), "every <path> must carry a fill"
    assert all(parse_hex(fill) is not None for fill in fills), (
        "fills must be #RRGGBB, got: " + ", ".join(str(fill) for fill in fills)
    )


@pytest.mark.parametrize("name", CASE_IDS)
def test_golden_semantic(name: str, generated_svgs: dict[str, str]) -> None:
    root = ET.fromstring(generated_svgs[name])
    paths = _paths(root)
    n_paths = len(paths)
    raw_fills = [parse_hex(path.get("fill")) for path in paths]
    fills: list[tuple[int, int, int]] = [rgb for rgb in raw_fills if rgb is not None]

    if name in {"photo_spline", "photo_pixel", "photo_polygon"}:
        # The fixture has a blue rectangle and a near-white ellipse on a gradient.
        assert any(b > 150 and r < 120 and g < 120 for r, g, b in fills), "missing blue shape"
        assert any(r > 200 and g > 200 and b > 200 for r, g, b in fills), "missing near-white shape"
        assert 5 <= n_paths <= 200, f"unexpected path count {n_paths}"
    elif name == "bw_spline":
        # Black line art on a white background: few paths, only near-black/white.
        assert 1 <= n_paths <= 5, f"unexpected path count {n_paths}"
        for r, g, b in fills:
            near_black = max(r, g, b) < 60
            near_white = min(r, g, b) > 195
            assert near_black or near_white, f"bw fill not near-black/white: #{r:02X}{g:02X}{b:02X}"
    elif name == "logo_spline":
        # Two flat shapes (dark + tan) on a transparent background.
        assert 1 <= n_paths <= 6, f"unexpected path count {n_paths}"
        assert any(_near(rgb, (0x1B, 0x1B, 0x1B), 24) for rgb in fills), "missing dark logo color"
        assert any(_near(rgb, (0xE0, 0xC0, 0x88), 24) for rgb in fills), "missing tan logo color"
    else:  # pragma: no cover - guarded by the case table
        pytest.fail(f"no semantic expectations defined for '{name}'")

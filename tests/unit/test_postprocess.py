"""Unit tests for the SVG post-processing pipeline (PRD section 14)."""

from __future__ import annotations

from raster2svg.config.models import PostprocessConfig
from raster2svg.postprocess.svg import apply_postprocessing, invert_svg

#: The dark background rect that inversion inserts as the first ``<svg>`` child.
BACKGROUND = '<rect width="100%" height="100%" fill="#000000"/>'


def test_invert_inverts_six_digit_hex_fill() -> None:
    svg = '<svg><path fill="#000000" d="M0 0"/></svg>'
    out = invert_svg(svg)
    assert 'fill="#ffffff"' in out
    # The only remaining black fill is the inserted background.
    assert 'fill="#000000"' not in out.replace(BACKGROUND, "")


def test_invert_inverts_three_digit_hex_fill() -> None:
    # #abc -> #aabbcc; complement is #554433.
    svg = '<svg><rect fill="#abc" width="1" height="1"/></svg>'
    out = invert_svg(svg)
    assert 'fill="#554433"' in out


def test_invert_forces_unfilled_shapes_to_white() -> None:
    svg = '<svg><path d="M0 0 L10 10"/></svg>'
    out = invert_svg(svg)
    # The shape (not the inserted background) picks up a white fill.
    assert '<path fill="#ffffff" d="M0 0 L10 10"/>' in out


def test_invert_preserves_fill_none() -> None:
    svg = '<svg><path fill="none" d="M0 0"/></svg>'
    out = invert_svg(svg)
    assert 'fill="none"' in out
    # No spurious white fill is added next to the "none" fill.
    assert 'fill="none" d=' in out


def test_invert_leaves_non_hex_fill_untouched() -> None:
    svg = '<svg><path fill="red" d="M0 0"/></svg>'
    out = invert_svg(svg)
    assert 'fill="red"' in out


def test_invert_inserts_black_background_as_first_child() -> None:
    svg = '<svg viewBox="0 0 1 1"><path d="M0 0"/></svg>'
    out = invert_svg(svg)
    assert out.startswith(f'<svg viewBox="0 0 1 1">{BACKGROUND}')


def test_invert_background_is_not_itself_inverted() -> None:
    out = invert_svg('<svg><path fill="#ffffff" d="M0 0"/></svg>')
    # The original white fill became black, but the background stays black.
    assert 'fill="#000000"' in out
    # Exactly one background rect was inserted.
    assert out.count(BACKGROUND) == 1


def test_invert_multi_shape_mixed_fills() -> None:
    svg = '<svg><path fill="#ff0000" d="A"/><path d="B"/></svg>'
    out = invert_svg(svg)
    assert 'fill="#00ffff"' in out  # red inverted
    assert '<path fill="#ffffff" d="B"/>' in out  # unfilled -> white


def test_apply_postprocessing_default_is_a_noop() -> None:
    svg = '<svg><path fill="#000000" d="M0 0"/></svg>'
    result = apply_postprocessing(svg, PostprocessConfig())
    assert result.applied == ()
    assert result.svg == svg


def test_apply_postprocessing_invert_applies_and_reports() -> None:
    svg = '<svg><path fill="#000000" d="M0 0"/></svg>'
    result = apply_postprocessing(svg, PostprocessConfig(invert=True))
    assert result.applied == ("invert",)
    assert result.svg != svg


def test_apply_postprocessing_is_idempotent_on_applied_list() -> None:
    # Running a no-op config any number of times changes nothing.
    svg = '<svg><path fill="#123456" d="M0 0"/></svg>'
    assert apply_postprocessing(svg, PostprocessConfig()).svg == svg
    assert apply_postprocessing(svg, PostprocessConfig(invert=False)).svg == svg

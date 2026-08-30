"""Unit tests for the in-memory web upload session store."""

from __future__ import annotations

import io
import time

import pytest
from PIL import Image

from raster2svg.core.errors import InputError
from raster2svg.web.session import SessionStore


def _jpeg_bytes(
    width: int = 32,
    height: int = 32,
    color: tuple[int, int, int] = (200, 30, 30),
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def test_add_returns_a_usable_record() -> None:
    store = SessionStore()
    data = _jpeg_bytes()
    record = store.add(data, "test.jpg")
    assert record.image_bytes == data
    assert record.width == 32
    assert record.height == 32
    assert record.size_bytes == len(data)
    assert record.image_format == "JPEG"
    assert record.session_id
    assert len(store) == 1


def test_get_returns_the_stored_record() -> None:
    store = SessionStore()
    record = store.add(_jpeg_bytes(), "a.jpg")
    assert store.get(record.session_id) is record


def test_get_unknown_session_is_none() -> None:
    store = SessionStore()
    assert store.get("does-not-exist") is None


def test_remove_drops_the_session() -> None:
    store = SessionStore()
    record = store.add(_jpeg_bytes(), "a.jpg")
    store.remove(record.session_id)
    assert store.get(record.session_id) is None
    assert len(store) == 0


def test_uncodeable_upload_is_an_input_error() -> None:
    store = SessionStore()
    with pytest.raises(InputError, match="Cannot decode"):
        store.add(b"not an image", "junk.jpg")


def test_session_expires_after_ttl() -> None:
    store = SessionStore(ttl_seconds=0.05)
    record = store.add(_jpeg_bytes(), "a.jpg")
    time.sleep(0.15)
    assert store.get(record.session_id) is None
    assert len(store) == 0


def test_session_cap_evicts_oldest() -> None:
    store = SessionStore(max_sessions=1)
    first = store.add(_jpeg_bytes(), "a.jpg")
    second = store.add(_jpeg_bytes(), "b.jpg")
    assert store.get(first.session_id) is None
    assert store.get(second.session_id) is not None
    assert len(store) == 1


def test_byte_cap_evicts_until_it_fits() -> None:
    data = _jpeg_bytes(64, 64)
    # Cap holds exactly one copy, not two, so the second add must evict the first.
    store = SessionStore(max_total_bytes=len(data) + 1)
    first = store.add(data, "a.jpg")
    second = store.add(data, "b.jpg")
    assert store.get(second.session_id) is not None
    assert store.get(first.session_id) is None
    assert len(store) == 1

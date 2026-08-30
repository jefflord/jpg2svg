"""In-memory upload sessions for the web interface.

The web flow uploads an image once (held in server memory) and then re-runs
the converter as options change, so the browser never re-uploads the image on
every tweak. Sessions are keyed by an unguessable id, capped in count and
total bytes, and expire after a TTL so a forgotten upload cannot linger.
"""

from __future__ import annotations

import io
import threading
import time
import uuid
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from raster2svg.core.errors import InputError

#: Evict a session after this much idle time.
DEFAULT_TTL_SECONDS = 1800.0
#: Hard caps so a long-running server cannot be pushed out of memory.
MAX_SESSIONS = 16
MAX_TOTAL_BYTES = 256 * 1024 * 1024


@dataclass
class UploadedImage:
    """A decoded-and-stored upload, ready for repeated conversion."""

    session_id: str
    image_bytes: bytes
    image_format: str
    width: int
    height: int
    size_bytes: int
    created: float


class SessionStore:
    """A thread-safe, bounded, expiring store of uploaded images."""

    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_sessions: int = MAX_SESSIONS,
        max_total_bytes: int = MAX_TOTAL_BYTES,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions
        self._max_total_bytes = max_total_bytes
        self._items: dict[str, UploadedImage] = {}
        self._lock = threading.Lock()

    def add(self, image_bytes: bytes, original_format: str) -> UploadedImage:
        """Decode, validate, and store an upload.

        Raises :class:`InputError` if the bytes are not a decodable raster
        image. Raises :class:`InputError` when the store caps are exceeded.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.load()
                width, height = image.size
                fmt = (image.format or "unknown").upper()
        except (OSError, UnidentifiedImageError) as exc:
            raise InputError(
                "Cannot decode the uploaded image.",
                hint="The file is corrupt or not a supported raster image.",
            ) from exc
        if width <= 0 or height <= 0:
            raise InputError(f"Uploaded image has invalid dimensions {width}x{height}.")

        record = UploadedImage(
            session_id=uuid.uuid4().hex,
            image_bytes=image_bytes,
            image_format=fmt,
            width=width,
            height=height,
            size_bytes=len(image_bytes),
            created=time.monotonic(),
        )
        with self._lock:
            self._evict_expired()
            self._enforce_caps(record)
            self._items[record.session_id] = record
        return record

    def get(self, session_id: str) -> UploadedImage | None:
        """Return a live session, or None if it is unknown or expired."""
        with self._lock:
            record = self._items.get(session_id)
            if record is None:
                return None
            if time.monotonic() - record.created > self._ttl:
                self._items.pop(session_id, None)
                return None
            return record

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._items.pop(session_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def _evict_expired(self) -> None:
        now = time.monotonic()
        for key in [key for key, item in self._items.items() if now - item.created > self._ttl]:
            del self._items[key]

    def _enforce_caps(self, record: UploadedImage) -> None:
        if len(self._items) >= self._max_sessions:
            oldest = min(self._items.values(), key=lambda item: item.created)
            del self._items[oldest.session_id]
        total = sum(item.size_bytes for item in self._items.values())
        if total + record.size_bytes > self._max_total_bytes:
            for item in sorted(self._items.values(), key=lambda entry: entry.created):
                if total <= self._max_total_bytes - record.size_bytes:
                    break
                del self._items[item.session_id]
                total -= item.size_bytes

"""A stdlib-only HTTP server for the web interface (no new dependencies).

Serves the single-page app (``/``) and a small JSON API:

* ``GET  /api/info``    server, engine, presets, and the option descriptors
* ``POST /api/upload``  base64 image -> a session id
* ``POST /api/convert`` session + options -> the rendered SVG text

Conversions run on the request thread (``ThreadingHTTPServer``); the
``Converter`` and engine are stateless per call and safe to share.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any

from raster2svg._version import __version__
from raster2svg.config.models import ConversionConfig, PreprocessConfig
from raster2svg.config.presets import available_presets
from raster2svg.core.capabilities import EngineCapabilities, split_engine_dependent
from raster2svg.core.errors import Raster2SvgError
from raster2svg.services.converter import Converter
from raster2svg.web.session import SessionStore


class _APIError(Exception):
    """A request-level failure carrying an HTTP status code."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


#: Option descriptors for the UI. ``requires`` is the VTracer parameter the
#: option depends on; when the installed engine lacks it, the server marks the
#: field ``unavailable`` so the UI can disable it (mirrors the CLI behavior).
CONVERSION_FIELDS: list[dict[str, Any]] = [
    {
        "name": "clustering",
        "label": "Clustering",
        "kind": "select",
        "options": [
            {"value": "color-cluster", "label": "Color"},
            {"value": "bw", "label": "Black & white"},
        ],
    },
    {
        "name": "hierarchical",
        "label": "Layering",
        "kind": "select",
        "options": [
            {"value": "stacked", "label": "Stacked"},
            {"value": "cutout", "label": "Cutout"},
        ],
    },
    {
        "name": "mode",
        "label": "Curve mode",
        "kind": "select",
        "options": [
            {"value": "spline", "label": "Spline"},
            {"value": "polygon", "label": "Polygon"},
            {"value": "pixel", "label": "Pixel (straight lines)"},
        ],
    },
    {"name": "filter_speckle", "label": "Speckle filter", "kind": "int", "min": 1, "max": 100},
    {"name": "color_precision", "label": "Color precision", "kind": "int", "min": 1, "max": 8},
    {"name": "layer_difference", "label": "Layer difference", "kind": "int", "min": 1, "max": 255},
    {
        "name": "corner_threshold",
        "label": "Corner threshold",
        "kind": "float",
        "min": 0,
        "max": 180,
    },
    {"name": "length_threshold", "label": "Segment length", "kind": "float", "min": 3.5, "max": 10},
    {"name": "max_iterations", "label": "Max iterations", "kind": "int", "min": 1, "max": 100},
    {
        "name": "splice_threshold",
        "label": "Splice threshold",
        "kind": "float",
        "min": 0,
        "max": 180,
    },
    {"name": "path_precision", "label": "Path precision", "kind": "int", "min": 0, "max": 8},
    {
        "name": "simplify",
        "label": "Simplify",
        "kind": "float",
        "min": 0.01,
        "max": 10,
        "requires": "simplify",
    },
    {"name": "palette", "label": "Palette (hex)", "kind": "palette", "requires": "palette"},
    {
        "name": "max_colors",
        "label": "Max colors",
        "kind": "int",
        "min": 1,
        "max": 65536,
        "requires": "max_colors",
    },
    {
        "name": "optimize",
        "label": "Optimize",
        "kind": "int",
        "min": 0,
        "max": 2,
        "requires": "optimize",
    },
    {
        "name": "binary_threshold",
        "label": "Binary threshold",
        "kind": "int",
        "min": 0,
        "max": 255,
        "requires": "binary_threshold",
    },
    {"name": "adaptive", "label": "Adaptive threshold", "kind": "bool", "requires": "adaptive"},
    {
        "name": "adaptive_window",
        "label": "Adaptive window",
        "kind": "int",
        "min": 3,
        "requires": "adaptive_window",
    },
    {
        "name": "adaptive_t",
        "label": "Adaptive constant",
        "kind": "int",
        "min": 0,
        "max": 255,
        "requires": "adaptive_t",
    },
    {
        "name": "watershed_detail",
        "label": "Watershed detail",
        "kind": "int",
        "min": 0,
        "max": 255,
        "requires": "watershed_detail",
    },
]

PREPROCESS_FIELDS: list[dict[str, Any]] = [
    {
        "name": "pre_max_colors",
        "label": "Pre-max colors",
        "kind": "int",
        "min": 1,
        "max": 256,
        "star": True,
    },
    {"name": "grayscale", "label": "Grayscale", "kind": "bool", "default": False},
    {"name": "denoise", "label": "Denoise", "kind": "bool", "default": False},
    {"name": "sharpen", "label": "Sharpen", "kind": "bool", "default": False},
    {"name": "auto_orient", "label": "Auto-orient (EXIF)", "kind": "bool", "default": True},
    {"name": "contrast", "label": "Contrast", "kind": "float", "min": 0, "max": 10, "default": 1.0},
    {
        "name": "brightness",
        "label": "Brightness",
        "kind": "float",
        "min": 0,
        "max": 10,
        "default": 1.0,
    },
    {"name": "scale", "label": "Scale factor", "kind": "float", "min": 0.01, "max": 10},
    {"name": "max_width", "label": "Max width (px)", "kind": "int", "min": 1},
    {"name": "max_height", "label": "Max height (px)", "kind": "int", "min": 1},
    {"name": "resize", "label": "Resize to (WxH)", "kind": "resize"},
]


def _finalize_fields(
    fields: list[dict[str, Any]], caps: EngineCapabilities
) -> list[dict[str, Any]]:
    """Attach an ``unavailable`` flag based on the installed engine."""
    out: list[dict[str, Any]] = []
    for field in fields:
        entry = dict(field)
        requires = entry.pop("requires", None)
        if requires is not None and not caps.supports(requires):
            entry["unavailable"] = True
            entry["unavailable_hint"] = f"Needs VTracer 1.0 (requires '{requires}')."
        else:
            entry["unavailable"] = False
        out.append(entry)
    return out


def build_info_payload(
    caps: EngineCapabilities, sample_name: str | None = None
) -> dict[str, Any]:
    """The ``/api/info`` payload: versions, presets, and option descriptors.

    ``sample`` is ``null`` unless the server was started with a ``--sample``
    SVG, in which case it carries the sample's file name.
    """
    available, unavailable = split_engine_dependent(caps)
    return {
        "version": __version__,
        "engine": {"name": caps.name, "version": caps.version},
        "supported_params": sorted(caps.supported_params),
        "available_advanced": available,
        "unavailable_advanced": unavailable,
        "presets": available_presets(),
        "conversion_fields": _finalize_fields(CONVERSION_FIELDS, caps),
        "preprocess_fields": _finalize_fields(PREPROCESS_FIELDS, caps),
        "sample": {"name": sample_name} if sample_name else None,
    }


class _AppServer(ThreadingHTTPServer):
    """An HTTP server carrying the shared application context."""

    context: Converter
    store: SessionStore
    html: str
    info: dict[str, Any]
    sample: tuple[Path, str] | None


class WebHandler(BaseHTTPRequestHandler):
    server: _AppServer

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        """Route access logs through the package logger instead of stderr."""
        import logging

        logging.getLogger("raster2svg.web").info("%s - %s", self.address_string(), format % args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self) -> None:
        body = self.server.html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return {}
        try:
            data: Any = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _APIError(400, f"Body must be valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise _APIError(400, "JSON body must be an object.")
        return data

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = self.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                self._send_html()
            elif path == "/api/info":
                self._send_json(200, self.server.info)
            elif path == "/api/sample":
                self._handle_sample()
            else:
                self._send_json(404, {"error": f"Unknown path: {path}"})
        except _APIError as exc:
            self._send_json(exc.status, {"error": exc.message})

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        path = self.path.split("?", 1)[0]
        try:
            if path == "/api/upload":
                self._handle_upload()
            elif path == "/api/convert":
                self._handle_convert()
            else:
                self._send_json(404, {"error": f"Unknown path: {path}"})
        except _APIError as exc:
            self._send_json(exc.status, {"error": exc.message})
        except Raster2SvgError as exc:
            payload: dict[str, Any] = {"error": exc.message}
            if exc.hint:
                payload["hint"] = exc.hint
            self._send_json(400, payload)
        except Exception as exc:  # noqa: BLE001 - surface unexpected failures to the client
            self._send_json(500, {"error": f"Internal error: {exc}"})

    def _handle_upload(self) -> None:
        data = self._read_json()
        image_b64 = data.get("image")
        if not isinstance(image_b64, str) or not image_b64:
            raise _APIError(400, "Field 'image' (base64) is required.")
        try:
            import base64

            image_bytes = base64.b64decode(image_b64, validate=True)
        except Exception as exc:
            raise _APIError(400, f"'image' is not valid base64: {exc}") from exc
        if len(image_bytes) == 0:
            raise _APIError(400, "Uploaded image is empty.")
        name = data.get("name")
        record = self.server.store.add(image_bytes, str(name) if name else "unknown")
        self._send_json(
            200,
            {
                "session": record.session_id,
                "format": record.image_format,
                "width": record.width,
                "height": record.height,
                "size_bytes": record.size_bytes,
            },
        )

    def _handle_convert(self) -> None:
        data = self._read_json()
        session_id = data.get("session")
        if not isinstance(session_id, str) or not session_id:
            raise _APIError(400, "Field 'session' is required.")
        record = self.server.store.get(session_id)
        if record is None:
            raise _APIError(409, "Session expired or unknown; please re-upload the image.")

        options = data.get("options") or {}
        if not isinstance(options, dict):
            raise _APIError(400, "'options' must be an object.")
        conv_data: dict[str, Any] = dict(options.get("conversion") or {})
        preset = options.get("preset")
        if preset is not None:
            conv_data["preset"] = preset
        conversion = ConversionConfig.from_dict(conv_data)
        preprocess = PreprocessConfig.from_dict(options.get("preprocess") or {})

        started = time.perf_counter()
        svg, applied = self.server.context.convert_bytes(
            record.image_bytes,
            record.image_format,
            config=conversion,
            preprocess=preprocess,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._send_json(
            200,
            {
            "svg": svg,
            "applied": applied,
            "duration_ms": duration_ms,
            "bytes": len(svg.encode("utf-8")),
            },
        )

    def _handle_sample(self) -> None:
        sample = self.server.sample
        if sample is None:
            raise _APIError(
                404, "No sample SVG configured. Start the server with --sample <path.svg>."
            )
        path, name = sample
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise _APIError(404, f"Could not read the sample SVG: {exc}") from exc
        self._send_json(
            200,
            {
                "svg": text,
                "name": name,
                "size_bytes": len(text.encode("utf-8")),
            },
        )


def _load_index_html() -> str:
    return files("raster2svg.web").joinpath("static/index.html").read_text(encoding="utf-8")


class WebServer:
    """Owns the HTTP server and its shared context.

    Call :meth:`bind` (surfaces port-in-use errors), then :meth:`serve_forever`
    to block in the foreground (the CLI flow). :meth:`serve` is a convenience
    wrapper for that, and :meth:`start_in_thread` is for tests and embedding.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 9921,
        converter: Converter | None = None,
        store: SessionStore | None = None,
        sample: Path | str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.context = converter or Converter()
        self.store = store or SessionStore()
        self.sample: Path | None = Path(sample).expanduser() if sample else None
        self.html = _load_index_html()
        self.info = build_info_payload(
            self.context.capabilities, self.sample.name if self.sample else None
        )
        self._httpd: _AppServer | None = None
        self._thread: threading.Thread | None = None

    def bind(self) -> None:
        """Create and bind the listening socket (idempotent).

        Raises :class:`OSError` if the host:port cannot be bound (e.g. it is
        already in use) so callers can report it before serving begins.
        """
        if self._httpd is None:
            if self.sample is not None and not self.sample.is_file():
                raise OSError(f"Sample SVG not found: {self.sample}")
            server = _AppServer((self.host, self.port), WebHandler)
            server.context = self.context
            server.store = self.store
            server.html = self.html
            server.info = self.info
            server.sample = (self.sample, self.sample.name) if self.sample else None
            self._httpd = server

    def serve_forever(self) -> None:
        """Block, serving requests. Call after :meth:`bind`."""
        if self._httpd is None:
            raise RuntimeError("Call bind() before serve_forever().")
        self._httpd.serve_forever()

    def serve(self) -> None:
        """Bind and serve until interrupted (blocking)."""
        self.bind()
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def start_in_thread(self) -> None:
        """Bind and serve in a daemon thread (for tests/embedding)."""
        self.bind()
        if self._httpd is None:
            raise RuntimeError("Call bind() before start_in_thread().")
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def bound_port(self) -> int:
        if self._httpd is None:
            raise RuntimeError("Server is not started.")
        return self._httpd.server_address[1]

"""Integration tests for the web interface HTTP server (raster2svg_web_prd.md)."""

from __future__ import annotations

import base64
import http.client
import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from raster2svg.web.server import WebServer

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture()
def webserver() -> Generator[WebServer, None, None]:
    server = WebServer(host="127.0.0.1", port=0)
    server.bind()
    server.start_in_thread()
    yield server
    server.shutdown()


def _conn(webserver: WebServer) -> http.client.HTTPConnection:
    return http.client.HTTPConnection("127.0.0.1", webserver.bound_port, timeout=30)


def _request(
    conn: http.client.HTTPConnection,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any, str | None]:
    """Send a request, read the body exactly once, and return (status, body, content_type)."""
    if payload is not None:
        conn.request(method, path, json.dumps(payload), {"Content-Type": "application/json"})
    else:
        conn.request(method, path)
    response = conn.getresponse()
    raw = response.read()
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        body = raw.decode("utf-8", "replace")
    return response.status, body, response.getheader("Content-Type")


def test_index_serves_the_app(webserver: WebServer) -> None:
    status, body, ctype = _request(_conn(webserver), "GET", "/")
    assert status == 200
    assert "text/html" in (ctype or "")
    assert "<script>" in body
    assert "raster2svg" in body


def test_api_info_shape(webserver: WebServer) -> None:
    status, info, _ = _request(_conn(webserver), "GET", "/api/info")
    assert status == 200
    assert info["engine"]["name"] == "vtracer"
    assert {"bw", "photo", "poster"} <= set(info["presets"])
    assert all("unavailable" in f for f in info["conversion_fields"])
    assert all("unavailable" in f for f in info["preprocess_fields"])


def test_unknown_path_is_404(webserver: WebServer) -> None:
    status, body, _ = _request(_conn(webserver), "GET", "/nope")
    assert status == 404
    assert "error" in body


def test_upload_rejects_missing_image(webserver: WebServer) -> None:
    status, body, _ = _request(_conn(webserver), "POST", "/api/upload", {"name": "x.jpg"})
    assert status == 400
    assert "image" in body["error"]


def test_upload_rejects_invalid_base64(webserver: WebServer) -> None:
    status, body, _ = _request(_conn(webserver), "POST", "/api/upload", {"image": "not-base64!!!"})
    assert status == 400
    assert "image" in body["error"]


def test_upload_rejects_uncodeable_bytes(webserver: WebServer) -> None:
    b64 = base64.b64encode(b"definitely not an image").decode()
    status, body, _ = _request(_conn(webserver), "POST", "/api/upload", {"image": b64})
    assert status == 400
    assert "decode" in (body["error"] + (body.get("hint") or "")).lower()


def test_upload_and_convert_round_trip(webserver: WebServer) -> None:
    data = (FIXTURES / "fixture_photo.jpg").read_bytes()
    b64 = base64.b64encode(data).decode()
    conn = _conn(webserver)

    status, uploaded, _ = _request(
        conn, "POST", "/api/upload", {"image": b64, "name": "fixture_photo.jpg"}
    )
    assert status == 200, uploaded
    assert uploaded["width"] == 96
    assert uploaded["height"] == 96
    session = uploaded["session"]

    status, result, _ = _request(conn, "POST", "/api/convert", {"session": session, "options": {}})
    assert status == 200, result
    assert result["svg"].lstrip().startswith("<?xml")
    assert result["applied"] == []
    assert result["bytes"] > 0


def test_convert_applies_preprocessing_options(webserver: WebServer) -> None:
    data = (FIXTURES / "fixture_photo.jpg").read_bytes()
    b64 = base64.b64encode(data).decode()
    conn = _conn(webserver)

    status, uploaded, _ = _request(conn, "POST", "/api/upload", {"image": b64})
    assert status == 200, uploaded
    session = uploaded["session"]

    status, result, _ = _request(
        conn,
        "POST",
        "/api/convert",
        {
            "session": session,
            "options": {"preset": "photo", "preprocess": {"pre_max_colors": 8, "grayscale": True}},
        },
    )
    assert status == 200, result
    assert set(result["applied"]) == {"pre_max_colors", "grayscale"}


def test_convert_unknown_session_is_409(webserver: WebServer) -> None:
    status, body, _ = _request(
        _conn(webserver), "POST", "/api/convert", {"session": "nope", "options": {}}
    )
    assert status == 409
    assert "re-upload" in body["error"]


def test_convert_rejects_invalid_options(webserver: WebServer) -> None:
    data = (FIXTURES / "fixture_photo.jpg").read_bytes()
    b64 = base64.b64encode(data).decode()
    conn = _conn(webserver)

    status, uploaded, _ = _request(conn, "POST", "/api/upload", {"image": b64})
    assert status == 200, uploaded
    session = uploaded["session"]

    status, body, _ = _request(
        conn,
        "POST",
        "/api/convert",
        {"session": session, "options": {"conversion": {"filter_speckle": 999}}},
    )
    assert status == 400
    assert "filter_speckle" in (body.get("hint") or "")

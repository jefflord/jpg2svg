# Product Requirements Document (PRD)

# Raster-to-SVG Live Web Interface

**Working name:** `raster2svg web`\
**Companion to:** `raster2svg_prd.md` (the CLI and core conversion product)\
**Version:** 1.0\
**Target platform:** Cross-platform, Windows first\
**Primary implementation:** Python 3.12+, stdlib `http.server`\
**Tracing engine:** Reuses the installed VTracer through the existing core\
**Status:** Build specification for implementation by a coding agent

------------------------------------------------------------------------

## 1. Executive Summary

`raster2svg web` adds a local, browser-based, live raster-to-SVG converter on
top of the existing `raster2svg` core library. It starts a small HTTP server
on the machine that hosts a single-page application where the user can:

-   Upload an image **once**.
-   Tweak conversion and preprocessing options in the browser.
-   See the **rendered SVG update live** as options change.
-   **Download** the resulting SVG file.

The interface reuses the same configuration model, presets, preprocessing
pipeline, and tracing engine as the command-line tool, so behaviour in the
browser matches `raster2svg convert` exactly. It introduces **no new runtime
dependencies**: the server is the Python standard-library `http.server`, and the
front end is a single self-contained HTML file with vanilla JavaScript and CSS.

The web interface is a convenience layer over the core library. It is not a
separate product and must not duplicate conversion, configuration, or
preprocessing logic that already exists in the core.

------------------------------------------------------------------------

# 2. Product Goals

## 2.1 Primary Goals

1.  Provide a local web interface for real-time raster-to-SVG conversion.
2.  Let the user upload an image once and re-convert it repeatedly as options
    change, without re-uploading the image each time.
3.  Render the produced SVG live in the browser as a preview.
4.  Let the user download the SVG as a file.
5.  Reuse the existing core configuration, presets, preprocessing, and tracing
    engine so browser results are identical to `raster2svg convert`.
6.  Expose only the options the installed VTracer actually supports, and clearly
    mark the rest as unavailable (mirroring the CLI).
7.  Add no new runtime dependencies.

## 2.2 Secondary Goals

-   Open the browser automatically on demand (`--open`).
-   Surface per-conversion diagnostics (applied preprocessing ops, duration,
    output size) in the response.
-   Bound memory (session count and total bytes) so a long-running local server
    cannot be pushed out of memory.
-   Be testable without a real browser (the JSON API is exercised directly).

## 2.3 Non-Goals for Version 1

The following are out of scope for the web interface:

-   A public or multi-user server (authentication, accounts, tenancy).
-   Editing the produced SVG (the UI previews and downloads; it does not edit).
-   Persisting uploads to disk or to a database (sessions are in-memory only).
-   Batch conversion of many images from the browser.
-   Replacing or diverging from the CLI's configuration model.
-   Any non-stdlib runtime dependency (no web framework, no bundler at runtime).

------------------------------------------------------------------------

# 3. Target Users

## 3.1 Designer / Technical Artist

A user who wants to see the effect of tuning tracing options without re-running
a command, iterating until the output looks right, then downloading the SVG.

## 3.2 Power User

A user who already knows the CLI but wants a faster visual loop for a single
image, and who needs the exact same engine behaviour as `raster2svg convert`.

## 3.3 Developer / Evaluator

A user who wants to compare engine versions or settings side by side on the same
image, using a quick local server.

------------------------------------------------------------------------

# 4. Functional Requirements

## 4.1 Web server and command

-   A `web` subcommand shall start a local HTTP server and block until
    interrupted (`Ctrl+C`), then shut down cleanly.
-   The server shall bind to `127.0.0.1` on port `9921` by default.
-   `--host` shall select the interface to bind (e.g. `0.0.0.0` for other
    machines on a trusted network).
-   `--port` shall select the port to listen on.
-   `--open` shall open the interface in the default browser on startup.
-   On successful start, the command shall print the URL to open and a one-line
    usage hint.
-   If the host:port cannot be bound (for example, it is already in use), the
    command shall fail with a clear message and the standard "invalid
    configuration" exit code (**2**) before serving begins.
-   The server shall be implemented with the standard-library `http.server`
    (`ThreadingHTTPServer`) and shall add no new runtime dependencies.

## 4.2 Upload

-   The interface shall accept an image upload (file picker or drag-and-drop).
-   The uploaded bytes shall be decoded and validated server-side; a corrupt or
    non-raster file shall be rejected with a clear error.
-   A successful upload shall create an in-memory **session** that stores the
    image bytes for repeated conversion, and return a session identifier plus
    the decoded dimensions and format.
-   The image shall **not** be re-sent to the server on every option change.

## 4.3 Conversion options

-   The interface shall present the conversion options and the preprocessing
    options as controls generated from a machine-readable descriptor list served
    by the server.
-   Only options the installed VTracer supports shall be enabled. Options that
    require an engine parameter the installed engine does not expose shall be
    disabled and labelled with a hint (e.g. "Needs VTracer 1.0"), matching the
    CLI behaviour.
-   The `pre_max_colors` preprocessing option (Pillow, always available) shall be
    presented as the available equivalent of the engine-native `max_colors`, and
    distinguished from it.
-   Presets (`bw`, `photo`, `poster`, and any saved custom presets) shall be
    selectable and shall seed the option controls.

## 4.4 Live preview

-   On every option change, the interface shall request a fresh conversion and
    render the returned SVG in the preview area.
-   The preview shall reflect the exact SVG that would be downloaded.

## 4.5 Download

-   The interface shall provide a control that downloads the current SVG as a
    file (client-side), without a round-trip to re-generate it.

## 4.6 Error handling

-   API errors shall be returned as JSON with a human-readable `error` message
    and, where applicable, a `hint`.
-   An unknown or expired session shall be reported so the user can re-upload.
-   Server-side failures that are not the client's fault shall be reported
    without leaking stack traces.

------------------------------------------------------------------------

# 5. HTTP API Specification

The API is JSON over HTTP. All responses use `Cache-Control: no-store`.

## 5.1 Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` (or `/index.html`) | Serve the single-page application. |
| `GET` | `/api/info` | Version, engine, presets, and option descriptors. |
| `POST` | `/api/upload` | Base64 image bytes → a session id. |
| `POST` | `/api/convert` | Session + options → rendered SVG text. |

## 5.2 `GET /`

Serves `static/index.html` with `Content-Type: text/html; charset=utf-8`.

## 5.3 `GET /api/info`

Returns the descriptors the front end uses to build its controls:

```json
{
  "version": "0.3.0",
  "engine": { "name": "VTracer", "version": "0.6.15" },
  "supported_params": ["color_precision", "mode", "..."],
  "available_advanced": ["..."],
  "unavailable_advanced": ["simplify", "palette", "max_colors", "optimize", "..."],
  "presets": ["bw", "photo", "poster"],
  "conversion_fields": [
    { "name": "clustering", "label": "Clustering", "kind": "select",
      "options": [ { "value": "color-cluster", "label": "Color" },
                   { "value": "bw", "label": "Black & white" } ],
      "unavailable": false },
    { "name": "simplify", "label": "Simplify", "kind": "float",
      "min": 0.01, "max": 10, "unavailable": true,
      "unavailable_hint": "Needs VTracer 1.0 (requires 'simplify')." }
  ],
  "preprocess_fields": [
    { "name": "pre_max_colors", "label": "Pre-max colors", "kind": "int",
      "min": 1, "max": 256, "star": true, "unavailable": false },
    { "name": "grayscale", "label": "Grayscale", "kind": "bool",
      "default": false, "unavailable": false }
  ]
}
```

Field descriptor keys:

-   `name`, `label`, `kind` — `select`, `int`, `float`, `bool`, `palette`, or
    `resize`.
-   `options` — for `select`: an array of `{value, label}`.
-   `min` / `max` — numeric bounds for `int` / `float`.
-   `default` — default for `bool` (and any field with an explicit default).
-   `star` — marks `pre_max_colors` as the available equivalent of `max_colors`.
-   `unavailable` — `true` when the installed engine lacks the required
    parameter; `false` otherwise.
-   `unavailable_hint` — present only when `unavailable` is `true`.

## 5.4 `POST /api/upload`

Request body:

```json
{ "image": "<base64-encoded image bytes>", "name": "optional original filename" }
```

-   `image` is required and must be valid base64 and a decodable raster image.
-   `name` is optional and is stored only for diagnostics.

Success (HTTP 200):

```json
{
  "session": "<uuid hex>",
  "format": "JPEG",
  "width": 6000,
  "height": 4000,
  "size_bytes": 1234567
}
```

Failure: HTTP 400 with `{ "error": "..." }` when `image` is missing, not valid
base64, empty, or not a decodable raster image.

## 5.5 `POST /api/convert`

Request body:

```json
{
  "session": "<uuid hex>",
  "options": {
    "preset": "photo",
    "conversion": { "mode": "spline", "color_precision": 8 },
    "preprocess": { "pre_max_colors": 32 }
  }
}
```

-   `session` is required and must name a live, unexpired session.
-   `options` is optional and must be an object. `preset`, `conversion`, and
    `preprocess` are all optional; the same five-layer precedence as the CLI
    applies (engine defaults < preset < user config < `--config` < the provided
    options).

Success (HTTP 200):

```json
{
  "svg": "<full SVG document text>",
  "applied": ["pre_max_colors"],
  "duration_ms": 412,
  "bytes": 98765
}
```

Failure:

-   HTTP 400 when `session` is missing, `options` is not an object, or the
    conversion fails due to a client-supplied problem (invalid option value or an
    unsupported engine feature). The body includes `error` and, where applicable,
    `hint`.
-   HTTP 409 when the session is unknown or expired; the body prompts a
    re-upload.
-   HTTP 500 for unexpected server-side failures (message only, no stack trace).

## 5.6 Status codes

| Code | Meaning |
| --- | --- |
| `200` | Success. |
| `400` | Bad request (malformed body, invalid option, unsupported feature). |
| `404` | Unknown path. |
| `409` | Unknown or expired session. |
| `500` | Unexpected server error. |

------------------------------------------------------------------------

# 6. Architecture

The web interface is a thin layer over the existing core. It reuses, and must
not duplicate:

-   `Converter` (services layer) — the conversion entry point. The web server
    calls a new in-memory method, `Converter.convert_bytes(image_bytes,
    image_format, *, config=None, preprocess=None)`, which returns `(svg_text,
    applied_ops)` and runs the same preprocessing-then-trace pipeline as the CLI.
-   `ConversionConfig` / `PreprocessConfig` — the canonical configuration model
    and its validation.
-   `EngineCapabilities` — the runtime feature check used to mark options
    available/unavailable.
-   Presets — the same preset bundles and availability list.

New web-specific pieces:

-   `web/server.py` — the HTTP server, the request handler, and the
    `/api/info` descriptor builder.
-   `web/session.py` — the in-memory, bounded, expiring upload session store.
-   `web/static/index.html` — the single-page front end.
-   `web/cli.py` — the `web` command.

The server shares one stateless `Converter` and one `SessionStore` across
request threads; each request is handled on its own thread
(`ThreadingHTTPServer`).

------------------------------------------------------------------------

# 7. Session Management

Uploaded images are held in server memory for the duration of a session so the
browser can re-convert without re-uploading.

-   Sessions shall be keyed by an unguessable identifier (a UUIDv4 hex string).
-   Sessions shall be stored **in memory only** and never written to disk.
-   Sessions shall expire after a time-to-live (default **30 minutes** of
    inactivity).
-   The store shall be bounded by a maximum session count (default **16**) and a
    maximum total byte count (default **256 MiB**); when a cap is exceeded, the
    oldest sessions are evicted first.
-   The store shall be safe for concurrent use across request threads.

------------------------------------------------------------------------

# 8. UI / UX

-   A single page with three regions: the upload area, the options panel, and
    the live preview.
-   The options panel shall be generated from `GET /api/info` so the set of
    controls always matches the installed engine.
-   Disabled (unavailable) controls shall be visibly marked, with the engine
    requirement shown on hover or as a label.
-   A preset selector shall seed the option controls.
-   The preview shall update after each conversion and the download control
    shall always reflect the most recent result.
-   Errors returned by the API shall be shown to the user in place, not as raw
    HTTP status codes.
-   The interface shall be self-contained (inline CSS and JavaScript) and usable
    offline from `file://` as well as from the server.

------------------------------------------------------------------------

# 9. Security

-   The server shall bind to loopback by default and expose no credentials.
-   The server is intended for trusted local use; it performs no
    authentication. Binding to `0.0.0.0` is the operator's explicit choice.
-   Uploaded bytes shall be decoded with a standard image decoder and treated as
    untrusted input (no shell or file-system access from the bytes).
-   Session identifiers shall be unguessable.
-   Error responses shall not leak stack traces or internal paths.
-   Responses shall be marked `no-store` to avoid caching uploads or results.

------------------------------------------------------------------------

# 10. Performance

-   Conversions run on the request thread; the core is expected to be the
    dominant cost, as it is for the CLI.
-   The upload is sent once per image; repeated conversions reuse the stored
    bytes, so the per-tweak cost is conversion only (no re-upload, no re-decode
    of the original file).
-   Session caps bound server memory for a long-running local server.

------------------------------------------------------------------------

# 11. Testing

-   **Unit:** the session store (add/get/remove, TTL expiry, count and byte
    caps, rejection of invalid images); the `/api/info` descriptor builder
    (shape, available/unavailable marking, preset list, the `pre_max_colors`
    star); and `Converter.convert_bytes` (default run, preprocessing applied,
    preset expansion, unsupported-feature error).
-   **Integration:** a real `ThreadingHTTPServer` on an ephemeral port exercised
    over HTTP — the index page, `/api/info`, upload (valid and invalid), and
    convert (valid, with preprocessing, with a preset) plus the 400/404/409
    error paths.
-   **CLI:** the `web` command's help text, its registration, and a clean failure
    when the port cannot be bound.
-   All tests shall run headless (no real browser) and pass the project's
    lint/type/test gates.

------------------------------------------------------------------------

# 12. Acceptance Criteria

-   `raster2svg web` starts a loopback server on port 9921, prints the URL, and
    stops cleanly on `Ctrl+C`.
-   Opening the URL shows the single-page app.
-   Uploading an image returns a session and dimensions; the image is decodable.
-   Changing options re-converts and updates the live preview without a
    re-upload.
-   Options the installed engine does not support are disabled with a clear
    hint; `pre_max_colors` is available and marked as the equivalent of
    `max_colors`.
-   Downloading produces the same SVG bytes the preview shows.
-   A bind failure exits with code **2** and a clear, actionable message.
-   `ruff`, `mypy`, and the test suite are green with the web interface in
    place.

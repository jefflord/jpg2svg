# Architecture

`raster2svg` is a thin CLI over a reusable Python core. The design keeps
tracing, configuration, and I/O out of the command layer so a future GUI can
reuse the same core without changing the engine (PRD sections 23, 24).

## Layering

```
cli/            thin Typer commands (arg parsing, exit codes, display)
   ↓
services/       Converter + BatchConverter (orchestration, concurrency)
   ↓
config/         canonical models + resolver + presets + loader
   ↓
engines/        VTracer adapter (canonical settings → installed API)
   ↓
output/         SVG validation, atomic writes, JSON reports
core/           models, error hierarchy, engine capabilities
```

Dependency rule: a layer only depends on layers below it. The CLI never calls
the engine directly, and no tracing logic lives in `cli/`.

## Key modules

| Package | Responsibility |
| --- | --- |
| `cli/` | `app.py` (root, shorthand routing), `convert.py`, `batch.py`, `inspect.py`, `config.py`, `preset.py`, `help.py`, `options.py` (shared option defs + resolution). |
| `services/converter.py` | Single-image conversion pipeline: preprocess → trace → validate → write → report. |
| `services/batch_converter.py` | File collection, entry mapping, bounded-concurrency execution, per-file error capture. |
| `config/models.py` | Pydantic `ConversionConfig`, `PreprocessConfig`, `OutputConfig`, `AppConfig`. `extra = "forbid"`. |
| `config/resolver.py` | Applies the precedence chain and produces a concrete `ConversionConfig`. |
| `config/presets.py` | Built-in + custom presets, `base` inheritance chain. |
| `config/loader.py` | TOML/JSON loading, sectioned + flat shapes, unknown-key rejection. |
| `config/user_config.py` | User-level config file discovery/loading (PRD 8, level 3). |
| `engines/vtracer_engine.py` | Maps canonical settings onto the installed VTracer API; reports capabilities. |
| `core/errors.py` | Exception hierarchy and exit codes. |
| `core/capabilities.py` | Detects installed VTracer version and supported parameters. |
| `output/` | SVG XML validation, atomic file writes, JSON/JSONL report rendering. |
| `web/` | `raster2svg web`: stdlib `http.server` + JSON API, in-memory session store, and the single-page front end. Reuses `services/`, `config/`, and `engines/` (spec: `raster2svg_web_prd.md`). |

## Configuration resolution

The canonical settings model (`ConversionConfig`) is the single source of
truth. Every engine-facing field is optional; `None` means "let the installed
engine use its own default", so the same model stays valid across VTracer
versions with different feature sets.

Resolution order (low → high): **engine defaults < preset < user-level config
< `--config` file < CLI options**. A higher layer only overrides the keys it
sets. The resolver (`config/resolver.py`) merges these into one concrete
`ConversionConfig`, which the engine adapter then maps onto the installed
VTracer API.

## Engine capability mapping

`core/capabilities.py` detects the installed VTracer version and the subset of
parameters it exposes. Settings the installed engine does not support are still
accepted by the canonical model (for forward/backward compatibility) but raise a
clear "unsupported" error (exit code **2**) at conversion time, rather than
being silently dropped (PRD 21). `raster2svg engine capabilities` lists what is
available.

## Error model and exit codes

All failures raise a `Raster2SvgError` subclass with a `message` and optional
`hint`. The CLI renders `ERROR: <message>` plus an optional `Hint:` line and
exits with the code defined on the exception:

| Exit code | Raised by |
| --- | --- |
| `0` | success |
| `1` | batch: one or more files failed/skipped |
| `2` | `ConfigError`, `UnsupportedFeatureError` |
| `3` | `InputError`, `OutputError` |
| `4` | `EngineError` / runtime (base `Raster2SvgError`) |

## Reusable core API (future GUI)

The CLI is a thin wrapper. A GUI (or any program) can drive the same pipeline:

```python
from raster2svg.config.models import ConversionConfig
from raster2svg.services.converter import Converter

config = ConversionConfig(preset="photo", mode="spline")
result = Converter().convert("photo.jpg", "photo.svg", config=config)
```

A future PySide6 application would call `services/` and `config/` directly and
re-use the same models, presets, validation, and reports — no tracing logic in
the widgets.

## Web interface

`raster2svg web` is the first concrete consumer of that reusable core. It is a
thin layer that adds:

-   `web/cli.py` — the `web` command (bind, serve, `--open`).
-   `web/server.py` — a stdlib `ThreadingHTTPServer`, a JSON API
    (`/api/info`, `/api/upload`, `/api/convert`), and the option descriptors.
-   `web/session.py` — the bounded, expiring in-memory upload store.
-   `web/static/index.html` — the self-contained front end.

It calls a new in-memory entry point, `Converter.convert_bytes(...)`, which runs
the same preprocess → trace pipeline as the CLI. No tracing, configuration, or
preprocessing logic is duplicated in the web layer (spec:
`raster2svg_web_prd.md`).

## Testing

- `tests/unit/` — config resolution, models, presets, loader, user config, the
  web session store, the `/api/info` descriptors, and `Converter.convert_bytes`.
- `tests/integration/` — CLI end-to-end (convert, batch, inspect, config,
  preset, help, logging, preprocessing), plus the web HTTP API and the `web`
  command.
- `tests/fixtures/` — small deterministic images generated by
  `tests/generate_fixtures.py`.
- `tests/golden/` — golden SVG outputs for regression comparison.

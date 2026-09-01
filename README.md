# raster2svg

Convert raster images (JPG/JPEG, PNG, ...) to SVG vector graphics, powered by the
VTracer tracing engine.

`raster2svg` is a command-line tool designed for automation and batch use, built as
a thin CLI over a reusable Python core library that a future GUI can reuse directly.

## Requirements

- Python 3.12+

## Setup (virtual environment)

All development and usage happens inside the project virtual environment.
Packages must never be installed into the system Python.

```powershell
# create the venv (once)
py -3.12 -m venv .venv

# activate (PowerShell)
.venv\Scripts\Activate.ps1

# install the tool + dev dependencies
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If the shell is not activated, always call the venv executables directly:

```powershell
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\raster2svg --help
.venv\Scripts\pytest
.venv\Scripts\ruff check .
.venv\Scripts\mypy
```

## Usage

```powershell
raster2svg photo.jpg photo.svg
raster2svg convert photo.jpg --preset photo --mode spline --overwrite
raster2svg convert photo.jpg --show-config
raster2svg inspect photo.jpg
raster2svg --verbose convert photo.jpg --log-file build\conversion.log
raster2svg engine capabilities
raster2svg web --open
raster2svg --help
```

## Configuration

Settings resolve from five layers, lowest to highest priority:

```text
engine defaults  <  preset  <  user config  <  --config file  <  CLI options
```

A higher layer only overrides the keys it sets; the rest fall through. So a
preset, a user file, and a project file can coexist without clobbering each
other.

The **user-level config file** (`config.toml` or `config.json`) is machine-wide
and lives in the platform data directory (alongside custom presets):

| OS | Directory |
| --- | --- |
| Windows | `%APPDATA%\raster2svg\` |
| Linux | `~/.local/share/raster2svg/` |
| macOS | `~/Library/Application Support/raster2svg/` |

(`RASTER2SVG_DATA_DIR` relocates it.) A key here never overrides a key set by a
`--config` file or a CLI flag — it only fills the gaps.

See [`docs/configuration.md`](docs/configuration.md) for every supported key and
[`examples/`](examples/) for ready-to-copy configs (`photo.toml`, `bw.toml`,
`poster.toml`, and a user-level `user-config.toml`).

## Help

Every command supports `--help` (or `-h`). A `help` subcommand works in both
positions, and prints exactly the same text as the matching `--help`:

```powershell
raster2svg help
raster2svg help convert
raster2svg help config show
raster2svg convert help
raster2svg batch help
raster2svg config help show
```

## Inspecting images

`raster2svg inspect` decodes the image and reports its properties without
converting it — useful before a large batch run:

```powershell
raster2svg inspect photo.jpg
# Path: photo.jpg
# Format: JPEG
# Mode: RGB
# Width: 6000
# Height: 4000
# Pixels: 24,000,000
# Has alpha: false
# EXIF orientation: 1
# Size: 1,234,567 bytes
# Estimated memory: 68.7 MiB

raster2svg inspect --format json photo.jpg
```

## Logging

Global options available on every command (before the subcommand):

| Flag | Effect |
| --- | --- |
| `--verbose` | Debug logging (default: INFO) |
| `--quiet` | Warnings and errors only |
| `--log-level LEVEL` | `debug`, `info`, `warning`, or `error`; overrides `--verbose`/`--quiet` |
| `--log-file PATH` | Also write log messages to a file |

`--verbose` and `--quiet` are mutually exclusive (exit code 2).

## Preprocessing

Optional Pillow-based image preprocessing runs before tracing and is always
reported in the resolved config (`--show-config`) and the conversion report
(`preprocess` / `preprocess_applied`). A default run never re-encodes the
image.

| Flag | Effect |
| --- | --- |
| `--auto-orient` / `--no-auto-orient` | Apply EXIF orientation (default: on) |
| `--resize WxH` | Fit within a box, aspect preserved (up- and down-scaling) |
| `--max-width N` / `--max-height N` | Shrink only, aspect preserved |
| `--scale F` | Scale both dimensions by factor `F` |
| `--grayscale` / `--color` | Convert to grayscale (default: color) |
| `--denoise` / `--no-denoise` | Conservative median speckle removal |
| `--blur` / `--no-blur` | Gentle Gaussian blur to soften noise |
| `--posterize N` | Reduce to N bits per channel (1-8), flattening gradients into bands |
| `--autocontrast` / `--no-autocontrast` | Stretch contrast to the image's full range |
| `--contrast F` / `--brightness F` | Adjust tone (1.0 = unchanged) |
| `--sharpen` / `--no-sharpen` | Conservative unsharp mask |
| `--pre-max-colors N` | Cap the raster to at most N colors (1-256) before tracing; no dithering (flat regions) |

The same settings can be placed in a config file under `[preprocess]`; CLI
flags override file values.

## Postprocessing

Optional SVG post-processing runs after tracing and is always reported in the
conversion report (`postprocess` / `postprocess_applied`). A default run
leaves the traced SVG untouched.

| Flag | Effect |
| --- | --- |
| `--invert` / `--no-invert` | Render a negative (light-on-dark): invert hex fills, force unfilled shapes white, and add a dark background (default: off) |

The `line-art-inverted` and `silhouette-inverted` presets are just their base
preset with invert switched on, so they trace identically and only differ in
this final step.

## Web interface

`raster2svg web` starts a local HTTP server that hosts a single-page app for
real-time conversion: upload an image once, tweak the options, watch the SVG
update live, and download the result. It reuses the same engine, presets,
preprocessing, and postprocessing as `convert`, so the output matches the CLI
exactly. There are no new runtime dependencies — the server is stdlib
`http.server`.

```powershell
raster2svg web                     # http://localhost:9921/ (loopback)
raster2svg web --open              # also open the browser on startup
raster2svg web --port 8080         # a different port
```

By default it binds to loopback only. Press `Ctrl+C` to stop.

## Engine feature support

`raster2svg` keeps a stable canonical configuration model and maps it onto the
installed VTracer engine(s) at runtime. Two engines can coexist:

- **VTracer 1.0 native CLI** (preferred). Discovered, in order, from the
  `RASTER2SVG_VTRACER_BIN` environment variable, `vtracer` on `PATH`, and
  `.venv/Bin/vtracer.exe`. It supports the full option surface (`simplify`,
  `palette`, `max_colors`, `optimize`, binary/adaptive thresholding,
  `watershed`) but not the 0.6.x smoothing thresholds.
- **VTracer 0.6.x Python package**. Supports the smoothing thresholds, but not
  the 1.0-only options above.

Every conversion uses the first installed engine that honours the requested
settings (1.0 CLI first), so both option families work side by side — e.g.
`--simplify` runs on the 1.0 CLI while `--corner-threshold` transparently
falls back to the 0.6.x Python engine. An option that *no* installed engine
supports fails with a clear `UnsupportedFeatureError` (exit code 2) — it is
never silently ignored.

| Option family | VTracer 1.0 (CLI) | VTracer 0.6.x (Python) |
| --- | --- | --- |
| `clustering`, `hierarchical`, `mode`, `filter_speckle`, `color_precision`, `layer_difference`, `path_precision` | yes | yes |
| `corner_threshold`, `length_threshold`, `max_iterations`, `splice_threshold` | no | yes |
| `simplify`, `palette`, `max_colors`, `optimize`, binary/adaptive thresholding, `watershed` | yes | no |

Run `raster2svg engine capabilities` to see exactly which engines are installed
and what each supports.

> **`max_colors` vs `color_precision`** — these sound alike but do different
> things:
>
> - **`color_precision`** (supported) = *bits per RGB channel* — how finely
>   colors are quantized. `4` ≈ 16 levels per channel, `8` = full 256.
>   Lowering it reduces color variety, but does not cap the palette size.
> - **`max_colors`** (VTracer 1.0 CLI) = a *hard cap on the total number of
>   distinct colors* in the output (palette quantization to N colors, like an
>   N-color GIF).
>
> So `color_precision` is not a substitute for `max_colors`: it changes color
> granularity, not the maximum palette count.
>
> **`pre_max_colors`** (preprocessor-side) applies the same N-color palette cap
> in Pillow *before* tracing, so it works on any VTracer version — including
> setups where only the 0.6.x Python engine is installed and `max_colors` is
> unavailable.

Presets (`bw`, `photo`, `poster`, `clip-art`, `line-art`, `pixel-art`,
`line-art-inverted`, `silhouette-inverted`, and more — 14 built-ins total) are
application-level bundles of canonical `[conversion]`, `[preprocess]`, and
`[postprocess]` settings; VTracer exposes no native preset API, so they map
onto the shared option surface. See [docs/presets.md](docs/presets.md).

## Documentation

- [`docs/configuration.md`](docs/configuration.md) — every config key, the
  five-layer precedence, and the user-level config file.
- [`docs/cli.md`](docs/cli.md) — all commands and flags.
- [`docs/presets.md`](docs/presets.md) — built-in presets and custom presets.
- [`docs/architecture.md`](docs/architecture.md) — how the core, config, and
  engine-adapter layers fit together.
- [`raster2svg_web_prd.md`](raster2svg_web_prd.md) — the web interface spec
  (the `raster2svg web` command).
- [`examples/`](examples/) — ready-to-copy sample configs.

## Development

```powershell
.venv\Scripts\pytest
.venv\Scripts\ruff check --fix .
.venv\Scripts\mypy
```

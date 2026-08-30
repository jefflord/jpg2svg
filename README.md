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
| `--contrast F` / `--brightness F` | Adjust tone (1.0 = unchanged) |
| `--sharpen` / `--no-sharpen` | Conservative unsharp mask |
| `--pre-max-colors N` | Cap the raster to at most N colors (1-256) before tracing; no dithering (flat regions) |

The same settings can be placed in a config file under `[preprocess]`; CLI
flags override file values.

## Engine feature support

`raster2svg` keeps a stable canonical configuration model and maps it onto the
installed VTracer API at runtime. Settings the installed VTracer does not expose
are still accepted by the parser but produce a clear "unsupported" error instead
of being silently ignored.

With vtracer 0.6.15:

| Supported | Not exposed by this engine version |
| --- | --- |
| `clustering` (color/binary), `hierarchical`, `mode` (pixel/polygon/spline), `filter_speckle`, `color_precision`, `layer_difference`, `corner_threshold`, `length_threshold`, `max_iterations`, `splice_threshold`, `path_precision` | `simplify`, `palette`, `max_colors`, `optimize`, binary/adaptive thresholding, `watershed` |

Any "Not exposed" option you request (on the CLI or in a config file) is
accepted by the parser but fails with a clear `UnsupportedFeatureError` (exit
code 2) — it is never silently ignored. Run `raster2svg engine capabilities`
to see exactly what your installed engine supports.

> **`max_colors` vs `color_precision`** — these sound alike but do different
> things:
>
> - **`color_precision`** (supported) = *bits per RGB channel* — how finely
>   colors are quantized. `4` ≈ 16 levels per channel, `8` = full 256.
>   Lowering it reduces color variety, but does not cap the palette size.
> - **`max_colors`** (not exposed here) = a *hard cap on the total number of
>   distinct colors* in the output (palette quantization to N colors, like an
>   N-color GIF). This VTracer build has no such parameter.
>
> So `color_precision` is not a substitute for `max_colors`: it changes color
> granularity, not the maximum palette count.
>
> **`pre_max_colors`** (supported, preprocessor-side) applies the same N-color
> palette cap in Pillow *before* tracing, so it works on any VTracer version.
> Use `--pre-max-colors N` as the available equivalent until VTracer 1.0's
> native `max_colors` lands.

Presets (`bw`, `photo`, `poster`) are application-level bundles of canonical
settings; vtracer 0.6.x exposes no native preset API.

## Documentation

- [`docs/configuration.md`](docs/configuration.md) — every config key, the
  five-layer precedence, and the user-level config file.
- [`docs/cli.md`](docs/cli.md) — all commands and flags.
- [`docs/presets.md`](docs/presets.md) — built-in presets and custom presets.
- [`docs/architecture.md`](docs/architecture.md) — how the core, config, and
  engine-adapter layers fit together.
- [`examples/`](examples/) — ready-to-copy sample configs.

## Development

```powershell
.venv\Scripts\pytest
.venv\Scripts\ruff check --fix .
.venv\Scripts\mypy
```

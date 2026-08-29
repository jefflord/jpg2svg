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
raster2svg engine capabilities
raster2svg --help
```

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

Presets (`bw`, `photo`, `poster`) are application-level bundles of canonical
settings; vtracer 0.6.x exposes no native preset API.

## Development

```powershell
.venv\Scripts\pytest
.venv\Scripts\ruff check --fix .
.venv\Scripts\mypy
```
